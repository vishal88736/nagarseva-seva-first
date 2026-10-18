"""Offline protocol tests use fixtures. Live acquisition is reported separately."""
from copy import deepcopy

import httpx
import pytest
from shapely.geometry import shape

import data_common as dc
from ingest_osm import parse_map_xml, parse_osm
from ingest_sra import esri_to_geojson, query_layer
from ingest_sra_projects import parse_listing
from ingest_census import parse_workbook


@pytest.fixture
def downloader(tmp_path, monkeypatch):
    monkeypatch.setattr(dc, "ROOT", tmp_path)
    monkeypatch.setattr(dc, "DATA", tmp_path / "data")
    monkeypatch.setattr(dc, "META", tmp_path / "data/metadata")
    def make(handler, limit=10000):
        return dc.Downloader("test", transport=httpx.MockTransport(handler), max_bytes=limit)
    return make


@pytest.mark.parametrize("kind", ["timeout", "empty", "forbidden", "invalid_json", "error_json", "oversize"])
def test_bounded_download_failures(downloader, kind):
    def handler(request):
        if kind == "timeout":
            raise httpx.ReadTimeout("fixture timeout")
        return httpx.Response(403 if kind == "forbidden" else 200, content={"empty": b"", "invalid_json": b"<html>bad</html>", "error_json": b'{"error":{"code":499}}', "oversize": b"x" * 101}.get(kind, b"x"))
    with pytest.raises(dc.DownloadError):
        downloader(handler, 100).json("https://example.test/data", "error")


def test_download_cache_is_checked_and_originals_not_overwritten(downloader, tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"features": []})
    d = downloader(handler)
    data, info = d.json("https://example.test/data", "cache")
    assert data == {"features": []}
    d.json("https://example.test/data", "cache")
    assert len(calls) == 1
    (tmp_path / info["path"]).write_bytes(b"tampered")
    with pytest.raises(dc.DownloadError, match="modified"):
        d.json("https://example.test/data", "cache")


def feature(identifier=1, geometry=None):
    return {"type": "Feature", "id": identifier, "properties": {"oid": identifier}, "geometry": geometry or {"type": "Polygon", "coordinates": [[[72.91,19.05],[72.92,19.05],[72.92,19.06],[72.91,19.06],[72.91,19.05]]]}}


@pytest.mark.parametrize("kind", ["duplicate", "invalid", "wrong_crs", "bad_coordinates", "missing_geometry", "wrong_schema"])
def test_invalid_features_are_not_accepted(kind):
    collection = {"type": "FeatureCollection", "features": [feature()]}
    if kind == "wrong_schema":
        with pytest.raises(ValueError): dc.validate_features({})
        return
    if kind == "wrong_crs":
        collection["crs"] = {"properties": {"name": "EPSG:32643"}}
        with pytest.raises(ValueError): dc.validate_features(collection)
        return
    if kind == "duplicate": collection["features"].append(feature())
    if kind == "invalid": collection["features"][0]["geometry"]["coordinates"] = [[[0,0],[1,1],[0,1],[1,0],[0,0]]]
    if kind == "bad_coordinates": collection["features"][0]["geometry"] = {"type": "Point", "coordinates": [200,100]}
    if kind == "missing_geometry": collection["features"][0]["geometry"] = None
    assert dc.validate_features(collection)["valid"] is False


def test_reprojection_round_trip_preserves_coordinate_order():
    point = {"type": "Point", "coordinates": [72.92,19.06]}
    projected = dc.reproject_geometry(point, "EPSG:4326", "EPSG:32643")
    assert projected["coordinates"][0] > 200000
    result = dc.reproject_geometry(projected, "EPSG:32643")
    assert result["coordinates"] == pytest.approx(point["coordinates"], abs=1e-8)


def test_spatial_join_requires_unique_whole_geometry_containment():
    unit = feature(1); unit["properties"]["id"] = "ward-old"
    inside = feature("inside", {"type":"Point", "coordinates":[72.915,19.055]})
    outside = feature("outside", {"type":"Point", "coordinates":[73,19]})
    assert dc.strict_spatial_join([inside,outside],[unit])[0]["unit_id"] == "ward-old"
    assert dc.strict_spatial_join([inside,outside],[unit])[1]["unit_id"] is None
    assert dc.strict_spatial_join([inside],[unit,deepcopy(unit)])[0]["unit_id"] is None


def test_sra_id_batch_pagination_and_output_schema(downloader):
    calls=[]
    def handler(request):
        q = request.url.params; calls.append(dict(q))
        if q.get("returnIdsOnly"):
            return httpx.Response(200,json={"objectIds":[1,2,3]})
        values=list(map(int,q["objectIds"].split(',')))
        return httpx.Response(200,json={"type":"FeatureCollection", "features":[feature(i) for i in values]})
    layer={"id":42,"object_id_field":"oid","max_record_count":2}
    collection, quality, _ = query_layer(downloader(handler),"https://example.test/MapServer",layer)
    assert len(collection["features"]) == 3 and quality["valid"]
    assert [q.get("objectIds") for q in calls[1:]] == ["1,2","3"]


