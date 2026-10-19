"""Actual Chromium UI checks with explicit test-only API fixtures.

This checks the field entry contract, not backend persistence or field validity.
The actual component is served by Vite; no real observations are created.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.runtime/field-collection-browser'
URL = 'http://127.0.0.1:14273'
SELECTED = {'id': 'fixture-source-label', 'source_id': 'TEST_ONLY_LABEL', 'name': 'TEST ONLY',
            'geometry': None, 'administrative_area': None, 'source': 'https://example.test',
            'source_date': None, 'source_date_basis': 'test fixture', 'retrieved_at': '',
            'record_type': 'test fixture', 'limitations': ['Not actual field data']}
HTML = '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="root"></div>
<script type="module">
import RefreshRuntime from '/@react-refresh';
RefreshRuntime.injectIntoGlobalHook(window);
window.$RefreshReg$ = () => {};
window.$RefreshSig$ = () => type => type;
window.__vite_plugin_react_preamble_installed__ = true;
</script>
<script type="module">
import React from '/node_modules/.vite/deps/react.js';
import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';
import PublicFieldCollection from '/src/urban/PublicFieldCollection.tsx';
import '/src/urban/urban.css';
ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(PublicFieldCollection, {
 selected: SELECTED_FIXTURE, officerKey: 'test-only-key', onChanged: () => { window.changes = (window.changes || 0) + 1; }
}));
</script></body></html>'''.replace('SELECTED_FIXTURE', json.dumps(SELECTED))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records, indices, errors, checks = [], [], [], []
    fail = {'surveys': True}
    with (OUT / 'vite.log').open('w') as log:
        server = subprocess.Popen(['npm', 'run', 'dev', '--', '--port', '14273', '--strictPort'], cwd=ROOT / 'nagarseva/website', stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError('Owned Vite process exited; inspect its log')
                try:
                    with urllib.request.urlopen(URL, timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(.2)
            else:
                raise RuntimeError('Vite readiness timeout')
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'))
                page = browser.new_page(viewport={'width': 1200, 'height': 1000}, accept_downloads=True)
                page.on('pageerror', lambda error: (errors.append(str(error)), print('BROWSER_ERROR', str(error))))
                page.route('**/field-test', lambda route: route.fulfill(status=200, content_type='text/html', body=HTML))

                def api(route):
                    request = route.request
                    parsed = urllib.parse.urlparse(request.url)
                    path = parsed.path.split('/urban/data')[-1]
                    assert request.headers.get('x-officer-key', '') in {'', 'test-only-key'}
                    if path == '/surveys':
                        if request.method == 'GET':
                            assert urllib.parse.parse_qs(parsed.query)['settlement_id'] == [SELECTED['id']]
                            if fail['surveys']:
                                fail['surveys'] = False
                                route.fulfill(status=503, json={'detail': 'TEST ONLY: temporary survey service failure'})
                            else:
                                route.fulfill(json={'items': records})
                        else:
                            payload = request.post_data_json
                            records.append({**payload, 'id': payload['survey_id']})
                            route.fulfill(status=201, json=records[-1])
                    elif path == '/indicators':
                        if request.method == 'GET':
                            route.fulfill(json={'items': indices, 'total': len(indices)})
                        else:
                            indices.append({**request.post_data_json, 'id': f'test-index-{len(indices)}'})
                            route.fulfill(status=201, json=indices[-1])
                    elif path == '/reports/surveys.csv':
                        assert request.headers.get('x-officer-key') == 'test-only-key'
                        route.fulfill(content_type='text/csv', body='survey_id,verification_status\nTEST-ONLY,reported\n')
                    else:
                        raise AssertionError(path)
                page.route('**/api/urban/data/**', api)
                page.goto(URL + '/field-test')
                expect(page.get_by_role('heading', name='Optional field collection')).to_be_visible()
                expect(page.get_by_role('alert')).to_contain_text('temporary survey service failure')
                page.get_by_role('button', name='Retry field records').click()
                expect(page.get_by_role('alert')).to_have_count(0)
                expect(page.get_by_label('Survey ID', exact=True)).to_be_hidden()
                expect(page.get_by_label('Reviewed deficit value')).to_be_hidden()
                checks.append('Actual component renders compact closed forms and recovers a failed survey request')

                page.get_by_text('Record an authorized field visit', exact=True).click()
                at = datetime.now(timezone.utc).isoformat()
                page.get_by_label('Survey ID', exact=True).fill('TEST-ONLY-VISIT-1')
                page.get_by_label('Survey inspector reference').fill('test-inspector')
                page.get_by_label('Survey protocol', exact=True).fill('TEST ONLY protocol v1, no field observations')
                page.get_by_label('Survey observation time').fill('2026-01-01T10:30')
                page.get_by_role('button', name='Save reported survey').click()
                expect(page.get_by_role('alert')).to_contain_text('with a timezone')
                assert not records
                page.get_by_label('Survey observation time').fill(at)
                page.get_by_label('Survey latitude').fill('19.06')
                page.get_by_role('button', name='Save reported survey').click()
                expect(page.get_by_role('alert')).to_contain_text('both coarse GPS')
                page.get_by_label('Survey longitude').fill('72.92')
                page.get_by_label('Survey evidence reference').fill('https://example.test/consented-fixture')
                page.get_by_role('button', name='Save reported survey').click()
                expect(page.get_by_role('alert')).to_contain_text('Confirm consent')
                page.get_by_label('Survey evidence consent').check()
                page.get_by_role('button', name='Save reported survey').click()
                expect(page.get_by_role('status').filter(has_text='Survey saved as reported')).to_be_visible()
                assert len(records) == 1 and not indices
                record = records[0]
                assert record['water_hours_per_day'] is record['functional_toilets_observed'] is record['blocked_drain_segments_observed'] is None
                assert record['verification_status'] == 'reported' and record['gps_latitude'] == 19.06 and record['gps_longitude'] == 72.92
                assert record['settlement_id'] == SELECTED['id']
                page.get_by_text('Survey records for this source record (1)', exact=True).click()
                expect(page.get_by_role('cell', name='TEST-ONLY-VISIT-1 Reported · unverified')).to_be_visible()
                expect(page.get_by_text('Water: Not observed hours/day', exact=False)).to_be_visible()
                page.get_by_label('Survey ID', exact=True).fill('TEST-ONLY-VISIT-1')
                page.get_by_label('Survey inspector reference').fill('test-inspector')
                page.get_by_label('Survey protocol', exact=True).fill('TEST ONLY approved revisit protocol')
                page.get_by_label('Survey observation time').fill(at)
                page.get_by_role('button', name='Save reported survey').click()
                expect(page.get_by_role('alert')).to_contain_text('already recorded')
                assert len(records) == 1
                page.get_by_label('Survey ID', exact=True).fill('TEST-ONLY-VISIT-2')
                page.get_by_label('Observed water hours', exact=True).fill('0')
                page.get_by_role('button', name='Save reported survey').click()
                expect(page.get_by_role('status').filter(has_text='Survey saved as reported')).to_be_visible()
                assert len(records) == 2 and records[1]['water_hours_per_day'] == 0
                assert records[1]['functional_toilets_observed'] is records[1]['gps_latitude'] is records[1]['gps_longitude'] is None
                assert not indices
                checks.append('Raw payload distinguishes zero/missing; timezone, paired GPS, consent and duplicate ID checks; no index POST generated')

                page.get_by_text('Record a separately reviewed deficit index', exact=True).click()
                page.get_by_label('Reviewed deficit value').fill('52.5')
                page.get_by_label('Deficit observation time').fill(at)
                page.get_by_label('Deficit source', exact=True).fill('TEST ONLY reviewed fixture source')
                page.get_by_label('Deficit normalization method').fill('TEST ONLY protocol; supplied normalized fixture value, not a survey conversion')
                page.get_by_label('Normalization protocol approved').check()
                page.get_by_label('Deficit inspector reference').fill('test-inspector')
                page.get_by_label('Deficit reviewer reference').fill('test-inspector')
                page.get_by_label('Deficit evidence reference').fill('https://example.test/review-fixture')
                page.get_by_label('Deficit evidence permission').check()
                page.get_by_role('button', name='Save reported index').click()
                expect(page.get_by_role('status').filter(has_text='Index saved as reported')).to_be_visible()
                assert len(indices) == 1 and indices[0]['verification_status'] == 'reported'
                assert indices[0]['reviewer_reference'] is None
                page.get_by_label('Reviewed deficit value').fill('52.5')
                page.get_by_label('Deficit observation time').fill(at)
                page.get_by_label('Deficit source', exact=True).fill('TEST ONLY reviewed fixture source')
                page.get_by_label('Deficit normalization method').fill('TEST ONLY reviewed protocol; externally supplied value')
                page.get_by_label('Normalization protocol approved').check()
                page.get_by_label('Deficit inspector reference').fill('test-inspector')
                page.get_by_label('Deficit reviewer reference').fill('test-inspector')
                page.get_by_label('Deficit evidence reference').fill('https://example.test/review-fixture')
                page.get_by_label('Deficit evidence permission').check()
                page.get_by_label('Confirm independent deficit review').check()
                page.get_by_role('button', name='Save user-recorded reviewed index').click()
                expect(page.get_by_role('alert')).to_contain_text('different from the inspector')
                assert len(indices) == 1
                page.get_by_label('Deficit reviewer reference').fill('test-reviewer')
                page.get_by_role('button', name='Save user-recorded reviewed index').click()
                expect(page.get_by_role('status').filter(has_text='Index saved with a user-recorded field review')).to_be_visible()
                assert len(indices) == 2 and indices[1]['verification_status'] == 'field_verified'
                assert indices[1]['unit'] == 'deficit_0_100' and indices[1]['value'] == 52.5
                assert indices[1]['reviewer_reference'] != indices[1]['inspector_reference']
                page.get_by_text('Recorded indicator observations (2)', exact=True).click()
                expect(page.get_by_text('Field-reviewed · user-recorded', exact=True)).to_be_visible()
                expect(page.get_by_text('TEST ONLY reviewed fixture source', exact=False).last).to_be_visible()
                checks.append('Reviewed index requires a distinct reviewer and explicit acknowledgement, retaining source/time/protocol')
                with page.expect_download() as download:
                    page.get_by_role('button', name='Export authorized survey CSV').click()
                assert download.value.suggested_filename == 'urbansaarthi-surveys.csv'
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
                page.screenshot(path=str(OUT / 'mobile.png'))
                assert not errors, errors
                checks.append('Protected CSV download and 390px layout checked without browser errors')
                browser.close()
            result = {'status': 'passed', 'checked_at': datetime.now(timezone.utc).isoformat(), 'scope': 'Actual Chromium UI with synthetic API fixtures; no field or backend validation', 'field_validation': False, 'checks': checks, 'browser_errors': errors}
            (OUT / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result, indent=2))
        finally:
            server.terminate()
            server.wait(timeout=15)


if __name__ == '__main__':
    main()
