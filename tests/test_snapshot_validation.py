"""Reject mixed-source and coordinate defects before replacing an active snapshot."""
from copy import deepcopy
import json

from fastapi.testclient import TestClient
import pytest

from model.api.snapshot_validation import validate_snapshot
from model.api.urban import create_app


def snapshot():
    settlement = {"id": "cluster-fixture", "source_id": "TEST_001", "name": "Fixture cluster", "source": "https://example.test/map",
                  "source_date": "2024", "geometry": None, "data_completeness": 0, "synthetic": False}
    project = {"id": "project-fixture", "source_id": None, "scheme_name": "Fixture scheme", "source_url": "https://example.test/projects",
               "source_date": None, "settlement_id": None, "project_status": "unknown", "geometry": None}
    return {"metadata": {"synthetic": False}, "settlements": [settlement], "projects": [project], "indicators": [],
            "spatial": {"type": "FeatureCollection", "features": [{"type": "Feature", "id": "node/1", "properties": {"category": "amenity"},
                         "geometry": {"type": "Point", "coordinates": [72.92, 19.06]}}]}}


def polygon():
    return {"type": "Polygon", "coordinates": [[[72.91, 19.05], [72.92, 19.05], [72.92, 19.06], [72.91, 19.05]]]}


def test_valid_snapshot_preserves_null_project_id_and_does_not_modify_source():
    data = snapshot()
    original = deepcopy(data)
    assert validate_snapshot(data) == ([], [])
    assert data == original
    assert data["projects"][0]["source_id"] is None
    for category in ("road", "building", "amenity", "transport", "water_infrastructure", "residential_context", "settlement", "project"):
        data["spatial"]["features"][0]["properties"]["category"] = category
        validate_snapshot(data)


@pytest.mark.parametrize("location", ["settlement", "project", "feature", "properties"])
def test_explicit_synthetic_source_cannot_hide_under_real_metadata(location):
    data = snapshot()
    row = {"settlement": data["settlements"][0], "project": data["projects"][0], "feature": data["spatial"]["features"][0],
           "properties": data["spatial"]["features"][0]["properties"]}[location]
    row["synthetic"] = True
    with pytest.raises(ValueError, match="Synthetic"):
        validate_snapshot(data)


def test_duplicate_official_ids_are_allowed_only_when_every_row_is_explicitly_ambiguous():
    data = snapshot()
    data["settlements"].append({**data["settlements"][0], "id": "cluster-fixture-other-row"})
    with pytest.raises(ValueError, match="Duplicate official"):
        validate_snapshot(data)
    data["settlements"][0]["source_id_unique"] = False
    with pytest.raises(ValueError, match="Duplicate official"):
        validate_snapshot(data)
    data["settlements"][1]["source_id_unique"] = False
    validate_snapshot(data)


