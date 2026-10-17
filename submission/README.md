# UrbanSaarthi submission pack

Prepared 18 October 2026 for an individual participant. This pack describes the focused React/FastAPI working prototype. Personal details remain omitted at the applicant's request. No operational pilot, agency acceptance or measured resident outcome is claimed.

## Review and use

1. Run the [five-screen app](../README.md) and follow the [demo route](browser_acceptance.md).
2. Read the [application drafts and word counts](application_answers.md). Draft budgets are authoring limits, not authenticated portal limits.
3. Use the [official-template editable deck](outputs/urbansaarthi-pitch.pptx) and [PDF copy](outputs/urbansaarthi-pitch.pdf), [six-slide outline](deck_outline.md), [speaking scripts](pitch_scripts.md) and [judge questions](judge_questions.md).
4. Inspect the [editable review-trial budget](outputs/pilot-budget.xlsx), [cost assumptions](financial_model.md) and [quotation template](../pilot/templates/cost_quote.json). Scenario construction assumptions are a separate model.
5. Review [pilot preparation](../pilot/README.md), [30–60–90 day plan](pilot_and_adoption.md), [metrics](impact_metrics.md), [phase checklist](phase_checklists.md) and [strict audit](winning_edge_and_audit.md).

The official six-slide template was acquired on 18 October 2026 and used for this deck. Its unchanged acquisition receipt is in [research/acquired/official-template-access.json](../research/acquired/official-template-access.json). The [website](https://sevainnovationchallenge.in/guidelines.html) says PPTX; the template itself says PDF under 10 MB. Both formats are supplied. Confirm the accepted format, size limit and personal/declaration requirements inside the portal before submitting. No application has been submitted.

The earlier `seva-evidence-pitch.pptx` remains as historical work. It is superseded and excluded from the current delivery archive. The earlier [evidence workbench](../prototype/README.md) remains supporting research, separate from the default UrbanSaarthi UI.

## Evidence boundary

The five mapped clusters, service indices, graph, household assumptions, scenario costs and work records are demonstrations. The three attributed SRA rows are real listing facts and remain separate. Public context acquisition attempts and failures are [recorded](../research/acquired/mumbai-context-access.json). No acquired settlement boundary or current service baseline is asserted.

Actual software checks are in [application CI](../integration/ci-validation.json) and [Chromium results](../integration/urban-validation.json). These do not establish field accuracy, independent ranking agreement, authenticated reviewer independence or government readiness. A prospective office has been identified; no participating official, operator or recurring payer has agreed.

## Reproduction and delivery

`python3 submission/scripts/prepare_pack.py` regenerates answer counts, checks required files and local links, checks native artifact contents and creates `submission/outputs/seva-submission-kit.zip`. The archive includes linked primary guides and the validation/advisory receipts. It is a submission/research pack, not a complete application-source or dependency bundle. Clone the repository for the app. Exclude private household/operational data from both.
