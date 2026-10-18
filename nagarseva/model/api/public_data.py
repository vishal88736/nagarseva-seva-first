"""Data-backed API. Acquired facts, submitted observations and plans stay distinct."""
from __future__ import annotations
import base64
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from shapely.geometry import box, shape

from model.src.urban_planning import KEYS, compare_scenarios
from .planning_schemas import PriorityInput, ScenarioInput, EvidenceInput
from .field_survey import FieldSurvey


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class GeographicUnit(Input):
    id: str = Field(pattern=r"^[a-zA-Z0-9:_-]{2,100}$")
    source_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    resolution: Literal["country", "state", "district", "city", "town", "ward"]
    reference_year: int = Field(ge=1900, le=2100)
    source: str = Field(min_length=5, max_length=2000)


class Observation(Input):
    id: str | None = Field(None, pattern=r"^[a-zA-Z0-9:_-]{2,100}$")
    settlement_id: str | None = None
    geographic_unit_id: str | None = None
    indicator_type: Literal["water", "sanitation", "drainage", "housing", "access", "risk", "population", "households", "water_hours", "functional_toilets", "blocked_drains"]
    value: float | None = Field(None, ge=0)
    unit: str = Field(min_length=1, max_length=80)
    reference_year: int = Field(ge=1900, le=2100)
    observation_date: datetime | None = None
    geographic_resolution: Literal["settlement", "country", "state", "district", "city", "town", "ward"]
    source: str = Field(min_length=5, max_length=2000)
    verification_status: Literal["reported", "field_verified", "historical_published", "rejected"] = "reported"
    inspector_reference: str = Field(min_length=2, max_length=80)
    reviewer_reference: str | None = Field(None, min_length=2, max_length=80)
    method: str = Field(min_length=10, max_length=2000)
    evidence_reference: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def valid_observation(self):
        if (self.settlement_id is None) == (self.geographic_unit_id is None):
            raise ValueError("Supply exactly one settlement_id or geographic_unit_id")
        if (self.geographic_resolution == "settlement") != bool(self.settlement_id):
            raise ValueError("Observation geography must match its original resolution")
        if self.unit == "deficit_0_100" and (self.indicator_type not in KEYS or self.value is not None and self.value > 100):
            raise ValueError("Deficit indices require a supported indicator and a value in 0-100")
        if self.observation_date:
            if self.observation_date.tzinfo is None or self.observation_date > datetime.now(timezone.utc) + timedelta(minutes=5):
                raise ValueError("Use a timezone-aware observation time, not in the future")
            if self.observation_date.year != self.reference_year:
                raise ValueError("Reference year must match observation date")
        if self.reference_year > datetime.now(timezone.utc).year:
            raise ValueError("Reference year cannot be in the future")
        if self.verification_status == "field_verified":
            if not self.reviewer_reference or self.reviewer_reference.casefold() == self.inspector_reference.casefold() or not self.evidence_reference or not self.observation_date:
                raise ValueError("Field verification needs a dated observation, evidence and a separate reviewer")
        return self


class Intervention(Input):
    settlement_id: str
    intervention_type: Literal["water", "sanitation", "drainage", "waste", "housing", "other"]
    description: str = Field(min_length=5, max_length=2000)
    planned_start: date
    planned_end: date
    estimated_cost: float | None = Field(None, ge=0, le=100_000_000_000)
    cost_basis: str = Field("Unquoted user assumption", min_length=5, max_length=2000)
    target_value: float | None = Field(None, ge=0)
    measurement_unit: str | None = Field(None, max_length=80)
    target_direction: Literal["at_least", "at_most"] = "at_least"
    actor: str = Field(min_length=2, max_length=80)
    scenario_snapshot: dict | None = None

    @model_validator(mode="after")
    def valid_dates(self):
        if self.planned_end < self.planned_start:
            raise ValueError("Planned end must follow planned start")
        if (self.target_value is None) != (self.measurement_unit is None):
            raise ValueError("Supply a target and its measurement unit together")
        return self


