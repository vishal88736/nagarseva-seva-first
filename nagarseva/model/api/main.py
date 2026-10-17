"""FastAPI service for the NagarSeva decision-support demo."""

from __future__ import annotations

import logging
import json
from contextlib import asynccontextmanager
import os
from pathlib import Path
import secrets
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "model" / "src"))

from model.src import features  # noqa: E402
from model.src.explain import priority_reasons  # noqa: E402
from model.src.feasibility import FeasibilityInput, sensitivity, simulate  # noqa: E402
from model.src.optimizer import optimise  # noqa: E402
from model.src.service_records import SERVICES, service_record, utc_now  # noqa: E402
from model.src.eligibility import screen  # noqa: E402
from model.src.public_context import ForecastService  # noqa: E402
from .store import RecordStore  # noqa: E402
from .urban import create_router as urban_router  # noqa: E402
from .schemas import (  # noqa: E402
    CostRequest, EligibilityRequest, FeasibilityRequest, GrievanceRequest,
    InterventionRequest, OptimizeRequest, PriorityRequest, ComplaintAction,
    ResidentConfirmation, ObservationRequest, ObservationVerification, PilotEvaluation,
    ServiceCommitmentRequest, PilotLocationRequest,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("nagarseva.api")

@asynccontextmanager
async def lifespan(application: FastAPI):
    _load()
    yield


app = FastAPI(lifespan=lifespan, title="NagarSeva API", version="0.3.0", description="Source-labelled housing planning, public context and resident-verified service assurance.")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("NAGARSEVA_CORS_ORIGINS", "http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173,http://127.0.0.1:4173").split(","), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Officer-Key", "X-Receipt-Token"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

MODELS: dict[str, Any] = {}
TABLES: dict[str, pd.DataFrame] = {}
STORE = RecordStore(os.getenv("NAGARSEVA_DB_PATH", str(ROOT / "model/data/local/nagarseva.sqlite3")))
FORECAST = ForecastService()


def officer_access(x_officer_key: str | None = Header(None)) -> None:
    expected = os.getenv("NAGARSEVA_OFFICER_KEY")
    if expected and not secrets.compare_digest(expected, x_officer_key or ""):
        raise HTTPException(401, "Officer access key required")
    if not expected and os.getenv("NAGARSEVA_MODE", "demo") != "demo":
        raise HTTPException(503, "Configure officer access before enabling a pilot")


app.include_router(urban_router(lambda: STORE, officer_access))


def _complaint_view(record: dict) -> dict:
    now = datetime.now(timezone.utc)
    closed = record["status"] == "resolved"
    overdue = not closed and now > datetime.fromisoformat(record["due_at"])
    observation = next((o for o in STORE.observations(record["pocket_id"]) if o["observation_id"] == record["pending_observation_id"]), None)
    return {**record, "repair_observation": observation, "sla_breached": overdue, "escalation_required": overdue and record["status"] != "awaiting_confirmation"}


def _planning_frame() -> pd.DataFrame:
    frame = TABLES.get("joined", pd.DataFrame()).copy()
    if not frame.empty:
        frame["synthetic"] = True
        frame["source_label"] = "Seeded synthetic planning data"
    locations = STORE.locations()
    if locations:
        frame = pd.concat([frame, pd.DataFrame(locations)], ignore_index=True)
    return frame


def _validated_observation(payload: ObservationRequest, pocket_id: str, verification: str = "reported", complaint_id: str | None = None) -> dict:
    if payload.value > SERVICES[payload.service]["ceiling"] or (payload.service == "health" and payload.value not in {0, 1}):
        raise HTTPException(422, "Measurement is outside the valid range for this service")
    if not payload.synthetic and not payload.consent:
        raise HTTPException(422, "Consent is required for a real field observation")
    now = utc_now()
    return {**payload.model_dump(mode="json"), "observation_id": f"OBS-{secrets.token_hex(6).upper()}", "pocket_id": pocket_id,
            "complaint_id": complaint_id, "unit": SERVICES[payload.service]["unit"], "verification": verification, "created_at": now,
            "history": [{"at": now, "action": "recorded", "actor": "officer", "notes": payload.notes}]}


def _load() -> None:
    """Load models once and use safe heuristic operation if artifacts are absent."""
    for name, path in {"priority": "priority_model.joblib", "intervention": "intervention_model.joblib", "service": "service_gap_model.joblib", "cost": "cost_model.joblib", "nlp": "grievance_model.joblib"}.items():
        try:
            MODELS[name] = joblib.load(features.ARTIFACTS / path)
        except Exception as exc:
            logger.warning("Artifact %s unavailable: %s; using fallback", name, exc)
    try:
        for name in ["slum_pockets", "service_access", "grievances", "redevelopment_projects", "households_sample"]:
            TABLES[name] = features.read_table(f"{name}.csv")
        TABLES["joined"] = TABLES["slum_pockets"].merge(TABLES["service_access"], on="pocket_id", how="left")
    except Exception as exc:
        logger.error("Data unavailable: %s", exc)
    logger.info("NagarSeva loaded %s models and %s tables", len(MODELS), len(TABLES))


def _row(pocket_id: str) -> pd.Series:
    frame = _planning_frame()
    if frame.empty:
        raise HTTPException(503, "Planning data is unavailable")
    found = frame[frame.pocket_id == pocket_id]
    if found.empty:
        raise HTTPException(status_code=404, detail=f"Pocket {pocket_id} not found")
    return found.iloc[0]


def _score(row: pd.Series) -> float:
    if row.get("synthetic", True) is False or row.get("synthetic", True) == False:
        value = row.get("approved_priority_score")
        return float(value) if value is not None and pd.notna(value) else float("nan")
    model = MODELS.get("priority")
    if model:
        values = features.numeric_frame(pd.DataFrame([row]), model["features"])
        return float(np.clip(model["model"].predict(values)[0], 0, 100))
    reference = features.numeric_frame(pd.DataFrame([row]), features.PRIORITY_FEATURES)
    return float(features.policy_priority(reference).iloc[0])


def _scores(frame: pd.DataFrame) -> np.ndarray:
    """Vectorised score path for map and summary endpoints."""
    model = MODELS.get("priority")
    if model:
        values = features.numeric_frame(frame, model["features"])
        scores = np.clip(model["model"].predict(values), 0, 100)
    else:
        scores = features.policy_priority(frame).to_numpy()
    if "synthetic" in frame:
        pilot = ~frame.synthetic.fillna(True).astype(bool).to_numpy()
        approved = pd.to_numeric(frame.get("approved_priority_score", pd.Series(np.nan, index=frame.index)), errors="coerce").to_numpy()
        scores[pilot] = approved[pilot]
    return scores


def _intervention(row: pd.Series) -> dict[str, Any]:
    if not row.get("synthetic", True):
        return {"top_options": [], "reasons": ["Approved pilot location. Intervention options require field risk, tenure and resident consultation evidence; the synthetic-trained recommender is not applied."]}
    labels = ["in_situ_SRA", "upgrading", "relocation", "rental_housing"]
    model = MODELS.get("intervention")
    if model:
        values = features.numeric_frame(pd.DataFrame([row]), model["features"])
        estimator = model["model"]
        probs = estimator.predict_proba(values)[0]
        classes = list(estimator.classes_)
        options = sorted(({"type": cls, "probability": round(float(prob), 3)} for cls, prob in zip(classes, probs)), key=lambda x: x["probability"], reverse=True)[:2]
    else:
        choices = [("relocation", .42 if row.get("flood_risk_score", 0) > 80 else .14), ("in_situ_SRA", .49 if row.get("tenure_security_score", 0) > 50 else .22), ("upgrading", .44), ("rental_housing", .18)]
        total = sum(value for _, value in choices)
        options = [{"type": key, "probability": round(value / total, 3)} for key, value in sorted(choices, key=lambda x: x[1], reverse=True)[:2]]
    reasons = []
    if row.get("land_ownership") in {"forest", "CRZ"} or row.get("flood_risk_score", 0) > 80:
        reasons.append("high hazard or restricted land makes a safer alternative important")
    if row.get("tenure_security_score", 0) > 55:
        reasons.append("stronger tenure signal supports in-situ investment")
    if row.get("density_per_ha", 0) > 500:
        reasons.append("dense settlement benefits from phased service upgrading")
    reasons.append("final selection requires resident consultation and statutory review")
    return {"top_options": options, "reasons": reasons}


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok" if "joined" in TABLES else "degraded", "synthetic_demo": True, "mode": os.getenv("NAGARSEVA_MODE", "demo"), "officer_auth_required": bool(os.getenv("NAGARSEVA_OFFICER_KEY")), "models_loaded": sorted(MODELS), "tables_loaded": sorted(TABLES)}


@app.get("/models/cards")
def model_cards() -> dict:
    cards = {}
    for name, artifact, filename in [("priority", "priority", "priority_metrics.json"), ("intervention", "intervention", "priority_metrics.json"), ("grievance", "nlp", "grievance_metrics.json"), ("cost", "cost", "cost_metrics.json")]:
        path = features.ARTIFACTS / filename
        try:
            metrics = json.loads(path.read_text())
        except (OSError, ValueError):
            metrics = {}
        cards[name] = {"loaded": artifact in MODELS, "source": filename if metrics else None, "metrics": metrics}
    return {"cards": cards, "synthetic": True, "scope": "Benchmarks from saved synthetic training artifacts. Independent field validation remains required."}


@app.get("/sources")
def public_sources() -> dict:
    return json.loads((ROOT / "shared/public-sources.json").read_text())


@app.get("/context/{pocket_id}/weather")
async def weather_context(pocket_id: str) -> dict:
    row = _row(pocket_id)
    lat, lon = row.get("lat"), row.get("lon")
    if lat is None or lon is None or not np.isfinite(lat) or not np.isfinite(lon):
        raise HTTPException(422, "Location coordinates are required for area weather context")
    result = await FORECAST.get(float(lat), float(lon), STORE, enabled=os.getenv("NAGARSEVA_WEATHER_ENABLED", "1") == "1")
    return {**result, "pocket_id": pocket_id, "location_synthetic": bool(row.get("synthetic", True))}


@app.get("/pockets")
def pockets(city: str | None = None, ward: str | None = None, tier: str | None = None, bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat")) -> dict[str, Any]:
    frame = _planning_frame()
    if frame.empty:
        return {"items": [], "total": 0}
    frame["priority_score"] = _scores(frame)
    frame["tier"] = frame.priority_score.map(features.tier)
    if city: frame = frame[frame.city.str.lower() == city.lower()]
    if ward: frame = frame[frame.ward.str.lower() == ward.lower()]
    if tier: frame = frame[frame.tier.str.lower() == tier.lower()]
    if bbox:
        try:
            min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(","))
            frame = frame[frame.lon.between(min_lon, max_lon) & frame.lat.between(min_lat, max_lat)]
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="bbox must be minLon,minLat,maxLon,maxLat") from exc
    frame = frame.sort_values("priority_score", ascending=False)
    items = frame.replace({np.nan: None}).to_dict("records")
    return {"items": items, "total": len(frame), "synthetic": True}


