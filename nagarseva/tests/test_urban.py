"""Hand-worked planning examples and persistent assurance state transitions."""
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from model.api.urban import create_app
from model.src.urban_planning import DEFAULT_WEIGHTS, compare_scenarios, dataset, network_access, prioritize, score


@pytest.mark.parametrize("fixture", json.loads((Path(__file__).resolve().parents[1] / 'shared/urban-validation-cases.json').read_text()), ids=lambda row: row['id'])
def test_shared_python_browser_fixtures(fixture):
    result = score(fixture['indicators'], fixture['weights'])
    for field in ['score', 'lower', 'upper', 'coverage_pct']:
        assert result[field] == fixture[field]


def assumptions(households=10):
    return {"households": households, "contingency_pct": 10, "temporary_rent_per_month": 20,
            "annual_maintenance_per_household": 12, "include_relocation": False, "relocation_reason": "",
            "options": [{"kind": kind, "unit_cost_inr": 100, "shared_works_inr": 50, "months": 6,
                         "temporary_months": 1, "disrupted_share": .2, "assumed_service_coverage_pct": 80}
                        for kind in ["upgrade", "redevelop"]]}


def test_proposal_example_is_65_not_65_point_5():
    actual = score(dict(zip(DEFAULT_WEIGHTS, [80, 70, 60, 50, 40])))
    assert actual["score"] == 65
    assert actual["contributions"] == {"water": 24, "sanitation": 17.5, "housing": 12, "access": 7.5, "risk": 4}


def test_missing_values_produce_bounds_and_do_not_get_a_rank():
    report = prioritize(dataset()["clusters"])
    missing = next(item for item in report["items"] if item["id"] == "US-E")
    assert missing["score"] is missing["rank"] is None
    assert missing["lower"] == 32.25
    assert missing["upper"] == 77.25
    assert missing["coverage_pct"] == 55
    assert [row["id"] for row in report["items"][:4]] == ["US-A", "US-C", "US-B", "US-D"]
    assert report["rank_correlation"] == .8


@pytest.mark.parametrize("weights", [{key: 0 for key in DEFAULT_WEIGHTS}, {**DEFAULT_WEIGHTS, "water": -1}, {"water": 1}, {**DEFAULT_WEIGHTS, "risk": float("nan")}])
def test_invalid_weights_are_rejected(weights):
    with pytest.raises(ValueError):
        prioritize(dataset()["clusters"], weights)


def test_rescaling_weights_and_equal_weights_have_expected_results():
    a = prioritize(dataset()["clusters"], {key: value * 100 for key, value in DEFAULT_WEIGHTS.items()})
    assert a["items"][0]["score"] == 65
    b = prioritize(dataset()["clusters"], {key: 1 for key in DEFAULT_WEIGHTS})
    assert b["items"][0]["id"] == "US-C"
    assert b["rank_correlation"] == 1
    assert score({key: 50 for key in DEFAULT_WEIGHTS})["score"] == 50


def test_equal_scores_have_shared_rank_and_undefined_constant_correlation():
    items = deepcopy(dataset()["clusters"][:2])
    for item in items:
        item["indicators"] = {key: 50 for key in DEFAULT_WEIGHTS}
    result = prioritize(items)
    assert [row["rank"] for row in result["items"]] == [1, 1]
    assert result["rank_correlation"] is None


def test_hypothetical_cost_is_hand_calculated_and_coverage_is_an_assumption():
    comparison = compare_scenarios(dataset(), "US-A", assumptions())
    assert comparison["assumptions"] == assumptions()
    result = comparison["options"][0]
    assert result["construction_and_shared_inr"] == 1050
    assert result["temporary_support_inr"] == 40
    assert result["total_cost_inr"] == 1199
    assert result["annual_maintenance_inr"] == 120
    assert result["disrupted_households"] == 2
    assert result["assumed_service_coverage_pct"] == 80
    assert all(row["change_m"] == 0 for row in result["access"])


def test_unknown_households_are_not_replaced_with_zero():
    with pytest.raises(ValueError):
        compare_scenarios(dataset(), "US-E", assumptions(None))


def test_relocation_requires_explicit_inclusion_and_a_stated_reason():
    inputs = assumptions()
    inputs["options"].append({**inputs["options"][0], "kind": "relocate"})
    with pytest.raises(ValueError):
        compare_scenarios(dataset(), "US-A", inputs)
    inputs["include_relocation"] = True
    with pytest.raises(ValueError):
        compare_scenarios(dataset(), "US-A", inputs)
    inputs["relocation_reason"] = "Hypothetical hazard-avoidance comparison, not a relocation recommendation."
    result = compare_scenarios(dataset(), "US-A", inputs)
    assert result["options"][2]["access"][3]["change_m"] > 1000


def test_disconnected_network_keeps_unreachable_distances_missing():
    data = deepcopy(dataset())
    data["network"]["edges"] = []
    result = network_access(data, "n00")
    assert all(row["distance_m"] is None for row in result[:3])
    assert result[3]["distance_m"] == 0


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("NAGARSEVA_OFFICER_KEY", raising=False)
    monkeypatch.setenv("NAGARSEVA_MODE", "demo")
    return TestClient(create_app(tmp_path / "urban.sqlite3"))


