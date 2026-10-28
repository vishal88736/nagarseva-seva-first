"""Exercise the actual mounted API/static wrapper without a listening socket."""
import importlib.util
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'nagarseva'))


@pytest.fixture
def hosted(tmp_path, monkeypatch):
    monkeypatch.setenv('URBANSAARTHI_DB_PATH', str(tmp_path / 'import.sqlite3'))
    monkeypatch.setenv('URBANSAARTHI_DATA_DIR', str(tmp_path / 'no-acquired-snapshot'))
    monkeypatch.setenv('URBANSAARTHI_ORIGIN_SECRET', 'a' * 64)
    monkeypatch.setenv('NAGARSEVA_OFFICER_KEY', 'b' * 64)
    monkeypatch.setenv('NAGARSEVA_MODE', 'hosted-demo')
    spec = importlib.util.spec_from_file_location('urban_hosted', ROOT / 'deploy/aws/app.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    frontend = tmp_path / 'frontend'
    frontend.mkdir()
    (frontend / 'index.html').write_text('<html><title>UrbanSaarthi</title></html>')
    return module, frontend, tmp_path / 'persistent.sqlite3'


def client(hosted):
    module, frontend, database = hosted
    return TestClient(module.build_app(frontend, database))


ORIGIN = {'X-Origin-Verify': 'a' * 64}
OFFICER = {**ORIGIN, 'X-Officer-Key': 'b' * 64}
WORK = {'cluster_id': 'US-A', 'title': 'AWS container persistence check', 'service': 'water',
        'target': 2, 'due_date': '2100-01-01', 'actor': 'Demo tester'}


@pytest.mark.parametrize('headers', [{}, {'X-Origin-Verify': 'wrong'}, {'X-Origin-Verify': b'\xff'}])
def test_direct_origin_requests_are_denied(hosted, headers):
    with client(hosted) as c:
        assert c.get('/api/urban/health', headers=headers).status_code == 403
        assert c.get('/', headers=headers).status_code == 403


def test_frontend_and_api_share_origin_and_api_errors_stay_api_errors(hosted):
    with client(hosted) as c:
        assert '<title>UrbanSaarthi</title>' in c.get('/', headers=ORIGIN).text
        health = c.get('/api/urban/health', headers=ORIGIN)
        assert health.json()['officer_auth_required'] is True
        assert health.headers['cache-control'] == 'no-store'
        assert c.get('/api/urban/nonexistent', headers=ORIGIN).status_code == 404
        assert c.post('/api/urban/priority', headers=ORIGIN, json={}).json()['items'][0]['score'] == 65


def test_historical_static_assets_are_served_separately_from_settlement_data(hosted):
    import hashlib
    import json
    _, frontend, _ = hosted
    assets = frontend / 'data'
    assets.mkdir()
    for name in ('mumbai_slum_clusters_2015.geojson', 'mumbai_slum_clusters_2015.metadata.json'):
        (assets / name).write_bytes((ROOT / 'nagarseva/website/public/data' / name).read_bytes())
    with client(hosted) as c:
        metadata = c.get('/data/mumbai_slum_clusters_2015.metadata.json', headers=ORIGIN).json()
        geometry = c.get('/data/mumbai_slum_clusters_2015.geojson', headers=ORIGIN)
        assert geometry.status_code == 200
        assert hashlib.sha256(geometry.content).hexdigest() == metadata['sha256']
        assert len(json.loads(geometry.content)['features']) == 2542
        assert c.get('/api/urban/data/settlements', headers=ORIGIN).json()['total'] == 0


def test_officer_protection_and_persistence_across_app_recreation(hosted):
    with client(hosted) as c:
        assert c.get('/api/urban/state', headers=ORIGIN).status_code == 401
        assert c.post('/api/urban/works', headers=ORIGIN, json=WORK).status_code == 401
        result = c.post('/api/urban/works', headers=OFFICER, json=WORK)
        assert result.status_code == 200
        work_id = result.json()['id']
    with client(hosted) as c:
        state = c.get('/api/urban/state', headers=OFFICER)
        assert state.json()['works'][0]['id'] == work_id
        assert state.headers['cache-control'] == 'no-store'


def test_declared_and_chunked_oversize_bodies_are_rejected(hosted):
    with client(hosted) as c:
        response = c.post('/api/urban/priority', headers={**ORIGIN, 'Content-Length': '3000001'}, content=b'{}')
        assert response.status_code == 413
        chunks = (b'x' * 100_000 for _ in range(31))
        assert c.post('/api/urban/priority', headers=ORIGIN, content=chunks).status_code == 413


@pytest.mark.parametrize('name,value', [('NAGARSEVA_OFFICER_KEY', ''), ('URBANSAARTHI_ORIGIN_SECRET', ''), ('NAGARSEVA_OFFICER_KEY', 'a' * 64)])
def test_insecure_startup_configuration_fails_closed(hosted, monkeypatch, name, value):
    module, frontend, database = hosted
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError):
        module.build_app(frontend, database)