@app.get("/pockets/{pocket_id}")
def pocket_detail(pocket_id: str) -> dict[str, Any]:
    row = _row(pocket_id)
    score = _score(row)
    data = row.replace({np.nan: None}).to_dict()
    record = service_record(data, STORE.observations(pocket_id), commitments=STORE.commitments(pocket_id))
    data.update({"priority_score": round(score, 1) if np.isfinite(score) else None, "tier": features.tier(score), "priority_reasons": priority_reasons(data), "explanation_method": "normalized feature signals, not SHAP attributions", "intervention": _intervention(row), "service_assurance": {name: value["score"] for name, value in record["services"].items()}, "service_record": record})
    return data


@app.post("/priority/score")
def priority_score(payload: PriorityRequest) -> dict[str, Any]:
    body = payload.model_dump()
    feature_values = {**body.pop("features", {}), **body}
    row = pd.Series(feature_values)
    score = _score(row)
    return {"priority_score": round(score, 1), "tier": features.tier(score), "reasons": priority_reasons(feature_values), "synthetic": True}


@app.post("/intervention/recommend")
def intervention(payload: InterventionRequest) -> dict[str, Any]:
    body = payload.model_dump()
    feature_values = {**body.pop("features", {}), **body}
    return {**_intervention(pd.Series(feature_values)), "synthetic": True}


