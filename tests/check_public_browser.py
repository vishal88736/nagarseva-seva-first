"""Actual browser + disposable API: user import through the five planning screens.

All injected values are explicit software fixtures, never field measurements.
"""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import expect, sync_playwright
from workspace_fixtures import workspace_fixture

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'.runtime/workspace-browser'
API = 'http://127.0.0.1:18101'
WEB = 'http://127.0.0.1:15175'


def wait_for(url, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError('Owned browser service exited; inspect .runtime/workspace-browser')
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(.2)
    raise RuntimeError('Browser service readiness timeout')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks, errors, processes, logs = [], [], [], []
    report = {'status':'failed', 'checked_at':datetime.now(timezone.utc).isoformat(), 'scope':'Actual Chromium and API using user-uploaded synthetic software fixtures in disposable SQLite', 'field_validation':False, 'checks':checks, 'browser_errors':errors}
    try:
        with tempfile.TemporaryDirectory(prefix='urban-workspace-browser-') as folder:
            key = secrets.token_urlsafe(32)
            env = {**os.environ, 'URBANSAARTHI_DB_PATH':str(Path(folder)/'test.sqlite3'), 'NAGARSEVA_OFFICER_KEY':key, 'URBANSAARTHI_EVIDENCE_STORAGE':'sqlite', 'NAGARSEVA_API_TARGET':API, 'URBANSAARTHI_DATA_DIR':str(Path(folder)/'empty-source')}
            for name, command, cwd in [('api',[sys.executable,'-m','uvicorn','model.api.urban:app','--host','127.0.0.1','--port','18101'],ROOT/'nagarseva'),('web',['npm','run','preview','--','--port','15175','--strictPort'],ROOT/'nagarseva/website')]:
                log = (OUT/f'{name}.log').open('w'); logs.append(log)
                processes.append(subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT))
            wait_for(API+'/urban/data/health',processes[0]); wait_for(WEB,processes[1])
            def api(path, private=False):
                request = urllib.request.Request(API+'/urban/data'+path,headers={'X-Officer-Key':key} if private else {})
                with urllib.request.urlopen(request,timeout=10) as response:
                    return json.load(response)
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH') or None)
                context = browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
                context.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
                page = context.new_page(); page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(WEB)
                expect(page.get_by_role('heading',name='UrbanSaarthi Dashboard',exact=True)).to_be_visible()
                assert page.get_by_role('heading',name='Dataset inventory',exact=True).count() == 0
                assert page.get_by_role('heading',name='Historical Census context',exact=True).count() == 0
                page.screenshot(path=str(OUT/'empty-overview.png'),full_page=True)
                checks.append('Empty product dashboard has a clear data entry path and keeps legacy planning tools accessible')
                page.get_by_role('button',name='Data sources',exact=True).click()
                page.get_by_label('Public data officer key').fill(key)
                page.get_by_role('button',name='Apply officer key',exact=True).click()
                with page.expect_download() as download:
                    page.get_by_role('button',name='Download template',exact=True).click()
                assert download.value.suggested_filename == 'urbansaarthi-workspace-template.json'
                filled_template = json.loads(Path(download.value.path()).read_text())
                filled_template['source'] = 'Software template validation'
                filled_template['source_date'] = datetime.now(timezone.utc).date().isoformat()
                filled_template['settlements']['features'][0]['properties'].update(id='TEMPLATE-TEST',name='Template software test')
                page.get_by_label('Dataset file').set_input_files({'name':'filled-template.json','mimeType':'application/json','buffer':json.dumps(filled_template).encode()})
                page.get_by_role('button',name='Validate file',exact=True).click()
                expect(page.get_by_role('button',name='Import validated dataset',exact=True)).to_be_visible()
                assert api('/overview')['settlements_loaded'] == 0
                page.get_by_label('Dataset file').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':b'{bad'})
                expect(page.get_by_role('alert')).to_be_visible()
                fixture = workspace_fixture()
                page.get_by_label('Dataset file').set_input_files({'name':'software-fixture.json','mimeType':'application/json','buffer':json.dumps(fixture).encode()})
                page.get_by_role('button',name='Validate file',exact=True).click()
                expect(page.get_by_role('button',name='Import validated dataset',exact=True)).to_be_visible()
                assert api('/overview')['settlements_loaded'] == 0
                page.get_by_role('button',name='Import validated dataset',exact=True).click()
                expect(page.get_by_role('status').filter(has_text='Dataset imported.')).to_be_visible()
                assert api('/overview')['settlements_loaded'] == 2
                checks.append('Template download, malformed-file recovery, nonmutating preview and actual authorized GeoJSON/observation/project import pass')
                page.locator('.us-sidebar nav').get_by_role('link',name='Projects & Reports',exact=True).click()
                page.get_by_role('tab',name='Data reports',exact=True).click()
                expect(page.locator('.dataset-report').nth(3).locator('dd').first).to_have_text('Not supplied')
                def nav(name):
                    mapping={'Overview':'Dashboard','Settlement map':'Explore Settlements'}
                    legacy={'Priorities':'prioritize','Scenarios':'compare','Service assurance':'assurance'}
                    if name in legacy:
                        page.goto(WEB+'/#'+legacy[name])
                    else:
                        page.get_by_role('navigation',name='Main navigation').get_by_role('link',name=mapping.get(name,name),exact=True).click()
                nav('Settlement map')
                expect(page.locator('.leaflet-container')).to_be_visible()
                expect(page.get_by_role('button',name='Settlement boundary Fixture Harbour',exact=True)).to_be_attached()
                page.locator('.workspace-settlement-list').get_by_role('button',name='Fixture Hill',exact=False).click()
                expect(page.get_by_role('heading',name='Fixture Hill',exact=True)).to_be_visible()
                boundary = page.get_by_role('button',name='Settlement boundary Fixture Hill',exact=True)
                expect(boundary).to_be_visible()
                box, extent = boundary.bounding_box(), page.locator('.leaflet-container').bounding_box()
                assert box and extent and extent['x'] <= box['x']+box['width']/2 <= extent['x']+extent['width']
                assert extent['y'] <= box['y']+box['height']/2 <= extent['y']+extent['height']
                page.locator('.workspace-settlement-list').get_by_role('button',name='Fixture Harbour',exact=False).click()
                expect(page.get_by_role('cell',name='Linked fixture scheme',exact=True)).to_be_visible()
                assert page.get_by_role('cell',name='Unlinked fixture scheme',exact=True).count() == 0
                page.get_by_role('button',name='Settlement boundary Fixture Harbour',exact=True).press('Enter')
                page.screenshot(path=str(OUT/'settlement-map.png'),full_page=True)
                checks.append('Map fits imported geometries outside the old fixed viewport; selection, keyboard boundary access and exact project joins are connected')
                nav('Priorities')
                expect(page.get_by_role('cell',name='51.0',exact=True)).to_be_visible()
                assert page.get_by_role('cell',name='Fixture Hill',exact=True).count() == 0
                page.get_by_text('Scoring weights',exact=False).first.click()
                for input in page.locator('.workspace-weights input').all():
                    input.fill('0')
                page.get_by_label('Water deficit weight',exact=True).fill('100')
                page.get_by_role('button',name='Apply weights',exact=True).click()
                expect(page.get_by_role('cell',name='80.0',exact=True)).to_be_visible()
                page.get_by_label('Water deficit weight',exact=True).fill('0')
                page.get_by_role('button',name='Apply weights',exact=True).click()
                expect(page.get_by_role('alert').filter(has_text='positive')).to_be_visible()
                expect(page.get_by_role('cell',name='80.0',exact=True)).to_be_visible()
                page.get_by_role('button',name='Reset weights',exact=True).click()
                expect(page.get_by_role('cell',name='51.0',exact=True)).to_be_visible()
                with page.expect_download() as csv:
                    page.get_by_role('button',name='CSV',exact=True).click()
                assert csv.value.suggested_filename == 'urbansaarthi-priorities.csv'
                page.get_by_label('Priority coverage filter').select_option('missing')
                expect(page.get_by_text('Fixture Hill',exact=True).first).to_be_visible()
                checks.append('Hand-worked 51-point score, water-only80, zero-weight rejection, missing-data separation and CSV pass')
                nav('Scenarios')
                expect(page.get_by_label('Scenario households')).to_have_value('120')
                page.get_by_label('Scenario households').fill('10')
                page.get_by_label('Contingency percent').fill('10')
                page.get_by_label('Temporary rent / month (₹)',exact=True).fill('20')
                page.get_by_label('Annual O&M / household (₹)',exact=True).fill('12')
                option = page.locator('.us-scenario').first
                option.get_by_label('Improve in place unit cost',exact=True).fill('100')
                for label,value in [('Shared works (₹)','50'),('Implementation (months)','6'),('Temporary support (months)','1'),('Household disruption share (0–1)','0.2')]:
                    option.get_by_label(label,exact=True).fill(value)
                expect(page.get_by_text('Python calculation checked',exact=True)).to_be_visible(timeout=15000)
                expect(option.get_by_text('₹1,199',exact=True)).to_be_visible()
                option.get_by_role('button',name='Draft a service work',exact=True).click()
                page.get_by_label('Record actor',exact=True).fill('test-contractor')
                page.get_by_label('Verification target',exact=True).fill('8')
                page.get_by_role('button',name='Create planned intervention',exact=True).click()
                expect(page.get_by_role('button',name='Start work',exact=True)).to_be_visible()
                page.get_by_label('Inspection notes',exact=True).fill('Software regression only; not a real inspection')
                revised = (datetime.now(timezone.utc)+timedelta(days=2)).date().isoformat()
                page.get_by_label('Revised due date',exact=True).fill(revised)
                with page.expect_response(lambda response: response.request.method == 'PATCH' and '/interventions/' in response.url) as updated:
                    page.get_by_role('button',name='Update due date',exact=True).click()
                assert updated.value.status == 200
                expect(page.get_by_role('button',name='Update due date',exact=True)).to_be_disabled()
                assert api('/interventions',True)['items'][0]['planned_end'] == revised
                page.get_by_role('button',name='Start work',exact=True).click()
                page.get_by_role('button',name='Report physical completion',exact=True).click()
                expect(page.locator('.us-tag').filter(has_text='Reported complete')).to_be_visible()
                assert api('/interventions',True)['items'][0]['status'] == 'reported_complete'
                page.get_by_role('button',name='Request verification',exact=True).click()
                page.get_by_label('Record actor',exact=True).fill('test-inspector')
                page.get_by_label('Upload inspection evidence').set_input_files({'name':'fixture.txt','mimeType':'text/plain','buffer':b'SOFTWARE TEST ONLY'})
                page.get_by_role('button',name='Upload consented evidence',exact=True).click()
                expect(page.locator('li').filter(has_text='fixture.txt')).to_be_visible()
                page.get_by_label('Record actor',exact=True).fill('test-reviewer')
                page.get_by_label('Measured service value').fill('8')
                page.get_by_label('Service functioning confirmed').check()
                page.get_by_role('button',name='Record verification outcome',exact=True).click()
                expect(page.locator('.us-tag').filter(has_text='Verified (recorded review)')).to_be_visible()
                page.get_by_label('Intervention service',exact=True).select_option('sanitation')
                page.get_by_label('Complaint description',exact=True).fill('Software fixture: water interrupted')
                page.get_by_role('button',name='Register issue against selected work',exact=True).click()
                expect(page.locator('.us-tag').filter(has_text='Requiring reinspection')).to_be_visible()
                assert api('/complaints',True)['items'][0]['service_type'] == 'water'
                checks.append('Imported120 households feed scenarios; hand-worked ₹1199 matches API; due-date edit, plan/completion/evidence/review and correct complaint service execute')
                nav('Overview'); page.reload()
                expect(page.get_by_role('heading',name='UrbanSaarthi Dashboard',exact=True)).to_be_visible()
                page.screenshot(path=str(OUT/'overview.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                for name in ['Overview','Settlement map','Priorities','Scenarios','Service assurance']:

                    if name in ['Overview','Settlement map']:
                        page.get_by_role('button',name='Toggle navigation',exact=True).click()
                    nav(name)
                    page.wait_for_timeout(150)
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), name
                page.get_by_role('button',name='Toggle navigation',exact=True).click(); nav('Overview')
                page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
                page.get_by_role('button',name='Data sources',exact=True).click()
                expect(page.get_by_label('Dataset file')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), 'Data & access'
                page.screenshot(path=str(OUT/'mobile-data.png'),full_page=True)
                page.route('**/api/urban/data/**',lambda route:route.abort()); page.reload()
                expect(page.get_by_role('button',name='Retry data connection',exact=True)).to_be_visible()
                assert errors == [], errors
                checks.append('Reload retains imported data; primary explorer and retained planning tools fit390px; offline API shows retry without substituting data')
                browser.close()
        report['status'] = 'passed'
    finally:
        for process in reversed(processes):
            process.terminate()
            try: process.wait(timeout=8)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        for log in logs: log.close()
        (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