class InterventionPatch(Input):
    description: str | None = Field(None, min_length=5, max_length=2000)
    planned_start: date | None = None
    planned_end: date | None = None
    estimated_cost: float | None = Field(None, ge=0, le=100_000_000_000)
    target_value: float | None = Field(None, ge=0)
    measurement_unit: str | None = Field(None, min_length=1, max_length=80)
    target_direction: Literal["at_least", "at_most"] | None = None
    actor: str = Field(min_length=2, max_length=80)


class Action(Input):
    action: Literal["start", "report_complete", "request_verification", "reopen"]
    actor: str = Field(min_length=2, max_length=80)
    notes: str = Field(min_length=5, max_length=2000)


class EvidenceReference(Input):
    evidence_reference: str = Field(pattern=r"^https://\S+$", max_length=2000)
    actor: str = Field(min_length=2, max_length=80)
    notes: str = Field(min_length=5, max_length=2000)


class Verification(Input):
    verification_type: Literal["inspection", "reinspection"]
    evidence_reference: str
    outcome: Literal["passed", "reinspection_required"]
    verifier_reference: str = Field(min_length=2, max_length=80)
    observed_at: datetime
    measured_value: float = Field(ge=0)
    functioning_confirmed: bool = False
    notes: str = Field(min_length=5, max_length=2000)


class Complaint(Input):
    settlement_id: str
    intervention_id: str | None = None
    service_type: Literal["water", "sanitation", "drainage", "waste", "housing", "other"]
    description: str = Field(min_length=5, max_length=2000)


class ComplaintUpdate(Input):
    status: Literal["in_review", "resolved", "reopened"]
    resolution_details: str = Field(min_length=5, max_length=2000)
    actor: str = Field(min_length=2, max_length=80)


def new_id(prefix):
    return prefix + "-" + secrets.token_hex(8)


