"""Original-geography source imports, revisions and exclusion from live scores."""
from copy import deepcopy
import json

from fastapi.testclient import TestClient
import pytest

from model.api.urban import create_app
from model.api.snapshot_validation import published_context


def snapshot():
    unit = {"id": "census-2011-city-test", "source_id": "TEST-CITY", "name": "Fixture City",
            "resolution": "city", "reference_year": 2011, "source": "https://example.test/census"}
    observation = {"id": "census-2011-city-test-population", "settlement_id": None,
                   "geographic_unit_id": unit["id"], "indicator_type": "population", "value": 123,
                   "unit": "persons", "reference_year": 2011, "observation_date": None,
                   "geographic_resolution": "city", "source": unit["source"],
                   "verification_status": "historical_published", "method": "Published 2011 fixture table; not real data"}
    settlement = {"id": "fixture-settlement", "source_id": "TEST-1", "name": "Fixture source",
                  "geometry": None, "administrative_area": None, "source": "https://example.test/map",
                  "source_date": "2024", "data_completeness": 0, "synthetic": False}
    return {"metadata": {"synthetic": False, "settlement_geometry_count": 0},
            "settlements": [settlement], "projects": [], "geographic_units": [unit],
            "indicators": [observation], "spatial": {"type": "FeatureCollection", "features": []}}


def test_published_context_is_loaded_once_with_original_geography_and_year(tmp_path):
    path = tmp_path / "urban_real.json"
    data = snapshot()
    path.write_text(json.dumps(data))
    app = create_app(tmp_path / "records.sqlite3", tmp_path)
    client = TestClient(app)
    result = client.get("/urban/data/context").json()
    assert result["observations"][0]["value"] == 123
    assert result["observations"][0]["reference_year"] == 2011
    assert result["observations"][0]["settlement_id"] is None
    assert result["geographic_units"][0]["resolution"] == "city"
    assert client.get("/urban/data/indicators").json()["total"] == 1
    assert client.post("/urban/data/priority", json={}).json()["items"][0]["coverage_pct"] == 0
    # Rebuild timestamps change hashes but cannot duplicate or silently alter facts.
    data["metadata"]["built_at"] = "another retrieval, not an observation"
    data["indicators"][0]["retrieved_at"] = "2026-10-18T15:00:00+00:00"
    path.write_text(json.dumps(data))
    app.state.public.sync_snapshot()
    assert client.get("/urban/data/indicators").json()["total"] == 1
    data["indicators"][0]["value"] = 124
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="source revisions require"):
        app.state.public.sync_snapshot()
    assert client.get("/urban/data/context").json()["observations"][0]["value"] == 123
    # Explicit source revision retains the old observation and activates the new one.
    data["indicators"][0]["id"] += "-revision-2"
    path.write_text(json.dumps(data))
    app.state.public.sync_snapshot()
    assert client.get("/urban/data/indicators").json()["total"] == 2
    assert len(client.get("/urban/data/context").json()["observations"]) == 1


def test_public_source_exports_remain_public_but_survey_exports_are_protected(tmp_path, monkeypatch):
    monkeypatch.delenv("NAGARSEVA_OFFICER_KEY", raising=False)
    (tmp_path / "urban_real.json").write_text(json.dumps(snapshot()))
    client = TestClient(create_app(tmp_path / "records.sqlite3", tmp_path))
    response = client.get("/urban/data/reports/historical.csv")
    assert response.status_code == 200 and "2011" in response.text and "persons" in response.text
    assert client.get("/urban/data/reports/datasets.csv").status_code == 200
    assert client.get("/urban/data/reports/surveys.csv").status_code == 503
    monkeypatch.setenv("NAGARSEVA_OFFICER_KEY", "fixture-only-key")
    assert client.get("/urban/data/reports/surveys.csv").status_code == 401
    assert client.get("/urban/data/reports/surveys.csv", headers={"X-Officer-Key": "fixture-only-key"}).status_code == 200


def test_historical_only_snapshot_is_loaded_without_inventing_settlements(tmp_path):
    data = snapshot()
    data["settlements"] = []
    (tmp_path / "urban_real.json").write_text(json.dumps(data))
    client = TestClient(create_app(tmp_path / "records.sqlite3", tmp_path))
    assert client.get("/urban/data/health").json()["snapshot_loaded"] is True
    assert client.get("/urban/data/settlements").json()["items"] == []
    assert len(client.get("/urban/data/context").json()["observations"]) == 1


def test_optional_historical_raster_is_checked_before_serving(tmp_path):
    import hashlib
    import struct
    import zlib
    (tmp_path / "urban_real.json").write_text(json.dumps(snapshot()))
    client = TestClient(create_app(tmp_path / "records.sqlite3", tmp_path))
    assert client.get("/urban/data/map-overlay").json()["available"] is False
    assert client.get("/urban/data/map-overlay/image").status_code == 404
    # This is a transport fixture, not geospatial source imagery.
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
    image = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
             + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00")) + chunk(b"IEND", b""))
    (tmp_path / "sra_pilot_overlay.png").write_bytes(image)
    metadata = {"image_file": "sra_pilot_overlay.png", "image_sha256": hashlib.sha256(image).hexdigest(), "image_bytes": len(image),
                "bounds": [72.90, 19.04, 72.94, 19.08], "crs": "EPSG:3857", "analysis_allowed": False,
                "width": 1, "height": 1, "source_url": "https://media.sra.gov.in/test-fixture.pdf", "source_date": "2024",
                "source_sha256": "a" * 64, "control_point_residual_m": [0.1] * 4}
    (tmp_path / "sra_pilot_overlay.json").write_text(json.dumps(metadata))
    assert client.get("/urban/data/map-overlay").json()["available"] is True
    assert client.get("/urban/data/map-overlay/image").headers["content-type"] == "image/png"
    (tmp_path / "sra_pilot_overlay.png").write_bytes(b"modified source")
    assert client.get("/urban/data/map-overlay").status_code == 503
    assert client.get("/urban/data/map-overlay/image").status_code == 503
    metadata.update(image_sha256=hashlib.sha256(b"modified source").hexdigest(), image_bytes=len(b"modified source"))
    (tmp_path / "sra_pilot_overlay.json").write_text(json.dumps(metadata))
    # Matching hashes do not make arbitrary bytes a PNG.
    assert client.get("/urban/data/map-overlay").status_code == 503


@pytest.mark.parametrize("change", [
    {"settlement_id": "fixture-settlement"}, {"geographic_unit_id": "unknown"},
    {"geographic_resolution": "ward"}, {"reference_year": 2024},
    {"verification_status": "field_verified"}, {"unit": "deficit_0_100"},
    {"value": -1}, {"value": True}, {"value": float("inf")},
    {"observation_date": "2024-01-01"}, {"synthetic": True},
])
def test_historical_import_rejects_allocation_or_corrupted_source_claims(change):
    data = snapshot()
    data["indicators"][0].update(change)
    with pytest.raises(ValueError):
        published_context(data)


def test_published_geography_duplicate_missingness_and_invalid_geography():
    data = snapshot()
    data["indicators"][0]["value"] = None
    assert published_context(data)[1][0]["value"] is None
    duplicate = deepcopy(data)
    duplicate["geographic_units"] *= 2
    with pytest.raises(ValueError, match="Duplicate"):
        published_context(duplicate)
    data["geographic_units"][0]["resolution"] = "settlement"
    with pytest.raises(ValueError):
        published_context(data)
