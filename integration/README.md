# Completed source merge

The combined project is published at [vishal88736/nagarseva-seva-first](https://github.com/vishal88736/nagarseva-seva-first). It contains all **118 tracked files** from the original NagarSeva snapshot, the local research, the evidence workbench and the submission materials. The original repository was read only and its main branch was rechecked at the pinned commit `f1049b6b274be996a9e09bf11011a724905c0c76` after publication. The user-created target repository is public.

[The passing workflow](https://github.com/vishal88736/nagarseva-seva-first/actions/runs/39061086658) completed **30 backend tests**, the frontend production build, 32 evidence-engine checks, 3 converter checks, 10 template checks and the 25 authored document-retrieval queries. These are development checks, not independent accuracy or field-impact measurements. The application checks used Python 3.12 and Node 24.

- [Current merge state](status.json) and [executed application-check results](ci-validation.json).
- [Original and current file hashes](source-manifest.json), including intentional integration changes.
- [Compatibility repair, CI fixes and validation limits](merge_fixes.md).
- [Initial local-material snapshot](local-snapshot.json), retained as historical provenance.

## Using the combined project

Follow [NagarSeva's run instructions](../nagarseva/README.md) for the FastAPI backend and React/Vite frontend. The evidence workbench is available at the frontend's `/evidence/` route and independently as [a standalone HTML file](../prototype/dist/standalone.html). The [root README](../README.md) links the research and editable submission pack.

The source merge is complete. The original `scripts/merge_source.py --publish` helper describes initial acquisition and creation of a new private repository; do not use it to publish this already-created target. This repository's configured `origin` is the new combined repository. Normal future Git changes should be made and pushed there.

## Acquisition and provenance

Direct terminal network access failed during preparation. After authentication, the GitHub connector accessed both the source and the new target. Its file-content endpoint retrieved 117 source files but could not deliver the large cost-model binary. GitHub Actions therefore performed a real clone, checked out the pinned commit and verified the full set of **118 original Git blob hashes**, including that binary, before integration.

The bootstrap ZIP contained checked local materials and a per-file SHA-256 manifest. The workflow verified and removed the payload, merged the original application and ran the software checks. A checksum-verified Git bundle from the workflow log synchronized the local checkout without including checkout credentials or Git configuration. This is a fresh combined repository; the original commit history was not imported.

## Included work and remaining limits

- `nagarseva/`: original application, model artifacts and tests, with the documented dependency repair.
- `research/`: evidence, literature, datasets, access limitations and validation plan.
- `prototype/`: evidence workbench, fixtures, calculations and document-retrieval checks.
- `submission/`: draft answers, editable six-slide deck, budget and pitch materials. Authenticated form limits remain unverified; applicant personal fields remain omitted at the user's request.

The initial frontend installation reported 10 dependency advisories, including 7 high-severity advisories; they have not been resolved by the compatibility repair. See [the merge findings](merge_fixes.md). No production deployment, real-browser acceptance, independent model evaluation, field-service verification or government adoption has been established. Synthetic models, hypothetical budgets and historical statistics retain their labels and limitations.

No credentials, household records, local databases, package caches or original workspace Git metadata were copied. Generated submission ZIP archives remain ignored; `python3 submission/scripts/prepare_pack.py` recreates the archive and its file manifest locally.
