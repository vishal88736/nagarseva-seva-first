# Optional authorized field collection

No field observations were acquired. KoboToolbox and ODK are collection tools,
not sources of an existing Mumbai service baseline. The proposed contract is
[survey.schema.json](survey.schema.json), generated from the API's `FieldSurvey`
model; the same schema is available at `/urban/data/surveys/schema`.

| Field | Proposed measurement / rule |
|---|---|
| survey_id | Stable survey UUID/reference; unique across imports |
| settlement_id | Select an existing approved source unit; do not match a typed name approximately |
| observed_at | Actual date/time with timezone; never substitute upload time |
| water_hours_per_day | Nullable 0–24; retain method/time window in protocol_reference |
| functional_toilets_observed | Nullable nonnegative integer; inspected assets, not a household coverage rate |
| blocked_drain_segments_observed | Nullable nonnegative integer with a defined inspection segment protocol |
| sanitation_condition / drainage_condition | Enumerated choices; `not_observed` stays unknown |
| housing_or_infrastructure_observation | Optional bounded note; avoid names, eligibility or inferred structural-safety claims |
| gps_latitude / gps_longitude | Both optional; at most 3 decimals, roughly 100 m; coarse shared-asset context only |
| evidence_reference / evidence_consent | Approved HTTPS storage reference, only with consent; no automatic photograph publication |
| inspector_reference | Pseudonymous authorized team reference, not a beneficiary identifier |
| verification_status | `reported` at import; independent review is a separate step |
| collection_platform / protocol_reference | KoboToolbox, ODK or authorized manual form, plus versioned measurement protocol |

Before collection, agree the unit list, responsible owner, sampling/inspection
protocol, consent, storage, retention and authorized reviewers. The published register
rows have no analytical boundaries; selecting a record or viewing the historical
raster does not establish a legally approved survey geography. No beneficiary names, phone numbers, Aadhaar, income,
religion, caste or household-level coordinates are required.

In Kobo, create a private project in the form builder using the field names and
choices in the schema (or prepare an XLSForm), preview and test on authorized test
units, then deploy after the responsible team approves it. Use XML names/values
for exports and retain dates as text with timezone. [Official export guide](https://support.kobotoolbox.org/export_download.html).

For ODK, prepare the form with those same names/constraints, upload a draft to
Central, use test submissions and restrict app-user access before publishing it.
[ODK Central form lifecycle](https://docs.getodk.org/central-forms/). Neither an
account nor a deployed project was created during this task.

Export only approved, minimised fields. Convert a reviewed platform export to the
JSON array described by the schema; remove system/personal columns explicitly.
Do not use row positions as identifiers, lose timezone offsets, or substitute
missing answers with zero. Coarsen any device GPS privately before creating this
import file; the importer rejects excess precision. No automatic Kobo/ODK account
sync is implemented.

From the repository root:

```bash
nagarseva/.venv/bin/python scripts/import_field_surveys.py /path/to/reviewed-surveys.json
# After reviewing validation output, with the API and officer key configured:
nagarseva/.venv/bin/python scripts/import_field_surveys.py /path/to/reviewed-surveys.json --apply
```

Dry run validates without writing. Apply checks settlement IDs first, sends the
key only in a header, and preserves duplicate originals (HTTP 409). Each survey
and its non-missing numerical spot observations are saved atomically. They remain
`reported`; qualitative observations are not converted into invented deficit
indices. An independently reviewed normalization protocol and repeated evidence
are required before a 0–100 service index is submitted through `/indicators`.
Inspector references and private evidence are protected by officer access.

## Authorized application entry

Service Assurance now includes collapsed forms for an authorized field visit and a
separately reviewed deficit index. Enter the configured officer key, choose the
source record and approved protocol, record the actual timezone-bearing date and
leave unobserved measurements blank. Reported visits persist through the same API
as the CLI importer and never automatically fill the priority indices. The index
form requires an explicit supplied value, normalization method, evidence permission
and separate review acknowledgement when claiming a field-reviewed record. These
are user-recorded references, not government identity authentication. Operational
records and survey CSV exports remain protected; public observations redact inspector,
reviewer and evidence references. No actual field baseline was collected by the
software tests.
