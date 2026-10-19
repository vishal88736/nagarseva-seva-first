"""Validate published aggregates without allocating them to settlement records."""
from __future__ import annotations

from datetime import datetime
import math


RESOLUTIONS = {"country", "state", "district", "city", "town", "ward"}
INDICATORS = {"water", "sanitation", "drainage", "housing", "access", "risk",
              "population", "households", "household_amenities", "water_hours", "functional_toilets", "blocked_drains"}


def published_context(data):
    """Return validated source rows. Never accept current/field claims in a download."""
    units, observations = data.get("geographic_units", []), data.get("indicators", [])
    if not isinstance(units, list) or not isinstance(observations, list):
        raise ValueError("Published context must contain lists of geographic units and indicators")
    by_id = {}
    for unit in units:
        if not isinstance(unit, dict) or any(not isinstance(unit.get(k), str) or not unit[k].strip()
                                             for k in ("id", "source_id", "name", "source")):
            raise ValueError("Published geography requires a source ID, name and provenance")
        if unit["id"] in by_id or unit.get("resolution") not in RESOLUTIONS:
            raise ValueError("Duplicate or unsupported published geographic unit")
        year = unit.get("reference_year")
        if type(year) is not int or not 1900 <= year <= datetime.now().year:
            raise ValueError("Published geography must retain its reference year")
        if unit.get("synthetic", False) is not False:
            raise ValueError("Synthetic geography is not allowed in acquired context")
        by_id[unit["id"]] = unit
    seen = set()
    for row in observations:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
            raise ValueError("Published observation requires a source observation ID")
        if row["id"] in seen:
            raise ValueError("Duplicate published observation ID")
        seen.add(row["id"])
        unit = by_id.get(row.get("geographic_unit_id"))
        if row.get("settlement_id") is not None or unit is None:
            raise ValueError("Published aggregates require their original geographic unit, not a settlement")
        if row.get("geographic_resolution") != unit["resolution"] or row.get("reference_year") != unit["reference_year"]:
            raise ValueError("Published observation geography and reference year must match its unit")
        if row.get("verification_status") != "historical_published" or row.get("synthetic", False) is not False:
            raise ValueError("Downloaded aggregates must remain historical published observations")
        if row.get("indicator_type") not in INDICATORS or row.get("unit") == "deficit_0_100":
            raise ValueError("Published aggregates cannot become normalized settlement deficit indices")
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in ("unit", "source", "method")):
            raise ValueError("Published observations require units, provenance and a method")
        value = row.get("value")
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
            raise ValueError("Published values must be nonnegative finite numbers or missing")
        if row.get("observation_date"):
            try:
                observed = datetime.fromisoformat(row["observation_date"])
                if observed.year != row["reference_year"]:
                    raise ValueError()
            except (ValueError, TypeError) as exc:
                raise ValueError("Published observation date must retain its reference year") from exc
    return units, observations
