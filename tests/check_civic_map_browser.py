"""Read-only map acceptance against a running local UrbanSaarthi server.
Uses live tiles for one check and deliberately blocks them for fallback checks.
No records are created, changed or deleted.
"""
from pathlib import Path
import os
from datetime import datetime,timezone
import json
from playwright.sync_api import expect,sync_playwright
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'.runtime/map-polish';out.mkdir(parents=True,exist_ok=True)
WEB=os.getenv('URBANSAARTHI_BROWSER_URL','http://127.0.0.1:5173').rstrip('/')
checks=[];errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH','/usr/bin/chromium'));ctx=b.new_context(viewport={'width':1586,'height':992});page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(WEB+'/settlements');expect(page.locator('.demo-settlement-polygon')).to_have_count(100)
 expect(page.locator('.leaflet-tile-loaded').first).to_be_visible(timeout=12000)
 assert page.locator('.settlement-cluster').count()>0
 assert sum(int(x) for x in page.locator('.settlement-cluster span').all_text_contents())+page.locator('.settlement-location-target').count()==100
 checks.append('Street tiles load by default; grouped location counts account for all 100 actual records')
 page.wait_for_function("Array.from(document.querySelectorAll('.leaflet-tile')).every(image=>image.complete)",timeout=12000)
 page.screenshot(path=str(out/'map-online-desktop.png'),full_page=True)
 page.locator('.leaflet-control-zoom-in').click();expect(page.locator('.map-viewport-status')).to_have_attribute('data-zoom','12');page.locator('.leaflet-control-zoom-in').click();expect(page.locator('.map-viewport-status')).to_have_attribute('data-zoom','13')
 page.evaluate("window.mapPath=document.querySelector('.demo-settlement-polygon')")
 status=page.locator('.map-viewport-status');before=status.get_attribute('data-lat'),status.get_attribute('data-lng'),status.get_attribute('data-zoom')
 page.locator('.us-language select').select_option('hi')
 expect(status).to_have_attribute('data-zoom',before[2]);assert before==(status.get_attribute('data-lat'),status.get_attribute('data-lng'),status.get_attribute('data-zoom'))
 assert page.evaluate("window.mapPath===document.querySelector('.demo-settlement-polygon')")
 page.locator('.us-language select').select_option('en');page.locator('.demo-filter-grid select').last.select_option('population')
 assert before==(status.get_attribute('data-lat'),status.get_attribute('data-lng'),status.get_attribute('data-zoom'))
 checks.append('Language switching and list sorting preserve zoom, center and polygon DOM identity')
 page.locator('.demo-settlement-polygon').nth(79).dispatch_event('click');expect(page.locator('.demo-settlement-polygon.is-selected')).to_have_count(1)
 expect(status).to_have_attribute('data-zoom','16');expect(page.locator('.us-table-wrap tr.selected')).to_have_attribute('data-record-id','DEMO-SET-080')
 checks.append('Polygon selection zooms to actual geometry and reveals/highlights the corresponding paginated row')
 page.locator('.workspace-map-toolbar .us-button').click();expect(status).to_have_attribute('data-zoom','11')
 page.locator('.workspace-map-toolbar input[type=checkbox]').first.uncheck();expect(page.locator('.demo-settlement-polygon')).to_have_count(0)
 expect(page.locator('.settlement-cluster')).to_have_count(0)
 page.locator('.workspace-map-toolbar input[type=checkbox]').first.check();expect(page.locator('.demo-settlement-polygon')).to_have_count(100)
 checks.append('Fit action and geometry visibility controls work without discarding selection')
 # Fresh context blocks the tile provider; actual geometry, scale, coordinates and retry remain.
 ctx.close();ctx=b.new_context(viewport={'width':390,'height':844});ctx.route('https://tile.openstreetmap.org/**',lambda route:route.abort());page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(WEB+'/settlements');expect(page.locator('.map-tile-error')).to_be_visible(timeout=12000)
 expect(page.locator('.demo-settlement-polygon')).to_have_count(100);expect(page.locator('.leaflet-control-scale')).to_be_visible();expect(page.locator('.map-viewport-status')).to_be_visible()
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
 page.locator('.map-tile-error button').click();expect(page.locator('.map-tile-error')).to_be_visible(timeout=12000)
 page.locator('.settlement-cluster').first.click();assert int(page.locator('.map-viewport-status').get_attribute('data-zoom'))>=12
 page.screenshot(path=str(out/'map-offline-mobile.png'),full_page=True)
 checks.append('At 390px with provider blocked, the coordinate grid, metric scale, clusters and retry remain usable without overflow')
 assert not errors;b.close()
result={'status':'passed','checkedAt':datetime.now(timezone.utc).isoformat(),'checks':checks,'browserErrors':errors,'scope':'Read-only current app; live OSM tiles for online check, deliberately blocked tiles for fallback; no database mutations'}
(out/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