@pytest.mark.parametrize("table", ["settlements", "projects"])
def test_duplicate_local_ids_are_never_upserted_as_two_source_records(table):
    data = snapshot()
    data[table].append(deepcopy(data[table][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        validate_snapshot(data)


@pytest.mark.parametrize("field,value", [("name", " "), ("source", ""), ("source_id", None), ("id", 12), ("source_date", True),
                                          ("data_completeness", float("nan")), ("data_completeness", True), ("data_completeness", 101)])
def test_settlement_schema_and_provenance_are_required(field, value):
    data = snapshot()
    data["settlements"][0][field] = value
    with pytest.raises(ValueError):
        validate_snapshot(data)


@pytest.mark.parametrize("field,value", [("scheme_name", ""), ("source_url", None), ("project_status", " "), ("source_id", []),
                                          ("settlement_id", "unknown-cluster"), ("settlement_id", {}), ("source_date", True)])
def test_project_unknowns_remain_null_but_invalid_fields_and_false_joins_are_rejected(field, value):
    data = snapshot()
    data["projects"][0][field] = value
    with pytest.raises(ValueError):
        validate_snapshot(data)


@pytest.mark.parametrize("location", ["settlement", "project", "spatial"])
def test_projected_coordinates_cannot_be_loaded_as_wgs84(location):
    data = snapshot()
    geometry = {"type": "Polygon", "coordinates": [[[280000, 2100000], [281000, 2100000], [281000, 2101000], [280000, 2100000]]]}
    row = data["spatial"]["features"][0] if location == "spatial" else data[location + "s"][0]
    row["geometry"] = geometry
    with pytest.raises(ValueError, match="WGS84"):
        validate_snapshot(data)


@pytest.mark.parametrize("geometry", [
    {"type": "Point", "coordinates": [72.9, float("nan")]},
    {"type": "Point", "coordinates": [72.9, 19.0, float("inf")]},
    {"type": "Point", "coordinates": [True, 19.0]},
    {"type": "Point", "coordinates": []},
    {"type": "GeometryCollection", "geometries": []},
    {"type": "Polygon", "coordinates": [[[72.9, 19.0], [72.91, 19.01], [72.9, 19.01], [72.91, 19.0], [72.9, 19.0]]]},
])
def test_spatial_geometry_validity_and_finite_ordinates(geometry):
    data = snapshot()
    data["spatial"]["features"][0]["geometry"] = geometry
    with pytest.raises(ValueError):
        validate_snapshot(data)


def test_spatial_categories_declared_crs_and_stringified_id_collisions():
    data = snapshot()
    data["spatial"]["crs"] = {"properties": {"name": "EPSG:32643"}}
    with pytest.raises(ValueError, match="WGS84"):
        validate_snapshot(data)
    del data["spatial"]["crs"]
    data["spatial"]["features"][0]["properties"]["category"] = "invented-layer"
    with pytest.raises(ValueError, match="category"):
        validate_snapshot(data)
    data["spatial"]["features"][0]["properties"]["category"] = "amenity"
    data["spatial"]["features"][0]["id"] = 1
    data["spatial"]["features"].append({**data["spatial"]["features"][0], "id": "1"})
    with pytest.raises(ValueError, match="Duplicate spatial"):
        validate_snapshot(data)


def test_available_polygons_remain_polygons_and_counts_cannot_misreport_geometry():
    data = snapshot()
    data["settlements"][0]["geometry"] = polygon()
    data["metadata"]["settlement_geometry_count"] = 1
    validate_snapshot(data)
    data["metadata"]["settlement_geometry_count"] = 0
    with pytest.raises(ValueError, match="does not match"):
        validate_snapshot(data)
    data["metadata"].pop("settlement_geometry_count")
    data["settlements"][0]["geometry"] = {"type": "Point", "coordinates": [72.9, 19.0]}
    with pytest.raises(ValueError, match="geometry type"):
        validate_snapshot(data)


def test_invalid_refresh_preserves_active_source_rows_and_operations(tmp_path, monkeypatch):
    monkeypatch.setenv("NAGARSEVA_OFFICER_KEY", "validation-fixture-key")
    path = tmp_path / "urban_real.json"
    data = snapshot()
    path.write_text(json.dumps(data))
    app = create_app(tmp_path / "records.sqlite3", tmp_path)
    client = TestClient(app)
    before = client.get("/urban/data/metadata").json()["snapshot"]["snapshot_sha256"]
    work = client.post("/urban/data/interventions", headers={"X-Officer-Key": "validation-fixture-key"}, json={
        "settlement_id": "cluster-fixture", "intervention_type": "water", "description": "Fixture inspection plan",
        "planned_start": "2026-01-01", "planned_end": "2026-01-02", "actor": "fixture-planner"})
    assert work.status_code == 201
    data["settlements"][0]["name"] = "This unvalidated name must not be applied"
    data["projects"][0]["synthetic"] = True
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Synthetic"):
        app.state.public.sync_snapshot()
    assert client.get("/urban/data/settlements").json()["items"][0]["name"] == "Fixture cluster"
    assert client.get("/urban/data/metadata").json()["snapshot"]["snapshot_sha256"] == before
    assert client.get("/urban/data/interventions", headers={"X-Officer-Key": "validation-fixture-key"}).json()["items"][0]["id"] == work.json()["id"]
