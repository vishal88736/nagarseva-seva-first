# Independent baseline and service-observation protocol

Version 1, prepared 18 October 2026. This is a proposed protocol, not a report of collected labels. All achieved sample counts and outcome metrics remain unavailable until observations exist.

## Design before seeing scores

Agree one cluster and the competent office's review task. Register all candidate areas/assets and selection exclusions. Aim for up to 20 public water assets and three dated review rounds, subject to permission and safe access. Document inaccessible assets and failed visits rather than replacing them with convenient observations. This small purposive sample cannot estimate ward-wide prevalence.

Before opening UrbanSaarthi, two independent reviewers receive the same approved source packet, observation window and decision rubric. Each records inspection urgency, reasons, missing inputs and a rank or tie. Reviewers must not see the engine weights or score. Preserve both original assessments and any later adjudication, including disagreements. Different self-entered names in the prototype do not establish reviewer independence.

Use [independent_assessment.json](templates/independent_assessment.json). Empty rank and evidence fields mean **not assessed**, not lowest priority. Keep a dated protocol hash before scoring. These assessments are an independent comparator for the agreed task, not universally correct redevelopment priorities.

## Observation method

Use [service_observation.json](templates/service_observation.json). A site visit can record whether a point functions **at that visit**. It cannot establish hours of supply per day, potability, affordability or household coverage. Supply-hour measurements require an agreed full observation window using a permitted instrument or timestamped operator log, with gaps disclosed. Record missing measurements as null. A resident's report remains a report until independently checked.

Proposed rounds: initial baseline, follow-up after the intervention/response window, and repeat check on an agreed date. Record dry/wet weather and planned interruptions when relevant. No unauthorised opening of infrastructure or water-quality claim from appearance. Field participants must follow the host's safe-access procedure.

Obtain voluntary accessible feedback separately from legal eligibility. Include women, older people, disabled residents, renters and migrants through an assisted route. Explain that participation does not affect housing/services. Do not put participant identities, faces, household coordinates or consent forms in the public demo. Retain only approved aggregates; the host must define retention and deletion.

## Measurement and comparison

| Measure | Calculation | Availability now |
|---|---|---|
| Source completeness | Eligible records with all required provenance / eligible records | Only after a real extract; denominator and exclusions required |
| Service-label agreement | Matches / independently checked paired observations; report confusion matrix | No labels collected |
| Ranking agreement | Tie-aware Spearman on jointly assessed/rankable candidates, with n | No independent ranking collected |
| Ranking stability | Rank changes under preregistered weight changes | Available on synthetic fixtures only |
| Review effort | Paired minutes and critical omissions, current process versus prototype | No users observed |
| Repeat service failure | Verified failures / assets actually revisited in the same window | No field measurements |

Counterbalance task order between reviewers to reduce learning effects. Do not show the answer from one method before the other assessment. Report actual n, ties, exclusions, missing pairs and descriptive differences. Predefine a practically useful improvement with the office; no percentage target is invented here. A small convenience sample is not evidence of causal population benefit.

## Continuation and stop rules

Do not enter operational use without an accountable owner, approved inputs and security controls. Stop a comparison that exposes personal data, disadvantages participants, or changes an official decision without authority. Stop expansion if the current process is equally adequate, independent assessment cannot be obtained, or maintenance has no owner/payer. Preserve negative findings.
