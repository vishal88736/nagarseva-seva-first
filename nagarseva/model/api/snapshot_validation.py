"""Validate published aggregates without allocating them to settlement records."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import math

from shapely.errors import ShapelyError
from shapely.geometry import shape


RESOLUTIONS = {"country", "state", "district", "city", "town", "ward"}
INDICATORS = {"water", "sanitation", "drainage", "housing", "access", "risk",
              "population", "households", "household_amenities", "water_hours", "functional_toilets", "blocked_drains"}
SPATIAL_CATEGORIES = {"road", "building", "amenity", "transport", "residential_context", "water_infrastructure", "settlement", "project"}
SPATIAL_GEOMETRIES = {"Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"}
WGS84_NAMES = {"EPSG:4326", "urn:ogc:def:crs:EPSG::4326", "urn:ogc:def:crs:OGC:1.3:CRS84", "urn:ogc:def:crs:OGC::CRS84"}


def _text(row, field, context):
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} requires nonempty {field}")
    return value


def _source_row(row, context):
    if not isinstance(row, dict):
        raise ValueError(f"{context} must be an object")
    # Older local fixtures omit the flag; an explicit non-false flag can never
    # enter the acquired workspace, even when metadata.synthetic is false.
    if row.get("synthetic", False) is not False:
        raise ValueError(f"Synthetic or unlabelled {context} cannot enter an acquired snapshot")


def _wgs84(container, context):
    if "crs" not in container:
        return  # RFC 7946 default is longitude/latitude WGS84.
    crs = container["crs"]
    if (not isinstance(crs, dict) or not isinstance(crs.get("properties"), dict)
            or not isinstance(crs["properties"].get("name"), str) or crs["properties"]["name"] not in WGS84_NAMES):
        raise ValueError(f"{context} must use WGS84 longitude/latitude GeoJSON")


def _finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except (OverflowError, TypeError):
        return False


def _coordinates(values):
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("Geometry coordinates must be nonempty arrays")
    if all(type(value) in (int, float) for value in values):
        if len(values) not in (2, 3) or not all(_finite_number(value) for value in values):
            raise ValueError("Geometry positions must have two or three finite numeric ordinates")
        if not (-180 <= values[0] <= 180 and -90 <= values[1] <= 90):
            raise ValueError("Geometry coordinates are outside WGS84 bounds")
        return
    for value in values:
        _coordinates(value)


def _geometry(geometry, allowed, context, nullable=True):
    if geometry is None:
        if nullable:
            return
        raise ValueError(f"{context} requires a geometry")
    if not isinstance(geometry, dict) or not isinstance(geometry.get("type"), str) or geometry["type"] not in allowed:
        raise ValueError(f"Unsupported geometry type in {context}")
    _wgs84(geometry, context)
    _coordinates(geometry.get("coordinates"))
    try:
        result = shape(geometry)
        if result.is_empty or not result.is_valid or not all(math.isfinite(value) for value in result.bounds):
            raise ValueError(f"Invalid or empty geometry in {context}")
    except (TypeError, KeyError, IndexError, ShapelyError) as exc:
        raise ValueError(f"Invalid geometry schema in {context}") from exc


def validate_snapshot(data):
    """Validate an acquired snapshot before changing any persisted source rows.

    Returns ``(geographic_units, published_observations)`` like
    :func:`published_context`; it does not mutate or repair the supplied data.
    Published duplicate cluster IDs remain usable only when every affected row
    explicitly marks the source identifier as non-unique and has its own local ID.
    """
    if not isinstance(data, dict) or not isinstance(data.get("metadata"), dict) or data["metadata"].get("synthetic") is not False:
        raise ValueError("Public snapshot must be an explicitly non-synthetic object")
    for table in ("settlements", "projects"):
        if not isinstance(data.get(table), list):
            raise ValueError(f"Snapshot {table} must be a list")
    units, observations = published_context(data)
    identifiers, official_ids = set(), Counter()
    for item in data["settlements"]:
        _source_row(item, "settlement")
        identifier = _text(item, "id", "Settlement")
        if identifier in identifiers:
            raise ValueError("Duplicate settlement local ID in public snapshot")
        identifiers.add(identifier)
        source_id = _text(item, "source_id", "Settlement")
        official_ids[source_id] += 1
        _text(item, "name", "Settlement")
        _text(item, "source", "Settlement")
        if "source_id_unique" in item and type(item["source_id_unique"]) is not bool:
            raise ValueError("Settlement source_id_unique must be a boolean")
        completeness = item.get("data_completeness")
        if not _finite_number(completeness) or not 0 <= completeness <= 100:
            raise ValueError("Settlement data_completeness must be finite and between zero and 100")
        if "geometry" not in item:
            raise ValueError("Settlement geometry must be explicit; missing geometry is null")
        if item.get("source_date") is not None:
            _text(item, "source_date", "Settlement")
        _geometry(item["geometry"], {"Polygon", "MultiPolygon"}, "settlement")
    for item in data["settlements"]:
        if official_ids[item["source_id"]] > 1 and item.get("source_id_unique") is not False:
            raise ValueError("Duplicate official settlement IDs require source_id_unique=false on every source row")
    project_ids = set()
    for item in data["projects"]:
        _source_row(item, "project")
        identifier = _text(item, "id", "Project")
        if identifier in project_ids:
            raise ValueError("Duplicate project local ID in public snapshot")
        project_ids.add(identifier)
        for field in ("scheme_name", "source_url", "project_status"):
            _text(item, field, "Project")
        if "source_id" not in item or item["source_id"] is not None and (not isinstance(item["source_id"], str) or not item["source_id"].strip()):
            raise ValueError("Project official source_id must be a nonempty string or null")
        if ("settlement_id" not in item or item["settlement_id"] is not None
                and (not isinstance(item["settlement_id"], str) or item["settlement_id"] not in identifiers)):
            raise ValueError("Project settlement join must reference an acquired settlement or remain null")
        if "source_date" not in item:
            raise ValueError("Project source_date must be explicit; unknown dates remain null")
        if item["source_date"] is not None:
            _text(item, "source_date", "Project")
        _geometry(item.get("geometry"), {"Point", "MultiPoint", "Polygon", "MultiPolygon"}, "project")
    spatial = data.get("spatial")
    if not isinstance(spatial, dict) or spatial.get("type") != "FeatureCollection" or not isinstance(spatial.get("features"), list):
        raise ValueError("Snapshot spatial data must be a GeoJSON FeatureCollection")
    _wgs84(spatial, "Spatial collection")
    feature_ids = set()
    for feature in spatial["features"]:
        _source_row(feature, "spatial feature")
        if feature.get("type") != "Feature":
            raise ValueError("Spatial collection contains a non-feature object")
        identifier = feature.get("id")
        if type(identifier) not in (str, int) or isinstance(identifier, str) and not identifier.strip():
            raise ValueError("Spatial feature requires a string or integer source ID")
        if str(identifier) in feature_ids:
            raise ValueError("Duplicate spatial feature ID in public snapshot")
        feature_ids.add(str(identifier))
        properties = feature.get("properties")
        _source_row(properties, "spatial properties")
        if not isinstance(properties.get("category"), str) or properties["category"] not in SPATIAL_CATEGORIES:
            raise ValueError("Spatial feature has an unsupported category")
        if properties.get("source_url") is not None:
            _text(properties, "source_url", "Spatial feature")
        _geometry(feature.get("geometry"), SPATIAL_GEOMETRIES, "spatial feature", nullable=False)
    expected_counts = {"settlement_count": len(data["settlements"]), "settlement_geometry_count": sum(item["geometry"] is not None for item in data["settlements"]),
                       "projects_count": len(data["projects"]), "mapped_objects_count": len(spatial["features"]),
                       "geographic_unit_count": len(units), "historical_observation_count": len(observations)}
    for name, count in expected_counts.items():
        if name in data["metadata"] and (type(data["metadata"][name]) is not int or data["metadata"][name] != count):
            raise ValueError(f"Snapshot {name} does not match the validated source rows")
    return units, observations


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
        if unit["id"] in by_id or not isinstance(unit.get("resolution"), str) or unit["resolution"] not in RESOLUTIONS:
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
        if not isinstance(row.get("geographic_unit_id"), str):
            raise ValueError("Published observation requires a geographic unit identifier")
        unit = by_id.get(row["geographic_unit_id"])
        if row.get("settlement_id") is not None or unit is None:
            raise ValueError("Published aggregates require their original geographic unit, not a settlement")
        if row.get("geographic_resolution") != unit["resolution"] or type(row.get("reference_year")) is not int or row["reference_year"] != unit["reference_year"]:
            raise ValueError("Published observation geography and reference year must match its unit")
        if row.get("verification_status") != "historical_published" or row.get("synthetic", False) is not False:
            raise ValueError("Downloaded aggregates must remain historical published observations")
        if not isinstance(row.get("indicator_type"), str) or row["indicator_type"] not in INDICATORS or row.get("unit") == "deficit_0_100":
            raise ValueError("Published aggregates cannot become normalized settlement deficit indices")
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in ("unit", "source", "method")):
            raise ValueError("Published observations require units, provenance and a method")
        value = row.get("value")
        if value is not None and (not _finite_number(value) or value < 0):
            raise ValueError("Published values must be nonnegative finite numbers or missing")
        if row.get("observation_date") is not None:
            try:
                if not isinstance(row["observation_date"], str):
                    raise ValueError()
                observed = datetime.fromisoformat(row["observation_date"])
                if observed.year != row["reference_year"]:
                    raise ValueError()
            except (ValueError, TypeError) as exc:
                raise ValueError("Published observation date must retain its reference year") from exc
    return units, observations
