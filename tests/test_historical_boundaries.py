"""Topology QA and immutable staging for the supplied display-only 2015 layer."""
import hashlib
import json
from pathlib import Path

import pytest
from stage_historical_boundaries import inspect, preserve, stage

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'nagarseva/website/public/data'


def square():
    return {'type':'Feature','properties':{'polyno':None},'geometry':{'type':'Polygon','coordinates':[[[72.9,19.0],[72.91,19.0],[72.91,19.01],[72.9,19.01],[72.9,19.0]]]}}


def test_staged_source_counts_topology_and_checksum():
    raw = (PUBLIC/'mumbai_slum_clusters_2015.geojson').read_bytes()
    metadata = json.loads((PUBLIC/'mumbai_slum_clusters_2015.metadata.json').read_text())
    checked = inspect(raw)
    assert checked['source_feature_count'] == 2542
    assert checked['valid_feature_count'] == 2517
    assert checked['coordinate_count'] == 70404
    assert checked['polyno_non_null_count'] == 0
    assert checked['fields'] == ['polyno']
    assert len(checked['excluded_features']) == 25
    assert checked['excluded_features'] == metadata['excluded_features']
    assert hashlib.sha256(raw).hexdigest() == metadata['sha256']
    assert metadata['retrieved_at'] is None
    assert metadata['reference_year'] == 2015 and metadata['analysis_allowed'] is False


@pytest.mark.parametrize('data',[None,[],{}, {'type':'FeatureCollection','features':[]}, {'type':'FeatureCollection','features':[square()],'crs':{'name':'EPSG:32643'}}])
def test_reject_invalid_collections(data):
    with pytest.raises(ValueError): inspect(json.dumps(data).encode())


def test_structurally_closed_but_self_intersecting_polygon_is_excluded():
    invalid = square()
    invalid['geometry']['coordinates'] = [[[72.9,19.0],[72.91,19.01],[72.9,19.01],[72.91,19.0],[72.9,19.0]]]
    quality = inspect(json.dumps({'type':'FeatureCollection','features':[square(),invalid]}).encode())
    assert quality['source_feature_count'] == 2 and quality['valid_feature_count'] == 1
    assert quality['excluded_features'][0]['source_feature_number'] == 2
    assert 'intersection' in quality['excluded_features'][0]['reason']


def test_immutable_staging_is_idempotent_and_rejects_conflicting_sources(tmp_path):
    source = tmp_path/'source'; source.mkdir()
    (source/'mumbai_slum_clusters_2015.geojson').write_text(json.dumps({'type':'FeatureCollection','features':[square()]}))
    (source/'mumbai_slum_clusters_2015.kml').write_text('<kml/>')
    (source/'resource.json').write_text(json.dumps({'result':{'name':'Mumbai - Slum Clusters Map 2015','url':'https://example.test/source.kml','package_id':'dataset','id':'resource'}}))
    first = stage(source,tmp_path/'public',tmp_path/'raw')
    second = stage(source,tmp_path/'public',tmp_path/'raw')
    assert first == second
    assert len(list((tmp_path/'raw').iterdir())) == 3
    (source/'mumbai_slum_clusters_2015.geojson').write_text(json.dumps({'type':'FeatureCollection','features':[square(),square()]}))
    with pytest.raises(ValueError,match='different input'): stage(source,tmp_path/'public',tmp_path/'raw')
    with pytest.raises(ValueError,match='Existing file differs'): preserve(tmp_path/'public/mumbai_slum_clusters_2015.geojson',b'other')
