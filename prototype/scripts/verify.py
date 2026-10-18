"""Run bounded, repeatable checks and package the self-contained prototype.

Browser/field validation is reported separately, never inferred from code tests.
"""
import argparse
import csv
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PROTO = ROOT / "prototype"
ARTIFACTS = PROTO / "test-artifacts"
ARTIFACTS.mkdir(exist_ok=True)
CORE = ["README.md", "official_sources.md", "literature_review.md", "existing_solutions.md", "research_gap.md", "dataset_inventory.csv", "problem_evidence_matrix.csv", "technical_feasibility.md", "evaluation_plan.md", "references.bib", "research_summary.md"]


def run(args, log=None):
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    output = result.stdout + result.stderr
    if log:
        (ARTIFACTS / log).write_text(output)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}\n{output[-10000:]}")
    return output


class MarkupCheck(HTMLParser):
    VOID = set("area base br col embed hr img input link meta param source track wbr".split())

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.ids, self.external_runtime = [], [], set(), []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if data.get("id"):
            if data["id"] in self.ids:
                self.errors.append("Duplicate id: " + data["id"])
            self.ids.add(data["id"])
        if tag == "script" and data.get("src"):
            self.external_runtime.append(data["src"])
        if tag == "link" and data.get("rel") == "stylesheet":
            self.external_runtime.append(data.get("href"))
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"Mismatched closing {tag}; stack tail {self.stack[-3:]}")
        elif self.stack:
            self.stack.pop()


def markup_check(text, name, standalone=False):
    parser = MarkupCheck()
    parser.feed(text)
    assert not parser.errors and not parser.stack, (name, parser.errors, parser.stack)
    if standalone:
        assert not parser.external_runtime, parser.external_runtime


def research_check():
    directory = ROOT / "research"
    assert all((directory / p).is_file() for p in CORE)
    counts = {}
    for filename, id_col in [("dataset_inventory.csv", "dataset_id"), ("problem_evidence_matrix.csv", "problem_id")]:
        inventory_path = directory / filename
        if filename == "dataset_inventory.csv" and (directory / "dataset_inventory_legacy.csv").exists():
            inventory_path = directory / "dataset_inventory_legacy.csv"
        with inventory_path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        assert len({r[id_col] for r in rows}) == len(rows)
        assert all(None not in r and all(v is not None and v != "" for v in r.values()) for r in rows)
        counts[filename] = len(rows)
        if filename.startswith("dataset"):
            census = next(r for r in rows if r[id_col] == "D03")
            assert "HL-04" in census["dataset_name"] and census["readiness"] == "METADATA_ONLY"
            assert next(r for r in rows if r[id_col] == "D32")["readiness"] == "SECONDARY_REFERENCE_POINTS_TRANSCRIBED"
    for path in [*directory.glob("*.md"), ROOT / "README.md", PROTO / "README.md"]:
        text = path.read_text()
        for url in re.findall(r"\]\(([^)]+)\)", text):
            if not url.startswith(("http://", "https://", "#")):
                assert (path.parent / url.split("#")[0]).is_file(), (path, url)
        assert "TODO" not in text
    bib = (directory / "references.bib").read_text()
    assert len(re.findall(r"(?m)^@article\{", bib)) == 14
    assert len(re.findall(r"(?m)^@techreport\{", bib)) == 1
    assert bib.count("{") == bib.count("}")
    assert len(re.findall(r"(?m)^## L\d\d", (directory / "literature_review.md").read_text())) == 14
    return counts


