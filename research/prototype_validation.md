# Executed prototype validation

Report generated: **2026-10-18T13:07:48.484019+00:00**. Source research access date: **2026-10-17**. This is software/development validation, not field evidence or an official service certification.

## Executed results

| Check | Actual result | Permitted conclusion |
|---|---|---|
| Deterministic engine tests | **32/32 passed**, 0 failed; no skipped/cancelled tests | Numerical routes, disconnections, missing-value intervals, restrictions, conflicts, workload limits, abstention and export cases behaved as tested |
| OSM conversion tests | **3 passed** on authored response-shaped fixtures | Node identity, representative-location labels, privacy filtering and date/source checks behaved as tested; no live data were downloaded |
| Template contracts | **10 checks passed**, 13 view/mode templates generated | Real render functions executed in a minimal document harness; this is not a real browser |
| HTML/source checks | **Passed: source syntax, generated view templates, standalone syntax/markup, embedded runtime assets and research links/hashes** | Balanced generated markup, unique IDs, source/module syntax and self-contained asset structure; not visual verification |
| Curated retrieval checklist | **25/25 status cases correct** | Results on these author-written development prompts only |
| Expected source in top 3 | **18/18** answerable prompts | No held-out or independently adjudicated retrieval accuracy established |
| Unweighted lexical comparator | **18/18** expected sources in top 3 | The small checklist does not demonstrate improvement over the simple baseline |
| Unsupported-request abstention | **7/7** development prompts | Includes current measurements, personal eligibility/relocation, prototype impact/performance and out-of-corpus requests |
| Real-browser QA | **not_attempted**; phase **not recorded**; **0 browser assertions completed**; most recent record No attempt recorded | Browser status is recorded separately from code/template checks. Only a passed browser report establishes that the listed browser interactions were exercised. |
| Field/service/adoption validation | **Not performed** | No measured service reliability, household coverage, repair-time reduction, SROI, resident benefit or government acceptance |

## What the real inputs establish

The default input has **three secondary OSM-derived transport reference points**, no acquired road graph, no area deficit observations and no service claims. Source pages and unknown observation dates are retained. Schema checks and reference display do not establish positional accuracy, current operation, accessible entrances, amenity completeness or walking access. See [access_followup.md](access_followup.md).

The separate real public-record case retains **three primary-source SRA listing records** with raw CTS strings, placeholders and unknown status/update fields. The code flags exact/contextual collisions and tentative formatting associations while merging zero records. This is a reproducible desk case, not independent transcription validation, legal matching, a delay assessment or a field service demonstration. See [public_record_case.md](public_record_case.md).

The synthetic sandbox has a deliberately invented grid, facilities, normalised deficits, missing values, conflicts and cost/coverage options. Its route/score/budget values are **calculations on test inputs**, not Maharashtra baselines, predictions or impacts. A successful route test does not validate the real pedestrian network.

## Failures found and corrected

An independent code/semantics review identified stale route displays after parameter changes, misleading OSM attribution on generic imports, unknown foot tags overriding private access, excessive synchronous scenario work, incomplete temporal abstention and missing CSV context. These were corrected with focused regressions/template contracts. Exported Markdown retains input provenance/parameters, and JSON analysis retains hypothetical maintenance inputs/results. A final packaging check found that universal-newline decoding changed embedded CSV bytes; the builder now preserves original line endings, and all embedded research files are checked against their recorded hashes. Corrections are source/engineering evidence; browser interactions still require an available browser.

The initial retrieval run returned an answerable state for “how many people ... now”; the temporal/local-metric guard was expanded and the development checklist rerun. **No machine-learning improvement is claimed**: the corpus has 14 curated source cards, and the unweighted overlap baseline performed equally on the 18 answerable prompts. Generalisation, Marathi quality and independent end-user review are untested.

## Reproduction and limits

Run `python3 prototype/scripts/verify.py` from the project root. Engine tests explicitly use `--test-isolation=none`; this workspace's default subprocess-isolated invocation reported a file wrapper rather than the individual cases, so the pipeline verifies the declared/actual test counts match. Runtime versions: `v26.12.0`; `Python 3.12.15`.

The generated [standalone entry point](../prototype/dist/standalone.html) embeds the interface, methods, data and research text and does not require a local port or external runtime assets. Optional workbench browser-check status for this run: `not_attempted`. The default verifier performs source/template/packaging checks; actual UrbanSaarthi browser results are recorded separately in `research/verification/browser_results.json`. No field verification is implied.

The static/template checks are a distinct, narrower validation layer. They do not establish pixel layout, keyboard/screen-reader behaviour, all file-import/download interactions, or production security. Field deployment additionally needs lawful current data, an approved operating owner, resident participation, independent labels, access controls, O&M funding and an actual workflow comparison.

## Source snapshot

SHA-256 values cover analysed source/input assets, not the generated HTML (which embeds this report):

| Asset | SHA-256 |
|---|---|
| `prototype/dist/index.html` | `54b92ec17206dec838a5f99a3a9fdf612b1c4ff9c4144e45ede85d105fb62e87` |
| `prototype/dist/app.mjs` | `d9f4d13acd6f977645d14b358d85b05090055034eeec66e4306edf0862281849` |
| `prototype/dist/lib/engine.mjs` | `64de9bece0a6f8f2ecf9a0b5d72a1b28bd5b6f3a84083e7b346d67de2d788e8e` |
| `prototype/dist/style.css` | `8fbc3d42a4ba3c4b4135eb76b9a1311d8a56f9415d3eeccb68fb4473b1e02626` |
| `prototype/dist/schema.md` | `a81f91353f7a3d8f498af11246db5a03dc0293a30aa4d407b9f43bf1acb11080` |
| `prototype/dist/data/reference-points.json` | `9e6590d4fde887bccb049be3fc473e8ff4a04d87b445bdd2e4376d3d1286b6d4` |
| `prototype/dist/data/example.json` | `d1c948f9149ff3298097306c7bb37f7304a5f1904ab9e6b857372d53725f3b4c` |
| `prototype/dist/data/public-schemes.json` | `82a8ab175cef333693c56f4aba758b1a9ea89518bbf8559630c5cb0e38eb39e0` |
| `prototype/scripts/prepare_osm.py` | `f53d89750a94b3e4e724700df867b2f9e6ac38d7e34cf59c9f687b3233fa42c3` |

Raw development outputs are retained locally in `prototype/test-artifacts/`; they contain no field household records.
