import asyncio
from datetime import datetime, timedelta, timezone
import httpx
from model.api import main
from model.api.store import RecordStore


def client():
    # ASGITransport avoids the blocking thread portal used by TestClient on Python 3.14.
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test")


def observation(value=8, synthetic=True):
    return {"service": "water", "value": value, "observed_at": datetime.now(timezone.utc).isoformat(),
            "source_label": "Test inspection log", "notes": "Measured service availability after the repair", "synthetic": synthetic, "consent": not synthetic}


async def create(c, synthetic=True, pocket_id="NS-0766"):
    response = await c.post("/grievances", json={"text": "Paani nahi aa raha, water supply stopped", "pocket_id": pocket_id, "language": "en", "synthetic": synthetic, "consent": not synthetic})
    assert response.status_code == 200, response.text
    return response.json()


async def act(c, report, action, **extra):
    return await c.post(f"/grievances/{report['complaint_id']}/action", json={"action": action, "officer": "Ward reviewer", "notes": "Action recorded in inspection log", **extra})


def test_core_api_contracts(api_store):
    async def run():
        async with client() as c:
            assert (await c.get("/health")).json()["status"] == "ok"
            pockets = (await c.get("/pockets")).json()
            assert pockets["total"] == len(pockets["items"])
            detail = (await c.get("/pockets/NS-0001")).json()
            assert detail["priority_reasons"]
            cards = (await c.get("/models/cards")).json()
            assert cards["synthetic"] is True
            assert cards["cards"]["priority"]["metrics"]["r2"] is not None
            assert cards["cards"]["cost"]["source"] == "cost_metrics.json"
            assert "shap_reasons" not in detail
            record = (await c.get("/service/NS-0001/assurance")).json()
            assert "failure_probability_90d" not in record["services"]["water"]
            assert "trend" not in record
            assert (await c.post("/priority/score", json={"features": {"flood_risk_score": 90}})).status_code == 200
            assert (await c.post("/cost/estimate", json={})).status_code == 200
            assert (await c.post("/feasibility/simulate", json={"land_area_sqm": 5000, "fsi": 2.5, "eligible_households": 200})).status_code == 200
            summary = (await c.get("/stats/summary")).json()
            assert summary["resident_verified_closures"] == 0
            assert summary["median_response_days"] is None
            assert "projected_cost_saved_inr" not in summary
            assert len(summary["wards"]) > 0
    asyncio.run(run())


def test_persistent_private_receipts_and_invalid_transitions(api_store, monkeypatch):
    async def run():
        async with client() as c:
            report = await create(c)
            key = {"X-Receipt-Token": report["receipt_token"]}
            path = f"/grievances/{report['complaint_id']}"
            assert (await c.get(path)).status_code == 404
            assert (await c.get(path, headers={"X-Receipt-Token": "wrong"})).status_code == 404
            assert (await act(c, report, "start")).status_code == 409
            # Reopen the database as a restarted server would.
            monkeypatch.setattr(main, "STORE", RecordStore(api_store.path))
            assert (await c.get(path, headers=key)).json()["text"] == report["text"]
            assert "receipt_token" not in (await c.get("/grievances")).text
            assert (await act(c, report, "assign", department="Water supply")).status_code == 200
            assert (await act(c, report, "start")).status_code == 200
            assert (await act(c, report, "complete")).status_code == 422
            assert (await c.post(path + "/confirm", headers=key, json={"resolved": True, "notes": "Not yet repaired"})).status_code == 409
    asyncio.run(run())


