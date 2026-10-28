"""Actual four-section product workflows; test issue reports use disposable SQLite."""
from datetime import datetime,timezone
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import expect,sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/('.runtime/product-browser-real' if os.getenv('URBANSAARTHI_BROWSER_REAL_DATA')=='1' else '.runtime/product-browser')
API='http://127.0.0.1:18108'
WEB='http://127.0.0.1:15182'
LABELS={
 'en':(['Dashboard','Explore Settlements','Report an Issue','Projects & Reports'],['Urban Overview','Explore Settlements','Report an Issue','Projects & Reports']),
 'hi':(['डैशबोर्ड','बस्तियाँ देखें','समस्या दर्ज करें','परियोजनाएँ और रिपोर्ट'],['शहरी परिदृश्य','बस्तियाँ देखें','समस्या दर्ज करें','परियोजनाएँ और रिपोर्ट']),
 'mr':(['आढावा','वस्त्या पाहा','समस्या नोंदवा','प्रकल्प आणि अहवाल'],['शहरी आढावा','वस्त्या पाहा','समस्या नोंदवा','प्रकल्प आणि अहवाल']),
}


def snapshot():
    row=lambda identity,name:{'id':identity,'source_id':identity,'source_name':name,'name':name,'geometry':None,'administrative_area':'TEST WARD','village':'TEST VILLAGE','taluka':'TEST TALUKA','shape_area_sq_m':100,'source':'https://example.test/fixture','source_date':'2024','source_date_basis':'TEST ONLY','retrieved_at':'','record_type':'published_cluster_register','data_completeness':0,'synthetic':False,'limitations':['SOFTWARE FIXTURE ONLY']}
    project={'id':'TEST-PROJECT','source_id':None,'scheme_name':'TEST ONLY PROJECT','administrative_area':'TEST WARD','village':'TEST VILLAGE','cts_raw':'TEST CTS','project_status':'unknown','source_date':None,'source_url':'https://example.test/fixture','settlement_id':None}
    return {'metadata':{'title':'SOFTWARE FIXTURE ONLY','synthetic':False,'settlement_count':2,'settlement_geometry_count':0,'projects_count':1,'mapped_objects_count':0,'historical_observation_count':0,'geographic_unit_count':0,'settlement_record_type':'published_cluster_register','settlement_reference':'2024','built_at':datetime.now(timezone.utc).isoformat(),'geographic_scope':'Software tests only','limitations':['Not government data']},'settlements':[row('TEST-REGISTER-A','TEST ONLY A'),row('TEST-REGISTER-B','TEST ONLY B')],'projects':[project],'spatial':{'type':'FeatureCollection','features':[]},'indicators':[],'geographic_units':[]}


def wait(url,process):
    for _ in range(100):
        if process.poll() is not None: raise RuntimeError('Owned product QA service exited')
        try:
            with urllib.request.urlopen(url,timeout=1) as response:
                if response.status==200:return
        except OSError:time.sleep(.2)
    raise RuntimeError('Product QA readiness timeout')