@app.get("/service/{pocket_id}/assurance")
def assurance(pocket_id: str) -> dict[str, Any]:
    row = _row(pocket_id)
    return service_record(row.to_dict(), STORE.observations(pocket_id), commitments=STORE.commitments(pocket_id))


@app.post("/cost/estimate")
def cost(payload: CostRequest) -> dict[str, Any]:
    model = MODELS.get("cost")
    values = pd.DataFrame([payload.model_dump()])
    if model:
        X = values[model["features"]]
        cost_value = float(model["cost"].predict(X)[0]); delay = float(model["delay"].predict(X)[0])
        cost_band = model.get("cost_residual_std", 400) * 1.28; delay_band = model.get("delay_residual_std", 5) * 1.28
    else:
        cost_value = 2200 + payload.land_value_per_sqm / 70 + payload.FSI * 190 + payload.cross_subsidy_ratio * 170
        delay = 10 + payload.units / 400 + payload.FSI * 2
        cost_band, delay_band = 420, 5
    return {"construction_cost_per_sqft": round(cost_value), "cost_interval": [round(max(0, cost_value - cost_band)), round(cost_value + cost_band)], "expected_delay_months": round(delay, 1), "delay_interval": [round(max(0, delay - delay_band), 1), round(delay + delay_band, 1)], "synthetic": True}


