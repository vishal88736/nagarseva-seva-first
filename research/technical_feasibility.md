# Technical feasibility and recommended prototype

Research/access date: **17 October 2026**. The original design assessment is retained below. The authorised follow-up now includes a [working browser prototype](../prototype/README.md), with executed checks in [prototype_validation.md](prototype_validation.md). No trained model, independent field dataset or measured public-service impact has been produced. The [inventory](dataset_inventory.csv) contains **32 candidates**, including inaccessible/prospective inputs and three transcribed reference points; it is not a list of downloaded datasets.

## Implemented follow-up

The prototype uses dependency-free browser JavaScript for candidate graph routes, source-supplied deficit bounds, weight sensitivity, same-window claim conflicts, an exact hypothetical maintenance-budget comparison and lexical search over curated source cards. It preserves real reference records separately from a labelled synthetic test network. A self-contained HTML build works without a local server or external runtime assets. Imported JSON stays in browser memory, with a schema/provenance gate and exportable review brief. Current household-service evidence, an acquired real road network and operational adoption remain missing. The software does not decide eligibility, allocation or relocation and does not create a new grievance inbox.

## Recommendation and boundary

Build an **evidence-linked service inspection and access workbench** for one small cluster, conditional on acquiring a lawful spatial input. Its value proposition is: *Show the source, date, location, uncertainty and next verification step behind a service-improvement discussion.* Adoption and time savings remain hypotheses.