def test_missing_frontend_build_is_not_a_successful_deployment(hosted, tmp_path):
    module, _, database = hosted
    with pytest.raises(RuntimeError, match='Build the frontend'):
        module.build_app(tmp_path / 'missing', database)


def test_hosted_public_data_empty_state_is_available_without_synthetic_substitution(hosted):
    with client(hosted) as c:
        health = c.get('/api/urban/data/health', headers=ORIGIN)
        assert health.status_code == 200
        assert health.json()['snapshot_loaded'] is False
        assert health.json()['synthetic'] is False
        settlements = c.get('/api/urban/data/settlements', headers=ORIGIN)
        assert settlements.status_code == 200
        assert settlements.json()['items'] == []
        assert settlements.json()['total'] == 0
        assert c.get('/api/urban/data/spatial', headers=ORIGIN).json()['features'] == []
        assert c.get('/api/urban/data/interventions', headers=ORIGIN).status_code == 401
        assert c.get('/api/urban/data/interventions', headers=OFFICER).json()['items'] == []

@pytest.mark.parametrize('path,expected', [('/api/urban/data/workspace/preview', 200), ('/api/urban/data/workspace/import', 200), ('/api/urban/data/complaints', 413)])
def test_large_import_envelope_does_not_relax_other_request_limits(hosted, path, expected):
    from starlette.responses import JSONResponse
    module, _, _ = hosted
    async def body_echo(scope, receive, send):
        size = 0
        while True:
            message = await receive(); size += len(message.get('body', b''))
            if not message.get('more_body', False): break
        await JSONResponse({'bytes': size})(scope, receive, send)
    c = TestClient(module.OriginGuard(body_echo, 'a' * 64))
    try:
        response = c.post(path, content=b'x' * (module.MAX_BODY_BYTES + 1), headers=ORIGIN)
    finally:
        c.close()
    assert response.status_code == expected
    if expected == 200: assert response.json()['bytes'] == module.MAX_BODY_BYTES + 1


def test_import_limit_also_rejects_oversized_chunked_bodies(hosted):
    from starlette.responses import JSONResponse
    module, _, _ = hosted
    async def unreachable(scope, receive, send):
        await JSONResponse({'unexpected': True})(scope, receive, send)
    c = TestClient(module.OriginGuard(unreachable, 'a' * 64))
    try:
        response = c.post('/api/urban/data/workspace/import', content=iter([b'x' * 1_000_000] * 13), headers=ORIGIN)
    finally:
        c.close()
    assert response.status_code == 413


@pytest.mark.parametrize('path',['/dashboard','/settlements','/report-issue','/projects','/projects/data','/projects/priorities','/projects/scenarios','/projects/assurance'])
def test_known_product_routes_support_direct_navigation_and_refresh(hosted,path):
    with client(hosted) as c:
        response=c.get(path,headers=ORIGIN)
        assert response.status_code==200 and '<title>UrbanSaarthi</title>' in response.text
        assert c.get('/data/missing.geojson',headers=ORIGIN).status_code==404
        assert c.get('/api/missing',headers=ORIGIN).status_code==404
