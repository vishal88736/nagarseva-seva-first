# Evaluation plan and honest measurement boundaries

Research/access date: **17 October 2026**. This file specifies the evaluation design. The authorised follow-up executes a bounded set of software checks and a **25-question development retrieval checklist**, recorded in [prototype_validation.md](prototype_validation.md). This is not independent field/model validation: no current service baseline, resident interview, general retrieval-accuracy estimate or public-service impact has been established.

## What can be measured with which evidence?

| Evaluation | Metric and denominator | Baseline/comparator | Inputs and current calculability | Target/acceptance approach |
|---|---|---|---|---|
| Data availability | Successfully acquired and parsed sources / sources required for the chosen task; report failed/restricted sources separately | Inventory's documented access state | Acquisition status is documented now; no raw spatial file parsed | Resolve required data gates before claiming a working map; do not maximise a count of irrelevant datasets |
| Schema/completeness | Nonmissing valid values / eligible records, separately for each field and date; unique-ID, valid-geometry, CRS and duplicate rates | Original source and independent publisher controls where available | Calculable after actual ingestion | Proposed engineering gate: every displayed record retains source/date or an explicit unknown; report all missingness, no invented coverage goal |
| Positional/data accuracy | Error distribution against independently checked coordinates/records; OSM facility recall against a permitted independently compiled list | Same list and geographic extent for every method | Requires independent ground truth; absent | Agree acceptable error for the actual decision before testing; do not call agreement with the same source “accuracy” |
| Amenity access | Shortest walk-network distance; unreachable count; snap-distance distribution; distribution across agreed public origins | Straight-line distance and independently inspected routes | Computable after dated graph/origin/amenity ingestion, not calculated here | Report discrepancies and route limitations; no universal service standard assumed |
| Actual service deficit | Confusion matrix and class-specific precision/recall/F1, plus verified coverage and unassessable cases | Existing record/process against independent, dated labels | Needs independently observed labels; unavailable | Set decision-specific error tolerance with service owner/community; review false negatives explicitly |
| Ranking robustness | Contribution reconciliation; rank correlation; top-k overlap; rank/score interval under plausible weights and missing values | Current process and a simple queue on same cases | Calculable after comparable inputs and criteria exist; external validity needs independent review | No “optimal fairness” threshold; disclose unstable cases and withhold unsupported rankings |
| Hypothetical costs/coverage | Cost, unique covered units, coverage under equal budget, constraint violations, Pareto trade-offs | No-change and simple feasible/equal-budget selection | Requires stated costs/options; real costs not obtained | Scenario outputs remain conditional estimates, not projected benefits or bankable SROI |
| Project/status verification | Supported claims / assessable claims; field agreement; unsupported/outdated claims; disagreement rate | Existing dated report, compared in same time window | Needs local documents and independent adjudication; absent | No engineering certification from a photo; keep disputes and unverified claims visible |
| Complaint follow-up | Time to first response/confirmed resolution, unresolved age, reopen/recurrence counts, evidence completeness | Existing platform/workflow over comparable periods | Needs authorised de-identified event logs and resident validation; absent | Analyse unresolved cases, changing categories and unequal follow-up; no promised reduction |
| Document retrieval/answers | Evidence recall@k, supported claim/citation precision, numeric correctness, source-version correctness and appropriate abstention | Manual source lookup and lexical retrieval without generation | Author-written development checklist executed; independent/held-out benchmark remains unavailable | Every factual answer claim must be traceable; development results do not establish general accuracy |
| Workflow usefulness | Task completion, elapsed time, incorrect conclusions and usability issues | Same task using existing tools; counterbalance order | Needs real or clearly identified proxy reviewers; none contacted | Predefine the task and compare errors as well as speed; no time-saved claim from a solo rehearsal |

Targets above are **proposed evaluation rules**, not achieved results, statutory service guarantees or official competition thresholds.

## 1. Register inputs and prevent false certainty

For each input record distinguish observation time, issue/publication time, source modification time and access time. A file downloaded today may contain 2011 observations. Record geographic unit, denominator, version and lineage. Keep a 2011 ward percentage in a context panel; never use it as a current household label.

For completeness, define the eligible denominator before inspecting results. A facility can have valid coordinates but unknown opening hours. A failed dataset acquisition is not 100% complete because an empty table has no nulls. Record unavailable sources outside record-level completeness.

