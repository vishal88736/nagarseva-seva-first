"""UrbanSaarthi's focused FastAPI app; no model artifacts or ML runtime required."""
from __future__ import annotations

import base64
import binascii
from datetime import date, datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import secrets
from typing import Callable, Literal

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import Field

from model.src.urban_planning import compare_scenarios, dataset, prioritize
from .store import RecordStore
from .planning_schemas import Request, PriorityInput, ScenarioInput, EvidenceInput

SERVICES = {
    "water": {"unit": "hours/day", "direction": "at_least", "ceiling": 24},
    "sanitation": {"unit": "functional toilets", "direction": "at_least", "ceiling": 10000},
    "drainage": {"unit": "blocked segments", "direction": "at_most", "ceiling": 10000},
    "waste": {"unit": "collections/week", "direction": "at_least", "ceiling": 21},
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def access(x_officer_key: str | None = Header(None)):
    expected = os.getenv("NAGARSEVA_OFFICER_KEY")
    if expected and not secrets.compare_digest(expected, x_officer_key or ""):
        raise HTTPException(401, "Officer access key required.")
    if not expected and os.getenv("NAGARSEVA_MODE", "demo") != "demo":
        raise HTTPException(503, "Configure officer access before enabling a pilot.")


class WorkInput(Request):
    cluster_id: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=5, max_length=160)
    service: Literal["water", "sanitation", "drainage", "waste"]
    target: float = Field(ge=0)
    due_date: date
    actor: str = Field(min_length=2, max_length=80)
    scenario_snapshot: dict | None = None


class ActionInput(Request):
    action: Literal["start", "complete", "verify", "reopen"]
    actor: str = Field(min_length=2, max_length=80)
    notes: str = Field(min_length=5, max_length=2000)
    evidence_id: str | None = None
    measured_value: float | None = Field(None, ge=0)
    observed_at: datetime | None = None
    functioning_confirmed: bool = False


class ComplaintInput(Request):
    work_id: str
    text: str = Field(min_length=5, max_length=2000)


class ResolutionInput(Request):
    actor: str = Field(min_length=2, max_length=80)
    notes: str = Field(min_length=5, max_length=2000)


def history(record, action, actor, notes):
    record["history"].append({"at": now(), "action": action, "actor": actor, "notes": notes})


def public_access(x_officer_key: str | None = Header(None)):
    expected = os.getenv("NAGARSEVA_OFFICER_KEY")
    if not expected:
        raise HTTPException(503, "Configure NAGARSEVA_OFFICER_KEY before recording work against acquired source data")
    if not secrets.compare_digest(expected, x_officer_key or ""):
        raise HTTPException(401, "Officer access key required")


