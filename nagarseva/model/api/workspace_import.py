"""User-supplied workspace data. No acquisition, inferred joins or invented indices."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import re

from shapely.geometry import shape

from .snapshot_validation import validate_snapshot, _wgs84

MAX_IMPORT_BYTES = 10 * 1024 * 1024
EMPTY_SPATIAL = {"type": "FeatureCollection", "features": []}


def text(value, label, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{label} must be nonempty text up to {limit} characters")
    return value.strip()


def identifier(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:_-]{0,99}", value):
        raise ValueError(f"{label} needs a stable ID using letters, digits, colon, underscore or hyphen")
    return value


def optional_text(value, label, limit=200):
    return None if value is None or value == "" else text(value, label, limit)


def source_date(value):
    if value is None:
        return None
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("source_date must be YYYY-MM-DD or null") from exc
    if parsed > datetime.now(timezone.utc).date():
        raise ValueError("source_date cannot be in the future")
    return parsed.isoformat()


def compile_workspace(payload, observation_model):
    """Return a normalized snapshot and reviewed/reported observations atomically."""
    if not isinstance(payload, dict):
        raise ValueError("Upload a JSON workspace or a GeoJSON FeatureCollection")
    raw = json.dumps(payload, allow_nan=False, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    if len(raw) > MAX_IMPORT_BYTES:
        raise ValueError("Dataset exceeds the 10 MiB import limit")
    if payload.get("synthetic", False) is not False or isinstance(payload.get("metadata"), dict) and payload["metadata"].get("synthetic", False) is not False:
        raise ValueError("Synthetic data belongs in the separate demonstration workspace")
    if payload.get("type") == "FeatureCollection":
        payload = {"title": payload.get("name", "My settlements"), "settlements": payload}
    unknown = set(payload) - {"title", "source", "source_date", "settlements", "observations", "projects", "spatial"}
    if unknown:
        raise ValueError("Unexpected dataset fields: " + ", ".join(sorted(unknown)))
    title = text(payload.get("title", "My workspace"), "Dataset title", 200)
    source = text(payload.get("source", "User-supplied dataset"), "Source")
    reference = source_date(payload.get("source_date"))
    collection = payload.get("settlements")
    if not isinstance(collection, dict) or collection.get("type") != "FeatureCollection" or not isinstance(collection.get("features"), list):
        raise ValueError("settlements must be a GeoJSON FeatureCollection")
    _wgs84(collection, "Settlement collection")
    if not 1 <= len(collection["features"]) <= 10000:
        raise ValueError("Import between 1 and 10000 settlement features")
    settlements = []
    for feature in collection["features"]:
        if not isinstance(feature, dict) or feature.get("type") != "Feature" or not isinstance(feature.get("properties"), dict):
            raise ValueError("Each settlement needs GeoJSON Feature properties")
        props = feature["properties"]
        if feature.get("synthetic", False) is not False or props.get("synthetic", False) is not False:
            raise ValueError("Synthetic settlements cannot enter the live workspace")
        if "indicators" in props:
            raise ValueError("Put indices in observations with their source, date and review status; not in feature properties")
        local_id = identifier(props.get("id", feature.get("id")), "Settlement")
        households = props.get("households")
        if households is not None and (type(households) is not int or not 0 <= households <= 1000000):
            raise ValueError(f"{local_id}: households must be an integer or null")
        settlements.append({"id": local_id, "source_id": text(props.get("source_id", local_id), "Source ID", 100),
                            "name": text(props.get("name"), f"{local_id} name", 200), "geometry": feature.get("geometry"),
                            "administrative_area": optional_text(props.get("administrative_area"), "Administrative area"), "source": text(props.get("source", source), "Settlement source"),
                            "source_date": source_date(props.get("source_date", reference)), "source_date_basis": "Date supplied by dataset owner",
                            "households": households, "households_source": text(props.get("households_source", source), "Household source"),
                            "data_completeness": 0, "synthetic": False, "record_type": "user_import", "limitations": []})
    ids = {row["id"] for row in settlements}
    projects = []
    project_input = payload.get("projects", [])
    if not isinstance(project_input, list) or len(project_input) > 10000:
        raise ValueError("projects must be a list with at most 10000 records")
    for row in project_input:
        if not isinstance(row, dict):
            raise ValueError("Each project must be an object")
        if row.get("synthetic", False) is not False:
            raise ValueError("Synthetic projects cannot enter the live workspace")
        projects.append({"id": identifier(row.get("id"), "Project"), "source_id": row.get("source_id"),
                         "settlement_id": row.get("settlement_id"), "scheme_name": text(row.get("scheme_name"), "Scheme name", 500),
                         "project_status": text(row.get("project_status", "unknown"), "Project status", 100),
                         "source_url": text(row.get("source_url", source), "Project source"), "source_date": source_date(row.get("source_date", reference)),
                         "geometry": row.get("geometry"), "administrative_area": optional_text(row.get("administrative_area"), "Project administrative area"), "village": optional_text(row.get("village"), "Village"),
                         "cts_raw": optional_text(row.get("cts_raw"), "CTS", 2000), "synthetic": False})
    spatial = payload.get("spatial", EMPTY_SPATIAL)
    features = spatial.get("features", []) if isinstance(spatial, dict) else []
    if len(features) > 10000:
        raise ValueError("Import at most 10000 context features")
    snapshot = {"metadata": {"title": title, "source_label": source, "source_type": "user_import", "synthetic": False,
                             "built_at": datetime.now(timezone.utc).isoformat(), "geographic_scope": "User-supplied settlement dataset",
                             "settlement_reference": reference, "settlement_count": len(settlements), "projects_count": len(projects),
                             "settlement_geometry_count": sum(row["geometry"] is not None for row in settlements),
                             "mapped_objects_count": len(features), "mapped_object_categories": {}, "limitations": []},
                "settlements": settlements, "projects": projects, "spatial": spatial, "geographic_units": [], "indicators": []}
    validate_snapshot(snapshot)
    import_id = hashlib.sha256(raw).hexdigest()
    observations = []
    entries = payload.get("observations", [])
    if not isinstance(entries, list) or len(entries) > 50000:
        raise ValueError("observations must be a list with at most 50000 records")
    observation_ids = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or type(entry.get("value")) is bool:
            raise ValueError("Each observation needs an object with a numeric or null value")
        row = observation_model.model_validate(entry).model_dump(mode="json")
        if row["settlement_id"] not in ids or row["geographic_resolution"] != "settlement":
            raise ValueError("Import observations must reference a settlement ID in this file")
        if row["verification_status"] == "historical_published":
            raise ValueError("Settlement observations cannot be labelled historical_published")
        row["id"] = row["id"] or f"IMPORT-{import_id[:20]}-{index}"
        if row["id"] in observation_ids:
            raise ValueError("Duplicate observation ID in dataset")
        observation_ids.add(row["id"])
        observations.append({**row, "synthetic": False, "import_id": import_id})
    now = datetime.now(timezone.utc)
    for settlement in settlements:
        covered = {row["indicator_type"] for row in observations if row["settlement_id"] == settlement["id"]
                   and row["unit"] == "deficit_0_100" and row["value"] is not None and row["verification_status"] == "field_verified"
                   and row["observation_date"] and timedelta(0) <= now - datetime.fromisoformat(row["observation_date"]) <= timedelta(days=365)}
        settlement["data_completeness"] = len(covered) / 5
    polygons = [shape(row["geometry"]) for row in settlements if row["geometry"] is not None]
    bounds = [min(s.bounds[0] for s in polygons), min(s.bounds[1] for s in polygons), max(s.bounds[2] for s in polygons), max(s.bounds[3] for s in polygons)] if polygons else None
    summary = {"dataset_id": import_id, "title": title, "settlements": len(settlements), "polygons": len(polygons), "projects": len(projects),
               "observations": len(observations), "context_features": len(features), "bounds": bounds,
               "warnings": (["Some settlements have no boundary geometry."] if len(polygons) < len(settlements) else [])}
    return snapshot, observations, summary
