"""Actual Chromium workflows against acquired source data and a disposable database.

Writes test-only plans to a temporary DB. Does not create real field evidence.
Owned API/browser/preview processes are stopped even on a failed assertion.
"""
from datetime import datetime, timezone
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

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.runtime/public-browser'


def wait_for(url,process):
    for _ in range(100):
        if process.poll() is not None: raise RuntimeError('Owned preview exited; inspect .runtime/public-browser logs')
        try:
            with urllib.request.urlopen(url,timeout=1) as response:
                if response.status==200:return
        except OSError:time.sleep(.2)
    raise RuntimeError('Preview readiness timeout')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[];processes=[];logs=[]
    report={'status':'failed','checked_at':datetime.now(timezone.utc).isoformat(),'data':'Acquired SRA/OSM snapshot; test-only operational records in disposable SQLite','field_validation':False,'checks':checks,'browser_errors':errors}
    try:
        with tempfile.TemporaryDirectory(prefix='urban-real-browser-') as folder:
            env=os.environ.copy();key=secrets.token_urlsafe(32)
            env.update(URBANSAARTHI_DB_PATH=str(Path(folder)/'test.sqlite3'),NAGARSEVA_OFFICER_KEY=key,NAGARSEVA_MODE='pilot-prototype',URBANSAARTHI_EVIDENCE_STORAGE='sqlite',NAGARSEVA_API_TARGET='http://127.0.0.1:18000',URBANSAARTHI_DATA_DIR=str(ROOT/'data/processed'))
            for name,args,cwd in [('api',[sys.executable,'-m','uvicorn','model.api.urban:app','--host','127.0.0.1','--port','18000'],ROOT/'nagarseva'),('web',['npm','run','preview','--','--port','14173','--strictPort'],ROOT/'nagarseva/website')]:
                log=(OUT/f'{name}.log').open('w');logs.append(log)
                processes.append(subprocess.Popen(args,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT))
            wait_for('http://127.0.0.1:18000/urban/data/health',processes[0]);wait_for('http://127.0.0.1:14173',processes[1])
            with sync_playwright() as pw:
                browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH','/usr/bin/chromium'))
                context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
                context.add_init_script('sessionStorage.setItem("urbansaarthi-officer-key", '+json.dumps(key)+')')
                page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto('http://127.0.0.1:14173')
                expect(page.get_by_role('heading',name='Plan from the evidence that exists.')).to_be_visible()
                expect(page.get_by_text('7,106 mapped OSM objects',exact=True)).to_be_visible();checks.append('Acquired dashboard counts/provenance loaded')
                page.screenshot(path=str(OUT/'overview.png'),full_page=True)
                def nav(name):page.get_by_role('navigation',name='Planning workflow').get_by_role('button',name=name,exact=True).click()
                nav('Explore Settlements')
                expect(page.locator('.leaflet-container')).to_be_visible()
                expect(page.get_by_role('status').filter(has_text='mapped objects shown')).to_contain_text('3,148',timeout=20000)
                expect(page.locator('.leaflet-container canvas').first).to_be_visible()
                page.screenshot(path=str(OUT/'acquired-map.png'),full_page=True)
                page.get_by_label('Search mapped objects',exact=True).fill('school')
                expect(page.get_by_role('status').filter(has_text='mapped objects shown')).not_to_contain_text('3,148')
                page.get_by_label('Search mapped objects',exact=True).fill('ZZZ-no-mapped-feature')
                expect(page.get_by_text('No acquired mapped objects match these layers and search.',exact=False)).to_be_visible()
                page.get_by_label('Search mapped objects',exact=True).fill('')
                page.get_by_label('Source settlement geometry filter').select_option('geometry')
                expect(page.get_by_text('No records match. No boundary geometries were acquired for the printed labels.')).to_be_visible()
                page.get_by_label('Source settlement geometry filter').select_option('all')
                page.get_by_label('Search source settlements').fill('ME_002')
                page.get_by_role('button',name='ME_002',exact=True).click()
                expect(page.get_by_role('heading',name='Map label ME_002',exact=True)).to_be_visible()
                page.get_by_label('Search public projects').fill('ZZZ-unmatched')
                expect(page.get_by_text('No project rows match.')).to_be_visible();checks.append('GIS rendered; map/label/project search, geometry filters and empty states checked')
                nav('Prioritize Needs')
                expect(page.get_by_role('heading',name='Prioritize needs',exact=True)).to_be_visible()
                expect(page.get_by_text('An exact score is not justified by the supplied data.')).to_be_visible()
                with page.expect_download() as download:page.get_by_role('button',name='CSV',exact=True).click()
                assert download.value.suggested_filename=='urbansaarthi-priorities.csv'
                checks.append('Real records stay unranked; configurable priority CSV downloads')
                nav('Compare Scenarios')
                page.get_by_label('Scenario households').fill('10')
                expect(page.get_by_text('Python calculation checked',exact=True)).to_be_visible(timeout=15000)
                expect(page.get_by_role('heading',name='Access comparison unavailable').first).to_be_visible()
                page.get_by_role('button',name='Draft a service work',exact=True).first.click()
                page.get_by_label('Record actor').fill('test-contractor')
                page.get_by_label('Verification target',exact=True).fill('8')
                page.get_by_role('button',name='Create planned intervention').click()
                expect(page.get_by_role('button',name='Start work',exact=True)).to_be_visible()
                page.get_by_label('Inspection notes').fill('AUTOMATED TEST ONLY: workflow transition')
                page.get_by_role('button',name='Start work',exact=True).click()
                page.get_by_role('button',name='Report physical completion',exact=True).click()
                expect(page.locator('.us-tag').filter(has_text='Reported complete')).to_be_visible()
                page.get_by_role('button',name='Request verification',exact=True).click()
                expect(page.locator('.us-tag').filter(has_text='Awaiting verification')).to_be_visible()
                page.get_by_label('Record actor').fill('test-inspector')
                page.get_by_label('Upload inspection evidence').set_input_files({'name':'test-only-evidence.txt','mimeType':'text/plain','buffer':b'AUTOMATED TEST FIXTURE ONLY; not field evidence.'})
                page.get_by_role('button',name='Upload consented evidence',exact=True).click()
                expect(page.locator('li').filter(has_text='test-only-evidence.txt')).to_be_visible()
                page.get_by_label('Record actor').fill('test-reviewer')
                page.get_by_label('Measured service value').fill('8')
                page.get_by_label('Service functioning confirmed').check()
                page.get_by_role('button',name='Record verification outcome').click()
                expect(page.locator('.us-tag').filter(has_text='Verified (recorded review)')).to_be_visible()
                page.get_by_label('Complaint description').fill('AUTOMATED TEST ONLY: reported service interruption')
                page.get_by_role('button',name='Register issue against selected work').click()
                expect(page.locator('.us-tag').filter(has_text='Requiring reinspection')).to_be_visible()
                page.get_by_label('Complaint resolution').fill('AUTOMATED TEST ONLY: response recorded, no automatic verification')
                page.get_by_role('button',name='Record response and resolve',exact=True).click()
                expect(page.locator('.us-tag').filter(has_text='Requiring reinspection')).to_be_visible()
                checks.append('Scenario-to-plan, completion, evidence upload, independent review and complaint dispute/response executed')
                page.screenshot(path=str(OUT/'assurance.png'),full_page=True)
                nav('Overview');page.set_viewport_size({'width':390,'height':844})
                page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
                expect(page.locator('.us-sidebar')).to_be_hidden()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
                page.screenshot(path=str(OUT/'mobile.png'))
                page.get_by_role('button',name='Toggle navigation',exact=True).click()
                nav('Explore Settlements')
                expect(page.locator('.leaflet-container canvas').first).to_be_visible()
                expect(page.locator('.us-sidebar')).to_be_hidden()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
                checks.append('Mobile overview/map fit 390px; navigation opens and closes')
                page.get_by_role('button',name='Toggle navigation',exact=True).click();nav('Overview')
                page.set_viewport_size({'width':1440,'height':1000})
                page.get_by_role('button',name='Open synthetic sandbox',exact=True).click()
                expect(page.get_by_text('Synthetic sandbox · all planning fixtures are invented',exact=True)).to_be_visible()
                expect(page.get_by_role('heading',name='A clear path from need to service.')).to_be_visible()
                page.get_by_role('button',name='Return to acquired public data',exact=True).click()
                expect(page.get_by_role('heading',name='Plan from the evidence that exists.')).to_be_visible();checks.append('Synthetic sandbox is explicitly selected and remains separate')
                offline=browser.new_context(viewport={'width':1280,'height':900})
                offline.route('**/api/urban/data/**',lambda route:route.abort())
                p=offline.new_page();p.goto('http://127.0.0.1:14173')
                expect(p.get_by_role('heading',name='Public data unavailable',exact=True)).to_be_visible()
                expect(p.get_by_role('button',name='Retry data connection')).to_be_visible();checks.append('Unavailable API displays error/retry without silently showing synthetic data')
                offline.close();context.close();browser.close()
                assert not errors,errors
        report['status']='passed'
    except Exception as exc:
        report['failure']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        for p in reversed(processes):p.terminate()
        for p in reversed(processes):
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
        for f in logs:f.close()
        target=ROOT/'research/verification/browser_results.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))


if __name__=='__main__':main()
