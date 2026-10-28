"""User data must drive the map, scores and scenarios without corrupting history."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest

from model.api.urban import create_app
from workspace_fixtures import workspace_fixture


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv('NAGARSEVA_OFFICER_KEY', 'test-only-key')
    db, source = tmp_path/'workspace.sqlite3', tmp_path/'source'
    client = TestClient(create_app(db, source)); client.headers['X-Officer-Key'] = 'test-only-key'
    return client, db, source


def apply(client, dataset):
    response = client.post('/urban/data/workspace/preview', json={'dataset': dataset})
    assert response.status_code == 200, response.text
    return client.post('/urban/data/workspace/import', json={'dataset': dataset, 'expected_snapshot': response.json()['expected_snapshot']})


def test_preview_is_authorized_and_never_activates_data(workspace):
    client, _, _ = workspace
    payload = {'dataset': workspace_fixture()}
    assert client.post('/urban/data/workspace/preview', json=payload, headers={'X-Officer-Key': ''}).status_code == 401
    result = client.post('/urban/data/workspace/preview', json=payload)
    assert result.status_code == 200
    assert result.json()['polygons'] == 2 and result.json()['observations'] == 5
    assert client.get('/urban/data/overview').json()['settlements_loaded'] == 0


def test_import_drives_scoring_geometry_projects_and_survives_restart(workspace):
    client, db, source = workspace
    assert apply(client, workspace_fixture()).status_code == 201
    stats = client.get('/urban/data/overview').json()
    assert stats['settlements_loaded'] == stats['settlements_with_geometry'] == 2
    assert stats['sufficient_indicator_coverage'] == 1
    ranks = {r['id']: r for r in client.post('/urban/data/priority', json={}).json()['items']}
    assert ranks['TEST-A']['score'] == 51 and ranks['TEST-A']['rank'] == 1
    assert ranks['TEST-B']['score'] is None and ranks['TEST-B']['rank'] is None
    selected = client.get('/urban/data/settlements/TEST-A').json()
    assert selected['households'] == 120 and selected['data_completeness'] == 1
    assert client.get('/urban/data/projects?settlement_id=TEST-A').json()['total'] == 1
    assert client.get('/urban/data/projects?settlement_id=TEST-B').json()['total'] == 0
    assert client.get('/urban/data/spatial?category=settlement').json()['total'] == 2
    assert client.get('/urban/data/context').json()['observations'] == []
    assert client.get('/urban/data/metadata').json()['datasets'] == []
    source.mkdir(); (source/'urban_real.json').write_text('This bundled input must not replace an imported workspace')
    restarted = TestClient(create_app(db, source))
    assert restarted.get('/urban/data/overview').json()['settlements_loaded'] == 2


@pytest.mark.parametrize('failure', ['duplicates', 'invalid_geometry', 'wrong_crs', 'unknown_join', 'invalid_households', 'invalid_ward', 'false_review', 'boolean_index', 'inline_indices', 'synthetic'])
def test_invalid_import_keeps_the_active_dataset(workspace, failure):
    client, _, _ = workspace; dataset = workspace_fixture()
    assert apply(client, dataset).status_code == 201
    previous = client.get('/urban/data/metadata').json()['snapshot']['snapshot_sha256']
    changed = deepcopy(dataset)
    if failure == 'duplicates': changed['settlements']['features'][1]['properties']['id'] = 'TEST-A'
    elif failure == 'invalid_geometry': changed['settlements']['features'][0]['geometry']['coordinates'] = [[[0,0],[1,1],[1,0],[0,1],[0,0]]]
    elif failure == 'wrong_crs': changed['settlements']['crs'] = {'type':'name','properties':{'name':'EPSG:3857'}}
    elif failure == 'unknown_join': changed['projects'][0]['settlement_id'] = 'UNKNOWN'
    elif failure == 'invalid_households': changed['settlements']['features'][0]['properties']['households'] = True
    elif failure == 'invalid_ward': changed['settlements']['features'][0]['properties']['administrative_area'] = {'bad':'shape'}
    elif failure == 'false_review': changed['observations'][0]['reviewer_reference'] = 'test-inspector'
    elif failure == 'boolean_index': changed['observations'][0]['value'] = True
    elif failure == 'synthetic': changed['settlements']['features'][0]['properties']['synthetic'] = True
    elif failure == 'inline_indices': changed['settlements']['features'][0]['properties']['indicators'] = {'water':80}
    response = client.post('/urban/data/workspace/import', json={'dataset': changed, 'expected_snapshot': previous})
    assert response.status_code == 422, response.text
    assert client.get('/urban/data/metadata').json()['snapshot']['snapshot_sha256'] == previous


def test_preview_conflict_is_explicit_and_does_not_overwrite(workspace):
    client, _, _ = workspace; dataset = workspace_fixture()
    preview = client.post('/urban/data/workspace/preview', json={'dataset':dataset}).json()
    other = deepcopy(dataset); other['title'] = 'Other dataset'
    assert apply(client, other).status_code == 201
    response = client.post('/urban/data/workspace/import', json={'dataset':dataset,'expected_snapshot':preview['expected_snapshot']})
    assert response.status_code == 409
    assert client.get('/urban/data/metadata').json()['snapshot']['title'] == 'Other dataset'


def test_refresh_retains_operations_without_reusing_retired_imported_indices(workspace):
    client, _, _ = workspace; dataset = workspace_fixture()
    assert apply(client, dataset).status_code == 201
    today = datetime.now(timezone.utc).date().isoformat()
    record = client.post('/urban/data/interventions', json={'settlement_id':'TEST-A','intervention_type':'water','description':'Software fixture only','planned_start':today,'planned_end':today,'actor':'test-planner'} )
    assert record.status_code == 201, record.text
    # Identical observations can be retained by their stable original IDs.
    dataset['title'] = 'Renamed workspace'
    assert apply(client, dataset).status_code == 201
    assert client.post('/urban/data/priority',json={}).json()['items'][0]['score'] == 51
    dataset['observations'] = []
    assert apply(client, dataset).status_code == 201
    assert all(row['score'] is None for row in client.post('/urban/data/priority',json={}).json()['items'])
    assert len(client.get('/urban/data/interventions').json()['items']) == 1


@pytest.mark.parametrize('kind', ['reported', 'stale', 'missing'])
def test_unreviewed_old_or_missing_indices_do_not_get_a_score(workspace, kind):
    client, _, _ = workspace; dataset = workspace_fixture()
    row = dataset['observations'][0]
    if kind == 'reported': row['verification_status'] = 'reported'
    elif kind == 'missing': row['value'] = None
    else:
        old = datetime.now(timezone.utc)-timedelta(days=366); row['observation_date'] = old.isoformat(); row['reference_year'] = old.year
    assert apply(client, dataset).status_code == 201
    first = next(row for row in client.post('/urban/data/priority', json={}).json()['items'] if row['id']=='TEST-A')
    assert first['score'] is None and first['indicators']['water'] is None


def test_standard_geojson_with_no_observations_is_accepted_as_unranked(workspace):
    client, _, _ = workspace
    assert apply(client, workspace_fixture()['settlements']).status_code == 201
    assert client.get('/urban/data/overview').json()['sufficient_indicator_coverage'] == 0
