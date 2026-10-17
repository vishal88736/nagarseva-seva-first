# Draft application answers

Prepared 18 October 2026. These sections map the public FAQ's requested content, not a verified authenticated form. **Draft budgets below are authoring constraints, not official word limits.** Counts include answer text only and use whitespace-separated words. Personal fields are deliberately omitted. No invention of identity, qualifications, IP, users or revenue is permitted.

Verify the actual word/character and file limits in the portal before transferring answers. [Requirements and source/access record](competition_requirements.md).

## 1. Project title

**7 words / 15-word draft budget.**

UrbanSaarthi: Explainable Settlement Planning and Basic-Service Assurance

## 2. Sector and sub-theme

**9 words / 25-word draft budget.**

Urban Development. Affordable housing, slum redevelopment and basic-service assurance.

## 3. One-line value proposition

**26 words / 40-word draft budget.**

Help a ward reviewer explain settlement priorities, compare explicitly hypothetical interventions and check documented service delivery, with sources, assumptions and missing evidence visible at every step.

## 4. Problem statement

**99 words / 150-word draft budget.**

A completed housing or infrastructure work does not by itself establish reliable and usable neighbourhood services. Mumbai research documents water-reliability and post-relocation governance concerns. Our proposed local task is to help an M-East ward reviewer choose the next water-service inspection and assess evidence for closing the related work. Current local failure rates and officer workflow gaps remain unmeasured. Three acquired SRA listing records provide locality leads but no acquired geometry or current service observations. We will test whether a source-linked review brief improves evidence quality or effort against the existing process, rather than assume authorities lack GIS or monitoring.

