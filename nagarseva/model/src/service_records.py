"""Source-labelled service measurements. Demo targets are explicitly local assumptions."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

SERVICES = {
    "water": {"field": "water_hours_per_day", "unit": "hours/day", "target": 4.0, "ceiling": 24.0, "higher": True, "department": "Water supply"},
    "sanitation": {"field": "toilets_per_100_people", "unit": "toilets/100 people", "target": 15.0, "ceiling": 100.0, "higher": True, "department": "Sanitation"},
    "power": {"field": "outage_hours_per_week", "unit": "outage hours/week", "target": 12.0, "ceiling": 168.0, "higher": False, "department": "Electricity liaison"},
    "waste": {"field": "waste_collection_frequency", "unit": "collections/week", "target": 3.0, "ceiling": 21.0, "higher": True, "department": "Solid waste"},
    "health": {"field": "clinic_within_1km", "unit": "clinic within 1 km (0/1)", "target": 1.0, "ceiling": 1.0, "higher": True, "department": "Public health"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def service_record(row: dict[str, Any], observations: list[dict], now: datetime | None = None, commitments: list[dict] | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    services = {}
    for name, definition in SERVICES.items():
        commitment = next((c for c in commitments or [] if c["service"] == name), None)
        history = sorted((o for o in observations if o["service"] == name), key=lambda o: (o["observed_at"], o["created_at"]), reverse=True)
        accepted = next((o for o in history if o["verification"] in {"resident_confirmed", "field_verified"}), None)
        raw = accepted["value"] if accepted else row.get(definition["field"])
        value = float(raw) if raw is not None and math.isfinite(float(raw)) else None
        target = commitment["target"] if commitment else definition["target"]
        meets_target = None if value is None else value >= target if definition["higher"] else value <= target
        # A local target attainment index, not a measured probability or legal certification.
        score = None if value is None else min(100.0, max(0.0, value / target * 100 if definition["higher"] else (100 if value <= target else target / value * 100)))
        observed_at = accepted["observed_at"] if accepted else None
        stale = bool(observed_at and (now - datetime.fromisoformat(observed_at)).total_seconds() > 30 * 86400)
        services[name] = {
            "value": value, "unit": definition["unit"], "score": round(score, 1) if score is not None else None,
            "status": "unknown" if value is None else "stale" if stale else "compliant" if meets_target else "breach",
            "meets_target": meets_target, "target": target, "target_direction": "at_least" if definition["higher"] else "at_most",
            "standard_source": commitment["standard_source"] if commitment else "NagarSeva demo planning target; replace with the approved ward/project commitment",
            "standard_url": commitment.get("source_url") if commitment else None,
            "standard_synthetic": commitment["synthetic"] if commitment else True,
            "department": commitment["department"] if commitment else definition["department"], "observed_at": observed_at, "stale": stale,
            "source_label": accepted["source_label"] if accepted else "Seeded synthetic baseline; no field observation" if row.get("synthetic", True) else "No service observation is recorded for the approved pilot location",
            "source_url": accepted.get("evidence_url") if accepted else None,
            "verification": accepted["verification"] if accepted else "synthetic" if value is not None else "unknown",
            "synthetic": accepted["synthetic"] if accepted else bool(row.get("synthetic", True)),
            "history": history,
        }
    scores = [s["score"] for s in services.values() if s["score"] is not None and not s["stale"]]
    real_verified = sum(not s["synthetic"] and s["verification"] == "field_verified" and not s["stale"] for s in services.values())
    return {"pocket_id": row["pocket_id"], "assurance_index": round(sum(scores) / len(scores), 1) if scores else None,
            "services": services, "field_verified_services": real_verified, "known_services": len(scores),
            "synthetic": any(s["synthetic"] for s in services.values()), "updated_at": utc_now(),
            "index_description": "Average attainment of explicit local planning targets. Missing/stale observations are excluded."}