def main():
    OUT.mkdir(parents=True,exist_ok=True);checks=[];errors=[];processes=[];logs=[]
    report={'status':'failed','checked_at':datetime.now(timezone.utc).isoformat(),'scope':'Actual Chromium and API in disposable SQLite; saved issue reports are software fixtures','checks':checks,'browser_errors':errors,'field_validation':False}
    try:
        with tempfile.TemporaryDirectory(prefix='urban-product-') as folder:
            folder=Path(folder);source=folder/'processed';source.mkdir()
            real=os.getenv('URBANSAARTHI_BROWSER_REAL_DATA')=='1'
            data=json.loads((ROOT/'data/processed/urban_real.json').read_text()) if real else snapshot()
            (source/'urban_real.json').write_text(json.dumps(data,ensure_ascii=False))
            report['source_counts']={key:len(data[key]) for key in ['settlements','projects','indicators']}
            report['real_source_records']=real
            key=secrets.token_urlsafe(32)
            env={**os.environ,'URBANSAARTHI_DB_PATH':str(folder/'test.sqlite3'),'URBANSAARTHI_DATA_DIR':str(source),'NAGARSEVA_OFFICER_KEY':key,'URBANSAARTHI_EVIDENCE_STORAGE':'sqlite','NAGARSEVA_API_TARGET':API}
            for name,command,cwd in [('api',[sys.executable,'-m','uvicorn','model.api.urban:app','--host','127.0.0.1','--port','18108'],ROOT/'nagarseva'),('web',['npm','run','preview','--','--port','15182','--strictPort'],ROOT/'nagarseva/website')]:
                log=(OUT/f'{name}.log').open('w');logs.append(log);processes.append(subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT))
            wait(API+'/urban/data/health',processes[0]);wait(WEB,processes[1])
            def api(path,body=None,method=None):
                headers={'Content-Type':'application/json','X-Officer-Key':key}
                req=urllib.request.Request(API+'/urban/data'+path,headers=headers,data=json.dumps(body).encode() if body is not None else None,method=method)
                with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
            with sync_playwright() as pw:
                browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH') or None)
                context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
                context.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
                page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                def nav(label):page.locator('.us-sidebar nav').get_by_role('link',name=label,exact=True).click()
                page.goto(WEB+'/dashboard')
                expect(page.get_by_role('heading',name='Urban Overview',exact=True)).to_be_visible()
                expect(page.locator('.us-sidebar nav a')).to_have_count(4)
                expect(page.locator('.us-reference-boundary')).to_have_count(2517,timeout=20000)
                expect(page.locator('.product-metrics .us-metric').nth(0).locator('strong')).to_have_text('2,517')
                expect(page.locator('.product-metrics .us-metric').nth(1).locator('strong')).to_have_text(f"{len(data['settlements']):,}")
                expect(page.locator('.product-metrics .us-metric').nth(2).locator('strong')).to_have_text('0')
                positions=[item.bounding_box()['y'] for item in page.locator('.product-metrics .us-metric').all()];assert max(positions)-min(positions)<2
                page.screenshot(path=str(OUT/'dashboard-en.png'),full_page=True)
                checks.append('Four routes and real dataset KPIs render; historical polygons are distinct from register records and four desktop metrics share one row')
                nav('Explore Settlements');expect(page).to_have_url(WEB+'/settlements')
                expect(page.locator('.us-reference-boundary')).to_have_count(2517)
                page.get_by_role('button',name='2015 reference boundary',exact=True).first.press('Enter')
                expect(page.locator('.us-reference-boundary.is-selected')).to_have_count(1)
                expect(page.get_by_role('region',name='Selected historical polygon')).to_contain_text('Not available in the supplied GeoJSON')
                page.locator('.leaflet-popup-close-button').click()
                transform=page.locator('.leaflet-map-pane').get_attribute('style')
                page.locator('.workspace-settlement-list button').nth(1).click()
                assert page.locator('.leaflet-map-pane').get_attribute('style')==transform
                first=data['settlements'][0];page.get_by_label('Search settlements',exact=True).fill(first['source_id'])
                expect(page.locator('.workspace-settlement-list button')).to_have_count(1)
                page.get_by_label('Settlement ward',exact=True).select_option(first['administrative_area'])
                if first.get('village'):page.get_by_label('Village/division filter',exact=True).select_option(first['village'])
                page.get_by_label('Language / भाषा',exact=True).select_option('hi')
                expect(page.get_by_role('heading',name=LABELS['hi'][1][1],exact=True)).to_be_visible()
                expect(page.locator('.workspace-settlement-search input')).to_have_value(first['source_id'])
                page.get_by_label('Language / भाषा',exact=True).select_option('mr')
                expect(page.locator('.workspace-settlement-search input')).to_have_value(first['source_id'])
                page.reload();expect(page.locator('html')).to_have_attribute('lang','mr')
                page.get_by_label('Language / भाषा',exact=True).select_option('en')
                nav('Dashboard');page.go_back();expect(page.get_by_role('heading',name='Explore Settlements',exact=True)).to_be_visible();page.go_forward();expect(page.get_by_role('heading',name='Urban Overview',exact=True)).to_be_visible()
                checks.append('Polygon highlight and source-only details work; register selection does not move the map; ward/village/search, language persistence and browser back/forward pass')
                nav('Report an Issue');page.get_by_label('Issue description',exact=True).fill('TEST ONLY public issue; this is not a real service observation')
                page.get_by_label('Ward, if known',exact=True).fill('TEST ONLY WARD')
                page.get_by_label('Language / भाषा',exact=True).select_option('hi')
                expect(page.locator('.product-issue-form textarea')).to_have_value('TEST ONLY public issue; this is not a real service observation')
                page.get_by_label('Language / भाषा',exact=True).select_option('en')
                page.get_by_text('Attach a supporting image (optional)',exact=True).click()
                png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3ioAAAAASUVORK5CYII=')
                page.get_by_label('Supporting image',exact=True).set_input_files({'name':'software-fixture.png','mimeType':'image/png','buffer':png})
                page.get_by_role('button',name='Save issue report',exact=True).click()
                expect(page.get_by_role('alert')).to_contain_text('Permission is required')
                assert api('/issues')['total']==0
                page.get_by_label('I have permission to store this image for review and have removed personal details.',exact=True).check()
                page.get_by_role('button',name='Save issue report',exact=True).click()
                expect(page.get_by_role('heading',name='Report saved',exact=True)).to_be_visible()
                issue=api('/issues')['items'][0];assert issue['status']=='submitted' and issue['official_submission'] is False
                expect(page.locator('.product-issue-confirmation code')).to_have_text(issue['id'])
                page.reload();expect(page.locator('.product-issue-confirmation code')).to_have_text(issue['id'])
                api('/issues/'+issue['id'],{'status':'under_review','note':'TEST ONLY review','reviewer_reference':'test-reviewer'},'PATCH')
                page.reload();expect(page.locator('.product-issue-confirmation')).to_contain_text('Under review')
                nav('Dashboard');expect(page.locator('.product-metrics .us-metric').nth(2).locator('strong')).to_have_text('1');expect(page.locator('.product-metrics .us-metric').nth(3).locator('strong')).to_have_text('0')
                checks.append('Anonymous issue form preserves translated drafts, validates image consent, persists one report with stable reference across reload, and separates review from service verification')
                nav('Projects & Reports');expect(page.locator('.workspace-project-records tbody tr').first).to_be_visible()
                project=data['projects'][0];page.get_by_label('Search project listings',exact=True).fill(project['scheme_name'])
                expect(page.locator('.workspace-project-records tbody tr').first).to_be_visible()
                page.locator('.workspace-project-records tbody tr .us-table-button').first.click()
                expect(page.get_by_role('dialog')).to_contain_text('No current progress, budget or beneficiary count is inferred.')
                page.get_by_role('button',name='Close',exact=True).click()
                page.get_by_role('tab',name='Data reports',exact=True).click()
                with page.expect_download() as download:page.get_by_role('button',name='Download issues CSV',exact=True).click()
                exported=Path(download.value.path()).read_text();assert issue['id'] in exported and 'False' in exported and 'official_submission' in exported
                checks.append('Project search, genuine fields, provenance dialog and issue CSV exports pass without invented costs, progress or cluster links')
                for language,(navigation,headings) in LABELS.items():
                    page.get_by_label('Language / भाषा',exact=True).select_option(language)
                    page.set_viewport_size({'width':390,'height':844})
                    for index,label in enumerate(navigation):
                        page.locator('.us-mobile-nav').click();nav(label)
                        expect(page.get_by_role('heading',name=headings[index],exact=True)).to_be_visible()
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        assert not page.locator('main').inner_text().count('nav.')
                        page.screenshot(path=str(OUT/f'{language}-{index}-mobile.png'),full_page=True)
                checks.append('All four sections render in English, Hindi and Marathi at390px without page overflow or untranslated navigation keys')
                # A failed issue POST cannot show success or create a second report.
                page.get_by_label('Language / भाषा',exact=True).select_option('en');page.set_viewport_size({'width':1440,'height':1000});nav('Report an Issue')
                page.get_by_label('Issue description',exact=True).fill('TEST ONLY failed submission must not be saved')
                page.route('**/api/urban/data/issues',lambda route:route.abort() if route.request.method=='POST' else route.continue_())
                page.get_by_role('button',name='Save issue report',exact=True).click()
                expect(page.get_by_role('alert')).to_contain_text('Cannot connect')
                assert page.get_by_role('heading',name='Report saved',exact=True).count()==0 and api('/issues')['total']==1
                checks.append('Network failure does not show a success confirmation or create an issue')
                context.close();browser.close()
            assert not errors,errors
            report['status']='passed'
    finally:
        for process in reversed(processes):
            process.terminate()
            try:process.wait(timeout=8)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        for log in logs:log.close()
        (OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