def decode_evidence(payload: EvidenceInput) -> bytes:
    try:
        raw = base64.b64decode(payload.content_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(422, "Invalid base64 file content.") from exc
    if not 0 < len(raw) <= 2_097_152:
        raise HTTPException(422, "Files must be nonempty and at most 2 MiB.")
    signatures = {"image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff", "application/pdf": b"%PDF-"}
    if payload.content_type in signatures and not raw.startswith(signatures[payload.content_type]):
        raise HTTPException(422, "File signature does not match its declared type.")
    if payload.content_type == "text/plain":
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(422, "Text evidence must be UTF-8.") from exc
    return raw


def create_router(store_provider: Callable[[], RecordStore], officer_access=access) -> APIRouter:
    router = APIRouter(prefix="/urban", tags=["UrbanSaarthi"])

    def cluster(cid):
        item = next((row for row in dataset()["clusters"] if row["id"] == cid), None)
        if item is None:
            raise HTTPException(404, "Cluster not found.")
        return item

    def transaction_error(exc):
        raise HTTPException(404 if isinstance(exc, LookupError) else 422, str(exc)) from exc

    @router.get("/health")
    def health():
        return {"status": "ok", "mode": "demonstration", "synthetic": True, "database": "SQLite",
                "officer_auth_required": bool(os.getenv("NAGARSEVA_OFFICER_KEY")), "real_pilot_approved": False}

    @router.get("/settlements")
    def settlements():
        return dataset()

    @router.post("/priority")
    def priority(payload: PriorityInput):
        try:
            return prioritize(dataset()["clusters"], payload.weights)
        except ValueError as exc:
            transaction_error(exc)

    @router.post("/scenarios/{cluster_id}")
    def scenarios(cluster_id: str, payload: ScenarioInput):
        cluster(cluster_id)
        try:
            return compare_scenarios(dataset(), cluster_id, payload.model_dump())
        except ValueError as exc:
            transaction_error(exc)

    @router.get("/state", dependencies=[Depends(officer_access)])
    def state():
        store = store_provider()
        evidence = [{key: value for key, value in item.items() if key != "content_base64"} for item in store.urban_records("evidence")]
        return {"works": store.urban_records("work"), "evidence": evidence,
                "complaints": store.urban_records("complaint"), "synthetic": True}

    @router.post("/works", dependencies=[Depends(officer_access)])
    def create_work(payload: WorkInput):
        cluster(payload.cluster_id)
        definition = SERVICES[payload.service]
        if payload.target > definition["ceiling"] or definition["direction"] == "at_least" and payload.target <= 0:
            raise HTTPException(422, "Target is outside the service's valid measurement range.")
        record = {**payload.model_dump(mode="json"), "id": "WORK-" + secrets.token_hex(5).upper(),
                  "unit": definition["unit"], "direction": definition["direction"], "created_at": now(),
                  "status": "planned", "verification": "unverified", "completed_at": None,
                  "completed_by": None, "verification_record": None, "synthetic": True, "history": []}
        history(record, "planned", payload.actor, "User-entered demonstration plan; no government approval implied.")
        with store_provider().connection(write=True) as db:
            return store_provider().save_urban_record(record, "work", db)

    @router.post("/works/{work_id}/evidence", dependencies=[Depends(officer_access)])
    def upload(work_id: str, payload: EvidenceInput):
        raw = decode_evidence(payload)
        store = store_provider()
        try:
            with store.connection(write=True) as db:
                work = store.urban_record(work_id, "work", db)
                record = {**payload.model_dump(), "filename": Path(payload.filename.replace("\\", "/")).name,
                          "id": "EVI-" + secrets.token_hex(5).upper(), "work_id": work_id,
                          "cluster_id": work["cluster_id"], "uploaded_at": now(), "bytes": len(raw),
                          "sha256": hashlib.sha256(raw).hexdigest(), "synthetic": True}
                store.save_urban_record(record, "evidence", db)
                history(work, "evidence_attached", payload.actor, payload.notes)
                store.save_urban_record(work, "work", db)
            return {key: value for key, value in record.items() if key != "content_base64"}
        except (ValueError, LookupError) as exc:
            transaction_error(exc)

    @router.get("/evidence/{evidence_id}/content", dependencies=[Depends(officer_access)])
    def content(evidence_id: str):
        try:
            with store_provider().connection() as db:
                item = store_provider().urban_record(evidence_id, "evidence", db)
            # Always download; uploaded HTML, SVG and executable formats are not accepted.
            return Response(base64.b64decode(item["content_base64"]), media_type=item["content_type"],
                            headers={"Content-Disposition": "attachment; filename=evidence", "X-Content-Type-Options": "nosniff"})
        except LookupError as exc:
            transaction_error(exc)

    @router.post("/works/{work_id}/action", dependencies=[Depends(officer_access)])
    def action(work_id: str, payload: ActionInput):
        store = store_provider()
        try:
            with store.connection(write=True) as db:
                work = store.urban_record(work_id, "work", db)
                if payload.action == "start":
                    if work["status"] != "planned":
                        raise ValueError("Only planned work can be started.")
                    work["status"] = "in_progress"
                elif payload.action == "complete":
                    if work["status"] != "in_progress":
                        raise ValueError("Start the work before marking physical completion.")
                    work.update(status="completed", verification="unverified", completed_at=now(), completed_by=payload.actor)
                elif payload.action == "reopen":
                    if work["status"] != "completed":
                        raise ValueError("Only completed work can be reopened.")
                    work.update(status="in_progress", verification="unverified", verification_record=None)
                else:
                    if work["status"] != "completed":
                        raise ValueError("Physical work must be completed before service verification.")
                    evidence = store.urban_record(payload.evidence_id or "", "evidence", db)
                    if evidence["work_id"] != work_id:
                        raise ValueError("Evidence must belong to this work.")
                    if payload.actor.casefold() in {work["completed_by"].casefold(), evidence["actor"].casefold()}:
                        raise ValueError("Use a reviewer different from the completion actor and evidence submitter.")
                    complaints = [item for item in store.urban_records("complaint", db) if item["work_id"] == work_id]
                    if any(item["status"] == "open" for item in complaints):
                        raise ValueError("Respond to open complaints before verifying the service.")
                    if complaints and evidence["uploaded_at"] < max(item["created_at"] for item in complaints):
                        raise ValueError("Attach fresh inspection evidence after the latest complaint.")
                    observed = payload.observed_at
                    if observed is None or observed.tzinfo is None:
                        raise ValueError("Supply a timezone-aware inspection time.")
                    if observed > datetime.now(timezone.utc) + timedelta(minutes=5) or observed < datetime.fromisoformat(work["completed_at"]) - timedelta(minutes=5):
                        raise ValueError("Inspection time must follow completion and not be in the future (five-minute clock tolerance).")
                    if datetime.now(timezone.utc) - observed > timedelta(days=7):
                        raise ValueError("An inspection older than seven days needs a fresh review.")
                    value = payload.measured_value
                    if value is None or value > SERVICES[work["service"]]["ceiling"]:
                        raise ValueError("Supply a valid measurement in the work's stated unit.")
                    meets = value >= work["target"] if work["direction"] == "at_least" else value <= work["target"]
                    if not payload.functioning_confirmed or not meets:
                        raise ValueError("Service functioning must be confirmed and the measured target met.")
                    work["verification"] = "verified"
                    work["verification_record"] = {**payload.model_dump(mode="json"), "verified_at": now(), "scope": "Demonstration review; not authenticated field validation"}
                history(work, payload.action, payload.actor, payload.notes)
                return store.save_urban_record(work, "work", db)
        except (ValueError, LookupError) as exc:
            transaction_error(exc)

    @router.post("/complaints", dependencies=[Depends(officer_access)])
    def complaint(payload: ComplaintInput):
        store = store_provider()
        try:
            with store.connection(write=True) as db:
                work = store.urban_record(payload.work_id, "work", db)
                record = {**payload.model_dump(), "id": "ISSUE-" + secrets.token_hex(5).upper(),
                          "cluster_id": work["cluster_id"], "status": "open", "created_at": now(),
                          "resolved_at": None, "resolution_notes": None, "history": [], "synthetic": True}
                history(record, "reported", "demo resident", payload.text)
                store.save_urban_record(record, "complaint", db)
                if work["verification"] == "verified":
                    work["verification"] = "disputed"
                history(work, "issue_reported", "demo resident", payload.text)
                store.save_urban_record(work, "work", db)
                return record
        except LookupError as exc:
            transaction_error(exc)

    @router.post("/complaints/{complaint_id}/resolve", dependencies=[Depends(officer_access)])
    def resolve(complaint_id: str, payload: ResolutionInput):
        store = store_provider()
        try:
            with store.connection(write=True) as db:
                item = store.urban_record(complaint_id, "complaint", db)
                if item["status"] != "open":
                    raise ValueError("This complaint already has a recorded response.")
                item.update(status="resolved", resolved_at=now(), resolution_notes=payload.notes)
                history(item, "response_recorded", payload.actor, payload.notes)
                # A complaint response never automatically verifies the associated service.
                return store.save_urban_record(item, "complaint", db)
        except (ValueError, LookupError) as exc:
            transaction_error(exc)

    return router


def create_app(db_path: str | Path | None = None, data_dir: str | Path | None = None) -> FastAPI:
    from .public_store import PublicStore
    from .public_data import create_public_router
    application = FastAPI(title="UrbanSaarthi", version="1.0.0",
                          description="Historical source exploration, prototype issue reporting and documented service assurance. No official municipal submission or automated eligibility decisions.")
    application.state.store = RecordStore(db_path or os.getenv("URBANSAARTHI_DB_PATH", str(Path(__file__).resolve().parents[1] / "data/local/urbansaarthi.sqlite3")))
    application.add_middleware(CORSMiddleware, allow_origins=os.getenv("NAGARSEVA_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173").split(","),
                               allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type", "X-Officer-Key", "Idempotency-Key"])
    application.include_router(create_router(lambda: application.state.store))
    source_dir = data_dir or os.getenv("URBANSAARTHI_DATA_DIR", str(Path(__file__).resolve().parents[3] / "data/processed"))
    application.state.public = PublicStore(application.state.store, source_dir)
    application.include_router(create_public_router(lambda: application.state.public, public_access, decode_evidence))
    from .citizen_issues import create_issue_router
    application.include_router(create_issue_router(lambda: application.state.public, public_access))
    return application


app = create_app()
