"""Actual CI container HTTP, upload, auth and restart-persistence checks."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get('URBANSAARTHI_SMOKE_BASE_URL', 'http://127.0.0.1:8080')
ORIGIN = {'X-Origin-Verify': os.environ['URBANSAARTHI_ORIGIN_SECRET']}
OFFICER = {**ORIGIN, 'X-Officer-Key': os.environ['NAGARSEVA_OFFICER_KEY']}
RECEIPT = Path('/tmp/urban-aws-smoke.json')


def request(path, headers=None, data=None):
    req = urllib.request.Request(BASE + path, headers=headers or {},
        data=json.dumps(data).encode() if data is not None else None)
    if data is not None:
        req.add_header('Content-Type', 'application/json')
    try:
        response = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as exc:
        response = exc
    return response.status, response.headers, response.read()


for _ in range(40):
    try:
        if request('/api/urban/health', ORIGIN)[0] == 200:
            break
    except OSError:
        pass
    time.sleep(1)
else:
    raise SystemExit('Container never became healthy.')

assert request('/api/urban/health')[0] == 403
assert request('/api/urban/state', ORIGIN)[0] == 401
assert request('/api/urban/state', {**ORIGIN, 'X-Officer-Key': 'wrong'})[0] == 401
status, headers, html = request('/', ORIGIN)
assert status == 200 and b'<html' in html.lower() and b'UrbanSaarthi' in html
assert headers['cache-control'] == 'no-store'
for secret in OFFICER.values():
    assert secret.encode() not in html

# Historical geometry is bundled with the UI, independent of acquired API data.
status, _, payload = request('/data/mumbai_slum_clusters_2015.metadata.json', ORIGIN)
assert status == 200, 'Historical boundary metadata is missing from the container'
reference = json.loads(payload)
status, _, payload = request('/data/mumbai_slum_clusters_2015.geojson', ORIGIN)
assert status == 200 and hashlib.sha256(payload).hexdigest() == reference['sha256']
assert len(json.loads(payload)['features']) == reference['source_feature_count'] == 2542
assert reference['valid_feature_count'] == 2517 and len(reference['excluded_features']) == 25
assert reference['analysis_allowed'] is False and reference['reference_year'] == 2015

# CI deliberately mounts no acquired source files. The active public API must
# expose an honest empty state while the separately labelled sandbox still works.
status, _, payload = request('/api/urban/data/health', ORIGIN)
assert status == 200, payload
health = json.loads(payload)
assert health['synthetic'] is False and health['snapshot_loaded'] is False
status, _, payload = request('/api/urban/data/settlements', ORIGIN)
assert status == 200 and json.loads(payload)['total'] == 0
assert request('/api/urban/data/interventions', ORIGIN)[0] == 401

if sys.argv[1] == 'create':
    status, _, payload = request('/api/urban/priority', ORIGIN, {})
    assert status == 200 and json.loads(payload)['items'][0]['score'] == 65
    status, _, payload = request('/api/urban/works', OFFICER, {
        'cluster_id': 'US-A', 'title': 'Hosted persistence validation', 'service': 'water',
        'target': 2, 'due_date': '2100-01-01', 'actor': 'CI demo operator'})
    assert status == 200, payload
    work_id = json.loads(payload)['id']
    status, _, payload = request(f'/api/urban/works/{work_id}/evidence', OFFICER, {
        'filename': 'synthetic-inspection.txt', 'content_type': 'text/plain',
        'content_base64': base64.b64encode(b'Synthetic CI evidence only.').decode(),
        'actor': 'CI demo inspector', 'notes': 'Container upload verification, not field evidence.'})
    assert status == 200, payload
    evidence = json.loads(payload)
    assert 'content_base64' not in evidence
    RECEIPT.write_text(json.dumps({'work': work_id, 'evidence': evidence['id']}))
else:
    receipt = json.loads(RECEIPT.read_text())
    status, headers, payload = request('/api/urban/state', OFFICER)
    assert status == 200 and headers['cache-control'] == 'no-store'
    state = json.loads(payload)
    assert any(w['id'] == receipt['work'] for w in state['works'])
    assert any(e['id'] == receipt['evidence'] for e in state['evidence'])
    assert request(f'/api/urban/evidence/{receipt["evidence"]}/content', ORIGIN)[0] == 401
    status, headers, payload = request(f'/api/urban/evidence/{receipt["evidence"]}/content', OFFICER)
    assert status == 200 and payload == b'Synthetic CI evidence only.'
    assert headers['cache-control'] == 'no-store'
    assert headers['x-content-type-options'] == 'nosniff'
print(f'Container {sys.argv[1]} checks passed (actual HTTP; synthetic CI records).')