Do not average Census counts, WorldPop and GHSL into a “true population.” They have different purposes and can share underlying inputs. Validate modelled exposure against an independent local enumeration if one becomes available. [WorldPop methods](https://www.worldpop.org/methods/populations/), [GHSL product](https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php)

## 2. Evaluate spatial access, not assumed service availability

Select origins and facility types before looking at route results. Prefer consenting/public entrances and known walking connections; retain each origin's selection method. Set and record a maximum snap distance, and inspect routes around rail lines, highways, waterways, private/gated land and grade separation. Use an appropriate projected metric CRS or a documented geodesic measurement method consistently. QGIS explicitly exposes direction, topology and non-routable-origin settings; defaults can produce misleading paths if applied without checking. [QGIS documentation](https://docs.qgis.org/3.44/en/docs/user_manual/processing_algs/qgis/networkanalysis.html)

For each origin report distance to the nearest **mapped candidate** amenity, network-connectivity result, snap distance, source date and any verified access restriction. An absent path is **unreachable in the current graph**, not a zero-distance journey. Absence of a mapped clinic/toilet is **unknown coverage**, not proof that none exists.

Do not calculate “share of households served” without household/origin weights and an agreed service definition. Do not calculate public-transport journey time from stop points alone. School admission, clinic affordability/capacity, toilet hours/fees, wheelchair accessibility and water quality need separate validation.

## 3. Design independent service labels

If authorised, agree a small sampling frame with the community and operator. Include different lanes/assets and relevant user groups; document refusals and unreachable cases. A convenience sample can support a limited demonstration, not ward prevalence.

Write an observation protocol per service. Examples: water availability during specified time windows; toilet openness and accessibility; scheduled waste collection observed repeatedly. Potability requires qualified sampling/testing. A drain photograph does not establish underground capacity or a cause of flooding.

Use an assessor independent of the score or status being evaluated. Record observer, date/window, evidence and uncertainty; recheck disagreements rather than silently resolving them in favour of a government or resident label. Report unassessable cases. For small samples show counts alongside rates and uncertainty; observations from one asset/household over time are not independent additional households.

The historical studies motivate these dimensions, not current labels. [Subbaraman et al. (2013)](https://link.springer.com/article/10.1186/1471-2458-13-173)

## 4. Audit scoring and scenario comparisons

For complete comparable records, verify `score = sum(weight × normalised criterion)` and that contributions reconcile. Publish criteria, direction, anchors, weights, exclusions and their rationale. Preserve legitimate zero values. Treat unknown criteria through explicit bounds or withheld results, not zero fill or hidden weight changes.

Pre-register plausible weight ranges with stakeholders. For a software stress test, one may perturb weights by **±20% and renormalise**; this is a proposed test input, not a measured uncertainty interval or validated preference distribution. Compare Spearman/Kendall rank measures and top-k set overlap, defining k in advance. For unknown criteria show score/rank ranges and ask whether priorities remain robust. Report ties honestly.

Ranking stability is not correctness. Compare independently observed need and the actual constrained task with the existing process. A current-queue disagreement alone is not improvement; a score's own weighted criteria cannot serve as its ground-truth label.

For hypothetical budget coverage, disclose every assumed cost and who/what is counted as covered. Prevent double-counting overlapping interventions. Compare equal budgets, feasibility constraints and sensitivity to costs/coverage. Check a small optimisation example by enumerating feasible choices. Do not translate algorithmic coverage into people rehoused, income gained, disease avoided or SROI without independent causal evidence.

## 5. Evaluate status and grievances without rewriting the workflow

Create a claim taxonomy before evaluating: document-issued, contractor-reported, independently observed, resident-confirmed, disputed, expired and unknown. Match asset, service and time window. Retain original source statements and adjudication history. Repeat observations assess persistence; a one-time photo cannot verify continuous water or engineering completion.

For complaint duration, define the start/end event and include unresolved cases as unresolved/right-censored rather than dropping them. Report selection bias, inconsistent categories and changes to intake. Link existing complaint IDs with permission. **Confirmation/reopening is an existing Swachhata capability**, so test incremental evidence quality against it. [Official description](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2162194&lang=2&reg=48)

## 6. Evaluate document-grounded assistance

Propose a benchmark of **25 independently reviewed questions** spanning scheme scope, dates/numbers, missing information, jurisdiction conflicts and outdated versions. Twenty-five is a design choice, not a completed benchmark or claim of statistical power. Record expected evidence spans before running retrieval/generation, retain a small held-out portion and do not tune on the final comparison.

Assess retrieval separately from answer generation. A citation counts only if the exact cited passage supports the associated claim and applies to the requested time/jurisdiction. Count unsupported numerical/legal assertions as critical errors. Test correct abstention on unanswerable questions, old-versus-new policy distinctions and Marathi extraction if used. Report an extractive/search baseline so an LLM's incremental contribution is visible.

## Inclusion and longer-term outcomes

Invite women, older people, disabled residents, renters and migrants into any authorised field review; document participation limitations without publicly exposing individual vulnerabilities. Assess routes/hours, fees, physical accessibility and assisted participation. Do not assume all members of a group share one preference or derive protected attributes from imagery.

Potential alignment: **SDG 6** through water/sanitation reliability measures; **SDG 11** through inclusive access and settlement improvement; **SDG 1** through attention to housing/service expenditure and security. These are directions for later measurement, not achieved SDG impact. A short prototype can establish data/analysis quality and limited workflow usability; service improvement requires an authorised intervention, repeated baseline/follow-up and appropriate attribution design.

## Reporting template

For every result state: task; input versions and dates; geography/sample/denominator; method and settings; comparator; actual value with uncertainty; failed/unassessable cases; reviewer; and permitted conclusion. Label screenshots with illustrative data as **demonstration only**, and never mix them into results from real records. Publish unsuccessful tests and acquisition failures alongside successful checks.
