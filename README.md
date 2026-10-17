# NagarSeva + Seva Evidence

NagarSeva's urban-housing and service-assurance application, combined with a research-led evidence workbench and Seva First submission materials.

- [NagarSeva application and run instructions](nagarseva/README.md)
- [Evidence workbench and demonstration](prototype/README.md)
- [Open the self-contained evidence workbench](prototype/dist/standalone.html)
- [Research overview](research/README.md) and [executive findings](research/research_summary.md)
- [Draft application, six-slide deck, budget and pitch](submission/README.md)
- [Source lineage, merge procedure and limits](integration/README.md)
- [Executed evidence checks](research/prototype_validation.md)

## Run the applications

Follow the NagarSeva guide for the FastAPI backend and React/Vite frontend. The evidence workbench is additionally served at `/evidence/` by Vite and included in its production build. It can also be opened independently from `prototype/dist/standalone.html`, without a server or credentials.

Run `python3 prototype/scripts/verify.py` and then `python3 submission/scripts/prepare_pack.py` to verify and rebuild the evidence/submission materials. Refresh the Vite copy with `python3 scripts/sync_evidence.py` after changing the standalone artifact.

## Evidence boundaries

Synthetic planning data, trained models, hypothetical budgets and author-written test fixtures do not establish field accuracy, cost savings or government adoption. Preserve NagarSeva's synthetic-data labels and model limitations. The evidence workbench keeps public-record audits, historical statistics, unknown service baselines and a clearly labelled synthetic sandbox separate. It does not make eligibility or relocation decisions.

Browser checks in the preparation environment were blocked before assertions; no new browser or original-application test pass is claimed by this merge. Original-application tests must be run separately in a compatible environment. Applicant personal details remain omitted, and authenticated application limits remain unverified.

The original repository is unchanged. Its commit and imported-file hashes are recorded in `integration/source-manifest.json`. This fresh repository does not import its Git history or imply that either prototype is a production public service.

## Published source and checks

The source merge and per-file hashes were verified in [this workflow](https://github.com/vishal88736/nagarseva-seva-first/actions/runs/39060182457). See [the recorded validation outcomes](integration/ci-validation.json) for backend, frontend and evidence-check results. Browser and field validation remain separate.
