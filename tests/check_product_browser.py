"""Civic dashboard acceptance in Chromium with disposable SQLite only.

Default: honest missing-source states. URBANSAARTHI_BROWSER_REAL_DATA=1 uses
existing acquired files without importing into or changing the user's database.
Basemap tiles are blocked in this repeatable test; visual live-tile QA is separate.
"""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import expect,sync_playwright

ROOT=Path(__file__).resolve().parents[1]
REAL=os.getenv('URBANSAARTHI_BROWSER_REAL_DATA')=='1'
OUT=ROOT/('.runtime/civic-browser-real' if REAL else '.runtime/civic-browser-empty')
API='http://127.0.0.1:18108'
WEB='http://127.0.0.1:15182'
NOTICE='Historical reference boundaries — 2015. Not verified against the 2024 SRA cluster list.'
LABELS={
 'en':(['Dashboard','Explore Settlements','Report an Issue','Projects & Reports'],['UrbanSaarthi Dashboard','Explore Settlements','Report an Issue','Projects & Reports']),
 'hi':(['डैशबोर्ड','बस्तियाँ देखें','समस्या दर्ज करें','परियोजनाएँ और रिपोर्ट'],['UrbanSaarthi डैशबोर्ड','बस्तियाँ देखें','समस्या दर्ज करें','परियोजनाएँ और रिपोर्ट']),
 'mr':(['आढावा','वस्त्या पाहा','समस्या नोंदवा','प्रकल्प आणि अहवाल'],['UrbanSaarthi आढावा','वस्त्या पाहा','समस्या नोंदवा','प्रकल्प आणि अहवाल']),
}


def wait(url,process):
    for _ in range(100):
        if process.poll() is not None:raise RuntimeError('Owned acceptance service exited')
        try:
            with urllib.request.urlopen(url,timeout=1) as response:
                if response.status==200:return
        except OSError:time.sleep(.2)
    raise RuntimeError('Acceptance service readiness timeout')