Use GIS and explicit rules first. Integrated GIS, community mapping and prioritisation are established approaches: see [NIC SRA](https://maharashtra.nic.in/news/gis-sra/), [Joshi et al.](https://doi.org/10.1177/095624780201400218), [Osrin et al.](https://link.springer.com/article/10.1007/s11524-011-9556-7) and [the MCDA review](https://doi.org/10.1080/13658810600661508). “AI” is not the contribution unless a measured, independently reviewed task benefits from it.

## Options A–F

Effort estimates are qualitative for a solo participant's one-week constraint, assuming basic GIS/Python ability **[VERIFY: actual skills]**. None are tested development-time estimates.

| Direction | Required data and readiness | Method and honest baseline | Validation and demonstrable value | Difficulty, risk and decision |
|---|---|---|---|---|
| **A. Settlement and service-gap mapping** | Permitted current cluster footprint or explicitly chosen analysis extent; dated OSM roads/amenities (D10); official assets if acquired (D08); independent observations for actual deficits (D28). No raw spatial files acquired. | GIS overlay and network distance to mapped amenities. Baseline: original table/map and straight-line distances, both using the same inputs. | Geometry/schema checks, route spot-checks and source completeness audit. Demonstrate where evidence is dated/missing and how network access differs from a simple radius. | **Medium** once inputs obtained. Do not equate unmapped with absent, or proximity with functionality. **Core**, labelled access/context mapping until deficits are independently established. |
| **B. Explainable inspection prioritisation** | Comparable dated observations, agreed units/criteria, service responsibility and constraints. Census/state averages cannot fill household gaps. | Weighted additive MCDA with anchored scales, visible contributions, unknown-value intervals and weight sensitivity. Baseline: current officer process or simple queue, recorded before showing results. | Independent observed labels where appropriate; ranking stability, false-negative review and stakeholder task assessment. Demonstrate why a case is selected and when evidence is insufficient. | **Medium**, data-dependent. Normative weights can encode bias; missingness can distort rankings. **Conditional core** for inspections/service improvement only; no eligibility or relocation decisions. |
| **C. Improvement/redevelopment/relocation scenario comparison** | Actual options, land/planning/legal constraints, resident-defined destinations/preferences, costs and O&M (D29), safe route network. Not acquired. | Side-by-side access/cost table. Optional small budget-constrained coverage optimisation; exhaustive enumeration for a few options is a transparent baseline. | Same-budget comparison, constraint audit, cost sensitivity and resident review. Demonstrate trade-offs, not a “best relocation” answer. | **High** for a credible real-site appraisal. **Defer real redevelopment optimisation**; permit an explicitly hypothetical example only. No legal-feasibility or displacement decision from software. |
| **D. Infrastructure progress and service verification** | Dated project/asset records (D27), named operator and actual contract/MoU; repeat observations (D28). No local records acquired. | Evidence/event ledger separating official issue, contractor claim, field observation, resident confirmation and disputes. Baseline: existing status report and same-window records. | Independently adjudicated claims, agreement, traceability and recurrence. Show contradictory/expired evidence instead of silently replacing a status. | **Medium** for evidence display; **high** for credible field verification. **Small conditional extension**, not engineering certification or a replacement PMAY/AMRUT MIS. |
| **E. Citizen grievance reporting/follow-up** | Existing complaint IDs, authorised de-identified logs (D26), routing owner, closure/reopen definitions and user access. Not acquired. | Link existing records and repeat observations; no new complaint intake by default. Baseline: current BMC/Swachhata process. | Approved sample audit, unresolved-age/recurrence and resident accessibility. Added value exists only if a local workflow test establishes it. | **High** for integration, ownership and privacy. **Defer new portal**: confirmation/reopening already exists in [Swachhata](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2162194&lang=2&reg=48). |
| **F. AI-assisted document search/summarisation** | Authoritative documents, exact version/date, section/page references and extraction QA. Official text was read on web; local PDF corpus not assembled. | Start with manual source cards and lexical retrieval/BM25. Add an LLM only to summarise retrieved evidence with citations and abstention. Baseline: search/extract without generation. | Blind question set with independently written answer spans; retrieval recall, claim/citation accuracy, version handling and correct abstention. Demonstrate reduced search effort only if actually measured. | **Low–Medium** for a small source-card search; **Medium–High** for reliable multilingual/OCR RAG. **Optional**, never an authority for unsourced legal facts or spatial conclusions. |

## Smallest implementable architecture

**Option 1, preferred for the deadline:** QGIS for inspection and routing, CSV/GeoPackage for versioned inputs, a short reproducible analysis script for joins/metrics, and a simple local map/report interface if time permits. A GIS project plus reproducible outputs is sufficient to demonstrate the analysis; a web application is optional. [QGIS network-analysis documentation](https://docs.qgis.org/3.44/en/docs/user_manual/processing_algs/qgis/networkanalysis.html)

**Option 2, after data and workflow validation:** a small web interface with a spatial database, permissioned event storage and scheduled approved imports. Add APIs only after the authority confirms the supported interface and data-sharing terms. Do not promise live SRA/MHADA/Aaple Sarkar integration from links alone. Institutional hosting, procurement, accessibility, security and departmental integration are production work beyond a one-week prototype.

Proposed data flow:

1. **Acquire and register:** source URL/publisher, observation date, publication date, retrieval date, licence, file hash and acquisition result. Keep each original unchanged if lawful to retain.
2. **Inspect:** schema, CRS/units, validity, extent, record count, duplicates, nulls, stale dates and geometry/attribute coverage. A failed import remains failed.
3. **Link:** preserve original IDs; map to local analysis IDs through an explicit crosswalk. Record method, confidence and reviewer. Do not join schemes solely by a shared CTS number or fuzzy locality name.
4. **Analyse:** compute mapped-amenity access; compare evidence in matching time windows; calculate priority intervals only for suitable data.
5. **Review/export:** display source/date/limitations, uncertain joins, disputes and reasons for withheld results. Export a dated inspection brief for the existing workflow.

### Minimum data model

| Entity | Minimum fields | Why it matters |
|---|---|---|
| Source/version | Source ID, URL, publisher, publication/version, observation period, access date, licence, hash | A recent upload may contain old observations |
| Analysis area | Local area ID, geometry/CRS, boundary source/version, geographic type | A demonstration extent is not a notified slum boundary |
| Asset/scheme | Local ID, source ID, original identifier, type, geometry and date | SRA schemes, settlement areas and service assets are different objects |
| Crosswalk | Source pair, linked IDs, match evidence/method, reviewer, confidence | Preserve uncertain and many-to-many matches |
| Observation/claim | Asset, service, observed/issued time, recorder role, claim type/value, evidence reference, uncertainty, dispute | Contractor claims and resident observations can coexist without one overwriting the other |
| Responsibility | Asset, authority/operator, dated agreement or confirmation, scope | An asset's maintenance owner cannot be guessed from its location |
| Analysis run | Input versions, criteria/weights, exclusions, algorithm settings, results and withheld-result reasons | Enables reproduction and challenge |

Store public aggregate sources separately from restricted observations. For a public demonstration use no names, Aadhaar, phone numbers, income/health records, eligibility labels or precise household locations. Provide an assisted/offline route if any later resident participation is authorised. Consent and data minimisation do not replace an actual institutional agreement, access controls and retention rules.

## Methods that fit the available evidence

### Network access

Build a walkable graph from a dated OSM extract. Preserve actual entrances, footpaths, bridges, level crossings and access restrictions where known. Roads crossing on a map must not become connected automatically if they are grade separated. Record snap distance and report unreachable or poorly mapped origins separately. Calculate shortest distances with QGIS or a standard graph algorithm; [NetworkX documents weighted and unweighted shortest paths](https://networkx.org/documentation/stable/reference/algorithms/shortest_paths.html).

Use several defensible public entrances/origins rather than pretending a polygon centroid represents all households. If no valid settlement polygon is available, state that origins represent an **illustrative analysis extent**. Publish a distance to a **mapped** school/clinic/stop, with the source caveat. Timetabled transport travel time needs a verified timetable/GTFS input, which was not acquired; walking-speed assumptions must be shown rather than described as observed commute times.

### Prioritisation and optimisation

Agree criteria before viewing outcomes. For a deficit-oriented criterion, map observations to a stated 0–1 scale using fixed substantive anchors. For complete comparable records, `score_i = sum(weight_j × deficit_ij)` with nonnegative weights summing to one. Show each contribution. A missing value is an unknown interval, not zero. Show best/worst feasible score bounds or withhold ranking; do not silently renormalise weights by what happens to be present.

Maintain separate **evidence-needed inspection** and **observed service-deficit** views. Sparse information may justify inspection, while being insufficient to claim deprivation. Keep imminent risks on an agreed escalation pathway rather than allowing weighted averages to hide them.

If a later budget exercise has verified candidate interventions, estimate coverage without double-counting and impose budget/legal/site constraints. A small maximum-coverage model is enough; [OR-Tools documents mixed-integer modelling](https://developers.google.com/optimization/mip/mip_example). Solver optimality means optimality under supplied assumptions, not a fair, lawful or resident-approved outcome. Do not optimise housing eligibility, beneficiary allocation or relocation.

### Computer vision and remote sensing

**Do not train a new slum classifier for this one-week submission.** Reviewed literature establishes both prior art and domain-transfer limitations. Open Sentinel-2 imagery provides 10/20/60 m bands; these are not direct measures of household water, toilets, poverty or tenure. [Product documentation](https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel2.html), [Wurm et al.](https://elib.dlr.de/126606/), [Kohli et al.](https://doi.org/10.1016/j.compenvurbsys.2011.11.001)

At most use a dated scene for broad context, with cloud/resolution caveats. A future morphology model needs permitted high-resolution imagery, a precise label definition, independent local labels, held-out spatial/temporal areas, external-domain testing and comparison with simpler methods. Change detection does not prove construction approval, completion or an occupied household's rights. Drone permissions and operational arrangements were not researched; exclude drone collection from the submission.

### Document assistance

Retain the authoritative document's date and section with each chunk. Check OCR tables/numerals manually. Retrieval must respect the requested scheme, jurisdiction and date. Where sources conflict, show both and state the unresolved point. For any LLM layer, treat document text as evidence rather than instructions, prohibit unsupported numerical/legal synthesis and return “insufficient evidence” when necessary. Marathi text requires reviewed extraction/translation; no translation quality was evaluated in this research.

## Adoption dependencies and operating costs

The proposed operational sponsor for Mumbai is the **BMC M/E ward administration together with the relevant service department and actual operator**; this is a recommendation, not acceptance. SRA/MHADA provide applicable project context. Obtain the specific asset agreement and delegated responsibility before designing escalation. Public systems already perform related monitoring, so the first integration should be a reviewable export that the sponsor can use. See [existing_solutions.md](existing_solutions.md).

No unit cost, CSR commitment, cost saving or SROI has been established. For a later cost model collect staff time, field travel/verification, data acquisition, hosting/storage, support, accessibility and security costs; identify who pays recurring O&M. A free map library does not make the public service free. Do not claim PMAY/AMRUT/SBM funds are available to purchase this tool without a competent authority's approval.

Proposed validation path, subject to approval: in the first 30 days obtain a bounded dataset/workflow and independent baseline; by 60 days compare a small repeat-inspection exercise with the existing process; by 90 days decide on adoption using evidence quality, effort, privacy and a named operating owner. These are proposed gates, not approved pilot targets. Expand ward by ward only after stable identifiers, training, recurring budget and an integration owner are established.

## One-week build sequence

| Day | Reviewable output | Stop/reduce scope if |
|---|---|---|
| 1 | Acquire one small lawful extract; write metadata and choose one service-review question | No usable data: switch to sourced document/evidence audit; do not fabricate a settlement baseline |
| 2 | Validate geometry/fields; inspect authoritative IDs and uncertain joins | Boundaries/denominators cannot be matched: retain separate layers, no household rates |
| 3 | Produce mapped-amenity network-access example and inspect routes | Network is inadequate: present data gaps and verified map context only |
| 4 | Add evidence/date/conflict cards; optionally add sensitivity-tested inspection scoring | No comparable observations: withhold service-deficit rankings |
| 5 | Run the applicable evaluation from [evaluation_plan.md](evaluation_plan.md); seek a workflow review if available | No field/official review: label desk validation explicitly |
| 6 | Prepare a reproducible demonstration, source list and limitations | Remove untested claims and simulated impact |
| 7 | Check the submission's current official instructions and rehearse questions | Cut features before weakening the evidence trail |

The three strongest submission elements are **dated evidence with explicit unknowns; barrier-aware access comparison; and explainable inspection priorities with sensitivity**. The third is conditional on suitable observations. If those are unavailable, substitute **document search with citations/abstention** and clearly narrow the claim. These are candidate differentiators to validate against an existing local workflow, not claims of first-ever functionality.
