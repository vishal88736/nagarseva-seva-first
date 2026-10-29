"""Production Chromium acceptance, synthetic test fixtures and disposable SQLite only.

No public data ingestion, external API, tile-provider or deployment validation.
Run with the project's Python environment after `npm run build`.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.runtime/integration-readiness/browser'

def port():
    with socket.socket() as stream:
        stream.bind(('127.0.0.1', 0))
        return stream.getsockname()[1]

def ready(url, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError('Owned acceptance service exited')
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(.2)
    raise RuntimeError('Acceptance service readiness timeout')

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks, errors, requests, processes, logs = [], [], [], [], []
    pw = None
    report = {'status':'failed', 'checkedAt':datetime.now(timezone.utc).isoformat(), 'checks':checks,
              'scope':'Production Chromium UI, synthetic software fixtures and disposable SQLite; no live authority connection', 'browserErrors':errors}
    try:
        with tempfile.TemporaryDirectory(prefix='urbansaarthi-acceptance-') as folder:
            folder = Path(folder)
            (folder/'no-real-data').mkdir()
            api, web = f'http://127.0.0.1:{port()}', f'http://127.0.0.1:{port()}'
            key = secrets.token_urlsafe(32)
            env = {**os.environ, 'URBANSAARTHI_DB_PATH':str(folder/'demo.sqlite3'), 'URBANSAARTHI_DATA_DIR':str(folder/'no-real-data'), 'NAGARSEVA_OFFICER_KEY':key, 'URBANSAARTHI_EVIDENCE_STORAGE':'sqlite', 'NAGARSEVA_API_TARGET':api}
            for name, command, cwd in [('api',[sys.executable,'-m','uvicorn','model.api.urban:app','--host','127.0.0.1','--port',api.rsplit(':',1)[1]],ROOT/'nagarseva'),('web',['npm','run','preview','--','--port',web.rsplit(':',1)[1],'--strictPort'],ROOT/'nagarseva/website')]:
                log = (OUT/f'{name}.log').open('w'); logs.append(log)
                processes.append(subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT))
            ready(api+'/urban/demo/health', processes[0]); ready(web, processes[1])
            def get(path):
                with urllib.request.urlopen(api+'/urban/'+path, timeout=20) as response:
                    return json.load(response)
            def state():
                return get('demo/workspace')
            initial = state()
            assert [len(initial[x]) for x in ['settlements','wards','issues','projects','visits','milestones']] == [100,24,60,20,30,40]
            assert all(x['status']=='not_provided' for x in get('integration/readiness')['categories'])
            checks.append('One deterministic persisted dataset: 100 settlements, 24 demo wards, 60 issues, 20 projects, 30 visits, 40 milestones; real integrations absent')
            if True:
                pw = sync_playwright().start()
                browser = pw.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH') or '/usr/bin/chromium')
                context = browser.new_context(viewport={'width':1586,'height':992}, accept_downloads=True)
                context.route('https://tile.openstreetmap.org/**', lambda route:route.abort())
                page = context.new_page(); page.set_default_timeout(7000); page.on('pageerror', lambda error:errors.append(str(error)))
                page.on('request', lambda request:requests.append(request.url))
                def goto(path):
                    page.goto(web+path); expect(page.locator('.demo-persistent-notice')).to_be_visible()
                    expect(page.locator('.demo-topbar .demo-mode')).to_be_visible()
                def save():
                    with page.expect_response(lambda response:response.url.endswith('/urban/demo/commands') and response.request.method=='POST') as saving:
                        page.get_by_role('dialog').get_by_role('button',name='Save',exact=True).click()
                    assert saving.value.status==200, saving.value.text()
                def close():
                    page.get_by_role('dialog').get_by_role('button', name='Close', exact=True).click()
                goto('/dashboard')
                expect(page.locator('.us-sidebar nav a')).to_have_count(5)
                expect(page.locator('.demo-settlement-polygon')).to_have_count(100)
                expect(page.locator('.demo-summary').first).to_contain_text('100')
                page.screenshot(path=str(OUT/'dashboard-desktop.png'),full_page=True)
                goto('/settlements')
                search = page.get_by_role('searchbox',name='Search settlements',exact=True)
                search.fill('001'); expect(page.locator('.us-table-wrap tbody tr')).to_have_count(1)
                expect(page.locator('.demo-settlement-polygon')).to_have_count(1)
                page.locator('.us-table-button').first.click()
                expect(page.locator('.demo-detail h2')).to_have_text('Settlement 001')
                expect(page.locator('.demo-settlement-polygon.is-selected')).to_have_count(1)
                page.locator('.demo-detail').get_by_role('tab',name='Services',exact=True).click()
                expect(page.locator('.demo-service-detail')).to_have_count(6)
                page.get_by_role('button',name='Reset filters',exact=True).click()
                expect(page.locator('.demo-settlement-polygon')).to_have_count(100)
                page.locator('.demo-settlement-polygon').nth(79).dispatch_event('click')
                expect(page.locator('.us-table-wrap tr.selected')).to_have_attribute('data-record-id','DEMO-SET-080')
                page.locator('.demo-settlement-polygon').nth(4).dispatch_event('click')
                expect(page.locator('.demo-detail h2')).to_have_text('Settlement 005')
                expect(page.locator('.demo-settlement-polygon.is-selected')).to_have_attribute('aria-label','Settlement 005')
                page.screenshot(path=str(OUT/'settlement-desktop.png'),full_page=True)
                checks.append('Actual map polygons and paginated list share filters and selection; six service gaps use stored indicators')
                goto('/report-issue?settlement=DEMO-SET-001')
                page.get_by_role('button',name='Submit issue',exact=True).click()
                expect(page.locator('[aria-invalid="true"]')).to_have_count(4)
                page.get_by_label('Category',exact=True).select_option('water')
                page.get_by_label('Issue title',exact=True).fill('Software acceptance water issue')
                page.get_by_label('Description',exact=True).fill('Synthetic browser test issue for a demonstration water service gap.')
                page.get_by_label('Location description',exact=True).fill('Demo test location only')
                page.get_by_role('button',name='Submit issue',exact=True).click()
                expect(page.get_by_role('dialog')).to_be_visible()
                expect(page.get_by_role('dialog')).to_contain_text('Software acceptance water issue')
                updated=state(); issue=next(x for x in updated['issues'] if x['title']=='Software acceptance water issue')
                assert len(updated['issues'])==61 and len(issue['history'])==1 and issue['settlementId']=='DEMO-SET-001'
                assert issue['history'][0]['eventType']=='issue_created'
                close(); page.reload(); assert len(state()['issues'])==61
                checks.append('Accessible required-field errors; public issue save confirmed by SQLite, genuine submission event and refresh persistence')
                goto('/projects/data')
                page.get_by_label('Administrator key (session only)',exact=True).fill(key)
                page.get_by_role('button',name='Use session key',exact=True).click()
                goto('/report-issue?issue='+issue['id'])
                dialog=page.get_by_role('dialog')
                dialog.get_by_label('Status',exact=True).select_option('acknowledged')
                dialog.get_by_label('Follow-up owner (start with Demo)',exact=True).fill('Demo Officer QA')
                dialog.get_by_label('Follow-up notes',exact=True).fill('Synthetic acknowledgement made during browser testing.')
                save()
                expect(dialog.get_by_text('Acknowledged',exact=True).first).to_be_visible()
                current=next(x for x in state()['issues'] if x['id']==issue['id']); assert current['status']=='acknowledged' and len(current['history'])>=2
                close()
                goto('/projects?project='+initial['projects'][0]['id'])
                expect(page.get_by_role('dialog')).to_be_visible()
                page.get_by_role('dialog').get_by_role('button',name='Add milestone',exact=True).click()
                page.get_by_label('Milestone name',exact=True).fill('Demo browser milestone')
                page.get_by_label('Planned date',exact=True).fill('2027-01-15')
                save()
                expect(page.get_by_role('dialog')).to_contain_text('Demo browser milestone')
                assert len(state()['milestones'])==41
                close()
                goto('/visits?new=1&settlement=DEMO-SET-001')
                page.get_by_label('Visit date',exact=True).fill((datetime.now(timezone.utc)+timedelta(days=5)).date().isoformat())
                page.get_by_label('Notes',exact=True).fill('Synthetic browser inspection plan.')
                save()
                expect(page.get_by_role('dialog')).to_contain_text('Synthetic browser inspection plan.')
                visit=next(x for x in state()['visits'] if x['notes']=='Synthetic browser inspection plan.')
                assert len(state()['visits'])==31
                page.get_by_role('dialog').get_by_role('button',name='Edit, complete or cancel visit',exact=True).click()
                page.get_by_role('dialog').get_by_label('Status',exact=True).select_option('cancelled')
                save()
                expect(page.get_by_role('dialog')).to_contain_text('Cancelled')
                assert next(x for x in state()['visits'] if x['id']==visit['id'])['status']=='cancelled'
                close()
                checks.append('Server-authorized issue acknowledgement and history, milestone creation, visit scheduling and cancellation update shared records')
                goto('/projects?tab=reports')
                with page.expect_download() as downloading:
                    page.get_by_role('button',name='Export filtered CSV',exact=True).click()
                csv=Path(downloading.value.path()).read_text()
                assert 'Synthetic demonstration data' in csv and 'DEMO-SET-001' in csv
                checks.append('CSV download contains actual filtered records and a synthetic-data disclaimer')
                goto('/data-integration')
                expect(page.get_by_role('heading',name='Real-World Data Integration',exact=True)).to_be_visible()
                expect(page.locator('.integration-matrix tbody tr')).to_have_count(7)
                expect(page.locator('.integration-matrix').get_by_text('Not provided',exact=True)).to_have_count(7)
                page.screenshot(path=str(OUT/'integration-desktop.png'),full_page=True)
                page.get_by_role('tab',name='Onboard a dataset',exact=True).click()
                file=page.locator('input[type=file]')
                file.set_input_files({'name':'unsupported.kml','mimeType':'application/xml','buffer':b'<kml/>'})
                expect(page.get_by_role('alert')).to_contain_text('.csv')
                file.set_input_files({'name':'too-large.csv','mimeType':'text/csv','buffer':b'x'*5242881})
                expect(page.get_by_role('alert')).to_contain_text('5')
                polygon={'type':'Polygon','coordinates':[[[72.85,19],[72.851,19],[72.851,19.001],[72.85,19.001],[72.85,19]]]}
                fixture={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'Cluster_ID':'QA-TEST-001','Slum_Name':'Synthetic test record only','Ward':'Test ward only'},'geometry':polygon}]}
                original=json.dumps(fixture).encode()
                file.set_input_files({'name':'synthetic-software-fixture.geojson','mimeType':'application/geo+json','buffer':original})
                permission=page.get_by_role('checkbox',name='I have permission to process this file here and have removed unnecessary personal or household information.',exact=True)
                expect(page.get_by_role('button',name='Inspect selected file',exact=True)).to_be_disabled()
                permission.check(); page.get_by_role('button',name='Inspect selected file',exact=True).click()
                expect(page.locator('.integration-column-tags')).to_contain_text('Cluster_ID')
                expect(page.get_by_label('Source field for Stable record identifier',exact=True)).to_have_value('Cluster_ID')
                expect(page.get_by_label('Source field for Settlement / project name',exact=True)).to_have_value('Slum_Name')
                page.get_by_role('button',name='Validate mapped records',exact=True).click()
                expect(page.locator('.integration-result-heading')).to_contain_text('Validation failed')
                page.get_by_role('checkbox',name='I confirm the geographic coordinates are WGS84 longitude / latitude in decimal degrees (RFC 7946). No reprojection is performed.',exact=True).check()
                page.get_by_role('button',name='Validate mapped records',exact=True).click()
                expect(page.locator('.integration-result-heading')).to_contain_text('Validation passed')
                expect(page.locator('.integration-result-heading')).to_contain_text('0 validation errors')
                expect(page.get_by_role('button',name='Confirm and save controlled import',exact=True)).to_be_disabled()
                page.get_by_label('Source / dataset title',exact=True).fill('Synthetic acceptance fixture')
                page.get_by_label('Publisher / data owner',exact=True).fill('Software test suite only')
                page.get_by_label('Documented geographic coverage',exact=True).fill('One synthetic test polygon in an illustrative extent')
                page.get_by_label('Source date',exact=True).fill('2026-10-01')
                page.get_by_label('Licence / permitted use',exact=True).fill('Demo data - test use only')
                page.get_by_label('Source link',exact=True).fill('https://example.test/demo-data')
                page.get_by_label('Data classification',exact=True).select_option('demo')
                page.get_by_role('checkbox',name='I confirm this isolated import and the source information above. The original file will be stored on this backend.',exact=True).check()
                page.screenshot(path=str(OUT/'integration-preview-desktop.png'),full_page=True)
                page.get_by_role('button',name='Confirm and save controlled import',exact=True).click()
                expect(page.locator('.integration-receipt')).to_contain_text('Controlled import saved')
                assert get('integration/readiness')['activeAdapter']=='sqlite-synthetic' and len(state()['settlements'])==100
                expect(page.locator('.integration-batch')).to_have_count(1)
                with page.expect_download() as download:
                    page.get_by_role('button',name='Download stored original',exact=True).click()
                assert Path(download.value.path()).read_bytes()==original
                page.reload(); page.get_by_role('tab',name='Onboard a dataset',exact=True).click()
                expect(page.locator('.integration-batch')).to_have_count(1)
                checks.append('GeoJSON actual metadata, existing-field suggestions, explicit CRS validation, preview, authorized confirmed import, hash/original preservation and refresh receipt; demo stays at 100')
                # CSV gets parsed, mapped and validated from its actual source rows.
                page.locator('input[type=file]').set_input_files({'name':'synthetic-invalid.csv','mimeType':'text/csv','buffer':b'id,name\nDUP,First synthetic row\nDUP,Second synthetic row\n'})
                page.get_by_label('Data category',exact=True).select_option('identifiers')
                permission.check(); page.get_by_role('button',name='Inspect selected file',exact=True).click()
                page.get_by_role('button',name='Validate mapped records',exact=True).click()
                expect(page.locator('.integration-result-heading')).to_contain_text('Validation failed')
                expect(page.get_by_text('Duplicate identifiers occur within the selected file. No row has been silently dropped.',exact=True)).to_be_visible()
                checks.append('CSV inspection, actual columns and duplicate-identifier validation; unsupported formats and oversized files rejected without saving')
                page.locator('input[type=file]').set_input_files({'name':'synthetic-mapped.csv','mimeType':'text/csv','buffer':b'external_code,label\nQA-CSV-001,Another synthetic software fixture\n'})
                permission.check(); page.get_by_role('button',name='Inspect selected file',exact=True).click()
                page.get_by_role('button',name='Validate mapped records',exact=True).click()
                expect(page.locator('.integration-result-heading')).to_contain_text('Validation failed')
                page.get_by_label('Source field for Stable record identifier',exact=True).select_option('external_code')
                page.get_by_label('Source field for Settlement / project name',exact=True).select_option('label')
                page.get_by_role('button',name='Validate mapped records',exact=True).click()
                expect(page.locator('.integration-result-heading')).to_contain_text('Validation passed')
                page.get_by_label('Source / dataset title',exact=True).fill('Synthetic mapped CSV acceptance fixture')
                page.get_by_label('Publisher / data owner',exact=True).fill('Software test suite only')
                page.get_by_label('Documented geographic coverage',exact=True).fill('One nonspatial synthetic software fixture')
                page.get_by_label('Source date',exact=True).fill('2026-10-01')
                page.get_by_label('Licence / permitted use',exact=True).fill('Demo data - test use only')
                page.get_by_label('Source link',exact=True).fill('https://example.test/demo-data')
                page.get_by_label('Data classification',exact=True).select_option('demo')
                page.get_by_role('checkbox',name='I confirm this isolated import and the source information above. The original file will be stored on this backend.',exact=True).check()
                def fail_import(route):
                    if route.request.method=='POST':route.fulfill(status=200,content_type='application/json',body='{"success":true}')
                    else:route.continue_()
                page.route('**/api/urban/integration/imports',fail_import)
                page.get_by_role('button',name='Confirm and save controlled import',exact=True).click()
                expect(page.get_by_role('alert')).to_contain_text('No successful import can be confirmed')
                expect(page.locator('.integration-receipt')).to_have_count(0)
                assert sum(x['importedBatches'] for x in get('integration/readiness')['categories'])==1
                page.unroute('**/api/urban/integration/imports',fail_import)
                page.get_by_role('button',name='Confirm and save controlled import',exact=True).click()
                expect(page.locator('.integration-receipt')).to_contain_text('Controlled import saved')
                expect(page.locator('.integration-batch')).to_have_count(2)
                assert len(state()['settlements'])==100
                checks.append('Manual mapping of actual CSV fields, confirmed CSV import, malformed HTTP-success rejection and no false saved state')

                page.get_by_role('tab',name='Roadmap & governance',exact=True).click()
                expect(page.locator('.integration-roadmap li')).to_have_count(8)
                expect(page.locator('.integration-governance article')).to_have_count(8)
                page.screenshot(path=str(OUT/'integration-governance-desktop.png'),full_page=True)
                for lang in ['hi','mr','en']:
                    page.locator('.us-language select').select_option(lang)
                    expect(page.locator('html')).to_have_attribute('lang',lang)
                    assert not page.locator('main').inner_text().find('ir.title')>=0
                    if lang!='en':
                        assert 'Real-World Data Integration' not in page.locator('main h1').inner_text()
                        page.set_viewport_size({'width':390,'height':844})
                        page.screenshot(path=str(OUT/f'integration-mobile-{lang}.png'),full_page=True)
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
                        page.locator('.us-mobile-nav').click()
                        expect(page.locator('.us-sidebar')).to_be_visible()
                        page.keyboard.press('Escape')
                        page.get_by_role('tab').nth(1).click()
                        assert not page.locator('main').inner_text().find('ir.step')>=0
                        page.set_viewport_size({'width':1586,'height':992})
                    for path in ['/methodology','/dashboard','/settlements','/report-issue','/projects','/housing','/services','/visits','/projects?tab=reports','/projects?tab=community','/projects/data','/projects/scenarios','/projects/priorities','/projects/assurance','/projects/reports','/projects/community','/data-integration/']:
                        goto(path)
                        expect(page.locator('main')).not_to_contain_text(re.compile(r'\b(?:d|ir)\.[A-Za-z]'))
                        expect(page.locator('html')).to_have_attribute('lang',lang)
                        if lang=='mr':
                            page.set_viewport_size({'width':390,'height':844})
                            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),path
                    page.set_viewport_size({'width':1586,'height':992})
                    goto('/data-integration')
                checks.append('English, Hindi and Marathi update headings, workflow, navigation and governance; 390px drawer and no document overflow')
                # The scoped reset preserves separately stored controlled imports.
                goto('/projects/data')
                page.get_by_role('button',name='Reset demonstration data',exact=True).click()
                expect(page.get_by_role('button',name='Confirm demo reset',exact=True)).to_be_disabled()
                page.get_by_role('checkbox',name="I understand that local demo changes and demo photos will be removed.",exact=True).check()
                page.get_by_role('button',name='Confirm demo reset',exact=True).click()
                expect(page.get_by_role('dialog')).to_have_count(0)
                assert len(state()['issues'])==60 and len(state()['visits'])==30 and len(state()['milestones'])==40
                assert sum(x['importedBatches'] for x in get('integration/readiness')['categories'])==2
                checks.append('Confirmed scoped reset restores initial counts and preserves controlled import provenance')
                assert not any('mumbai_slum_clusters_2015' in url or '/data/urban_real' in url for url in requests)
                assert not errors
                checks.append('No old GIS data requests and no uncaught browser errors')
                context.route('**/api/urban/demo/workspace',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"demo.error.backend"}'))
                goto('/dashboard')
                expect(page.get_by_role('alert')).to_be_visible()
                expect(page.locator('.demo-summary')).to_have_count(0)
                context.unroute('**/api/urban/demo/workspace')
                page.get_by_role('button',name='Retry',exact=True).click()
                expect(page.locator('.demo-summary')).to_have_count(4)
                checks.append('Backend failure shows an honest unavailable state, no invented metrics, and Retry restores the actual snapshot')

                browser.close()
        report['status']='passed'
    except Exception as exc:
        report['failure']=f'{type(exc).__name__}: {exc}'
        try:
            page.screenshot(path=str(OUT/'failure.png'),full_page=True)
            (OUT/'failure-body.txt').write_text(page.locator('body').inner_text())
        except Exception:
            pass
        raise
    finally:
        if pw is not None:
            pw.stop()
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        for log in logs: log.close()
        (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
