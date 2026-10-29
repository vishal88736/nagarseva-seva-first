"""Actual Chromium QA of the supplied 2015 reference layer in three languages.

Uses disposable API storage; never writes the user's workspace or source data.
"""
from datetime import datetime, timezone
import hashlib
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
OUT = ROOT/'.runtime/boundaries-browser'
API = 'http://127.0.0.1:18103'
WEB = 'http://127.0.0.1:15177'
ASSET = '/data/mumbai_slum_clusters_2015.geojson'
META = '/data/mumbai_slum_clusters_2015.metadata.json'
LABELS = {
    'en': ['2015 Reference Boundaries','Historical reference boundaries — 2015. Not verified against the 2024 SRA cluster list.','2015 reference boundary','Reference Polygon 001','Reference boundary layer hidden','Retry reference boundaries','Boundary source & limitations','Fit reference boundaries'],
    'hi': ['2015 संदर्भ सीमाएँ','ऐतिहासिक संदर्भ सीमाएँ — 2015। 2024 की SRA क्लस्टर सूची से सत्यापित नहीं हैं।','2015 की संदर्भ सीमा','संदर्भ बहुभुज 001','संदर्भ सीमा परत छिपी हुई है','संदर्भ सीमाएँ फिर लोड करें','सीमा स्रोत और सीमाएँ','संदर्भ सीमाएँ पूरी दिखाएँ'],
    'mr': ['2015 संदर्भ सीमा','ऐतिहासिक संदर्भ सीमा — 2015. 2024 च्या SRA क्लस्टर यादीशी पडताळणी केलेली नाही.','2015 ची संदर्भ सीमा','संदर्भ बहुभुज ००१','संदर्भ सीमा स्तर लपवला आहे','संदर्भ सीमा पुन्हा लोड करा','सीमांचा स्रोत आणि मर्यादा','सर्व संदर्भ सीमा दाखवा'],
}