def create_public_router(provider, officer_access, decode_evidence):
    router = APIRouter(prefix="/urban/data", tags=["Acquired public data"])

    def find(table, identifier, db=None):
        try:
            return provider().record(table, identifier, db)
        except LookupError as exc:
            raise HTTPException(404, "Record not found") from exc

    def save_body(db, table, record):
        # Table names are internal constants, never supplied by a request.
        db.execute(f"UPDATE {table} SET body=? WHERE id=?", (provider().encode(record), record["id"]))

    def audit(record, action, actor, notes):
        record.setdefault("history", []).append({"at": provider().now(), "action": action, "actor": actor, "notes": notes})

    @router.get("/health")
    def health():
        return {"status": "ok", "database": "SQLite", "schema_version": 1, "synthetic": False,
                "snapshot_loaded": bool(provider().metadata()["active_settlement_ids"]), "officer_auth_required": True,
                "evidence_storage": os.getenv("URBANSAARTHI_EVIDENCE_STORAGE") == "sqlite", "government_connected": False}

    @router.get("/metadata")
    def metadata():
        path = provider().data_dir.parent.parent / "research/dataset_inventory.csv"
        if not path.exists():
            path = provider().data_dir.parent / "metadata/dataset_inventory.csv"
        rows = list(csv.DictReader(path.open())) if path.exists() else []
        meta = {k: v for k, v in provider().metadata().items() if not k.startswith("active_")}
        return {"snapshot": meta, "datasets": rows}

    @router.get("/overview")
    def overview():
        return provider().stats()

    @router.get("/settlements")
    def settlements(search: str = Query("", max_length=200), page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000)):
        rows = [r for r in provider().settlements() if search.casefold() in (r["name"] + " " + r["source_id"]).casefold()]
        start = (page - 1) * page_size
        return {"items": rows[start:start + page_size], "total": len(rows), "page": page, "page_size": page_size, "synthetic": False}

    @router.get("/settlements/{settlement_id}")
    def settlement(settlement_id: str):
        item = find("settlements", settlement_id)
        return {**item, "observations": [r for r in provider().records("indicator_observations") if r.get("settlement_id") == settlement_id],
                "projects": [r for r in provider().projects() if r.get("settlement_id") == settlement_id]}

    @router.get("/spatial")
    def spatial(category: str = "amenity,transport,water_infrastructure", bbox: str | None = None,
                offset: int = Query(0, ge=0), limit: int = Query(1000, ge=1, le=10000)):
        categories = category.split(",")
        allowed = {"road", "building", "amenity", "transport", "residential_context", "water_infrastructure", "settlement", "project"}
        if not set(categories) <= allowed:
            raise HTTPException(422, "Unknown map category")
        bounds = None
        if bbox:
            try:
                values = [float(v) for v in bbox.split(",")]
                if len(values) != 4 or not (-180 <= values[0] < values[2] <= 180 and -90 <= values[1] < values[3] <= 90):
                    raise ValueError()
                bounds = box(*values)
            except ValueError as exc:
                raise HTTPException(422, "bbox must be west,south,east,north in WGS84") from exc
        if categories == ["settlement"]:
            features = [{"type": "Feature", "id": r["id"], "geometry": r["geometry"], "properties": {"source_id": r["source_id"], "name": r["name"], "category": "settlement", "source_url": r["source"], "source_date": r["source_date"]}} for r in provider().settlements() if r.get("geometry")]
        elif categories == ["project"]:
            features = [{"type": "Feature", "id": r["id"], "geometry": r["geometry"], "properties": {"name": r["scheme_name"], "category": "project"}} for r in provider().projects() if r.get("geometry")]
        else:
            if "project" in categories or "settlement" in categories:
                raise HTTPException(422, "Request settlement or project layers separately")
            clauses = "category IN (" + ",".join("?" for _ in categories) + ")"
            params = list(categories)
            if bounds:
                w, s, e, n = bounds.bounds
                clauses += " AND maxx >= ? AND minx <= ? AND maxy >= ? AND miny <= ?"
                params += [w, e, s, n]
            with provider().store.connection() as db:
                features = [json.loads(r[0]) for r in db.execute("SELECT body FROM spatial_features WHERE " + clauses + " ORDER BY id", params)]
        if bounds:
            features = [f for f in features if shape(f["geometry"]).intersects(bounds)]
        return {"type": "FeatureCollection", "features": features[offset:offset + limit], "total": len(features), "offset": offset, "limit": limit,
                "attribution": "OpenStreetMap contributors; ODbL 1.0. Source-specific attribution for SRA layers.", "limitations": "Mapped features do not prove operation; absent map features do not prove absence"}

    @router.get("/projects")
    def projects(search: str = Query("", max_length=200), page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000)):
        rows = [r for r in provider().projects() if search.casefold() in (r["scheme_name"] + " " + r.get("administrative_area", "")).casefold()]
        return {"items": rows[(page - 1) * page_size:page * page_size], "total": len(rows), "scope": "First public listing page; status unknown; unjoined records retained"}

    @router.get("/geographic-units")
    def units():
        return {"items": provider().records("geographic_units")}

    @router.post("/geographic-units", dependencies=[Depends(officer_access)], status_code=201)
    def add_unit(payload: GeographicUnit):
        item = payload.model_dump()
        with provider().store.connection(write=True) as db:
            if db.execute("SELECT 1 FROM geographic_units WHERE id=?", (item["id"],)).fetchone():
                raise HTTPException(409, "Geographic unit already exists")
            db.execute("INSERT INTO geographic_units VALUES(?,?,?,?,?,?)", (item["id"], item["source_id"], item["name"], item["resolution"], item["reference_year"], provider().encode(item)))
        return item

    @router.get("/indicators")
    def indicators(settlement_id: str | None = None, geographic_unit_id: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000)):
        rows = [r for r in provider().records("indicator_observations") if (not settlement_id or r.get("settlement_id") == settlement_id) and (not geographic_unit_id or r.get("geographic_unit_id") == geographic_unit_id)]
        # Inspector and evidence references are operational records; public fields are the observations and provenance.
        public = [{k: v for k, v in r.items() if k not in {"inspector_reference", "reviewer_reference", "evidence_reference"}} for r in rows]
        return {"items": public[(page - 1) * page_size:page * page_size], "total": len(rows)}

    @router.get("/surveys/schema")
    def survey_schema():
        return FieldSurvey.model_json_schema()

    @router.get("/surveys", dependencies=[Depends(officer_access)])
    def surveys():
        return {"items": provider().records("field_surveys")}

    @router.post("/surveys", dependencies=[Depends(officer_access)], status_code=201)
    def add_survey(payload: FieldSurvey):
        find("settlements", payload.settlement_id)
        record = {**payload.model_dump(mode="json"), "id": payload.survey_id, "recorded_at": provider().now(), "synthetic": False}
        with provider().store.connection(write=True) as db:
            if db.execute("SELECT 1 FROM field_surveys WHERE id=?", (payload.survey_id,)).fetchone():
                raise HTTPException(409, "Survey already imported; originals are immutable")
            db.execute("INSERT INTO field_surveys VALUES(?,?,?,?)", (payload.survey_id, payload.settlement_id, record["observed_at"], provider().encode(record)))
            fields = {"water_hours_per_day": ("water_hours", "hours/day"), "functional_toilets_observed": ("functional_toilets", "observed functional toilets"), "blocked_drain_segments_observed": ("blocked_drains", "observed blocked segments")}
            for field, (kind, unit) in fields.items():
                value = getattr(payload, field)
                if value is None:
                    continue
                identifier = "SURVEYOBS-" + hashlib.sha256((payload.survey_id + field).encode()).hexdigest()[:24]
                observation = {"id": identifier, "settlement_id": payload.settlement_id, "geographic_unit_id": None, "indicator_type": kind, "value": value, "unit": unit,
                               "reference_year": payload.observed_at.year, "observation_date": record["observed_at"], "geographic_resolution": "settlement", "source": f"Authorized {payload.collection_platform} survey {payload.survey_id}",
                               "verification_status": "reported", "inspector_reference": payload.inspector_reference, "method": payload.protocol_reference,
                               "limitations": "Spot observation only; not representative household coverage or a normalized deficit index", "synthetic": False}
                db.execute("INSERT INTO indicator_observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", tuple(observation[k] for k in ("id", "settlement_id", "geographic_unit_id", "indicator_type", "value", "unit", "reference_year", "observation_date", "geographic_resolution", "source", "verification_status")) + (provider().encode(observation),))
        return record

    @router.post("/indicators", dependencies=[Depends(officer_access)], status_code=201)
    def add_indicator(payload: Observation):
        if payload.settlement_id:
            find("settlements", payload.settlement_id)
        else:
            unit = find("geographic_units", payload.geographic_unit_id)
            if unit["resolution"] != payload.geographic_resolution or unit["reference_year"] != payload.reference_year:
                raise HTTPException(422, "Observation must retain its geographic unit's resolution and reference year")
        item = {**payload.model_dump(mode="json"), "id": payload.id or new_id("OBS"), "synthetic": False, "recorded_at": provider().now(), "verification_scope": "User-recorded evidence review; inspector identity not independently authenticated by this prototype"}
        with provider().store.connection(write=True) as db:
            if db.execute("SELECT 1 FROM indicator_observations WHERE id=?", (item["id"],)).fetchone():
                raise HTTPException(409, "Observation ID already exists; originals are immutable")
            db.execute("INSERT INTO indicator_observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", tuple(item[k] for k in ("id", "settlement_id", "geographic_unit_id", "indicator_type", "value", "unit", "reference_year", "observation_date", "geographic_resolution", "source", "verification_status")) + (provider().encode(item),))
        return item

    @router.post("/priority")
    def priority(payload: PriorityInput):
        try:
            return provider().priority(payload.weights)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.post("/scenarios/{settlement_id}")
    def scenario(settlement_id: str, payload: ScenarioInput):
        item = find("settlements", settlement_id)
        data = {"clusters": [{**item, "node_id": ""}], "network": {"nodes": [], "edges": []}, "amenities": [], "relocation_node_id": ""}
        try:
            result = compare_scenarios(data, settlement_id, payload.model_dump())
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        result.update(geometry_source_synthetic=False, hypothetical=True, access_available=False,
                      limits="Costs, households, disruption and coverage are user assumptions. No quoted costs, household counts, routable settlement origins, relocation site or engineering constraints acquired. Access comparison is unavailable.")
        return result

    @router.get("/interventions", dependencies=[Depends(officer_access)])
    def interventions():
        return {"items": [{**r, "overdue": r["planned_end"] < provider().now()[:10] and r["status"] != "verified"} for r in provider().records("interventions")]}

    @router.post("/interventions", dependencies=[Depends(officer_access)], status_code=201)
    def create_intervention(payload: Intervention):
        find("settlements", payload.settlement_id)
        item = {**payload.model_dump(mode="json"), "id": new_id("INT"), "status": "planned", "created_at": provider().now(), "completed_at": None, "completed_by": None,
                "synthetic": False, "hypothetical_plan": True, "history": [], "verification_scope": "User records; no government approval or authenticated field validation implied"}
        audit(item, "created", payload.actor, "Unapproved user plan with explicit cost assumptions")
        with provider().store.connection(write=True) as db:
            db.execute("INSERT INTO interventions VALUES(?,?,?,?,?,?,?,?,?)", tuple(item[k] for k in ("id", "settlement_id", "intervention_type", "description", "planned_start", "planned_end", "estimated_cost", "status")) + (provider().encode(item),))
        return item

    @router.patch("/interventions/{identifier}", dependencies=[Depends(officer_access)])
    def update_intervention(identifier: str, payload: InterventionPatch):
        with provider().store.connection(write=True) as db:
            item = find("interventions", identifier, db)
            if item["status"] not in {"planned", "in_progress"}:
                raise HTTPException(409, "Reopen work before changing the plan")
            updates = payload.model_dump(mode="json", exclude_unset=True)
            if any(updates.get(k, "not_null") is None for k in ("description", "planned_start", "planned_end")):
                raise HTTPException(422, "Description and dates cannot be null")
            item.update({k: v for k, v in updates.items() if k != "actor"})
            if item["planned_end"] < item["planned_start"]:
                raise HTTPException(422, "Planned end must follow start")
            if (item["target_value"] is None) != (item["measurement_unit"] is None) or item["target_direction"] is None:
                raise HTTPException(422, "Supply a target and unit together, with a valid direction")
            audit(item, "plan_updated", payload.actor, "User edited plan assumptions")
            db.execute("UPDATE interventions SET description=?, planned_start=?, planned_end=?, estimated_cost=? WHERE id=?", (item["description"], item["planned_start"], item["planned_end"], item["estimated_cost"], identifier))
            save_body(db, "interventions", item)
        return item

    @router.post("/interventions/{identifier}/actions", dependencies=[Depends(officer_access)])
    def intervention_action(identifier: str, payload: Action):
        transitions = {"start": ({"planned"}, "in_progress"), "report_complete": ({"in_progress"}, "reported_complete"),
                       "request_verification": ({"reported_complete"}, "awaiting_verification"), "reopen": ({"reported_complete", "awaiting_verification", "verified", "requiring_reinspection"}, "in_progress")}
        with provider().store.connection(write=True) as db:
            item = find("interventions", identifier, db)
            allowed, target = transitions[payload.action]
            if item["status"] not in allowed:
                raise HTTPException(409, "Action is incompatible with intervention status")
            item["status"] = target
            if payload.action == "report_complete":
                item.update(completed_at=provider().now(), completed_by=payload.actor)
            if payload.action == "reopen":
                item.update(completed_at=None, completed_by=None)
            audit(item, payload.action, payload.actor, payload.notes)
            db.execute("UPDATE interventions SET status=? WHERE id=?", (target, identifier))
            save_body(db, "interventions", item)
        return item

    def save_evidence(identifier, item):
        item.update(id=new_id("EVD"), intervention_id=identifier, recorded_at=provider().now())
        with provider().store.connection(write=True) as db:
            find("interventions", identifier, db)
            db.execute("INSERT INTO inspection_evidence VALUES(?,?,?)", (item["id"], identifier, provider().encode(item)))
        return {k: v for k, v in item.items() if k != "content_base64"}

    @router.post("/interventions/{identifier}/evidence-references", dependencies=[Depends(officer_access)], status_code=201)
    def evidence_reference(identifier: str, payload: EvidenceReference):
        return save_evidence(identifier, {**payload.model_dump(), "storage": "external_reference", "scope": "Reference recorded; remote contents are not fetched or independently validated"})

    @router.post("/interventions/{identifier}/evidence", dependencies=[Depends(officer_access)], status_code=201)
    def upload_evidence(identifier: str, payload: EvidenceInput):
        if os.getenv("URBANSAARTHI_EVIDENCE_STORAGE") != "sqlite":
            raise HTTPException(503, "Configure URBANSAARTHI_EVIDENCE_STORAGE=sqlite for consented prototype uploads, or record an approved evidence reference")
        raw = decode_evidence(payload)
        return save_evidence(identifier, {**payload.model_dump(), "filename": Path(payload.filename.replace("\\", "/")).name, "storage": "sqlite", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})

    @router.get("/evidence/{identifier}/content", dependencies=[Depends(officer_access)])
    def evidence_content(identifier: str):
        item = find("inspection_evidence", identifier)
        if item["storage"] != "sqlite":
            raise HTTPException(404, "This record references external evidence")
        return Response(base64.b64decode(item["content_base64"]), media_type=item["content_type"], headers={"Content-Disposition": "attachment; filename=evidence", "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})

    @router.get("/evidence", dependencies=[Depends(officer_access)])
    def evidence_list():
        return {"items": [{k: v for k, v in r.items() if k != "content_base64"} for r in provider().records("inspection_evidence")]}

    @router.get("/verifications", dependencies=[Depends(officer_access)])
    def verifications():
        return {"items": provider().records("verification_records")}

    @router.post("/interventions/{identifier}/verifications", dependencies=[Depends(officer_access)], status_code=201)
    def verify_intervention(identifier: str, payload: Verification):
        with provider().store.connection(write=True) as db:
            item = find("interventions", identifier, db)
            evidence = find("inspection_evidence", payload.evidence_reference, db)
            if item["status"] not in {"awaiting_verification", "requiring_reinspection"}:
                raise HTTPException(409, "Request verification after reported completion")
            if evidence["intervention_id"] != identifier or payload.verifier_reference.casefold() in {evidence["actor"].casefold(), (item.get("completed_by") or "").casefold()}:
                raise HTTPException(422, "Use evidence from this intervention and a reviewer distinct from completion/evidence actors")
            if evidence["recorded_at"] < item["completed_at"]:
                raise HTTPException(422, "Attach inspection evidence after reported completion")
            observed = payload.observed_at
            if observed.tzinfo is None or observed > datetime.now(timezone.utc) + timedelta(minutes=5) or datetime.now(timezone.utc) - observed > timedelta(days=7) or observed < datetime.fromisoformat(item["completed_at"]) - timedelta(minutes=5):
                raise HTTPException(422, "Inspection must follow completion, be timezone aware and be within seven days")
            complaints = [r for r in provider().records("service_complaints", db) if r.get("intervention_id") == identifier]
            if payload.outcome == "passed":
                if any(r["status"] != "resolved" for r in complaints):
                    raise HTTPException(409, "Respond to open complaints before verification")
                if complaints and evidence["recorded_at"] < max(c.get("last_reopened_at", c["reported_at"]) for c in complaints):
                    raise HTTPException(422, "Fresh evidence after the latest complaint is required")
                target = item.get("target_value")
                meets = target is not None and (payload.measured_value >= target if item["target_direction"] == "at_least" else payload.measured_value <= target)
                if not meets or not payload.functioning_confirmed:
                    raise HTTPException(422, "A passed review requires functioning confirmation and the planned measurement target")
            record = {**payload.model_dump(mode="json"), "id": new_id("VER"), "intervention_id": identifier, "recorded_at": provider().now(), "measurement_unit": item["measurement_unit"], "scope": "User-recorded inspection; identity and external evidence not independently authenticated"}
            db.execute("INSERT INTO verification_records VALUES(?,?,?,?,?,?,?,?)", tuple(record[k] for k in ("id", "intervention_id", "verification_type", "recorded_at", "evidence_reference", "outcome", "verifier_reference")) + (provider().encode(record),))
            item["status"] = "verified" if payload.outcome == "passed" else "requiring_reinspection"
            audit(item, item["status"], payload.verifier_reference, payload.notes)
            db.execute("UPDATE interventions SET status=? WHERE id=?", (item["status"], identifier))
            save_body(db, "interventions", item)
        return record

    @router.get("/complaints", dependencies=[Depends(officer_access)])
    def complaints():
        return {"items": provider().records("service_complaints")}

    @router.post("/complaints", dependencies=[Depends(officer_access)], status_code=201)
    def create_complaint(payload: Complaint):
        find("settlements", payload.settlement_id)
        record = {**payload.model_dump(), "id": new_id("CMP"), "reported_at": provider().now(), "status": "open", "resolution_details": None, "history": []}
        with provider().store.connection(write=True) as db:
            if payload.intervention_id:
                work = find("interventions", payload.intervention_id, db)
                if work["settlement_id"] != payload.settlement_id:
                    raise HTTPException(422, "Complaint and intervention settlements must match")
                if work["status"] == "verified":
                    work["status"] = "requiring_reinspection"
                    audit(work, "complaint_requires_reinspection", "authorized reporter", payload.description)
                    db.execute("UPDATE interventions SET status=? WHERE id=?", (work["status"], work["id"]))
                    save_body(db, "interventions", work)
            db.execute("INSERT INTO service_complaints VALUES(?,?,?,?,?,?,?,?,?)", tuple(record[k] for k in ("id", "settlement_id", "intervention_id", "service_type", "description", "reported_at", "status", "resolution_details")) + (provider().encode(record),))
        return record

    @router.patch("/complaints/{identifier}", dependencies=[Depends(officer_access)])
    def update_complaint(identifier: str, payload: ComplaintUpdate):
        with provider().store.connection(write=True) as db:
            item = find("service_complaints", identifier, db)
            if payload.status == "reopened" and item["status"] != "resolved" or payload.status != "reopened" and item["status"] == "resolved":
                raise HTTPException(409, "Reopen a resolved complaint before reviewing it")
            item.update(status=payload.status, resolution_details=payload.resolution_details)
            if payload.status == "reopened":
                item["last_reopened_at"] = provider().now()
                if item.get("intervention_id"):
                    work = find("interventions", item["intervention_id"], db)
                    if work["status"] == "verified":
                        work["status"] = "requiring_reinspection"
                        audit(work, "complaint_reopened", payload.actor, payload.resolution_details)
                        db.execute("UPDATE interventions SET status=? WHERE id=?", (work["status"], work["id"]))
                        save_body(db, "interventions", work)
            audit(item, payload.status, payload.actor, payload.resolution_details)
            db.execute("UPDATE service_complaints SET status=?, resolution_details=? WHERE id=?", (item["status"], item["resolution_details"], identifier))
            save_body(db, "service_complaints", item)
        return item

    @router.get("/reports/{kind}.csv")
    def report(kind: Literal["priority", "settlements", "projects", "datasets", "interventions", "complaints"], auth=Depends(officer_access)):
        if kind == "priority":
            rows = provider().priority()["items"]
        elif kind == "settlements":
            rows = provider().settlements()
        elif kind == "projects":
            rows = provider().projects()
        elif kind == "datasets":
            rows = metadata()["datasets"]
        else:
            rows = provider().records("interventions" if kind == "interventions" else "service_complaints")
        out = io.StringIO(newline="")
        fields = list(dict.fromkeys(k for row in rows for k in row)) or ["id", "status"]
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            safe = {}
            for k, value in row.items():
                text = "" if value is None else json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
                safe[k] = "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text
            writer.writerow(safe)
        return Response(out.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="urbansaarthi-{kind}.csv"', "Cache-Control": "no-store"})

    return router