def plan(client):
    response = client.post("/urban/works", json={"cluster_id": "US-A", "title": "Demo water improvement", "service": "water",
                          "target": 6, "due_date": "2026-10-01", "actor": "Contractor"})
    assert response.status_code == 200, response.text
    return response.json()


def act(client, work_id, action, **extra):
    return client.post(f"/urban/works/{work_id}/action", json={"action": action, "actor": "Contractor", "notes": "Recorded demo work update", **extra})


def attach(client, work_id, text="Demonstration inspection record"):
    response = client.post(f"/urban/works/{work_id}/evidence", json={"filename": "../inspection.txt", "content_type": "text/plain",
                           "content_base64": base64.b64encode(text.encode()).decode(), "actor": "Inspector", "notes": "Synthetic inspection document"})
    assert response.status_code == 200, response.text
    return response.json()


def verification(evidence_id, **overrides):
    return {"actor": "Reviewer", "notes": "Independent demonstration review", "evidence_id": evidence_id,
            "measured_value": 6, "observed_at": datetime.now(timezone.utc).isoformat(), "functioning_confirmed": True, **overrides}


def test_complete_is_not_verified_and_uploaded_bytes_round_trip(client):
    work = plan(client)
    assert act(client, work["id"], "complete").status_code == 422
    assert act(client, work["id"], "start").status_code == 200
    completed = act(client, work["id"], "complete").json()
    assert completed["status"] == "completed" and completed["verification"] == "unverified"
    proof = attach(client, work["id"])
    assert proof["filename"] == "inspection.txt"
    assert "content_base64" not in proof
    response = client.get(f"/urban/evidence/{proof['id']}/content")
    assert response.content == b"Demonstration inspection record"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert act(client, work["id"], "verify", **verification(proof["id"], measured_value=5)).status_code == 422
    assert act(client, work["id"], "verify", **verification(proof["id"], actor="Inspector")).status_code == 422
    verified = act(client, work["id"], "verify", **verification(proof["id"]))
    assert verified.status_code == 200, verified.text
    assert verified.json()["verification"] == "verified"
    state = client.get("/urban/state").json()
    assert "content_base64" not in state["evidence"][0]


def test_complaint_disputes_verification_and_response_does_not_restore_it(client):
    work = plan(client)
    act(client, work["id"], "start")
    act(client, work["id"], "complete")
    evidence = attach(client, work["id"])
    assert act(client, work["id"], "verify", **verification(evidence["id"])).status_code == 200
    issue = client.post("/urban/complaints", json={"work_id": work["id"], "text": "Water service stopped again in this demo."}).json()
    assert client.get("/urban/state").json()["works"][0]["verification"] == "disputed"
    assert act(client, work["id"], "verify", **verification(evidence["id"])).status_code == 422
    assert client.post(f"/urban/complaints/{issue['id']}/resolve", json={"actor": "Officer", "notes": "Demo repair response recorded"}).status_code == 200
    assert client.get("/urban/state").json()["works"][0]["verification"] == "disputed"
    assert act(client, work["id"], "verify", **verification(evidence["id"])).status_code == 422
    fresh = attach(client, work["id"], "Fresh inspection following the reported interruption")
    assert act(client, work["id"], "verify", **verification(fresh["id"])).status_code == 200


def test_evidence_cannot_be_reused_for_another_work_and_future_inspection_is_rejected(client):
    a, b = plan(client), plan(client)
    for work in [a, b]:
        act(client, work["id"], "start")
        act(client, work["id"], "complete")
    evidence = attach(client, a["id"])
    assert act(client, b["id"], "verify", **verification(evidence["id"])).status_code == 422
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    assert act(client, a["id"], "verify", **verification(evidence["id"], observed_at=future)).status_code == 422


def test_authentication_applies_to_state_mutations_and_file_download(client, monkeypatch):
    work = plan(client)
    evidence = attach(client, work["id"])
    monkeypatch.setenv("NAGARSEVA_OFFICER_KEY", "test-only-officer-key")
    assert client.get("/urban/state").status_code == 401
    assert act(client, work["id"], "start").status_code == 401
    assert client.get(f"/urban/evidence/{evidence['id']}/content").status_code == 401
    assert client.get("/urban/state", headers={"X-Officer-Key": "test-only-officer-key"}).status_code == 200


def test_records_persist_when_reopening_the_database(client):
    original = plan(client)
    reopened = TestClient(create_app(client.app.state.store.path))
    assert reopened.get("/urban/state").json()["works"][0]["id"] == original["id"]


def test_invalid_file_signature_does_not_create_evidence(client):
    work = plan(client)
    result = client.post(f"/urban/works/{work['id']}/evidence", json={"filename": "fake.png", "content_type": "image/png",
                         "content_base64": base64.b64encode(b'not an image').decode(), "actor": "Inspector", "notes": "Invalid demonstration attachment"})
    assert result.status_code == 422
    assert client.get("/urban/state").json()["evidence"] == []
