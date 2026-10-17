# NagarSeva + Seva Evidence

**Preparation status: local research, evidence prototype and submission materials are copied. The NagarSeva GitHub source has not yet been cloned or merged.**

The clone attempt on 17 October 2026 failed because GitHub DNS was unavailable in this session. A later check detected the configured GitHub CLI account `vishal88736`, but authentication could not be validated because `gh api user` could not reach GitHub. This directory is a separate fresh local repository; the original GitHub repository and local work remain untouched.

## Included Seva Evidence work

A research-led prototype for traceable urban-service evidence and inspection review, prepared for the Seva First Innovation Challenge, Maharashtra zone.

**Open [the standalone prototype](prototype/dist/standalone.html) in a browser.** It needs no server, credentials, package installation or network access for its embedded analysis.

- [Prototype guide and demonstration](prototype/README.md)
- [Research executive summary](research/research_summary.md)
- [Research overview and all deliverables](research/README.md)
- [Executed validation and remaining limits](research/prototype_validation.md)
- [Application, editable pitch deck, pilot budget and submission checklist](submission/README.md)

The default dataset contains three secondary OSM-derived reference points, with no acquired road network or current service baseline. A separate, visibly labelled synthetic sandbox exercises routes, uncertainty, evidence conflicts and hypothetical maintenance comparisons. Historical Census 2011 measures remain historical.

A separate **real public-record demonstration** retains three primary-source SRA listing rows, flags CTS matching ambiguity and preserves unknown project status/update dates. Open it from Overview. It is a desk record audit, not a current service-access or redevelopment-performance assessment.

This prototype supports review. It does not decide household eligibility, beneficiary allocation or relocation, submit complaints, certify services or demonstrate field impact. Government adoption and local workflow usefulness remain unvalidated.

For an optional modular preview:

```bash
python3 prototype/serve.py
```

For repeatable engineering/research checks and a fresh standalone build:

```bash
python3 prototype/scripts/verify.py
```

Browser/field verification boundaries are recorded explicitly. No unrelated existing project files were modified.

## Complete the source merge

See [the merge status and command](integration/README.md). `python3 scripts/merge_source.py --publish` clones the original source, preserves its tracked application files, validates the evidence materials, commits the combined project and creates a **private** new GitHub repository. It stops if authentication, access, conflicts or checks fail.
