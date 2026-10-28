"""Public source data and operational records, isolated from the synthetic sandbox."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path

from shapely.geometry import shape
from model.src.urban_planning import KEYS, prioritize
from .snapshot_validation import validate_snapshot


class SnapshotConflict(ValueError):
    pass


class PublicStore:
    def __init__(self, store, data_dir):
        self.store, self.data_dir = store, Path(data_dir)
        migration = Path(__file__).parent / "migrations/001_public_data.sql"
        with self.store.connection(write=True) as db:
            db.executescript(migration.read_text())
            db.execute("INSERT OR IGNORE INTO public_schema_migrations VALUES(1, ?)", (self.now(),))
        self.sync_snapshot()

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def encode(data):
        return json.dumps(data, ensure_ascii=False, allow_nan=False)

    def sync_snapshot(self):
        if self.metadata().get("source_type") == "user_import":
            return  # An imported workspace remains active across server restarts.
        path = self.data_dir / "urban_real.json"
        if not path.exists():
            return  # Retain the last imported snapshot when the acquisition mount is offline.
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        self.activate_snapshot(data, digest)

    def activate_snapshot(self, data, digest, imported_observations=None, expected_snapshot=None):
        if data.get("metadata", {}).get("synthetic") is not False:
            raise ValueError("Public snapshot must be explicitly non-synthetic")
        ids = [r["id"] for r in data["settlements"]]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate settlement IDs in public snapshot")
        units, observations = validate_snapshot(data)
        published_observations = observations
        observations = [*observations, *(imported_observations or [])]
        with self.store.connection(write=True) as db:
            active = db.execute("SELECT id FROM public_snapshots ORDER BY imported_at DESC, rowid DESC LIMIT 1").fetchone()
            if imported_observations is not None and (active[0] if active else None) != expected_snapshot:
                raise SnapshotConflict("Dataset changed after preview. Preview the file again before importing.")
            if active and active[0] == digest:
                return
            for item in data["settlements"]:
                geom = item.get("geometry")
                if geom:
                    s = shape(geom)
                    if s.is_empty or not s.is_valid or s.geom_type not in {"Polygon", "MultiPolygon"}:
                        raise ValueError("Invalid public settlement polygon")
                db.execute("INSERT INTO settlements VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET source_id=excluded.source_id, name=excluded.name, geometry=excluded.geometry, administrative_area=excluded.administrative_area, source=excluded.source, source_date=excluded.source_date, data_completeness=excluded.data_completeness, body=excluded.body",
                           (item["id"], item["source_id"], item["name"], self.encode(geom) if geom else None, item.get("administrative_area"), item["source"], item.get("source_date"), item["data_completeness"], self.encode(item)))
            for item in data["projects"]:
                db.execute("INSERT INTO redevelopment_projects VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET source_id=excluded.source_id, settlement_id=excluded.settlement_id, scheme_name=excluded.scheme_name, project_status=excluded.project_status, source_date=excluded.source_date, source_url=excluded.source_url, body=excluded.body",
                           (item["id"], item["source_id"], item["settlement_id"], item["scheme_name"], item["project_status"], item["source_date"], item["source_url"], self.encode(item)))
            for item in units:
                existing = db.execute("SELECT body FROM geographic_units WHERE id=?", (item["id"],)).fetchone()
                if existing and json.loads(existing[0]) != item:
                    raise ValueError("Published geographic unit ID changed; retain a versioned source identifier")
                db.execute("INSERT OR IGNORE INTO geographic_units VALUES(?,?,?,?,?,?)",
                           (item["id"], item["source_id"], item["name"], item["resolution"], item["reference_year"], self.encode(item)))
            for item in observations:
                existing = db.execute("SELECT body FROM indicator_observations WHERE id=?", (item["id"],)).fetchone()
                facts = lambda row: {k: v for k, v in row.items() if k not in {"retrieved_at", "import_id"}}
                if existing and facts(json.loads(existing[0])) != facts(item):
                    raise ValueError("Published observation ID changed; source revisions require a new identifier")
                db.execute("INSERT OR IGNORE INTO indicator_observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                           tuple(item.get(k) for k in ("id", "settlement_id", "geographic_unit_id", "indicator_type", "value", "unit", "reference_year", "observation_date", "geographic_resolution", "source", "verification_status")) + (self.encode(item),))
            db.execute("DELETE FROM spatial_features")  # Source snapshot only; no operational/user records here.
            for feature in data["spatial"]["features"]:
                geom = shape(feature["geometry"])
                if geom.is_empty or not geom.is_valid:
                    raise ValueError("Invalid source geometry in snapshot")
                db.execute("INSERT INTO spatial_features VALUES(?,?,?,?,?,?,?)", (str(feature["id"]), feature["properties"]["category"], *geom.bounds, self.encode(feature)))
            metadata = {**data["metadata"], "snapshot_sha256": digest, "active_settlement_ids": ids, "active_project_ids": [r["id"] for r in data["projects"]],
                        "active_geographic_unit_ids": [r["id"] for r in units], "active_published_observation_ids": [r["id"] for r in published_observations],
                        "historical_observation_count": len(published_observations),
                        "active_import_id": digest if imported_observations is not None else None,
                        "active_imported_observation_ids": [row["id"] for row in (imported_observations or [])],
                        "geographic_unit_count": len(units)}
            db.execute("INSERT INTO public_snapshots VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET imported_at=excluded.imported_at,body=excluded.body", (digest, self.now(), self.encode(metadata)))
            # IDs removed from a source refresh are retained for existing interventions but excluded from the active view.

    def metadata(self):
        with self.store.connection() as db:
            row = db.execute("SELECT body FROM public_snapshots ORDER BY imported_at DESC, rowid DESC LIMIT 1").fetchone()
        return json.loads(row[0]) if row else {"title": "No dataset loaded", "synthetic": False, "active_settlement_ids": [], "active_project_ids": [], "settlement_count": 0, "settlement_geometry_count": 0, "projects_count": 0, "mapped_objects_count": 0, "limitations": ["Import your dataset from Data & access."]}

    def records(self, table, db=None):
        allowed = {"settlements", "redevelopment_projects", "indicator_observations", "interventions", "inspection_evidence", "verification_records", "service_complaints", "geographic_units", "field_surveys"}
        if table not in allowed:
            raise ValueError("Unsupported table")
        if db is None:
            with self.store.connection() as connection:
                return self.records(table, connection)
        return [json.loads(row[0]) for row in db.execute(f"SELECT body FROM {table} ORDER BY id")]

    def record(self, table, identifier, db=None):
        item = next((r for r in self.records(table, db) if r["id"] == identifier), None)
        if item is None:
            raise LookupError("Record not found")
        return item

    def settlements(self):
        ids = set(self.metadata()["active_settlement_ids"])
        return [r for r in self.records("settlements") if r["id"] in ids]

    def projects(self):
        ids = set(self.metadata()["active_project_ids"])
        return [r for r in self.records("redevelopment_projects") if r["id"] in ids]

    def context(self):
        metadata = self.metadata()
        ids = set(metadata.get("active_published_observation_ids", []))
        units = set(metadata.get("active_geographic_unit_ids", []))
        return {"geographic_units": [r for r in self.records("geographic_units") if r["id"] in units],
                "observations": [r for r in self.records("indicator_observations") if r["id"] in ids],
                "limitations": "Historical aggregates at their original geography. Not allocated to SRA settlements and excluded from current deficit rankings.",
                "synthetic": False}

    def priority(self, weights=None):
        active_imported_ids = set(self.metadata().get("active_imported_observation_ids", []))
        observations = [o for o in self.records("indicator_observations") if not o.get("import_id") or o["id"] in active_imported_ids]
        grouped = {}
        for observation in observations:
            grouped.setdefault((observation.get("settlement_id"), observation["indicator_type"]), []).append(observation)
        items = self.settlements()
        now = datetime.now(timezone.utc)
        for item in items:
            item["indicators"] = {key: None for key in KEYS}
            item["indicator_sources"] = {}
            for key in KEYS:
                candidates = [o for o in grouped.get((item["id"], key), []) if o["unit"] == "deficit_0_100" and o["value"] is not None and o["verification_status"] == "field_verified" and o["geographic_resolution"] == "settlement" and o.get("observation_date")]
                candidates = [o for o in candidates if timedelta(0) <= now - datetime.fromisoformat(o["observation_date"]) <= timedelta(days=365)]
                if candidates:
                    best = max(candidates, key=lambda o: (datetime.fromisoformat(o["observation_date"]), o["id"]))
                    latest_time = datetime.fromisoformat(best["observation_date"])
                    latest = [o for o in candidates if datetime.fromisoformat(o["observation_date"]) == latest_time]
                    if len({o["value"] for o in latest}) == 1:
                        item["indicators"][key] = best["value"]
                        item["indicator_sources"][key] = {k: best[k] for k in ("id", "source", "observation_date", "verification_status")}
        report = prioritize(items, weights)
        by_id = {item["id"]: item for item in items}
        for row in report["items"]:
            source = by_id[row["id"]]
            row["indicator_sources"] = source["indicator_sources"]
            row["indicators"] = source["indicators"]
            row["confidence"] = "Coverage of reviewed inputs only; predictive accuracy unvalidated" if row["rankable"] else "Insufficient evidence; further assessment required"
        report.update(synthetic=False, freshness_rule="Only field_verified settlement deficit indices observed within 365 days; prototype review rule, not official policy", explanation="Default weights are design assumptions. Physical measurements need an approved normalization protocol. Historical aggregates are excluded.")
        return report

    def stats(self):
        ranking = self.priority()
        active_ids = {row["id"] for row in ranking["items"]}
        works = [w for w in self.records("interventions") if w["settlement_id"] in active_ids]
        return {"settlements_loaded": len(ranking["items"]), "settlements_with_geometry": self.metadata().get("settlement_geometry_count", 0),
                "sufficient_indicator_coverage": sum(r["rankable"] for r in ranking["items"]),
                "documented_deficits": sum(v is not None and v >= 60 for r in ranking["items"] for v in r["indicators"].values()),
                "requires_assessment": sum(not r["rankable"] for r in ranking["items"]), "projects": len(self.projects()),
                "awaiting_verification": sum(w["status"] in {"reported_complete", "awaiting_verification", "requiring_reinspection"} for w in works),
                "verified_interventions": sum(w["status"] == "verified" for w in works),
                "overdue_interventions": sum(w["planned_end"] < self.now()[:10] and w["status"] != "verified" for w in works),
                "synthetic": False, "deficit_threshold": "Index >=60; illustrative review threshold"}
