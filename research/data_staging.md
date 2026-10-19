# Staging the acquired public snapshot

`stage_public_data.py` prepares a local, portable data bundle for the existing API.
It does not download data, contact AWS, change a server, copy operational records or
publish files. Source-specific reuse conditions remain in the snapshot and inventory;
creating a bundle does not establish a redistribution licence.

From the repository root, after acquisition and validation:

```bash
nagarseva/.venv/bin/python scripts/prepare_real_data.py
nagarseva/.venv/bin/python scripts/validate_datasets.py
nagarseva/.venv/bin/python scripts/stage_public_data.py
```

The script prints the bundle ID, directory, archive size and SHA-256, per-file
checksums, validated counts and number of distinct originals checked. The default
output is `.runtime/public-data-bundles/`, which is excluded from Git. Use
`--output /absolute/path/to/a/separate-directory` to choose another destination or
`--data-root /absolute/path/to/data` to select a prepared source directory.

Each bundle directory is named with its full SHA-256 content identity and contains
only:

```text
<bundle-id>/
  manifest.json
  processed/urban_real.json
  metadata/dataset_inventory.csv
  processed/sra_pilot_overlay.png   # only when both overlay files exist
  processed/sra_pilot_overlay.json
```

The adjacent `<bundle-id>.tar.gz` contains these same relative paths. It uses
consistent entry ordering, timestamps, ownership and modes. Repeating staging with
the same inputs verifies and reuses the existing directory and identical archive.
Changed public inputs produce a new bundle. Modified existing bundles or archives
are rejected rather than overwritten. No `--force` option is provided.

Validation before staging checks:

- The public inventory's exact schema, unique dataset names and access statuses.
- Snapshot local IDs, WGS84 geometry validity and CRS, source labels, counts and
  project references, using the API's shared `validate_snapshot` validator.
- Published Census units, years and observations through the API's shared
  snapshot/context validators. Historical aggregates cannot be assigned to
  settlements, converted into current observations or staged as deficit indices.
- The successful local validation receipt and checksums of its distinct downloaded
  originals. Missing or modified originals stop staging. Those originals are read
  locally for integrity checks and are never included in the bundle.
- Optional overlay pairing, PNG parsing/dimensions, image checksum, historical
  `analysis_allowed=false`, source year/official provenance, Web Mercator CRS,
  geographic bounds, control-fit residuals and matching original-map checksum
  through the API's shared raster validator. The raster remains cartographic context with zero
  settlement vector geometries.
- A 64 MiB total payload limit, a 10 MB raster-file limit and a 4096-pixel-per-dimension
  image limit. Symlinks, path traversal, unexpected bundle files, operational
  tables and known credential/upload fields are rejected.

Only the explicitly listed public files are selected. Nearby `.env` files,
SQLite databases, raw originals, field-survey exports and uploaded inspection
evidence are not copied. New public directories use mode `0755`; public files and
archives use `0644`, allowing the container's UID 10001 to read them. Existing
source permissions and unrelated files are not changed.

To verify a transferred or unpacked directory without the original downloads:

```bash
nagarseva/.venv/bin/python scripts/stage_public_data.py \
  --verify /absolute/path/to/<bundle-id>
```

Verification checks the content identity, exact file list, checksums, schemas,
geometries, historical geography, overlay consistency and public read permissions.
The directory name must remain the bundle ID. Keep the printed archive SHA-256
with the transfer receipt and compare it before unpacking into a new directory.
Checksums show integrity against the supplied manifest, not a government digital
signature or field validation.

For the existing hosted container, mount the **two subdirectories read-only**:

```text
host: <bundle-id>/processed  -> container: /data/processed
host: <bundle-id>/metadata   -> container: /data/metadata
URBANSAARTHI_DATA_DIR=/data/processed
```

Keep the existing writable database mount and officer/origin secrets separate.
Mounting a public bundle over the whole `/data` directory would hide the existing
SQLite database, so use the subdirectory mounts above. The API finds the public
inventory at `/data/metadata/dataset_inventory.csv` and loads the acquired snapshot
on startup. Restart the API through the existing deployment procedure, then check
`/api/urban/data/health`, `/api/urban/data/overview`, `/api/urban/data/context` and
`/api/urban/data/map-overlay` with the configured origin protection. Staging alone
is not proof that a remote server loaded the files.

Local fixture verification:

```bash
PYTHONPATH=nagarseva nagarseva/.venv/bin/python -m pytest \
  tests/test_public_data_staging.py -q
CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python \
  tests/check_field_collection_browser.py
```

The field browser check uses explicit synthetic API fixtures and a disposable Vite
process. When `CHROMIUM_PATH` is unset, it uses Playwright's installed Chromium,
including on GitHub Actions. These UI checks do not create field observations.