@pytest.mark.parametrize("ids", [[1,1], list(range(20001))])
def test_sra_refuses_duplicate_or_excessive_ids(downloader, ids):
    d=downloader(lambda r:httpx.Response(200,json={"objectIds":ids}))
    with pytest.raises(ValueError): query_layer(d,"https://example.test/sra",{"id":1,"object_id_field":"oid","max_record_count":250})


def test_sra_refuses_partial_batches(downloader):
    def handler(r):
        return httpx.Response(200,json={"objectIds":[1,2]}) if r.url.params.get("returnIdsOnly") else httpx.Response(200,json={"type":"FeatureCollection","features":[feature(1)]})
    with pytest.raises(ValueError,match="Incomplete"):
        query_layer(downloader(handler),"https://example.test/sra",{"id":1,"object_id_field":"oid","max_record_count":250})


def test_esri_rings_preserve_holes_and_crs():
    outer=[[0,0],[4,0],[4,4],[0,4],[0,0]]; hole=[[1,1],[3,1],[3,3],[1,3],[1,1]]
    result=esri_to_geojson({"spatialReference":{"wkid":4326},"features":[{"attributes":{"oid":1},"geometry":{"rings":[outer,hole]}}]},"oid")
    assert shape(result["features"][0]["geometry"]).area == 12


def test_osm_xml_geometry_tags_and_missing_nodes():
    raw=b'''<osm><node id="1" lon="72.91" lat="19.05" timestamp="2020-01-01T00:00:00Z"><tag k="amenity" v="school"/></node><node id="2" lon="72.92" lat="19.06"/><way id="3"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/></way></osm>'''
    collection, quality, rejected=parse_osm(parse_map_xml(raw))
    assert quality["valid"] and len(collection["features"])==2 and rejected==[]
    assert collection["features"][0]["properties"]["observation_date"] is None
    assert collection["features"][0]["properties"]["tags"] == {"amenity":"school"}
    with pytest.raises(ValueError,match="missing node"):
        parse_map_xml(raw.replace(b'ref="2"',b'ref="9"'))


def test_osm_empty_error_and_duplicate_results():
    assert parse_osm({"elements":[]})[1]["record_count"]==0
    with pytest.raises(ValueError): parse_osm({"elements":[],"remark":"timeout"})
    node={"type":"node","id":1,"lon":72.91,"lat":19.05,"tags":{"amenity":"toilets"}}
    with pytest.raises(ValueError,match="Duplicate"): parse_osm({"elements":[node,node]})


def test_osm_bad_relation_is_quarantined_without_fabricating_centroid():
    c,q,rejected=parse_osm({"elements":[{"type":"relation","id":1,"tags":{"amenity":"school"},"center":{"lat":19.05,"lon":72.91}}]})
    assert not c["features"] and len(rejected)==1 and q["valid"]


def test_listing_does_not_invent_project_status_ids_or_join():
    raw=b'<table><tr><th>SrNo</th><th>Scheme Name</th><th>Ward Name</th><th>Address</th><th>CTS No</th><th>Village</th></tr><tr><td>1</td><td>Test CHS</td><td>M-E</td><td>Example</td><td>1-A</td><td>Deonar</td></tr></table>'
    rows,fields=parse_listing(raw,"2026-01-01")
    assert rows[0]["source_id"] is rows[0]["source_date"] is rows[0]["settlement_id"] is None
    assert rows[0]["project_status"]=="unknown" and rows[0]["cts_raw"]=="1-A"
    with pytest.raises(ValueError):parse_listing(b'<html>login</html>',"2026")
    with pytest.raises(ValueError):parse_listing(b'<table><tr><td>Scheme Name</td><td>Ward Name</td><td>CTS No</td></tr></table>',"2026")


def test_excel_parser_checks_nonempty_cells_and_preserves_original_rows():
    from openpyxl import Workbook
    from io import BytesIO
    book=Workbook(); sheet=book.active; sheet.append(["State Code","Year","Households"]); sheet.append(["27",2011,100]); f=BytesIO();book.save(f)
    data=parse_workbook(f.getvalue(),".xlsx")
    assert data[0]["rows"][1]==["27",2011,100]


def test_inventory_preserves_legacy_and_has_exact_schema(tmp_path,monkeypatch):
    monkeypatch.setattr(dc,"ROOT",tmp_path);monkeypatch.setattr(dc,"META",tmp_path/"data/metadata")
    (tmp_path/"research").mkdir(); path=tmp_path/"research/dataset_inventory.csv";path.write_text('old_column\nold_fact\n')
    dc.inventory(dataset_name="fixture",access_status="metadata_only")
    assert path.read_text().splitlines()[0].split(',')==dc.INVENTORY_FIELDS
    assert path.with_name('dataset_inventory_legacy.csv').read_text()=='old_column\nold_fact\n'