@app.post("/feasibility/simulate")
def feasibility(payload: FeasibilityRequest) -> dict[str, Any]:
    values = payload.model_dump()
    return {"result": simulate(values), "sensitivity": sensitivity(values), "synthetic": True}


@app.post("/optimize")
def optimize(payload: OptimizeRequest) -> dict[str, Any]:
    frame = _planning_frame()
    if frame.empty:
        raise HTTPException(503, "Planning data is unavailable")
    frame["priority_score"] = _scores(frame)
    return {**optimise(frame, payload.budget_inr, payload.min_vulnerable_share, payload.min_wards), "synthetic": True}


@app.post("/grievance/classify")
def classify_grievance(payload: GrievanceRequest) -> dict[str, Any]:
    model = MODELS.get("nlp")
    if model:
        category = str(model.predict([payload.text])[0])
        probabilities = model.predict_proba([payload.text])[0]
        confidence = float(max(probabilities))
    else:
        lower = payload.text.lower()
        terms = {"water": ["water", "paani", "पानी"], "sanitation": ["toilet", "शौचालय", "safai"], "power": ["light", "bijli", "बिजली"], "waste": ["garbage", "kachra", "कचरा"], "drainage": ["drain", "nala", "नाला"], "health": ["clinic", "fever", "बच्चों"], "safety": ["unsafe", "women", "सुरक्षित"], "housing": ["sra", "rehab", "पुनर्विकास"]}
        counts = {key: sum(term in lower for term in tokens) for key, tokens in terms.items()}
        category = max(counts, key=counts.get) if max(counts.values()) else "other"
        confidence = None
    urgency = "urgent" if any(term in payload.text.lower() for term in ["fire", "danger", "unsafe", "fever", "गंदा", "असुरक्षित", "आग", "धोका", "धूर", "खतरा"]) else "standard"
    return {"category": category, "confidence": round(confidence, 3) if confidence is not None else None, "urgency": urgency,
            "expected_resolution_days": 2 if urgency == "urgent" else 7, "classification_method": "synthetic-trained model" if model else "keyword rules",
            "confidence_description": "Model confidence on a synthetic training distribution; not calibrated on real resident reports", "synthetic": payload.synthetic}


@app.post("/grievances")
def create_grievance(payload: GrievanceRequest) -> dict[str, Any]:
    if not payload.pocket_id:
        raise HTTPException(422, "Choose the project/location before submitting")
    _row(payload.pocket_id)
    if not payload.synthetic and not payload.consent:
        raise HTTPException(422, "Consent is required for a real resident report")
    classification = classify_grievance(payload)
    now = datetime.now(timezone.utc)
    receipt = secrets.token_urlsafe(32)
    record = {"complaint_id": f"NSG-{secrets.token_hex(6).upper()}", "text": payload.text, "pocket_id": payload.pocket_id,
              "language": payload.language, **classification, "status": "received", "consent": payload.consent,
              "created_at": now.isoformat(), "due_at": (now + timedelta(days=classification["expected_resolution_days"])).isoformat(),
              "department": SERVICES.get(classification["category"], {}).get("department", "Ward help desk"),
              "assigned_to": None, "assigned_at": None, "resolved_at": None, "pending_observation_id": None, "escalations": 0,
              "history": [{"at": now.isoformat(), "action": "received", "actor": "resident", "notes": "Report received; department suggestion awaits officer review"}]}
    STORE.create_complaint(record, receipt)
    return {**_complaint_view(record), "receipt_token": receipt}


