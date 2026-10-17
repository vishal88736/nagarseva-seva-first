"""Read-only smoke review of the local public integrations; mock tiles, real cached weather."""
import base64
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    output = Path('/tmp/nagarseva-public-review')
    output.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        tile = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jJm0AAAAASUVORK5CYII=')
        context.route('https://tile.openstreetmap.org/**', lambda route: route.fulfill(body=tile, content_type='image/png'))
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:5173/#dashboard/NS-0001')
        attribution = page.get_by_role('link', name='© OpenStreetMap contributors', exact=True)
        expect(attribution).to_be_visible()
        page.get_by_role('button', name='Use schematic map', exact=True).click()
        expect(attribution).to_have_count(0)
        page.get_by_role('button', name='Use geographic map', exact=True).click()
        expect(attribution).to_be_visible()
        page.goto('http://127.0.0.1:5173/#sources/NS-0001')
        expect(page.locator('.forecast-day')).to_have_count(7, timeout=20000)
        with page.expect_download() as exported:
            page.get_by_role('button', name='Download forecast & source', exact=True).click()
        exported.value.save_as(str(output / 'live-weather-export.json'))
        weather = json.loads((output / 'live-weather-export.json').read_text())
        assert weather['provider'] == 'Open-Meteo' and weather['fetched_at'] and weather['status'] in ['live', 'cached', 'stale']
        assert len(weather['days']) == 7 and weather['location_synthetic'] is True
        expect(page.locator('.source-entry')).to_have_count(8)
        assert errors == [], errors
        page.evaluate('window.scrollTo(0, 0)')
        page.evaluate('document.fonts.ready')
        page.screenshot(path=str(output / 'sources-desktop.png'), full_page=True)
        context.close()
        browser.close()
    print(json.dumps({'result': 'passed', 'map_attribution_and_switch': True, 'live_forecast_days': len(weather['days']),
                      'forecast_status': weather['status'], 'source_records': 8, 'screenshot': str(output / 'sources-desktop.png')}))


if __name__ == '__main__':
    main()
