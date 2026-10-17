# Browser acceptance and recorded blocker

Status: **not passed in this workspace**, checked again 17 October 2026. CUA inventory returned no browser/app surfaces and an in-app browser could not be created. After resolving local Playwright/executable paths, installed Chromium again terminated at `sandbox_host_linux.cc` with `shutdown: Operation not permitted` before opening a page. This is a launch failure, not a failed UI assertion. No responsive screenshots or accessibility pass are claimed.

Do not repeat browser-launch flags or weaken machine protections to turn this into a pass. Code syntax, numerical tests, render-template contracts and exact standalone-data checks remain a narrower validation layer. [Executed validation](../research/prototype_validation.md)

## Reproduce in an environment with an available browser

Open [the standalone file](../prototype/dist/standalone.html) directly. From the project root run `node prototype/scripts/browser_check.mjs`. The runner detects installed Playwright or the existing bundled runtime and common Chromium executable paths; it installs nothing. `NODE_PATH` and `BROWSER_PATH` can override discovery. The report at `prototype/test-artifacts/browser.json` records the entry hash and distinguishes dependency/launch blocks from application-startup/check failures. An execution outside this restricted agent workspace is still required for actual browser acceptance.

| Acceptance task | Expected result | Recorded status here |
|---|---|---|
| Open standalone without network | Overview loads and research context appears | MISSING: browser unavailable |
| Open every navigation item at desktop and 390px width | No hidden controls, horizontal overflow or clipped essential text | MISSING |
| Inspect real references and public-record case | Sources/unknowns visible; no current-service ranking or road distance invented | Template/data checks only |
| Select synthetic sandbox and calculate access | Candidate/disconnected/restricted facilities remain distinct | Engine/template checks only |
| Change route inputs | Old distance/path clears until recalculation | Template contract only |
| Import valid aggregate JSON, then an invalid file | Valid data retain provenance; rejected data preserve previous dataset | Source/engine checks; real file input MISSING |
| Export Markdown, JSON, CSV and research files | Browser downloads match intended contents and preserve provenance | Contents/embedded hashes checked; download interaction MISSING |
| Search supported and unsupported questions | Cited context or explicit abstention as applicable | Development search checks only |
| Keyboard navigation, dialog escape/close and focus visibility | Controls accessible without a mouse | MISSING |
| Screen-reader labels and language review | Meaningful labels; no unsupported Marathi quality claim | MISSING |

The applicant should retain the completed browser report/screenshots and any defects before claiming an end-to-end demonstration. A hosted URL or production launch has not been created.