def test_resident_confirmation_updates_service_and_dispute_reopens(api_store):
    async def run():
        async with client() as c:
            report = await create(c)
            original = (await c.get("/service/NS-0766/assurance")).json()["services"]["water"]["value"]
            assert (await act(c, report, "assign")).status_code == 200
            value = 23 if original != 23 else 22
            assert (await act(c, report, "complete", observation=observation(value))).status_code == 200
            record = (await c.get("/service/NS-0766/assurance")).json()
            assert record["services"]["water"]["value"] == original
            key = {"X-Receipt-Token": report["receipt_token"]}
            path = f"/grievances/{report['complaint_id']}"
            tracked = (await c.get(path, headers=key)).json()
            assert tracked["repair_observation"]["value"] == value
            assert (await c.post(path + "/confirm", headers=key, json={"resolved": False, "notes": "Water is still not available"})).json()["status"] == "reopened"
            assert (await c.get("/service/NS-0766/assurance")).json()["services"]["water"]["value"] == original
            rejected = api_store.observations()[0]
            assert (await c.post(f"/observations/{rejected['observation_id']}/verify", json={"reviewer": "Reviewer", "notes": "Disputed evidence"})).status_code == 409
            assert (await act(c, report, "start")).status_code == 200
            assert (await act(c, report, "complete", observation=observation(value))).status_code == 200
            assert (await c.post(path + "/confirm", headers=key, json={"resolved": True, "notes": "Water availability improved after the repair"})).json()["status"] == "resolved"
            record = (await c.get("/service/NS-0766/assurance")).json()
            assert record["services"]["water"]["value"] == value
            assert record["services"]["water"]["verification"] == "resident_confirmed"
            assert (await c.get("/stats/summary")).json()["resident_verified_closures"] == 1
            assert (await act(c, report, "complete", observation=observation())).status_code == 409
    asyncio.run(run())


