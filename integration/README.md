# Source merge status

The local Seva Evidence materials are present in this fresh repository. **At the preparation checkpoint on 17 October 2026, the upstream NagarSeva application had not been cloned or merged, and no new GitHub repository had been created.** See [status.json](status.json) for the current recorded boundary and [local-snapshot.json](local-snapshot.json) for the initial source-file hashes. A later successful merge creates `source-manifest.json`; a verified publish writes the local `.merge-work/published.json` receipt.

Direct terminal `git clone` failed with `Could not resolve host: github.com`. After browser authentication, the GitHub connector successfully accessed the source and the newly created public repository, [vishal88736/nagarseva-seva-first](https://github.com/vishal88736/nagarseva-seva-first). The source is pinned to `f1049b6b274be996a9e09bf11011a724905c0c76`. The connector retrieved 117 original files with matching Git blob hashes; its binary/inline-size limitations prevented retrieving the generated cost-model artifact directly. The one-time GitHub Actions workflow therefore performs a real, pinned clone and verifies all 118 files before merging. Its actual outcomes are recorded in `ci-validation.json` after execution.

The bootstrap ZIP contains only checked local project materials, with a per-file SHA-256 manifest. The workflow validates and removes that temporary payload, merges the original application, and runs software checks. A Git bundle exported through the authenticated workflow log permits local synchronization without transferring checkout credentials or changing the terminal sandbox. No browser or field-validation pass is inferred from CI.

## Finish with access available

From this directory, on a host with GitHub connectivity and `gh` signed in as `vishal88736`:

```bash
python3 scripts/merge_source.py --publish
```

To merge and commit locally without creating a GitHub repository:

```bash
python3 scripts/merge_source.py
```

The script clones the original repository into an ignored cache, records its commit, copies its tracked files without overwriting conflicting local work, combines ignore rules, and keeps NagarSeva as the main application. The evidence workbench is also copied to the Vite public directory at `/evidence/`. It runs the evidence checks and submission-package checks, makes a local merge commit, then optionally creates **a new private repository** named `vishal88736/nagarseva-seva-first` and pushes it. It never pushes to the original repository. If the new name already exists, it stops.

This is a fresh combined repository, rather than a rewrite of the upstream commit history. The upstream commit and original-file hashes remain in `source-manifest.json` after a successful merge. No application feature equivalence, original-application test pass, browser pass, field validation, adopter acceptance or real-world impact is established by copying files.

## Included work

- `research/`: evidence, source access limits, literature, datasets and validation plan.
- `prototype/`: standalone evidence workbench, source, fixtures and tests.
- `submission/`: draft answers, six-slide editable deck, budget and pitch materials. Official authenticated form limits and personal fields remain unverified/omitted.

No credentials, household records, local databases, package caches or original workspace Git metadata were copied. Generated ZIP archives remain ignored; `submission/scripts/prepare_pack.py` recreates the delivery ZIP locally.

## Validation boundary

The evidence checks exercise deterministic calculations, converter fixtures, templates, source packaging and a small authored retrieval checklist. They do not test NagarSeva's FastAPI/React application, perform an independent model evaluation, launch a real browser here, or verify services in the field. Once the original source is available, its backend and frontend checks must be run separately and recorded against that source commit. Synthetic models and cost estimates must retain their labels and limitations.
