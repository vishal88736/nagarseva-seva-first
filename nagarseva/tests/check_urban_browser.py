"""Exercise the actual five-screen app against a disposable SQLite API.

Requires a built frontend and Playwright Chromium. No field data or OSM tiles
are downloaded. Servers and the test database are owned by this check.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "nagarseva"
OUT = ROOT / ".merge-work/urban-browser"
REPORT = ROOT / "integration/urban-validation.json"


def wait_for(url, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError(f"Owned preview process exited: {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=1) as result:
                if result.status == 200:
                    return
        except Exception:
            time.sleep(.2)
    raise RuntimeError(f"Preview readiness timeout: {url}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks, screenshots, errors = [], [], []
    result = {"status": "failed", "checked_at": datetime.now(timezone.utc).isoformat(),
              "tested_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "workflow_url": f"https://github.com/{os.getenv('GITHUB_REPOSITORY', 'vishal88736/nagarseva-seva-first')}/actions/runs/{os.getenv('GITHUB_RUN_ID', 'local')}",
              "browser": "Playwright Chromium", "data": "Synthetic demonstration only", "field_validation": False}
    processes, logs = [], []
    try:
        with tempfile.TemporaryDirectory(prefix="urban-browser-") as folder:
            env = os.environ.copy()
            env.update(URBANSAARTHI_DB_PATH=str(Path(folder) / "test.sqlite3"), NAGARSEVA_MODE="demo")
            env.pop("NAGARSEVA_OFFICER_KEY", None)
            for name, args, cwd in [
                ("api", [sys.executable, "-m", "uvicorn", "model.api.urban:app", "--host", "127.0.0.1", "--port", "8000"], APP),
                ("web", ["npm", "run", "preview", "--", "--host", "127.0.0.1", "--port", "4173", "--strictPort"], APP / "website"),
            ]:
                log = (OUT / f"{name}.log").open("w")
                logs.append(log)
                processes.append(subprocess.Popen(args, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT))
            wait_for("http://127.0.0.1:8000/urban/health", processes[0])
            wait_for("http://127.0.0.1:4173", processes[1])
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
                context.route("https://tile.openstreetmap.org/**", lambda route: route.abort())
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))

                def nav(label):
                    if page.viewport_size["width"] <= 800:
                        page.get_by_role("button", name="Open navigation menu", exact=True).click()
                    page.get_by_role("navigation", name="Planning workflow").get_by_role("button", name=label, exact=True).click()

                def check(label):
                    checks.append(label)
                    print("URBAN_BROWSER_CHECK " + label, flush=True)

                page.goto("http://127.0.0.1:4173", wait_until="networkidle")
                expect(page.locator(".us-context-bar")).to_contain_text("Python calculation checked")
                expect(page.get_by_role("heading", name="A clear path from need to service.")).to_be_visible()
                expect(page.get_by_text("Official listing fact", exact=True)).to_have_count(3)
                check("Overview distinguishes five synthetic clusters from three separate official listing records")
                nav("Explore Settlements")
                expect(page.locator(".leaflet-container")).to_be_visible()
                page.get_by_label("Service deficit filter").select_option("missing")
                page.get_by_role("button", name=re.compile(r"^US-E")).click()
                expect(page.get_by_text("Unranked · missing inputs", exact=True)).to_be_visible()
                expect(page.get_by_label("Selected settlement cluster")).to_have_value("US-E")
                check("Map filter and accessible cluster selection preserve missing data")
                nav("Prioritize Needs")
                expect(page.get_by_role("row").filter(has_text="Eastern cluster E")).to_contain_text("Unranked interval")
                page.get_by_label("Selected settlement cluster").select_option("US-A")
                harbour = page.get_by_role("row").filter(has_text="Harbour cluster A")
                expect(harbour.get_by_role("cell").nth(2)).to_have_text("65.0")
                page.get_by_role("button", name="Equal weights", exact=True).click()
                expect(page.get_by_role("row").filter(has_text="Market cluster C").get_by_role("cell").first).to_have_text("1")
                page.get_by_role("button", name="Default weights", exact=True).click()
                expect(harbour.get_by_role("cell").first).to_have_text("1")
                check("Priority example equals 65.0; equal weights alter the ranking without filling missing values")
                nav("Compare Scenarios")
                expect(page.locator(".us-scenario-cards > section")).to_have_count(2)
                page.get_by_role("checkbox", name="Include a relocation thought experiment").check()
                expect(page.locator(".us-scenario-cards > section")).to_have_count(3)
                expect(page.get_by_role("alert")).to_contain_text("Explain the assumptions")
                page.get_by_label("Why is relocation relevant to this scenario?").fill("Hypothetical risk constraint only; resident consultation and official review still required.")
                page.get_by_role("checkbox", name="Include a relocation thought experiment").uncheck()
                expect(page.locator("#us-main")).to_contain_text("Python calculation checked")
                expect(page.get_by_role("button", name="Draft a service work", exact=True).first).to_be_enabled()
                check("Scenario comparison is Python-checked and relocation is explicit and conditional")
                page.get_by_role("button", name="Draft a service work", exact=True).first.click()
                page.get_by_label("Work title", exact=True).fill("CI demo water improvement")
                page.get_by_label("Due date (UTC calendar)").fill((datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat())
                page.get_by_role("button", name="Save planned work", exact=False).click()
                expect(page.get_by_role("heading", name="CI demo water improvement", exact=True)).to_be_visible()
                expect(page.get_by_text("Overdue physical work", exact=True)).to_be_visible()
                page.get_by_label("Update or review note").fill("Starting the synthetic water improvement.")
                page.get_by_role("button", name="Start work", exact=True).click()
                expect(page.get_by_role("button", name="Mark physically complete", exact=True)).to_be_visible()
                page.get_by_label("Update or review note").fill("Physical work complete; functioning-service inspection is still required.")
                page.get_by_role("button", name="Mark physically complete", exact=True).click()
                verified = page.locator(".us-metrics .us-metric").nth(3).locator("strong")
                expect(verified).to_have_text("00")
                expect(page.get_by_role("button", name="Record service verification", exact=False)).to_be_disabled()
                check("Planned work and physical completion do not count as verified services")

                def evidence(name, body):
                    page.get_by_label("Evidence file", exact=True).set_input_files({"name": name, "mimeType": "text/plain", "buffer": body.encode()})
                    page.get_by_label("Evidence description", exact=True).fill("Synthetic inspection document for the demonstration service.")
                    page.get_by_role("button", name="Attach evidence", exact=False).click()
                    expect(page.get_by_text(name, exact=True)).to_be_visible()
                    page.get_by_label("Inspection evidence", exact=True).select_option(label=f"{name} · Inspector")

                evidence("inspection.txt", "Demonstration evidence: six water supply hours per day; no field observation.")
                page.get_by_label("Measured service value", exact=True).fill("5")
                page.get_by_label("Confirm service functioning", exact=True).check()
                page.get_by_label("Update or review note").fill("Reviewer checked the demonstration file and explicit measurement.")
                page.get_by_role("button", name="Record service verification", exact=False).click()
                expect(page.get_by_role("alert")).to_contain_text("measured target met")
                expect(verified).to_have_text("00")
                page.get_by_label("Measured service value", exact=True).fill("6")
                page.get_by_role("button", name="Record service verification", exact=False).click()
                expect(verified).to_have_text("01")
                check("File upload, evidence selection, independent reviewer and measured target gate service verification")
                page.get_by_label("Resident reported issue", exact=True).fill("Water supply stopped again in this synthetic demonstration.")
                page.get_by_role("button", name="Record resident issue", exact=False).click()
                expect(verified).to_have_text("00")
                expect(page.get_by_text("Disputed · review needed", exact=True).first).to_be_visible()
                page.get_by_label("Response / resolution note").fill("A demonstration repair response was recorded; inspection must follow.")
                page.get_by_role("button", name="Record response", exact=True).click()
                expect(page.get_by_text("Response recorded", exact=True)).to_be_visible()
                expect(verified).to_have_text("00")
                evidence("inspection-followup.txt", "Fresh synthetic inspection after the reported interruption.")
                page.get_by_label("Update or review note").fill("Fresh inspection reviewed after the recorded service interruption.")
                page.get_by_role("button", name="Record service verification", exact=False).click()
                expect(verified).to_have_text("01")
                check("A new issue disputes verification; a response alone cannot restore it; fresh evidence permits a new review")
                with page.expect_download() as download:
                    page.get_by_role("button", name="Export brief", exact=False).click()
                brief_path = OUT / "tested-brief.json"
                download.value.save_as(brief_path)
                brief = json.loads(brief_path.read_text())
                assert brief["project"] == "UrbanSaarthi" and brief["works"][0]["verification"] == "verified"
                assert brief["priority_report"]["items"][0]["score"] == 65
                assert "content_base64" not in json.dumps(brief) and "officerKey" not in json.dumps(brief)
                page.reload(wait_until="networkidle")
                expect(page.get_by_role("heading", name="CI demo water improvement", exact=True)).to_be_visible()
                expect(verified).to_have_text("01")
                check("Exported brief contains scores, assumptions and evidence metadata; SQLite records persist after reload")
                for width, height in [(1440, 1000), (768, 1024), (375, 812)]:
                    page.set_viewport_size({"width": width, "height": height})
                    for label in ["Overview", "Explore Settlements", "Prioritize Needs", "Compare Scenarios", "Service Assurance"]:
                        nav(label)
                        expect(page.locator("#us-main h1")).to_be_visible()
                        page.wait_for_timeout(150)
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"Horizontal overflow: {width} / {label}"
                        check(f"Responsive navigation and no document overflow: {width}px / {label}")
                    if width in {1440, 375}:
                        nav("Overview")
                        path = OUT / f"overview-{width}.jpg"
                        page.screenshot(path=path, type="jpeg", quality=70, full_page=True)
                        screenshots.append(str(path.relative_to(ROOT)))
                offline = browser.new_context(viewport={"width": 1280, "height": 900})
                offline.route("**/api/**", lambda route: route.abort())
                sandbox = offline.new_page()
                sandbox.on("pageerror", lambda error: errors.append(str(error)))
                sandbox.goto("http://127.0.0.1:4173/#assurance", wait_until="networkidle")
                expect(sandbox.locator(".us-sandbox-banner")).to_contain_text("browser-only demonstration")
                sandbox.get_by_role("button", name="Plan a service work", exact=False).click()
                sandbox.get_by_label("Work title", exact=True).fill("Offline browser-only work")
                sandbox.get_by_role("button", name="Save planned work", exact=False).click()
                expect(sandbox.get_by_role("heading", name="Offline browser-only work", exact=True)).to_be_visible()
                sandbox.reload(wait_until="networkidle")
                expect(sandbox.get_by_role("heading", name="Offline browser-only work", exact=True)).to_be_visible()
                with urllib.request.urlopen("http://127.0.0.1:8000/urban/state") as response:
                    server = json.load(response)
                assert all(work["title"] != "Offline browser-only work" for work in server["works"])
                check("Browser sandbox persists locally and never silently writes its records to the API")
                assert not errors, errors
                browser.close()
                result.update(status="passed", checks=checks, executed_checks=len(checks), page_errors=errors, screenshots=screenshots)
    except Exception as exc:
        result.update(error=f"{type(exc).__name__}: {exc}", checks=checks, executed_checks=len(checks), page_errors=errors, screenshots=screenshots)
        raise
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        for log in logs:
            log.close()
        REPORT.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)
    # Public, synthetic UI screenshots only. No credentials, local data or tokens.
    for name in screenshots:
        data = (ROOT / name).read_bytes()
        checksum = hashlib.sha256(data).hexdigest()
        print(f"URBAN_PREVIEW_BEGIN {Path(name).stem} {checksum} {len(data)}", flush=True)
        encoded = base64.b64encode(data).decode()
        for offset in range(0, len(encoded), 8192):
            print("URBAN_PREVIEW_PART " + encoded[offset:offset + 8192], flush=True)
        print(f"URBAN_PREVIEW_END {Path(name).stem} {checksum}", flush=True)


if __name__ == "__main__":
    main()