Supporting sources; access dates recorded in the research and pilot notes: [source 1](https://link.springer.com/article/10.1186/1471-2458-13-173), [source 2](https://knowledge.uchicago.edu/records/c0z96-tzt75), [source 3](https://dms.sra.gov.in/SRAPUBLIC/).

## 5. People affected and proposed geography

**77 words / 100-word draft budget.**

Prospective users are the BMC M-East ward reviewer, Assistant Engineer for Water Works, actual asset operator and consenting community representatives. Mumbai M-East is the desk-demonstration context. One operational cluster remains to be agreed. The conditional trial proposes up to 20 public water assets and three review rounds, not 20 beneficiaries. No current household denominator or verified settlement-level service baseline is available. The five mapped prototype clusters are synthetic and must not be presented as actual settlements surveyed.

Supporting sources; access dates recorded in the research and pilot notes: [source 1](https://dms.sra.gov.in/SRAPUBLIC/), [source 2](https://www.mcgm.gov.in/irj/go/km/docs/documents/Environment/Climate/Mumbai%20Climate%20Action%20Plan.pdf).

## 6. Proposed solution

**97 words / 150-word draft budget.**

UrbanSaarthi has five screens: Overview, Explore Settlements, Prioritize Needs, Compare Scenarios and Service Assurance. An interactive map exposes indicators and provenance. Configurable weighted scores show contributions, missing-input intervals and ranking sensitivity. Two in-place intervention scenarios compare hypothetical costs, access and disruption. Relocation appears only as an explicitly enabled thought experiment. A drafted service work progresses through physical completion and a separate evidence-and-measurement review. New complaints dispute verification; a response alone cannot restore it. Exports retain assumptions and evidence metadata. All operational records currently demonstrate the workflow. The software does not decide eligibility, allocate housing or authorise relocation.

## 7. Innovation and existing alternatives

**90 words / 150-word draft budget.**

The proposed contribution is one traceable workflow connecting transparent priorities, intervention assumptions and evidence required for service review. Its incremental local benefit remains to be tested. SRA GIS, PMAY monitoring, SBM functional-asset monitoring, Swachhata complaint follow-up and community scorecards are existing alternatives. GIS, weighted scoring and file uploads are not novel by themselves. A spreadsheet may adequately solve the review task. UrbanSaarthi must show fewer critical evidence omissions or reduced effort against the actual existing process before claiming a defensible advantage. There is no claimed patent or validated AI superiority.

Supporting sources; access dates recorded in the research and pilot notes: [source 1](https://maharashtra.nic.in/news/gis-sra/), [source 2](https://mahadma.maharashtra.gov.in/wp-content/uploads/2025/07/swachh-bharat-2.pdf), [source 3](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2162194&lang=2&reg=48).

## 8. Technology and methodology

**99 words / 150-word draft budget.**

The focused app uses React, TypeScript, Vite and Leaflet with a Python FastAPI backend and SQLite. Deterministic weighted scoring preserves missing positive-weight inputs as intervals without a rank. Dijkstra computes distances on the supplied synthetic graph. Scenario arithmetic exposes unit costs, temporary support, contingency and maintenance assumptions. Python and browser calculations are checked for consistency. File hashes, review gates, complaint invalidation and transactional records support the demonstration audit trail. A separate browser sandbox never silently synchronises its records to the API. No LLM calculates scores or supplies infrastructure facts. PostGIS, operational data imports and authenticated roles remain production work.

## 9. Current stage and testing

**91 words / 150-word draft budget.**

UrbanSaarthi is a working software prototype, not a field pilot. The repository contains the research review and a separate three-record SRA desk case. Calculation tests, API tests, the production frontend build and actual Chromium checks have executed successfully on the recorded source version. The browser workflow covers scenario drafting, file evidence, failed and passing service measurements, complaint disputes, fresh review, persistence, exports and responsive screens. Exact commits and current outcomes are linked in the validation records. No independent field priorities, resident outcomes, agency acceptance or real construction-cost validation have been obtained.

## 10. Implementation and feasibility

**95 words / 150-word draft budget.**

The proposed 90-day trial starts with a named task owner, an agreed area, permitted records and a safe observation protocol. Days 1–30 document the existing process and prepare up to 20 approved public water assets. Days 31–60 aim for three dated review rounds, recording missing observations and disagreements. Independent reviewers assess evidence before seeing engine scores. Days 61–90 compare review time and critical omissions against the current process and agree handover costs. These are conditional targets. Use approved exports before promising an integration. Operational use requires authenticated roles, independent inspections and an accountable maintenance operator.

## 11. Government adopter and operating model

**85 words / 100-word draft budget.**

The prospective sponsor is BMC M-East ward administration. The proposed water-domain owner is Assistant Engineer (Water Works), M-East, with the actual asset operator. The published ward directory and departmental manual support this role mapping, but no office has accepted the trial. Obtain current delegation, data permission, inspection rules, operator responsibility and a recurring payer before use. SRA/MHADA may supply relevant project context. Begin with a reviewable brief within the current process. A pilot work order or grant is a candidate funding route, not a commitment.

Supporting sources; access dates recorded in the research and pilot notes: [source 1](https://portal.mcgm.gov.in/irj/portal/anonymous/qlacmeward).

## 12. Expected impact and measurement

**81 words / 100-word draft budget.**

Expected benefits are hypotheses: fewer critical evidence omissions, clearer handling of missing information and less effort for one review. Independently assess the same cases before showing scores. Measure paired review time, omissions, source completeness, rank agreement with ties and repeat service observations. Report actual sample sizes and exclusions. Current resident benefit, reliability improvement and SROI are unmeasured. Include women, older and disabled residents, renters and migrants through voluntary accessible participation. SDG 6, 11 and 1 describe intended relevance, not measured progress.

## 13. Scalability

**88 words / 100-word draft budget.**

First validate one review task with an accountable operator. Test a second ward only after an independent assessment shows useful results and a recurring payer is identified. Add approved spatial imports, Marathi and accessibility improvements with user testing. Agency integrations require confirmed interfaces, stable identifiers and data-sharing agreements. Expansion over three to five years depends on successful transfer, security, maintenance and governance. No city-wide coverage or beneficiary forecast is claimed. If current municipal reports already solve the task adequately, integrate with them or stop the separate platform proposal.

## 14. Financial requirement and sustainability

**88 words / 150-word draft budget.**

The illustrative 90-day review trial costs INR 132,000: INR 120,000 of assumed analyst, software, observation, community, travel, hosting, review and training costs plus 10% contingency. Annual continuation is illustrated at INR 162,360. These are editable workload assumptions, not quotations or approved funding. They exclude construction, relocation and asset-repair capital costs. Redevelopment scenarios use separate hypothetical inputs. Cost per household and SROI remain unavailable without verified denominators and benefits. A quotation template records scope, units, dates, taxes and exclusions. Before handover, confirm the paying institution, operator and maintenance obligation.

## 15. Inclusion and safeguards

**83 words / 100-word draft budget.**

Use public-asset or approved aggregate evidence and voluntary assisted feedback. Keep names, Aadhaar, phone numbers, household eligibility, health records and identifying images out of the public demo. Inspect affordability, opening hours, safety and disability barriers separately from distance. A configured officer key protects demo records, but self-entered reviewer names do not establish authenticated independence. Production needs roles, storage controls, retention, backups and the host agency’s security approval. Browser sandbox records remain separate from server records. No housing allocation or relocation decision is automated.

## 16. Risks and mitigation

**76 words / 100-word draft budget.**

The main risks are duplication, unacquired current service data, misleading hypothetical costs, unverified inspections and insufficient maintenance capacity. Validate the existing task before expanding. Preserve dates and missingness, seek permitted aggregate records, obtain independent labels and engineering-reviewed rates, and separate physical completion from service review. Mapped amenities do not prove accessible or functioning services. Stage a small supervised trial with an operator and recurring payer. Automated software checks do not establish field accuracy or government readiness.

## 17. Individual applicant and support required

**79 words / 100-word draft budget.**

I am applying as an individual participant. Personal profile and eligibility details will be completed privately. UrbanSaarthi is a working research-based software prototype. I seek a ward/service-domain mentor, an agreed de-identified review task, a community and independent field-validation partner, and a scoped trial budget subject to quotations and approval. No agency, operational users or funding commitments are confirmed. The next milestone is a fair comparison against the existing inspection-review process, followed by a documented continue, adapt or stop decision.

## Applicant-only fields

Complete legal name, age/category, domicile, background/skills, contact details, identity authentication, declarations, actual IP/registration details and final submission privately in the actual portal. These were skipped at the applicant's request. No profile fact should be inferred from a workspace username. Do not invent a hosted demo URL; the repository and local five-screen application are the demonstration deliverables.