@app.get("/grievances")
def list_grievances(status: str | None = None, pocket_id: str | None = None, _: None = Depends(officer_access)) -> dict[str, Any]:
    data = [_complaint_view(g) for g in STORE.complaints() if (not status or g["status"] == status) and (not pocket_id or g["pocket_id"] == pocket_id)]
    data.sort(key=lambda g: (g["status"] == "resolved", not g["sla_breached"], g["urgency"] != "urgent", g["due_at"]))
    return {"items": data, "total": len(data)}


@app.get("/grievances/{complaint_id}")
def track_grievance(complaint_id: str, x_receipt_token: str = Header("")) -> dict:
    if not STORE.receipt_matches(complaint_id, x_receipt_token):
        raise HTTPException(404, "Receipt not found; check the reference and receipt token")
    return _complaint_view(STORE.complaint(complaint_id))


@app.post("/grievances/{complaint_id}/action")
def act_on_grievance(complaint_id: str, payload: ComplaintAction, _: None = Depends(officer_access)) -> dict:
    def change(record: dict, db: Any) -> dict:
        status, now = record["status"], utc_now()
        if payload.action == "assign":
            if status not in {"received", "assigned", "reopened"}:
                raise HTTPException(409, "Only a received, assigned or reopened report can be assigned")
            record.update(status="assigned", assigned_to=payload.officer.strip(), department=payload.department or record["department"])
            record["assigned_at"] = record["assigned_at"] or now
            if payload.category:
                if payload.category != record["category"]:
                    record["confidence"] = None
                    record["classification_method"] = "officer_review"
                record["category"] = payload.category
            if payload.urgency:
                record["urgency"] = payload.urgency
                record["expected_resolution_days"] = 2 if payload.urgency == "urgent" else 7
                record["due_at"] = (datetime.fromisoformat(record["created_at"]) + timedelta(days=record["expected_resolution_days"])).isoformat()
        elif payload.action == "start":
            if status not in {"assigned", "reopened"} or not record["assigned_to"]:
                raise HTTPException(409, "Assign the complaint before starting work")
            record["status"] = "in_progress"
        elif payload.action == "complete":
            if status not in {"assigned", "in_progress"}:
                raise HTTPException(409, "Only assigned work can be submitted for resident confirmation")
            if record["category"] in SERVICES and payload.observation is None:
                raise HTTPException(422, "Record an after-repair service measurement and source")
            if payload.observation:
                if payload.observation.observed_at < datetime.fromisoformat(record["created_at"]) - timedelta(minutes=1):
                    raise HTTPException(422, "An after-repair observation cannot predate the report")
                if record["category"] in SERVICES and payload.observation.service != record["category"]:
                    raise HTTPException(422, "The measurement must match the reported service")
                if payload.observation.synthetic != record["synthetic"]:
                    raise HTTPException(422, "Demo and real field evidence must match the report's data scope")
                observation = _validated_observation(payload.observation, record["pocket_id"], "pending_confirmation", complaint_id)
                STORE.save_observation(observation, db)
                record["pending_observation_id"] = observation["observation_id"]
            record["status"] = "awaiting_confirmation"
        elif payload.action == "escalate":
            if status == "resolved":
                raise HTTPException(409, "A resolved complaint cannot be escalated")
            record["escalations"] += 1
        record["history"].append({"at": now, "action": payload.action, "actor": payload.officer.strip(), "notes": payload.notes.strip(),
                                  **({"category": record["category"], "urgency": record["urgency"], "department": record["department"], "due_at": record["due_at"]} if payload.action == "assign" else {})})
        return record
    result = STORE.change_complaint(complaint_id, change)
    if result is None:
        raise HTTPException(404, "Complaint not found")
    return _complaint_view(result)


@app.post("/grievances/{complaint_id}/confirm")
def confirm_grievance(complaint_id: str, payload: ResidentConfirmation, x_receipt_token: str = Header("")) -> dict:
    if not STORE.receipt_matches(complaint_id, x_receipt_token):
        raise HTTPException(404, "Receipt not found")
    def change(record: dict, db: Any) -> dict:
        if record["status"] != "awaiting_confirmation":
            raise HTTPException(409, "This complaint is not awaiting resident confirmation")
        now = utc_now()
        observation = next((o for o in STORE.observations(record["pocket_id"], db) if o["observation_id"] == record["pending_observation_id"]), None)
        if observation:
            observation["verification"] = "resident_confirmed" if payload.resolved else "disputed"
            observation["history"].append({"at": now, "action": observation["verification"], "actor": "resident", "notes": payload.notes.strip()})
            STORE.save_observation(observation, db)
        record["status"] = "resolved" if payload.resolved else "reopened"
        record["resolved_at"] = now if payload.resolved else None
        record["history"].append({"at": now, "action": record["status"], "actor": "resident", "notes": payload.notes.strip()})
        return record
    return _complaint_view(STORE.change_complaint(complaint_id, change))