def main():
    OUT.mkdir(parents=True,exist_ok=True);checks=[];errors=[];processes=[];logs=[]
    report={'status':'failed','checked_at':datetime.now(timezone.utc).isoformat(),'scope':'Production build, Chromium, actual bundled GeoJSON and disposable SQLite; software issue fixtures only',
            'real_acquired_sources':REAL,'basemap_tiles':'Blocked in automated tests','checks':checks,'browser_errors':errors,'field_validation':False}
    try:
        with tempfile.TemporaryDirectory(prefix='urban-civic-') as folder:
            folder=Path(folder);source=folder/'input';source.mkdir()
            data=json.loads((ROOT/'data/processed/urban_real.json').read_text()) if REAL else None
            if data:(source/'urban_real.json').write_text(json.dumps(data,ensure_ascii=False))
            key=secrets.token_urlsafe(32)
            env={**os.environ,'URBANSAARTHI_DB_PATH':str(folder/'test.sqlite3'),'URBANSAARTHI_DATA_DIR':str(source),'NAGARSEVA_OFFICER_KEY':key,'URBANSAARTHI_EVIDENCE_STORAGE':'sqlite','NAGARSEVA_API_TARGET':API}
            for name,command,cwd in [('api',[sys.executable,'-m','uvicorn','model.api.urban:app','--host','127.0.0.1','--port','18108'],ROOT/'nagarseva'),('web',['npm','run','preview','--','--port','15182','--strictPort'],ROOT/'nagarseva/website')]:
                log=(OUT/f'{name}.log').open('w');logs.append(log);processes.append(subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT))
            wait(API+'/urban/data/health',processes[0]);wait(WEB,processes[1])
            def api(path):
                with urllib.request.urlopen(API+'/urban/data'+path,timeout=20) as response:return json.load(response)
            boundary=json.loads((ROOT/'nagarseva/website/public/data/mumbai_slum_clusters_2015.geojson').read_text())
            manifest=json.loads((ROOT/'nagarseva/website/public/data/mumbai_slum_clusters_2015.metadata.json').read_text())
            count=len(boundary['features'])-len(manifest['excluded_features'])
            with sync_playwright() as pw:
                browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH') or '/usr/bin/chromium')
                context=browser.new_context(viewport={'width':1586,'height':992},accept_downloads=True)
                context.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
                page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                def nav(index):
                    page.locator('.us-sidebar nav a').nth(index).click()
                page.goto(WEB+'/dashboard')
                expect(page.get_by_role('heading',name=LABELS['en'][1][0],exact=True)).to_be_visible()
                expect(page.locator('.us-sidebar nav a')).to_have_count(4)
                expect(page.locator('.us-reference-boundary')).to_have_count(count,timeout=20000)
                expect(page.locator('.civic-count')).to_have_text(f"{len(boundary['features']):,}")
                expect(page.locator('.civic-summary-card.blue')).to_contain_text(f'{count:,} displayed')
                expect(page.locator('.civic-data-coverage li')).to_have_count(5)
                expect(page.locator('.civic-activity')).to_contain_text('No activity recorded yet')
                expect(page.locator('.civic-summary-card.rose')).to_contain_text('No verified issue reports yet.')
                expect(page.locator('.civic-summary-card.mint')).to_contain_text('No verified project records available yet.')
                if REAL:
                    expect(page.locator('.civic-summary-card.amber')).to_contain_text(f"{len(data['settlements']):,} extracted rows")
                    expect(page.locator('.civic-summary-card.mint')).to_contain_text(f"{len(data['projects']):,} source listings")
                else:expect(page.locator('.civic-summary-card.amber')).to_contain_text('Import pending')
                assert page.locator('.product-shell').evaluate('(node)=>getComputedStyle(node).backgroundColor')=='rgb(237, 245, 250)'
                assert page.locator('.us-brand-mark').evaluate('(node)=>node.complete&&node.naturalWidth>0')
                page.screenshot(path=str(OUT/'dashboard-desktop.png'),full_page=True)
                checks.append('Light civic shell, four routes, actual source counts, five coverage states, no fabricated activity/issues/projects')
                search=page.get_by_role('searchbox',name='Find a reference polygon',exact=True)
                search.fill('6');expect(page.locator('.reference-polygon-table tbody tr')).to_have_count(0)
                search.fill('7');expect(page.locator('.reference-polygon-table tbody tr')).to_have_count(1)
                expect(page.locator('.reference-polygon-table tbody')).to_contain_text('Reference Polygon 007')
                search.fill('');page.get_by_role('button',name='Next',exact=True).click()
                expect(page.locator('.reference-polygon-table tbody tr').first).to_contain_text('Reference Polygon 007')
                page.get_by_role('button',name='Last page',exact=True).click()
                expect(page.locator('.reference-pagination')).to_contain_text(f'of {count:,} displayable polygons')
                page.get_by_role('button',name='First page',exact=True).click()
                page.get_by_role('button',name='View Reference Polygon 001',exact=True).press('Enter')
                expect(page).to_have_url(WEB+'/settlements?reference=1')
                expect(page.locator('.reference-detail h2')).to_have_text('Reference Polygon 001')
                expect(page.locator('.us-reference-boundary.is-selected')).to_have_count(1)
                expect(page.locator('.us-reference-boundary.is-selected')).to_have_attribute('aria-label','Reference Polygon 001')
                expect(page.locator('.reference-detail')).to_contain_text('Not available in this dataset.')
                page.get_by_text('Inspect original source properties',exact=True).click()
                expect(page.locator('.reference-detail pre')).to_have_text('{\n  "polyno": null\n}')
                expect(page.locator('.reference-table-panel')).to_contain_text('Name, SRA ID and ward search are unavailable')
                page.get_by_role('button',name='View Reference Polygon 002',exact=True).press('Enter')
                expect(page.locator('.us-reference-boundary.is-selected')).to_have_attribute('aria-label','Reference Polygon 002')
                selected=page.locator('.us-reference-boundary.is-selected')
                assert selected.get_attribute('stroke')=='#00544f' and selected.get_attribute('stroke-width')=='4'
                selected.dispatch_event('click');expect(page.locator('.leaflet-popup-content')).to_contain_text('Reference Polygon 002')
                expect(page.locator('.leaflet-popup-content')).to_contain_text(NOTICE)
                page.locator('.leaflet-popup-close-button').click()
                page.get_by_role('button',name='Reset view',exact=True).click()
                expect(page.locator('.us-reference-boundary.is-selected')).to_have_count(0)
                page.locator('.leaflet-control-zoom-in').click()
                box=page.locator('.leaflet-container').bounding_box();assert box
                page.mouse.move(box['x']+box['width']*.55,box['y']+box['height']*.5);page.mouse.down();page.mouse.move(box['x']+box['width']*.6,box['y']+box['height']*.55,steps=5);page.mouse.up()
                page.get_by_role('button',name='Fit reference boundaries',exact=True).click()
                page.locator('.workspace-map-toolbar details summary').click()
                page.get_by_label('2015 Reference Boundaries',exact=True).uncheck();expect(page.locator('.us-reference-boundary')).to_have_count(0)
                page.get_by_label('2015 Reference Boundaries',exact=True).check();expect(page.locator('.us-reference-boundary')).to_have_count(count)
                page.locator('.workspace-map-toolbar details summary').click()
                if REAL:
                    expect(page.locator('.workspace-settlement-list button')).to_have_count(10)
                    page.get_by_label('Search settlements',exact=True).fill(data['settlements'][1]['source_id'])
                    assert page.locator('.workspace-settlement-list button').count()>=1
                    expect(page.locator('.workspace-settlement-list')).to_contain_text(data['settlements'][1]['source_id'])
                else:expect(page.locator('.workspace-settlement-column')).to_have_count(0)
                page.screenshot(path=str(OUT/'settlements-desktop.png'),full_page=True)
                checks.append('Real polygon lookup/pagination, preserved source numbering, table keyboard selection, actual geometry highlight, popup, zoom/pan/fit and layer toggle')
                nav(2)
                submits=[];page.on('request',lambda request:submits.append(request.url) if request.method=='POST' and request.url.endswith('/issues') else None)
                page.get_by_role('button',name='Save issue report',exact=True).click();assert not submits
                page.get_by_label('Issue category',exact=True).select_option('water')
                page.get_by_label('Issue description',exact=True).fill('TEST ONLY browser acceptance report; not a real public complaint.')
                location=page.get_by_label('Location description (required)',exact=True)
                location.fill('   ');page.get_by_role('button',name='Save issue report',exact=True).click()
                expect(page.get_by_role('alert')).to_contain_text('A location description is required.')
                location.fill('TEST ONLY public landmark')
                page.get_by_text('Attach a supporting image (optional)',exact=True).click()
                image=page.get_by_label('Supporting image',exact=True)
                image.set_input_files({'name':'test-only.pdf','mimeType':'application/pdf','buffer':b'not an image'})
                page.get_by_role('button',name='Save issue report',exact=True).click()
                expect(page.get_by_role('alert')).to_contain_text('PNG or JPEG')
                assert api('/issues')['total']==0
                image.set_input_files([])
                page.get_by_role('button',name='Save issue report',exact=True).click()
                expect(page.get_by_role('heading',name='Report saved',exact=True)).to_be_visible()
                issue=api('/issues')['items'][0]
                assert issue['official_submission'] is False and issue['verification_status']=='self_reported' and issue['location']=='TEST ONLY public landmark'
                page.reload();expect(page.get_by_role('heading',name='Report saved',exact=True)).to_be_visible()
                nav(0);expect(page.locator('.civic-activity')).to_contain_text(issue['id'])
                expect(page.locator('.civic-summary-card.rose')).to_contain_text('1 saved self-reports')
                checks.append('Required category/description/location, whitespace and invalid-photo rejection, confirmed SQLite persistence, reload and actual dashboard activity')
                nav(3)
                expect(page.get_by_role('heading',name='Projects & Reports',exact=True)).to_be_visible()
                expect(page.locator('.workspace-project-records')).to_contain_text(f"{len(data['projects']) if data else 0:,} published project records")
                if REAL:
                    first_project=api('/projects?page=1&page_size=20')['items'][0]
                    page.get_by_role('button',name=first_project['scheme_name'],exact=True).first.click()
                    expect(page.get_by_role('dialog')).to_be_visible();page.get_by_role('button',name='Close',exact=True).click()
                    page.get_by_label('Search project listings',exact=True).fill(first_project['scheme_name'])
                    expect(page.locator('.workspace-project-records tbody')).to_contain_text(first_project['scheme_name'])
                else:expect(page.locator('.workspace-project-records')).to_contain_text('No sourced project records')
                page.get_by_role('tab',name='Data reports',exact=True).click()
                expect(page.locator('.dataset-reports')).to_contain_text('2,542')
                expect(page.locator('.dataset-reports')).to_contain_text('70,404')
                expect(page.locator('.dataset-reports')).to_contain_text('No 2015 polygon join is established.')
                with page.expect_download() as download:page.get_by_role('button',name='Download issues CSV',exact=True).click()
                exported=Path(download.value.path()).read_text();assert issue['id'] in exported and 'official_submission' in exported
                with page.expect_download() as download:page.locator('.dataset-reports').get_by_role('link',name='Download original GeoJSON',exact=True).click()
                assert hashlib.sha256(Path(download.value.path()).read_bytes()).hexdigest()==manifest['sha256']
                checks.append('Truthful empty/published project views, source details, dataset provenance and real issue/GeoJSON downloads')
                for language,(navigation,headings) in LABELS.items():
                    page.locator('.us-language select').select_option(language)
                    page.set_viewport_size({'width':390,'height':844})
                    for index,label in enumerate(navigation):
                        page.locator('.us-mobile-nav').click()
                        active=page.locator('.us-sidebar nav a[aria-current="page"]')
                        expect(active).to_be_focused()
                        if index==0:
                            page.keyboard.press('Escape');expect(page.locator('.us-mobile-nav')).to_have_attribute('aria-expanded','false')
                            expect(page.locator('.us-mobile-nav')).to_be_focused();page.locator('.us-mobile-nav').click()
                        page.locator('.us-sidebar nav').get_by_role('link',name=label,exact=True).click()
                        expect(page.get_by_role('heading',level=1,name=headings[index],exact=True)).to_be_visible()
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(language,index)
                        assert not re.search(r'\b(?:civic|nav|issues|projects)\.[A-Za-z]',page.locator('main').inner_text())
                        page.screenshot(path=str(OUT/f'{language}-{index}-mobile.png'),full_page=True)
                    page.reload();expect(page.locator('html')).to_have_attribute('lang',language)
                checks.append('All four sections in English/Hindi/Marathi, 390px navigation and layouts without page overflow; language persists on reload')
                page.locator('.us-language select').select_option('en');page.set_viewport_size({'width':1586,'height':992});nav(2)
                page.get_by_label('Issue category',exact=True).select_option('water');page.get_by_label('Issue description',exact=True).fill('TEST ONLY failed network submission must remain unsaved.');page.get_by_label('Location description (required)',exact=True).fill('TEST ONLY location')
                page.route('**/api/urban/data/issues',lambda route:route.abort() if route.request.method=='POST' else route.continue_())
                page.get_by_role('button',name='Save issue report',exact=True).click()
                expect(page.get_by_role('alert')).to_contain_text('Cannot connect')
                expect(page.get_by_role('heading',name='Report saved',exact=True)).to_have_count(0)
                assert api('/issues')['total']==1
                page.unroute('**/api/urban/data/issues')
                page.route('**/api/urban/data/issues',lambda route:route.fulfill(status=200,body='{}',content_type='application/json'))
                page.get_by_role('button',name='Save issue report',exact=True).click()
                expect(page.get_by_role('alert')).to_contain_text('did not confirm report persistence')
                expect(page.get_by_role('heading',name='Report saved',exact=True)).to_have_count(0)
                assert api('/issues')['total']==1
                context.close()
                for payload in ['', 'not JSON']:
                    failing=browser.new_context(viewport={'width':390,'height':844})
                    failing.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
                    failing.route('**/data/mumbai_slum_clusters_2015.geojson',lambda route:route.fulfill(status=200,body=payload,content_type='application/json'))
                    broken=failing.new_page();broken.on('pageerror',lambda error:errors.append(str(error)));broken.goto(WEB+'/dashboard')
                    expect(broken.locator('.civic-summary-card.blue')).to_contain_text('Unavailable',timeout=20000)
                    expect(broken.locator('.us-reference-boundary')).to_have_count(0)
                    expect(broken.get_by_role('alert').first).to_be_visible()
                    failing.close()
                pending_context=browser.new_context(viewport={'width':390,'height':844})
                pending_context.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
                pending=[]
                pending_context.route('**/api/urban/data/overview',lambda route:pending.append(route))
                delayed=pending_context.new_page();delayed.goto(WEB+'/dashboard')
                expect(delayed.locator('.civic-summary-card.amber')).to_contain_text('Loading…')
                expect(delayed.locator('.civic-summary-card.mint')).to_contain_text('Loading…')
                assert 'Register import is not available' not in delayed.locator('.civic-summary-card.amber').inner_text()
                expect(delayed.locator('.us-reference-boundary')).to_have_count(count,timeout=20000)
                for route in pending:route.continue_()
                expect(delayed.locator('.civic-summary-card.amber')).to_contain_text('extracted rows' if REAL else 'Import pending')
                pending_context.close()
                checks.append('Network failure cannot claim issue success; empty and malformed source files produce useful errors without fake polygons; delayed APIs retain truthful loading states')
                browser.close()
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
