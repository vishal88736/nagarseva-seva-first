# Research decision brief

Research/access date: **17 October 2026**. Prepared for a solo participant with approximately one week available. This package reviews **14 journal publications and one additional government impact study**, compares public systems and inventories **32 dataset/input candidates**. Full-text access varies and limitations are marked. The follow-up adds a [working local prototype](../prototype/README.md) and [executed software checks](prototype_validation.md); no field survey, real road-network ingestion or measured service impact is claimed.

## Build decision

**Do not commit to a city-wide AI urban-planning platform.** Build a bounded **evidence-linked service inspection and access workbench**, conditional on acquiring a lawful small spatial input and identifying a real review task. Demonstrate what is known, from which source/date, what conflicts, and what needs checking before an inspection or service-improvement decision.

The research supports the importance of service reliability, livelihood continuity and maintenance. It does **not** establish that a new integrated platform is absent or wanted locally. Existing GIS, mapping, scorecards and complaint verification weaken broad novelty claims. Follow-up also verified that **SBM-U 2.0 already specifies integrated GIS and functional-asset monitoring**. [SBM Chapter 10](https://mahadma.maharashtra.gov.in/wp-content/uploads/2025/07/swachh-bharat-2.pdf), [NIC SRA GIS](https://maharashtra.nic.in/news/gis-sra/), [Shelter Associates](https://shelter-associates.org/), [Mumbai scorecard study](https://link.springer.com/article/10.1007/s11524-011-9556-7), [Swachhata](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2162194&lang=2&reg=48)

## Strongest supported problem

**A dwelling or mapped infrastructure asset does not by itself establish reliable, affordable and usable neighbourhood services.** Mumbai studies document water-reliability and post-relocation governance/livelihood concerns, alongside benefits and resident adaptation. These are historical/local mechanisms, not a current ward prevalence estimate. [Water study](https://link.springer.com/article/10.1186/1471-2458-13-173), [relocation governance study](https://knowledge.uchicago.edu/records/c0z96-tzt75), [women's livelihood study](https://doi.org/10.1016/j.worlddev.2016.04.007)

Official historical anchors include **11,848,423 Maharashtra slum residents in Census 2011** and **1.94 million estimated Maharashtra urban housing shortage in 2012**. They establish scale, not today's baseline. M/E water/toilet percentages reproduced in later climate documents also originate in Census 2011, use a ward-wide household denominator and do not measure continuous service. [MoHUA handbook](https://mohua.gov.in/pdf/6253c2f3cea11Handbook-of-Urban-Statistics-2016.pdf), [2012–13 annual report](https://mohua.gov.in/upload/uploadfiles/files/5Annual_Reprot_English_2012-13.pdf), [Mumbai climate plan](https://www.mcgm.gov.in/irj/go/km/docs/documents/Environment/Climate/Mumbai%20Climate%20Action%20Plan.pdf)

Current local rates for unreliable water, unusable toilets, missed waste collection, drainage failures and housing shortage remain **[VERIFY]**. PMAY already defines completed projects with infrastructure; do not pitch “government only counts houses” as the research finding. [PMAY-U 2.0 guidelines](https://pmaymis.gov.in/PMAYMIS2_2024/Operational-Guidelines-of-PMAY-U-2.pdf)

## Most defensible gap

Test whether **a dated, geographically matched evidence brief with explicit missingness and uncertainty** helps a ward/operator conduct one service review more accurately or efficiently than the current process. The untested part is the **incremental local workflow benefit**, not the existence of GIS or citizen feedback.

The gap fails if existing reports already answer that task adequately. Obtain a de-identified walkthrough before expanding. Keep alternative explanations and existing capabilities visible in [research_gap.md](research_gap.md).

## Location and adopter

**Mumbai M/E is the preferred desk-demonstration area**, with a candidate Deonar–Govandi/Baiganwadi cluster. The source base is stronger here and public SRA rows identify M-E locality leads. Precise current boundaries, actual deficits and community/official access remain unverified. [SRA public list](https://dms.sra.gov.in/SRAPUBLIC/)

**Pune is the preferred conditional field alternative** if a municipal/NGO partner provides a permitted extract and review access. PMC GIS and established community-mapping practice are strengths; this research encountered failed or restricted data access. No partner has been contacted. Nagpur and Nashik remain alternatives if actual access becomes available; this review did not establish a stronger one-week data path. [PMC GIS](https://iwmsgis.pmc.gov.in/geopulse/autodcr/), [Shelter Associates report](https://shelter-associates.org/wp-content/uploads/2025/11/Annual-Report-24-25-05.11.25.pdf)

For a Mumbai operational pilot, approach **BMC M/E ward administration with the relevant service department and actual operator** as proposed sponsor/owner. SRA/MHADA would contribute applicable project context. This is an adoption recommendation, not an approved pilot or verified delegation of every maintenance duty.

## Data that can support a demonstration

| Input | Use | Acquisition/interpretation boundary |
|---|---|---|
| **OSM via Geofabrik western-zone extract** | Roads, walking links and mapped amenities | Download routes documented, file not ingested; ODbL obligations; completeness and access restrictions need checking. [Download page](https://download.geofabrik.de/asia/india/western-zone.html) |
| **Public SRA scheme rows** | Locality discovery and record evidence cards | Readable rows; no acquired spatial geometry, current service status or bulk licence. [Portal](https://dms.sra.gov.in/SRAPUBLIC/) |
| **Official policy text and historical census/ward tables** | Source-grounded context and document-search baseline | Retain observation year, geography and version; do not substitute for current local measurements. See [official_sources.md](official_sources.md). |
| **Sentinel-2, WorldPop, GHSL** | Optional broad spatial/population context | Product metadata verified, no selected India scene/tile ingested; no household-service or eligibility inference. See [dataset_inventory.csv](dataset_inventory.csv). |
| **Municipal assets, operator observations, complaint logs and costs** | Real deficits, closure verification and budget scenarios | Require successful acquisition, permission and validation; these inputs were not obtained. |

## One-week prototype and evidence of value

Prioritise three elements: **source/date/unknown cards; a checked network-access comparison; and explainable inspection priorities with sensitivity**, only when comparable service observations exist. Otherwise replace the third with **document search using citations and abstention**. Use QGIS/CSV and a small reproducible analysis; add an interface only if time permits.

The follow-up implements source cards, imported-graph routes, interval scoring, claim conflicts and explicitly hypothetical maintenance comparisons. Three secondary OSM-derived transport points supply real location references; the default real-reference view calculates no walking route without a network. Software/retrieval checks are reported separately from actual deficit accuracy, uptime, resident benefit and adoption, which still require field/official validation. [Evaluation plan](evaluation_plan.md), [access follow-up](access_followup.md), [prototype validation](prototype_validation.md)

Cut satellite-model training, drones, blockchain allocation, automatic eligibility/relocation, a new grievance inbox, city-wide household registration and a complete redevelopment-finance engine. They increase scope or duplicate prior art without establishing local value.

## Major risks and next decisions

1. **Data:** failed exports, uncertain licences and old boundaries may prevent a real map. Secure the smallest lawful extract first; switch to an evidence/document audit if this fails.
2. **Duplication/adoption:** a new dashboard may solve no new task. Review the existing officer/operator workflow and assign one operating owner.
3. **Misinterpretation:** proximity, modelled population and historical ward rates can become false household claims. Preserve denominators, unknowns and validation boundaries.
4. **Governance/privacy:** case and resident records need permission, minimisation and controlled use. No public household registry or automated housing decisions.
5. **Scope:** a solo week supports a research prototype. Engineering approval, finance, institutional integration and sustained O&M remain deployment dependencies.

Before an operational trial, resolve **which review decision, which current boundary/input, which responsible official/operator, and which independent evidence/comparator**. The follow-up includes a [real three-record SRA desk case](public_record_case.md) and a [submission/pilot pack](../submission/README.md). The case verifies evidence-handling arithmetic, not current service conditions, duplicate schemes or delays. Details and unresolved questions are in [technical_feasibility.md](technical_feasibility.md).

## Competition checks

The live site advertises **30 October 2026**, **50 awardees across ten sectors**, and conditional **work orders up to Rs 10 lakh**, rather than guaranteed unrestricted cash. Indexed older pages still show 17 October and category wording conflicts. Exact cutoff time, stage dates and application limits remain **[VERIFY]** in the current portal. Individuals/concepts are permitted; check domicile requirements and the official presentation template. [Live competition page](https://sevainnovationchallenge.in/), [guidelines](https://sevainnovationchallenge.in/guidelines.html)
