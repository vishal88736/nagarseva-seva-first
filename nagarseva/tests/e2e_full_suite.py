"""Run an isolated, synthetic browser walkthrough. No real resident data is written."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright, expect
from weather_fixture import weather_fixture

ROOT = Path(__file__).resolve().parents[1]
API_PORT, WEB_PORT = 17860, 17861
API = f"http://127.0.0.1:{API_PORT}"
SITE = f"http://127.0.0.1:{WEB_PORT}"
SCREENSHOTS = Path("/tmp/nagarseva-browser-review")


def get_json(path: str):
    with urllib.request.urlopen(API + path, timeout=15) as response:
        return json.load(response)


def ready(url: str, process: subprocess.Popen):
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Server exited before it became ready: {url}")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(.2)
    raise RuntimeError(f"Server readiness timed out: {url}")


def main():
    SCREENSHOTS.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nagarseva-e2e-") as folder:
        env = {**os.environ, "NAGARSEVA_MODE": "demo", "NAGARSEVA_OFFICER_KEY": "", "NAGARSEVA_DB_PATH": str(Path(folder) / "test.sqlite3"), "NAGARSEVA_API_TARGET": API, "NAGARSEVA_WEATHER_ENABLED": "0"}
        processes = []
        with open(Path(folder) / "servers.log", "w+") as log:
            try:
                api = subprocess.Popen(["python3", "-m", "uvicorn", "model.api.main:app", "--host", "127.0.0.1", "--port", str(API_PORT), "--loop", "asyncio"], cwd=ROOT, env=env, stdout=log, stderr=log, start_new_session=True)
                processes.append(api); ready(API + "/health", api)
                web = subprocess.Popen(["npm", "run", "preview", "--", "--host", "127.0.0.1", "--port", str(WEB_PORT), "--strictPort"], cwd=ROOT / "website", env=env, stdout=log, stderr=log, start_new_session=True)
                processes.append(web); ready(SITE, web)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
                    context.route('https://tile.openstreetmap.org/**', lambda route: route.abort())
                    page = context.new_page(); errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(SITE + "/#resident/NS-0001")
                    expect(page.get_by_label("Complaint", exact=True)).to_be_visible()
                    expect(page.get_by_label("Select project")).to_have_value("NS-0001")
                    page.get_by_label("Complaint", exact=True).fill("Water supply stopped for three days. Synthetic browser fixture.")
                    with page.expect_response(lambda r: r.url.endswith("/api/grievances") and r.request.method == "POST") as created:
                        page.get_by_role("button", name="Submit complaint", exact=True).click()
                    report = created.value.json(); assert report["pocket_id"] == "NS-0001"
                    assert report["status"] == "received" and report["synthetic"] is True
                    with page.expect_download() as exported:
                        page.get_by_role("button", name="Download private receipt", exact=True).first.click()
                    receipt = json.loads(Path(exported.value.path()).read_text())
                    assert receipt["complaint_id"] == report["complaint_id"]
                    page.goto(SITE + "/#admin/NS-0001")
                    page.get_by_role("button", name="Review report", exact=True).click()
                    panel = page.locator('.action-panel')
                    panel.get_by_label("Officer / reviewer name", exact=True).fill("Browser fixture reviewer")
                    panel.get_by_label("Action notes", exact=True).fill("Reviewed report; assigned water team")
                    panel.get_by_label("Likely category", exact=True).select_option('water')
                    panel.get_by_label("Responsible department", exact=True).fill("Water supply")
                    panel.get_by_role("button", name="Assign", exact=True).click()
                    expect(panel.get_by_role('button', name='Start work', exact=True)).to_be_visible()
                    panel.get_by_label("Action notes", exact=True).fill("Work started; inspection scheduled")
                    panel.get_by_role('button', name='Start work', exact=True).click()
                    expect(panel.get_by_role('button', name='Start work', exact=True)).not_to_be_visible()
                    panel.get_by_label("Action notes", exact=True).fill("Repair completed; resident confirmation requested")
                    panel.get_by_label(re.compile('Measured value')).fill("8")
                    panel.get_by_label('Source / measurement method', exact=True).fill("Browser fixture inspection log")
                    panel.get_by_label('Evidence', exact=True).fill("Synthetic after-repair reading from the demonstration")
                    with page.expect_response(lambda r: r.url.endswith('/action') and r.request.method == 'POST') as repaired:
                        panel.get_by_role('button', name='Submit repair for confirmation', exact=True).click()
                    assert repaired.value.json()['status'] == 'awaiting_confirmation'
                    page.screenshot(path=str(SCREENSHOTS / 'officer-desktop.png'), full_page=True)
                    panel.screenshot(path=str(SCREENSHOTS / 'repair-history.png'))
                    page.goto(SITE + "/#resident/NS-0001")
                    page.get_by_role('tab', name='Track a complaint', exact=True).click()
                    expect(page.get_by_text('Browser fixture inspection log', exact=False)).to_be_visible()
                    page.get_by_label('What changed, or what is still failing?', exact=True).fill('Demo supply is restored; confirming the fixture repair')
                    with page.expect_response(lambda r: r.url.endswith('/confirm')) as confirmed:
                        page.get_by_role('button', name='Yes, the issue is resolved', exact=True).click()
                    assert confirmed.value.json()['status'] == 'resolved'
                    assert get_json('/stats/summary')['resident_verified_closures'] == 1
                    assert get_json('/pilot/evidence')['metrics']['real_verified_closures'] == 0
                    record = get_json('/service/NS-0001/assurance')
                    assert record['services']['water']['value'] == 8 and record['services']['water']['verification'] == 'resident_confirmed'
                    page.goto(SITE + '/#assurance/NS-0001')
                    expect(page.locator('.service-record-card').first).to_contain_text('Browser fixture inspection log')
                    page.screenshot(path=str(SCREENSHOTS / 'assurance-desktop.png'), full_page=True)
                    page.screenshot(path=str(SCREENSHOTS / 'assurance-viewport.png'))
                    page.goto(SITE + '/#simulator/NS-0001')
                    expect(page.get_by_label('Eligible rehab households', exact=True)).to_have_value(str(round(get_json('/pockets/NS-0001')['households'])))
                    expect(page.get_by_text('Household affordability', exact=True)).to_be_visible()
                    page.get_by_label('Monthly household income', exact=True).fill('22000')
                    page.goto(SITE + '/#simulator/NS-0002')
                    expect(page.get_by_label('Select project')).to_have_value('NS-0002')
                    page.goto(SITE + '/#simulator/NS-0001')
                    expect(page.get_by_label('Monthly household income', exact=True)).to_have_value('22000')
                    with page.expect_download() as exported:
                        page.get_by_role('button', name='Download scenario', exact=True).click()
                    scenario = json.loads(Path(exported.value.path()).read_text())
                    assert scenario['pocket_id'] == 'NS-0001' and scenario['household_income_inr'] == 22000
                    page.locator('.affordability-panel').screenshot(path=str(SCREENSHOTS / 'affordability-desktop.png'))
                    page.goto(SITE + '/#optimizer/NS-0001')
                    expect(page.get_by_role('button', name='Export CSV', exact=True)).to_be_enabled(timeout=30000)
                    with page.expect_download() as exported:
                        page.get_by_role('button', name='Export CSV', exact=True).click()
                    assert 'pocket_id' in Path(exported.value.path()).read_text()
                    page.goto(SITE + '/#pilot/NS-0001')
                    expect(page.get_by_text('No field observation is recorded for this project yet.', exact=True)).not_to_be_visible()
                    expect(page.get_by_text('Median seconds saved', exact=True)).to_be_visible()
                    assert get_json('/pilot/evidence')['metrics']['real_evaluations'] == 0
                    # Complete the pilot forms using synthetic fixtures in the isolated database.
                    observation_panel = page.locator('section').filter(has=page.get_by_role('heading', name='Record service observation', exact=True))
                    observation_panel.get_by_label(re.compile('Measured value')).fill('6')
                    observation_panel.get_by_label('Source / measurement method', exact=True).fill('Browser field observation fixture')
                    observation_panel.get_by_label('Evidence', exact=True).fill('Synthetic inspection fixture with known service units')
                    with page.expect_response(lambda r: r.url.endswith('/observations') and r.request.method == 'POST'):
                        observation_panel.get_by_role('button', name='Record service observation', exact=True).click()
                    history_panel = page.locator('section').filter(has=page.get_by_role('heading', name='Observation history', exact=True))
                    history_panel.get_by_label('Officer / reviewer name', exact=True).fill('Fixture field reviewer')
                    history_panel.get_by_label('Field review notes', exact=True).fill('Reviewed the synthetic inspection fixture')
                    history_panel.locator('article').filter(has_text='Browser field observation fixture').get_by_role('button', name='Verify field observation', exact=True).click()
                    expect(history_panel.locator('article').filter(has_text='Browser field observation fixture')).to_contain_text('Field reviewer verified')
                    page.locator('.resident-tabs button').nth(1).click()
                    evaluation_panel = page.locator('section').filter(has=page.get_by_role('heading', name='Record user evaluation', exact=True)).filter(has=page.locator('form'))
                    evaluation_panel.get_by_label('Anonymous participant reference', exact=True).fill('DEMO-001')
                    evaluation_panel.get_by_label('Baseline task time (seconds)', exact=True).fill('120')
                    evaluation_panel.get_by_label('NagarSeva task time (seconds)', exact=True).fill('60')
                    evaluation_panel.get_by_label('Feedback / errors observed', exact=True).fill('Synthetic usability fixture, not a real pilot participant')
                    with page.expect_response(lambda r: r.url.endswith('/pilot/evaluations') and r.request.method == 'POST'):
                        evaluation_panel.get_by_role('button', name='Record user evaluation', exact=True).click()
                    assert get_json('/pilot/evidence')['metrics']['real_evaluations'] == 0
                    page.locator('.resident-tabs button').nth(2).click()
                    commitment_panel = page.locator('section').filter(has=page.get_by_role('heading', name='Approved service commitment', exact=True))
                    commitment_panel.get_by_label('Planning target', exact=True).fill('6')
                    commitment_panel.get_by_label('Standard / commitment reference', exact=True).fill('Browser fixture project commitment')
                    commitment_panel.get_by_label('Responsible department', exact=True).fill('Water supply')
                    commitment_panel.get_by_label('Approved by', exact=True).fill('Browser fixture reviewer')
                    with page.expect_response(lambda r: r.url.endswith('/commitment') and r.request.method == 'POST'):
                        commitment_panel.get_by_role('button', name='Save service commitment', exact=True).click()
                    assert get_json('/service/NS-0001/assurance')['services']['water']['target'] == 6
                    assert get_json('/pilot/evidence')['metrics']['field_verified_observations'] == 0
                    # Approved-import UI fixture: this is never written to the normal local database.
                    imported = {'pocket_id':'PILOT-E2E','city':'Pune','ward':'Fixture ward','lat':18.52,'lon':73.85,'area_sqm':2000,'households':20,'population':80,'source_label':'Synthetic browser import fixture, not field data','source_url':'https://example.org/test-fixture','licence':'Synthetic test fixture only','approved_by':'Fixture reviewer','consent':True}
                    page.get_by_label('Location JSON', exact=True).fill(json.dumps(imported))
                    with page.expect_response(lambda r: r.url.endswith('/pilot/locations') and r.request.method == 'POST'):
                        page.get_by_role('button',name='Import approved location',exact=True).click()
                    page.goto(SITE + '/#pocket/PILOT-E2E')
                    expect(page.get_by_label('Select project')).to_have_value('PILOT-E2E')
                    expect(page.get_by_text('Unassessed',exact=True)).to_be_visible()
                    expect(page.get_by_text('Field measurements and an independent priority review are needed before ranking this location.',exact=True)).to_be_visible()
                    page.goto(SITE + '/#dashboard/PILOT-E2E')
                    page.get_by_label('Filter by city',exact=True).select_option('Pune')
                    expect(page.get_by_text('1',exact=True).first).to_be_visible()
                    # Public sources and forecasts: no live provider traffic during automated tests.
                    page.goto(SITE + '/#sources/NS-0001')
                    expect(page.get_by_text('External weather access is disabled for this deployment.', exact=True)).to_be_visible()
                    page.route('**/api/context/*/weather', lambda route: route.fulfill(json=weather_fixture()))
                    page.reload()
                    expect(page.locator('.forecast-day')).to_have_count(7)
                    with page.expect_download() as forecast_export:
                        page.get_by_role('button', name='Download forecast & source', exact=True).click()
                    forecast_file = forecast_export.value
                    forecast_file.save_as(str(SCREENSHOTS / 'forecast-fixture.json'))
                    forecast = json.loads((SCREENSHOTS / 'forecast-fixture.json').read_text())
                    assert forecast['licence'] == 'CC BY 4.0' and len(forecast['days']) == 7
                    page.unroute('**/api/context/*/weather')
                    page.route('**/api/context/*/weather', lambda route: route.fulfill(json=weather_fixture('stale')))
                    page.reload()
                    expect(page.get_by_text('Previously fetched forecast; the provider could not be refreshed. Check the retrieval time before using it.', exact=True)).to_be_visible()
                    page.unroute('**/api/context/*/weather')
                    page.route('**/api/context/*/weather', lambda route: route.fulfill(json=weather_fixture('unavailable')))
                    page.reload()
                    expect(page.locator('.forecast-day')).to_have_count(0)
                    expect(page.get_by_text('Weather is unavailable. No sample forecast is substituted; check the official IMD portal or try again later.', exact=True)).to_be_visible()
                    assert page.locator('a[href="https://pmaymis.gov.in/pmaymis2_2024/PmayFAQ.aspx"]').count() > 0
                    assert page.locator('a[href="https://censusindia.gov.in/nada/index.php/catalog/6190/study-description"]').count() > 0
                    page.unroute('**/api/context/*/weather')
                    # Check responsive layout for every product flow.
                    page.set_viewport_size({'width': 390, 'height': 844})
                    for screen in ['home', 'dashboard', 'pocket', 'simulator', 'optimizer', 'resident', 'admin', 'assurance', 'methodology', 'sources', 'pilot']:
                        page.goto(SITE + f'/#{screen}/NS-0001')
                        expect(page.locator('.page-pad')).to_be_visible()
                        page.wait_for_timeout(400)
                        if not page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'):
                            page.screenshot(path=str(SCREENSHOTS / f'{screen}-overflow.png'), full_page=True)
                            offenders = page.evaluate("[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1 && getComputedStyle(e).position !== 'absolute').slice(0, 12).map(e => ({tag: e.tagName, cls: e.className, text: e.textContent.slice(0, 70), right: e.getBoundingClientRect().right}))")
                            raise AssertionError(f'Mobile overflow: {screen}: {offenders}')
                    page.screenshot(path=str(SCREENSHOTS / 'pilot-mobile.png'), full_page=True)
                    page.get_by_label('Language', exact=True).select_option('mr')
                    expect(page.get_by_text('परिणाम दाव्यापूर्वी पुरावे गोळा करा', exact=True)).to_be_visible()
                    page.get_by_label('भाषा', exact=True).select_option('hi')
                    expect(page.get_by_text('प्रभाव दावे से पहले प्रमाण जुटाएं', exact=True)).to_be_visible()
                    assert not errors, errors
                    # Offline previews must never manufacture a submitted complaint.
                    fallback = json.loads((ROOT / 'website/src/data/fallback.json').read_text())
                    offline_context = browser.new_context(viewport={'width': 390, 'height': 844})
                    offline_context.route('**/api/**', lambda route: route.abort())
                    off = offline_context.new_page()
                    off.goto(SITE + '/#resident/' + fallback['items'][0]['pocket_id'])
                    expect(off.get_by_label('Complaint', exact=True)).to_be_visible()
                    off.get_by_label('Complaint', exact=True).fill('Offline fixture report; keep this text as a draft')
                    off.get_by_role('button', name='Submit complaint', exact=True).click()
                    expect(off.get_by_role('alert')).to_contain_text('server could not confirm')
                    expect(off.get_by_label('Complaint', exact=True)).to_have_value('Offline fixture report; keep this text as a draft')
                    assert get_json('/grievances')['total'] == 1
                    off.get_by_role('button', name='Save draft', exact=True).click()
                    off.reload(); expect(off.get_by_label('Complaint', exact=True)).to_have_value('Offline fixture report; keep this text as a draft')
                    off.screenshot(path=str(SCREENSHOTS / 'offline-resident-mobile.png'), full_page=True)
                    blocked = browser.new_context(viewport={'width':390,'height':844},accept_downloads=True)
                    blocked.add_init_script("Storage.prototype.getItem=()=>{throw new DOMException('Blocked','SecurityError')};Storage.prototype.setItem=()=>{throw new DOMException('Blocked','SecurityError')};Storage.prototype.removeItem=()=>{throw new DOMException('Blocked','SecurityError')}")
                    limited = blocked.new_page(); limited.goto(SITE + '/#resident/NS-0001')
                    expect(limited.get_by_text('Browser storage is unavailable.',exact=False)).to_be_visible()
                    limited.get_by_label('Complaint',exact=True).fill('Water supply issue; synthetic blocked-storage fixture')
                    limited.get_by_role('button',name='Submit complaint',exact=True).click()
                    with limited.expect_download() as backup:
                        limited.get_by_role('button',name='Download private receipt',exact=True).first.click()
                    assert json.loads(Path(backup.value.path()).read_text())['receipt_token']
                    browser.close()
                print(json.dumps({'result': 'passed', 'checks': ['complaint lifecycle', 'private receipt export', 'resident confirmation', 'service update', 'real/demo separation', 'shared project context', 'affordability persistence', 'scenario/CSV exports', 'all-page mobile layout', 'Hindi/Marathi UI', 'pilot observation/evaluation/commitment/import', 'blocked storage receipt delivery', 'offline write failure and draft', 'source library and official handoffs', 'forecast export and stale/unavailable states'], 'screenshots': str(SCREENSHOTS)}))
            except Exception:
                log.flush(); log.seek(0); print(log.read()[-1200:]); raise
            finally:
                for process in reversed(processes):
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        try: process.wait(timeout=5)
                        except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'{type(error).__name__}: {str(error).split("Aria snapshot:")[0]}')
        raise SystemExit(1)