def validation_text(unit, converter, template, evaluation, browser, source_hashes, static_result):
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    browser_status = browser.get("status", "not_attempted")
    browser_phase = browser.get("phase", "not recorded")
    browser_checks = len(browser.get("checks", []))
    recent = browser.get("checked_at", "No attempt recorded")
    browser_note = "The most recent recorded browser launch was blocked before page checks by sandbox socket permissions. Native browser inventory was empty. Chromium first failed in crashpad setsockopt; a documented crashpad-test flag then reached another socket shutdown permission failure. No screenshot, real-DOM, responsive-layout or accessibility pass is claimed." if browser_status == "blocked" else "Browser status is recorded separately from code/template checks. Only a passed browser report establishes that the listed browser interactions were exercised."
    recall = evaluation["retrieval_recall_at_3"]
    baseline = evaluation["unweighted_overlap_recall_at_3"]
    abstain = evaluation["unsupported_abstentions"]
    return f"""# Executed prototype validation

Report generated: **{now}**. Source research access date: **2026-10-17**. This is software/development validation, not field evidence or an official service certification.

## Executed results

| Check | Actual result | Permitted conclusion |
|---|---|---|
| Deterministic engine tests | **{unit['passed']}/{unit['tests']} passed**, {unit['failed']} failed; no skipped/cancelled tests | Numerical routes, disconnections, missing-value intervals, restrictions, conflicts, workload limits, abstention and export cases behaved as tested |
| OSM conversion tests | **{converter} passed** on authored response-shaped fixtures | Node identity, representative-location labels, privacy filtering and date/source checks behaved as tested; no live data were downloaded |
| Template contracts | **{len(template['checks'])} checks passed**, {template['renderedViews']} view/mode templates generated | Real render functions executed in a minimal document harness; this is not a real browser |
| HTML/source checks | **{static_result}** | Balanced generated markup, unique IDs, source/module syntax and self-contained asset structure; not visual verification |
| Curated retrieval checklist | **{evaluation['status_correct']}/{evaluation['queries']} status cases correct** | Results on these author-written development prompts only |
| Expected source in top 3 | **{recall['numerator']}/{recall['denominator']}** answerable prompts | No held-out or independently adjudicated retrieval accuracy established |
| Unweighted lexical comparator | **{baseline['numerator']}/{baseline['denominator']}** expected sources in top 3 | The small checklist does not demonstrate improvement over the simple baseline |
| Unsupported-request abstention | **{abstain['numerator']}/{abstain['denominator']}** development prompts | Includes current measurements, personal eligibility/relocation, prototype impact/performance and out-of-corpus requests |
| Real-browser QA | **{browser_status}**; phase **{browser_phase}**; **{browser_checks} browser assertions completed**; most recent record {recent} | {browser_note} |
| Field/service/adoption validation | **Not performed** | No measured service reliability, household coverage, repair-time reduction, SROI, resident benefit or government acceptance |

## What the real inputs establish

The default input has **three secondary OSM-derived transport reference points**, no acquired road graph, no area deficit observations and no service claims. Source pages and unknown observation dates are retained. Schema checks and reference display do not establish positional accuracy, current operation, accessible entrances, amenity completeness or walking access. See [access_followup.md](access_followup.md).

The separate real public-record case retains **three primary-source SRA listing records** with raw CTS strings, placeholders and unknown status/update fields. The code flags exact/contextual collisions and tentative formatting associations while merging zero records. This is a reproducible desk case, not independent transcription validation, legal matching, a delay assessment or a field service demonstration. See [public_record_case.md](public_record_case.md).

The synthetic sandbox has a deliberately invented grid, facilities, normalised deficits, missing values, conflicts and cost/coverage options. Its route/score/budget values are **calculations on test inputs**, not Maharashtra baselines, predictions or impacts. A successful route test does not validate the real pedestrian network.

## Failures found and corrected

An independent code/semantics review identified stale route displays after parameter changes, misleading OSM attribution on generic imports, unknown foot tags overriding private access, excessive synchronous scenario work, incomplete temporal abstention and missing CSV context. These were corrected with focused regressions/template contracts. Exported Markdown retains input provenance/parameters, and JSON analysis retains hypothetical maintenance inputs/results. A final packaging check found that universal-newline decoding changed embedded CSV bytes; the builder now preserves original line endings, and all embedded research files are checked against their recorded hashes. Corrections are source/engineering evidence; browser interactions still require an available browser.

The initial retrieval run returned an answerable state for “how many people ... now”; the temporal/local-metric guard was expanded and the development checklist rerun. **No machine-learning improvement is claimed**: the corpus has 14 curated source cards, and the unweighted overlap baseline performed equally on the 18 answerable prompts. Generalisation, Marathi quality and independent end-user review are untested.

## Reproduction and limits

Run `python3 prototype/scripts/verify.py` from the project root. Engine tests explicitly use `--test-isolation=none`; this workspace's default subprocess-isolated invocation reported a file wrapper rather than the individual cases, so the pipeline verifies the declared/actual test counts match. Runtime versions: `{run(['node', '--version']).strip()}`; `{run([sys.executable, '--version']).strip()}`.

The generated [standalone entry point](../prototype/dist/standalone.html) embeds the interface, methods, data and research text and does not require a local port or external runtime assets. Optional workbench browser-check status for this run: `{browser.get('status', 'not_attempted')}`. The default verifier performs source/template/packaging checks; actual UrbanSaarthi browser results are recorded separately in `research/verification/browser_results.json`. No field verification is implied.

The static/template checks are a distinct, narrower validation layer. They do not establish pixel layout, keyboard/screen-reader behaviour, all file-import/download interactions, or production security. Field deployment additionally needs lawful current data, an approved operating owner, resident participation, independent labels, access controls, O&M funding and an actual workflow comparison.

## Source snapshot

SHA-256 values cover analysed source/input assets, not the generated HTML (which embeds this report):

| Asset | SHA-256 |
|---|---|
""" + "\n".join(f"| `{name}` | `{digest}` |" for name, digest in source_hashes.items()) + "\n\nRaw development outputs are retained locally in `prototype/test-artifacts/`; they contain no field household records.\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", action="store_true", help="Attempt the optional real-browser checks; requires Playwright/browser availability")
    args = parser.parse_args()
    run([sys.executable, "prototype/scripts/sync_research.py"])
    for file in ["prototype/dist/app.mjs", "prototype/dist/lib/engine.mjs", "prototype/scripts/evaluate.mjs", "prototype/scripts/template_check.mjs", "prototype/scripts/browser_check.mjs"]:
        run(["node", "--check", file])
    tap = run(["node", "--test", "--test-isolation=none", "--test-reporter=tap", "prototype/tests/engine.test.mjs"], "engine-tap.txt")
    number = lambda label: int(re.search(rf"(?m)^# {label} (\d+)$", tap).group(1))
    unit = dict(tests=number("tests"), passed=number("pass"), failed=number("fail"))
    declared = len(re.findall(r"(?m)^test\(", (PROTO / "tests/engine.test.mjs").read_text()))
    assert unit["tests"] == unit["passed"] == declared and unit["failed"] == 0
    assert number("skipped") == number("cancelled") == 0
    converted = run([sys.executable, "-m", "unittest", "discover", "-s", "prototype/tests", "-p", "test_*.py", "-v"], "converter-tests.txt")
    converter_count = int(re.search(r"Ran (\d+) tests?", converted).group(1))
    run(["node", "prototype/scripts/evaluate.mjs"])
    run(["node", "prototype/scripts/template_check.mjs"])
    for item in json.loads((ARTIFACTS / "rendered-templates.json").read_text()):
        markup_check(item["html"], item["name"])
    evaluation = json.loads((ARTIFACTS / "evaluation.json").read_text())
    template = json.loads((ARTIFACTS / "template-checks.json").read_text())
    if args.browser:
        # A blocked attempt remains explicit; it never turns a failed test into PASS.
        result = subprocess.run(["node", "prototype/scripts/browser_check.mjs"], cwd=ROOT, text=True, capture_output=True)
        (ARTIFACTS / "browser-attempt.txt").write_text(result.stdout + result.stderr)
    browser_path = ARTIFACTS / "browser.json"
    browser = json.loads(browser_path.read_text()) if browser_path.exists() else {"status": "not_attempted"}
    snapshots = ["dist/index.html", "dist/app.mjs", "dist/lib/engine.mjs", "dist/style.css", "dist/schema.md", "dist/data/reference-points.json", "dist/data/example.json", "dist/data/public-schemes.json", "scripts/prepare_osm.py"]
    source_hashes = {"prototype/"+name: hashlib.sha256((PROTO / name).read_bytes()).hexdigest() for name in snapshots}
    report_path = ROOT / "research/prototype_validation.md"
    report_path.write_text(validation_text(unit, converter_count, template, evaluation, browser, source_hashes, "Passed source/template checks; final standalone packaging checked below"))
    run([sys.executable, "prototype/scripts/sync_research.py"])
    run([sys.executable, "prototype/scripts/build_standalone.py"])
    standalone = (PROTO / "dist/standalone.html").read_text()
    markup_check(standalone, "standalone.html", standalone=True)
    match = re.search(r'<script type="module">([\s\S]+)</script>', standalone)
    assert match
    (ARTIFACTS / "standalone-script.mjs").write_text(match.group(1))
    run(["node", "--check", "prototype/test-artifacts/standalone-script.mjs"])
    counts = research_check()
    generated = json.loads((PROTO / "dist/data/research.json").read_text())
    assert generated["counts"]["dataset_candidates"] == counts["dataset_inventory.csv"]
    for file in generated["files"]:
        assert hashlib.sha256((PROTO / "dist/research" / file["name"]).read_bytes()).hexdigest() == file["sha256"]
    report_path.write_text(validation_text(unit, converter_count, template, evaluation, browser, source_hashes, "Passed: source syntax, generated view templates, standalone syntax/markup, embedded runtime assets and research links/hashes"))
    # Re-embed the completed report. No source/method/input changed after checks.
    run([sys.executable, "prototype/scripts/sync_research.py"])
    run([sys.executable, "prototype/scripts/build_standalone.py"])
    # Validate the completed artifact itself, including exact original CSV bytes.
    final_html = (PROTO / "dist/standalone.html").read_text()
    markup_check(final_html, "final standalone.html", standalone=True)
    decoder = json.JSONDecoder()
    embedded_files, _ = decoder.raw_decode(final_html.split("window.__SEVA_FILES__=", 1)[1])
    embedded_data, _ = decoder.raw_decode(final_html.split("window.__SEVA_EMBEDDED__=", 1)[1])
    for path in (ROOT / "research").iterdir():
        if path.is_file():
            assert embedded_files[path.name].encode("utf-8") == path.read_bytes(), path.name
    for path in (PROTO / "dist/data").glob("*.json"):
        assert embedded_data["./data/"+path.name].encode("utf-8") == path.read_bytes(), path.name
    final_manifest = json.loads(embedded_data["./data/research.json"])
    for file in final_manifest["files"]:
        assert hashlib.sha256(embedded_files[file["name"]].encode("utf-8")).hexdigest() == file["sha256"], file["name"]
    summary = dict(engine=unit, converter_tests=converter_count, template_checks=len(template["checks"]), development_queries=evaluation["queries"], development_status_correct=evaluation["status_correct"], browser_status=browser.get("status"), research_counts=counts, standalone_bytes=(PROTO / "dist/standalone.html").stat().st_size, field_validation=False)
    (ARTIFACTS / "verification-summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary, indent=2))
    if args.browser and browser.get("status") != "passed":
        print("Requested browser checks did not pass; inspect the recorded browser result.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError, ValueError) as exc:
        print(f"Verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