@app.post("/service/{pocket_id}/observations")
def add_observation(pocket_id: str, payload: ObservationRequest, _: None = Depends(officer_access)) -> dict:
    _row(pocket_id)
    return STORE.save_observation(_validated_observation(payload, pocket_id))


@app.post("/observations/{observation_id}/verify")
def verify_observation(observation_id: str, payload: ObservationVerification, _: None = Depends(officer_access)) -> dict:
    with STORE.connection(write=True) as db:
        record = next((o for o in STORE.observations(db=db) if o["observation_id"] == observation_id), None)
        if record is None:
            raise HTTPException(404, "Observation not found")
        if record["verification"] not in {"reported", "resident_confirmed"}:
            raise HTTPException(409, "Pending repair evidence needs resident confirmation; disputed evidence cannot be approved")
        record["verification"] = "field_verified"
        record["history"].append({"at": utc_now(), "action": "field_verified", "actor": payload.reviewer.strip(), "notes": payload.notes.strip()})
        STORE.save_observation(record, db)
    return record


@app.get("/pilot/evidence")
def pilot_evidence(_: None = Depends(officer_access)) -> dict:
    observations, evaluations = STORE.observations(), STORE.evaluations()
    measured = [e for e in evaluations if not e["synthetic"]]
    usability = [e for e in measured if e["task"] != "classify_complaint"]
    paired = [e for e in usability if e["completed"] and e["baseline_seconds"] is not None and e["app_seconds"] is not None]
    language_metrics = {}
    for language in ["en", "hi", "mr"]:
        rows = [e for e in measured if e["language"] == language and e["task"] == "classify_complaint" and e["expected_category"] and e["predicted_category"]]
        language_metrics[language] = {"sample_size": len(rows), "accuracy": sum(e["expected_category"] == e["predicted_category"] for e in rows) / len(rows) if rows else None}
    real_complaints = [c for c in STORE.complaints() if not c["synthetic"]]
    return {"observations": observations, "evaluations": evaluations, "locations": STORE.locations(), "commitments": STORE.commitments(), "metrics": {
        "real_observations": sum(not o["synthetic"] for o in observations),
        "field_verified_observations": sum(not o["synthetic"] and o["verification"] == "field_verified" for o in observations),
        "real_evaluations": len(measured), "paired_sample_size": len(paired),
        "median_seconds_saved": median(e["baseline_seconds"] - e["app_seconds"] for e in paired) if paired else None,
        "usability_sample_size": len(usability), "completion_rate": sum(e["completed"] for e in usability) / len(usability) if usability else None,
        "real_reports": len(real_complaints), "real_verified_closures": sum(c["status"] == "resolved" for c in real_complaints),
        "classification_by_language": language_metrics,
    }, "description": "Metrics include only consented non-synthetic entries. Small samples are exploratory evidence; observations do not validate synthetic geography or the priority model."}


@app.post("/pilot/evaluations")
def add_evaluation(payload: PilotEvaluation, _: None = Depends(officer_access)) -> dict:
    if not payload.synthetic and not payload.consent:
        raise HTTPException(422, "Consent is required for a real pilot evaluation")
    if payload.task == "classify_complaint" and (not payload.expected_category or not payload.predicted_category):
        raise HTTPException(422, "A classification trial needs independent expected and predicted categories")
    return STORE.save_evaluation({**payload.model_dump(), "evaluation_id": f"EVAL-{secrets.token_hex(6).upper()}", "created_at": utc_now()})


@app.post("/service/{pocket_id}/commitment")
def set_commitment(pocket_id: str, payload: ServiceCommitmentRequest, _: None = Depends(officer_access)) -> dict:
    _row(pocket_id)
    if payload.target > SERVICES[payload.service]["ceiling"] or (payload.service == "health" and payload.target != 1):
        raise HTTPException(422, "Target is outside the valid range for the service")
    if not payload.synthetic and not payload.source_url:
        raise HTTPException(422, "An approved commitment needs a reference link")
    return STORE.save_commitment({**payload.model_dump(mode="json"), "pocket_id": pocket_id, "created_at": utc_now()})