def test_consent_source_ranges_and_demo_exclusion(api_store):
    async def run():
        async with client() as c:
            assert (await c.post("/grievances", json={"text": "Water unavailable", "pocket_id": "NS-0766", "synthetic": False})).status_code == 422
            bad = observation(); bad["value"] = 25
            assert (await c.post("/service/NS-0766/observations", json=bad)).status_code == 422
            bad = observation(); bad["observed_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            assert (await c.post("/service/NS-0766/observations", json=bad)).status_code == 422
            assert (await c.post("/service/NS-0766/observations", json=observation())).status_code == 200
            real = (await c.post("/service/NS-0766/observations", json=observation(8, False))).json()
            assert (await c.post(f"/observations/{real['observation_id']}/verify", json={"reviewer": "Independent field reviewer", "notes": "Checked the measurement and source log"})).status_code == 200
            evidence = (await c.get("/pilot/evidence")).json()
            assert evidence["metrics"]["real_observations"] == 1
            assert evidence["metrics"]["field_verified_observations"] == 1
            assert evidence["metrics"]["median_seconds_saved"] is None
            test = {"participant_ref": "P-001", "task": "prepare_brief", "completed": True, "feedback": "Could find the action quickly", "baseline_seconds": 120, "app_seconds": 60, "synthetic": True}
            assert (await c.post("/pilot/evaluations", json=test)).status_code == 200
            assert (await c.get("/pilot/evidence")).json()["metrics"]["real_evaluations"] == 0
            test.update(synthetic=False, consent=True)
            assert (await c.post("/pilot/evaluations", json=test)).status_code == 200
            metrics = (await c.get("/pilot/evidence")).json()["metrics"]
            assert metrics["paired_sample_size"] == 1
            assert metrics["median_seconds_saved"] == 60
    asyncio.run(run())


def test_officer_authorization_and_sla_calculation(api_store, monkeypatch):
    async def run():
        async with client() as c:
            report = await create(c)
            api_store.change_complaint(report["complaint_id"], lambda row, db: {**row, "due_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()})
            assert (await c.get("/stats/summary")).json()["sla_breaches"] == 1
            monkeypatch.setenv("NAGARSEVA_OFFICER_KEY", "test-access-key")
            assert (await c.get("/grievances")).status_code == 401
            assert (await act(c, report, "assign")).status_code == 401
            assert (await c.get("/grievances", headers={"X-Officer-Key": "test-access-key"})).json()["items"][0]["sla_breached"] is True
            monkeypatch.delenv("NAGARSEVA_OFFICER_KEY")
            monkeypatch.setenv("NAGARSEVA_MODE", "pilot")
            assert (await c.get("/pilot/evidence")).status_code == 503
    asyncio.run(run())


def test_approved_location_and_commitment_are_source_labelled(api_store):
    async def run():
        async with client() as c:
            location = {"pocket_id": "PILOT-TEST", "city": "Mumbai", "ward": "Test ward", "lat": 19.01, "lon": 72.91, "area_sqm": 2000, "households": 20, "population": 80,
                        "source_label": "Approved test fixture; not a real location", "source_url": "https://example.org/fixture", "licence": "Test fixture licence", "approved_by": "Fixture reviewer", "consent": True}
            assert (await c.post("/pilot/locations", json=location)).status_code == 200
            assert (await c.post("/pilot/locations", json=location)).status_code == 409
            detail = (await c.get("/pockets/PILOT-TEST")).json()
            assert detail["synthetic"] is False
            assert detail["priority_score"] is None
            assert detail["tier"] == "Unassessed"
            assert detail["intervention"]["top_options"] == []
            assert all(s["status"] == "unknown" for s in detail["service_record"]["services"].values())
            commitment = {"service": "water", "target": 8, "standard_source": "Fixture project commitment", "department": "Water supply", "approved_by": "Fixture reviewer", "source_url": "https://example.org/commitment", "synthetic": False}
            assert (await c.post("/service/PILOT-TEST/commitment", json=commitment)).status_code == 200
            record = (await c.get("/service/PILOT-TEST/assurance")).json()
            assert record["services"]["water"]["target"] == 8
            assert record["services"]["water"]["standard_synthetic"] is False
            assert record["services"]["water"]["score"] is None
    asyncio.run(run())


def test_current_eligibility_requires_declared_base_conditions(api_store):
    async def run():
        async with client() as c:
            base = {"monthly_income_inr": 18000, "family_size": 4, "urban_resident": True, "owns_pucca_house": False, "received_housing_benefit_last_20_years": False, "owns_buildable_land": True}
            result = (await c.post("/eligibility/check", json=base)).json()
            assert "PMAY-U 2.0 — BLC" in result["pathways_to_verify"]
            assert result["policy_version"] == "PMAY-U 2.0"
            assert not any("CLSS" in scheme for scheme in result["eligible_schemes"])
            assert (await c.post("/eligibility/check", json={**base, "owns_pucca_house": True})).json()["eligible_schemes"] == []
            assert (await c.post("/eligibility/check", json={"monthly_income_inr": 18000, "family_size": 4})).json()["screening_status"] == "needs_information"
    asyncio.run(run())


def test_officer_review_removes_the_previous_category_confidence(api_store):
    async def run():
        async with client() as c:
            report = await create(c)
            corrected = "waste" if report["category"] != "waste" else "water"
            response = await act(c, report, "assign", category=corrected, urgency="urgent", department="Reviewed service team")
            assert response.status_code == 200
            reviewed = response.json()
            assert reviewed["confidence"] is None
            assert reviewed["classification_method"] == "officer_review"
            assert reviewed["history"][-1]["category"] == corrected
            assert reviewed["history"][-1]["department"] == "Reviewed service team"
            assert reviewed["history"][-1]["due_at"] == reviewed["due_at"]
    asyncio.run(run())


def test_pilot_timings_exclude_failed_tasks_and_classification_trials(api_store):
    async def run():
        async with client() as c:
            base = {"participant_ref": "P-TEST", "task": "prepare_brief", "completed": True, "feedback": "Anonymous test fixture", "baseline_seconds": 120, "app_seconds": 60, "synthetic": False, "consent": True}
            assert (await c.post("/pilot/evaluations", json=base)).status_code == 200
            assert (await c.post("/pilot/evaluations", json={**base, "completed": False, "baseline_seconds": 2000, "app_seconds": 1})).status_code == 200
            trial = {**base, "task": "classify_complaint", "language": "mr", "expected_category": "water", "predicted_category": "waste", "baseline_seconds": 1000, "app_seconds": 1}
            assert (await c.post("/pilot/evaluations", json=trial)).status_code == 200
            assert (await c.post("/pilot/evaluations", json={**trial, "predicted_category": "invented-category"})).status_code == 422
            assert (await c.post("/pilot/evaluations", json={**trial, "expected_category": None})).status_code == 422
            metrics = (await c.get("/pilot/evidence")).json()["metrics"]
            assert metrics["real_evaluations"] == 3
            assert metrics["usability_sample_size"] == 2
            assert metrics["completion_rate"] == .5
            assert metrics["paired_sample_size"] == 1
            assert metrics["median_seconds_saved"] == 60
            assert metrics["classification_by_language"]["mr"] == {"sample_size": 1, "accuracy": 0}
    asyncio.run(run())
