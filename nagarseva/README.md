# UrbanSaarthi application

**People • Places • Better Cities**

The active application is the English/Hindi/Marathi **Demo data** prototype for
SEVAMO96. React/TypeScript/Vite/Leaflet use a shared FastAPI/SQLite synthetic
workspace. Historical/acquired datasets and model-backed routes are preserved
compatibility material and are disconnected from the active UI.

Read the [main project README](../README.md) for the feature directory, data model,
configuration, calculation methods, file onboarding, test commands and limitations.
The [AWS operations guide](../deploy/aws/README.md) describes current hosting.

## Start the application

Run from the **repository root**, one directory above this file:

```bash
bash start-local.sh
```

The launcher uses Python 3.12, creates `nagarseva/.venv` if required, installs the
focused backend requirements/frontend lockfile dependencies when changed, and
starts both owned processes. Node 24 matches the Docker and CI configuration.

- Website: <http://localhost:5173/dashboard>.
- Local API docs: <http://localhost:8000/docs>.
- Default SQLite file: `model/data/local/urbansaarthi.sqlite3`, relative to this
  `nagarseva/` directory.
- Logs: `.runtime/local/8000-5173/`, relative to the repository root.
- Stop both processes with **Ctrl+C** in the launcher terminal.

The parent repository directory has no frontend package.json. Use
`npm --prefix nagarseva/website ...` from the repository root, or `npm ...` from
`nagarseva/website/`. No ML training or original-dataset ingestion is needed.

## Entry points

| Path | Responsibility |
| --- | --- |
| `website/src/civic/` | Active civic UI, typed adapter, shared state and calculations. |
| `website/src/integration/` | Isolated file inspection, mapping, validation/import and audit UI. |
| `website/src/i18n/` | Language resources, preference and locale formatting. |
| `model/api/urban.py` | Active FastAPI app: `model.api.urban:app`. |
| `model/api/civic_demo.py` | Deterministic generator, validation, transactional civic commands. |
| `model/api/data_onboarding.py` | Controlled import batches, provenance and rollback. |
| `model/requirements-urban.txt` | Dependencies needed by the active civic application. |
| `model/api/main.py` | Preserved legacy/model-backed API; not the default runtime. |

Affordable Housing is under **Projects & Reports → Affordable Housing**, with a
direct `/housing` route. Basic-service assurance and visits also have `/services`
and `/visits` routes. The [root feature table](../README.md#features-and-navigation)
lists every main view.

## Persistence and authorization

The active workspace is synthetic and stored on the API server in SQLite, not
browser localStorage. Public demo submissions and authorized administrative edits
update that same store. Controlled imports are separate, inactive batches.

Use the [configuration guide](../README.md#configuration) to set a private server
administrator key and enter it in **Administration**. This is demonstration access,
not production identity/RBAC. Never embed keys in `VITE_*` variables or source files.

The older [NagarSeva guide](README.NagarSeva.md), acquired-data documentation and
`Makefile` targets remain available for historical/legacy work. In particular,
`make acquire-public-data`, `make data` and `make train` are not steps for running
the current synthetic prototype. Do not reactivate those pipelines accidentally.