@app.post("/pilot/locations")
def import_location(payload: PilotLocationRequest, _: None = Depends(officer_access)) -> dict:
    if not payload.consent:
        raise HTTPException(422, "Confirm permission/licence to import this location record")
    record = {**{field: None for field in features.PRIORITY_FEATURES + [definition["field"] for definition in SERVICES.values()] + ["years_since_settlement", "land_ownership"]},
              **payload.model_dump(mode="json"), "synthetic": False, "created_at": utc_now()}
    try:
        STORE.save_location(record)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "This pilot location already exists; choose a unique PILOT identifier") from exc
    return record


@app.post("/eligibility/check")
def eligibility(payload: EligibilityRequest) -> dict[str, Any]:
    return screen(payload.model_dump())


@app.get("/stats/summary")
def summary() -> dict[str, Any]:
    frame = _planning_frame()
    observations = STORE.observations()
    by_pocket: dict[str, list] = {}
    for observation in observations:
        by_pocket.setdefault(observation["pocket_id"], []).append(observation)
    commitments: dict[str, list] = {}
    for commitment in STORE.commitments():
        commitments.setdefault(commitment["pocket_id"], []).append(commitment)
    records = [(row, service_record(row, by_pocket.get(row["pocket_id"], []), commitments=commitments.get(row["pocket_id"], []))) for row in frame.to_dict("records")]
    wards: dict[str, dict] = {}
    gaps = verified = known = 0
    averages = []
    for row, record in records:
        key = f"{row['city']} / {row['ward']}"
        ward = wards.setdefault(key, {"ward": row["ward"], "city": row["city"], "scores": [], "gaps": 0, "known_services": 0, "compliant_services": 0, "field_verified_services": 0})
        services = list(record["services"].values())
        has_gap = any(s["status"] == "breach" for s in services)
        gaps += has_gap; ward["gaps"] += has_gap
        verified += record["field_verified_services"]; ward["field_verified_services"] += record["field_verified_services"]
        known += record["known_services"]; ward["known_services"] += record["known_services"]
        ward["compliant_services"] += sum(s["status"] == "compliant" for s in services)
        if record["assurance_index"] is not None:
            averages.append(record["assurance_index"]); ward["scores"].append(record["assurance_index"])
    ward_items = [{**{key: value for key, value in ward.items() if key != "scores"}, "assurance_index": round(sum(ward["scores"]) / len(ward["scores"]), 1) if ward["scores"] else None,
                   "compliance": round(ward["compliant_services"] / ward["known_services"] * 100, 1) if ward["known_services"] else None} for ward in wards.values()]
    complaints = [_complaint_view(c) for c in STORE.complaints()]
    closed = [c for c in complaints if c["status"] == "resolved"]
    response = [(datetime.fromisoformat(c["assigned_at"]) - datetime.fromisoformat(c["created_at"])).total_seconds() / 86400 for c in complaints if c["assigned_at"]]
    return {"pockets_prioritised": len(frame), "households_covered": int(frame.households.sum()) if not frame.empty else 0,
            "critical_pockets": int((_scores(frame) >= 75).sum()) if not frame.empty else 0,
            "service_gaps_flagged": int(gaps), "avg_assurance_index": round(sum(averages) / len(averages), 1) if averages else None,
            "resident_verified_closures": len(closed), "open_complaints": len(complaints) - len(closed),
            "sla_breaches": sum(c["sla_breached"] for c in complaints), "urgent_complaints": sum(c["urgency"] == "urgent" and c["status"] != "resolved" for c in complaints),
            "within_sla_pct": round(sum(datetime.fromisoformat(c["resolved_at"]) <= datetime.fromisoformat(c["due_at"]) for c in closed) / len(closed) * 100, 1) if closed else None,
            "median_response_days": round(median(response), 2) if response else None,
            "known_services": known, "field_verified_services": verified, "wards": ward_items,
            "real_observations": sum(not o["synthetic"] for o in observations),
            "synthetic": True, "updated_at": utc_now(), "data_scope": "Synthetic planning baseline with explicitly labelled local reports and observations"}