def wait_for(url, process):
    for _ in range(100):
        if process.poll() is not None: raise RuntimeError('Owned QA server exited; inspect .runtime/boundaries-browser')
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200: return
        except OSError: time.sleep(.2)
    raise RuntimeError('QA service readiness timeout')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    checks, errors, processes, logs = [], [], [], []
    report = {'status':'failed','checked_at':datetime.now(timezone.utc).isoformat(),'scope':'Actual Chromium, bundled historical GeoJSON and disposable API; no field validation','checks':checks,'browser_errors':errors,'tested_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'working_tree_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),'source_features':2542,'rendered_features':2517,'topology_exclusions':25,'basemap_tiles':'Blocked for deterministic tests; no live tile availability claim'}
    try:
        with tempfile.TemporaryDirectory(prefix='urban-reference-browser-') as folder:
            key = secrets.token_urlsafe(32)
            env = {**os.environ,'URBANSAARTHI_DB_PATH':str(Path(folder)/'test.sqlite3'),'NAGARSEVA_OFFICER_KEY':key,'NAGARSEVA_API_TARGET':API,'URBANSAARTHI_DATA_DIR':str(Path(folder)/'empty-source')}
            for name,command,cwd in [('api',[sys.executable,'-m','uvicorn','model.api.urban:app','--host','127.0.0.1','--port','18103'],ROOT/'nagarseva'),('web',['npm','run','preview','--','--port','15177','--strictPort'],ROOT/'nagarseva/website')]:
                log=(OUT/f'{name}.log').open('w'); logs.append(log); processes.append(subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT))
            wait_for(API+'/urban/data/health',processes[0]); wait_for(WEB,processes[1])
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH') or None)
                context = browser.new_context(viewport={'width':1440,'height':1000})
                context.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
                page = context.new_page(); page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(WEB+'/#explore')
                paths = page.locator('.us-reference-boundary')
                expect(paths).to_have_count(2517,timeout=20000)
                expect(page.locator('.workspace-reference-notice')).to_be_visible()
                expect(page.locator('.workspace-reference-status')).to_contain_text('2,517 of 2,542')
                first = paths.first; extent=page.locator('.leaflet-container').bounding_box(); box=first.bounding_box()
                assert extent and box and extent['x'] <= box['x']+box['width']/2 <= extent['x']+extent['width'] and extent['y'] <= box['y']+box['height']/2 <= extent['y']+extent['height']
                page.locator('.workspace-map-toolbar details summary').click()
                for language, labels in LABELS.items():
                    page.locator('.us-language select').select_option(language)
                    expect(page.locator('html')).to_have_attribute('lang',language)
                    expect(page.get_by_label(labels[0],exact=True)).to_be_checked()
                    expect(page.locator('.workspace-reference-notice')).to_be_visible()
                    expect(paths).to_have_count(2517)
                    expect(page.locator('.leaflet-control-zoom-in')).to_have_count(1)
                    page.get_by_role('button',name=labels[3],exact=True).press('Enter')
                    popup=page.locator('.leaflet-popup-content')
                    expect(popup).to_contain_text(labels[3])
                    expect(popup).to_contain_text('SRA')
                    assert not any(word in popup.inner_text() for word in ['Fixture Harbour','GANESH MURTHI','population','Households'])
                    page.screenshot(path=str(OUT/f'map-{language}.png'),full_page=True)
                    page.locator('.leaflet-popup-close-button').click()
                    page.get_by_label(labels[0],exact=True).uncheck()
                    expect(paths).to_have_count(0); expect(page.locator('.workspace-reference-status')).to_contain_text(labels[4])
                    page.get_by_label(labels[0],exact=True).check(); expect(paths).to_have_count(2517)
                # DOM click dispatch also exercises Leaflet's popup handler.
                page.get_by_role('button',name=LABELS['mr'][3],exact=True).dispatch_event('click')
                expect(page.locator('.leaflet-popup-content')).to_contain_text(LABELS['mr'][3])
                page.locator('.us-language select').select_option('hi')
                expect(page.locator('.leaflet-popup-content')).to_contain_text(LABELS['hi'][3])
                page.locator('.leaflet-popup-close-button').click()
                page.locator('.us-language select').select_option('mr')
                checks.append('All 2542 original features are parsed; 2517 topology-valid polygons render at the Mumbai extent, with source-only click/keyboard popups, translated open popups and a working toggle in English, Hindi and Marathi')
                page.get_by_role('button',name=LABELS['mr'][7],exact=True).click()
                zoom=page.locator('.leaflet-control-zoom-in'); zoom.click(); page.wait_for_timeout(350)
                transform=page.locator('.leaflet-map-pane').get_attribute('style')
                search=page.locator('.workspace-map-toolbar input:not([type=checkbox])').first
                search.fill('retained search')
                page.get_by_label(LABELS['mr'][0],exact=True).uncheck()
                page.locator('.us-language select').select_option('hi')
                expect(search).to_have_value('retained search')
                expect(page.get_by_label(LABELS['hi'][0],exact=True)).not_to_be_checked()
                assert page.locator('.leaflet-map-pane').get_attribute('style') == transform
                page.reload(); expect(page.locator('html')).to_have_attribute('lang','hi'); expect(paths).to_have_count(2517)
                checks.append('Language changes preserve the live map viewport, visibility and search state; the chosen language survives reload')
                for language,labels in LABELS.items():
                    page.locator('.us-language select').select_option(language)
                    page.set_viewport_size({'width':390,'height':844})
                    expect(page.locator('.workspace-reference-notice')).to_be_visible()
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                    page.screenshot(path=str(OUT/f'mobile-{language}.png'),full_page=True)
                checks.append('390px mobile layout has no horizontal overflow in any supported language')
                offline=browser.new_context(viewport={'width':1200,'height':900})
                offline.route('**/api/urban/data/**',lambda route:route.abort())
                offline.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
                offline_page=offline.new_page(); offline_page.goto(WEB+'/#explore')
                expect(offline_page.locator('.us-reference-boundary')).to_have_count(2517,timeout=20000)
                expect(offline_page.locator('.workspace-reference-notice')).to_be_visible()
                offline.close()
                checks.append('The bundled historical layer remains usable when the operational API is unavailable')
                # Error states use new contexts so immutable in-memory caching cannot conceal a failed fetch.
                for kind in ['http','empty','malformed','empty-collection']:
                    ctx=browser.new_context(viewport={'width':1200,'height':900})
                    ctx.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
                    ctx.add_init_script("localStorage.setItem('urbansaarthi-language','mr')")
                    p=ctx.new_page(); p.on('pageerror',lambda error:errors.append(str(error)))
                    if kind == 'http': p.route('**'+ASSET,lambda route:route.fulfill(status=503,body='Unavailable'))
                    elif kind == 'empty': p.route('**'+ASSET,lambda route:route.fulfill(status=200,body=''))
                    elif kind == 'malformed': p.route('**'+META,lambda route:route.fulfill(status=200,body='not JSON'))
                    else:
                        empty=json.dumps({'type':'FeatureCollection','features':[]}).encode()
                        metadata=json.loads((ROOT/'nagarseva/website/public'/META.lstrip('/')).read_text())
                        metadata.update(source_feature_count=0,valid_feature_count=0,excluded_features=[],sha256=hashlib.sha256(empty).hexdigest(),bytes=len(empty))
                        p.route('**'+ASSET,lambda route:route.fulfill(status=200,body=empty))
                        p.route('**'+META,lambda route:route.fulfill(status=200,body=json.dumps(metadata)))
                    p.goto(WEB+'/#explore')
                    if kind == 'empty-collection': expect(p.locator('.workspace-reference-error')).to_contain_text('संदर्भ सीमा उपलब्ध नाहीत.')
                    else:
                        expect(p.get_by_role('button',name=LABELS['mr'][5],exact=True)).to_be_visible()
                        assert p.locator('.workspace-reference-error').inner_text().count('Reference boundary') == 0
                        if kind == 'http':
                            p.unroute('**'+ASSET); p.get_by_role('button',name=LABELS['mr'][5],exact=True).click(); expect(p.locator('.us-reference-boundary')).to_have_count(2517,timeout=20000)
                    ctx.close()
                checks.append('HTTP failures, empty responses, malformed metadata and empty valid collections show localized states; retry recovers a failed request')
                # Import is isolated, with no auto-join to a historical polygon.
                fixture=workspace_fixture(); fixture['settlements']['features'][0]['properties']['name']='Overview'
                request=urllib.request.Request(API+'/urban/data/workspace/import',headers={'X-Officer-Key':key,'Content-Type':'application/json'},data=json.dumps({'dataset':fixture,'expected_snapshot':None}).encode())
                with urllib.request.urlopen(request,timeout=15) as response: assert response.status == 201
                page.set_viewport_size({'width':1440,'height':1000}); page.goto(WEB+'/#explore'); page.reload()
                expect(page.get_by_role('heading',name='Overview',exact=True)).to_be_visible()
                expect(paths).to_have_count(2517)
                for language in LABELS:
                    page.locator('.us-language select').select_option(language)
                    expect(page.get_by_role('heading',name='Overview',exact=True)).to_be_visible()
                with urllib.request.urlopen(API+'/urban/data/overview',timeout=10) as response: stats=json.load(response)
                assert stats['settlements_loaded'] == 2 and stats['settlements_with_geometry'] == 2
                checks.append('Imported settlement names remain original; the 2015 layer adds no settlement, household or service observations and no identifier joins')
                context.close(); browser.close()
        assert not errors,errors
        report['status']='passed'
    finally:
        for process in reversed(processes):
            process.terminate()
            try: process.wait(timeout=8)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        for log in logs: log.close()
        (OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
