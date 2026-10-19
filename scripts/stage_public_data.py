"""Stage a bounded, immutable public-data bundle locally; never deploy or download.

Only the acquired application snapshot, public inventory and optional historical
map overlay are allowed. Operational SQLite records and field evidence cannot be
selected. Original checksums are checked in place, never copied into the bundle.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile
import tempfile

from PIL import Image

from data_common import INVENTORY_FIELDS, ROOT

sys.path.insert(0, str(ROOT / "nagarseva"))
from model.api.snapshot_validation import validate_snapshot as shared_validate_snapshot
from model.api.raster_validation import validate_overlay as shared_validate_overlay

REQUIRED = {"processed/urban_real.json", "metadata/dataset_inventory.csv"}
OVERLAY = {"processed/sra_pilot_overlay.png", "processed/sra_pilot_overlay.json"}
MAX_BYTES = 64 * 1024 * 1024
MAX_SOURCE_BYTES = 1024 * 1024 * 1024
STATUSES = {"downloaded", "accessible_not_downloaded", "authentication_required", "unavailable", "failed", "metadata_only"}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(data):
    return (json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode()


def read_bounded(path, limit):
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("Only regular public source files are accepted")
    if not 0 < path.stat().st_size <= limit:
        raise ValueError("Public source exceeds its size limit or is empty: " + path.name)
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Source changed or exceeded its size limit while reading")
    return raw


def safe_source(root, relative):
    if not isinstance(relative, str):
        raise ValueError("Unsafe public source path")
    name = PurePosixPath(relative)
    if name.is_absolute() or ".." in name.parts or "\\" in relative or name.as_posix() != relative:
        raise ValueError("Unsafe public source path")
    path = root / name
    if any(part.is_symlink() for part in [path, *path.parents] if part != root.parent):
        raise ValueError("Symlinked public source paths are not accepted")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Public source escapes its data directory")
    return path


def validate_snapshot(raw):
    data = json.loads(raw)
    allowed = {"metadata", "settlements", "projects", "geographic_units", "indicators", "spatial"}
    if not isinstance(data, dict) or set(data) - allowed or not {"metadata", "settlements", "projects", "spatial"} <= set(data):
        raise ValueError("Only acquired public source tables can be staged; operational tables are excluded")
    private_keys = {"content_base64", "upload_content", "officer_key", "api_key", "password", "access_token", "beneficiary_name", "beneficiary_phone"}
    pending = [data]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            if private_keys.intersection(str(key).lower() for key in item):
                raise ValueError("Private credentials, beneficiary details or uploaded evidence cannot be staged")
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    if not isinstance(data["metadata"], dict) or data["metadata"].get("synthetic") is not False:
        raise ValueError("Snapshot must be explicitly acquired and non-synthetic")
    units, observations = shared_validate_snapshot(data)
    for table in ("settlements", "projects"):
        for row in data[table]:
            if row.get("synthetic") is not False:
                raise ValueError("Synthetic or unlabelled records cannot be staged as acquired data")
            source_key = "source" if table == "settlements" else "source_url"
            if not isinstance(row.get(source_key), str) or not row[source_key].startswith("https://"):
                raise ValueError("Public records require HTTPS source provenance")
            if table == "settlements" and any(value is not None for value in row.get("indicators", {}).values()):
                raise ValueError("User field deficit indices cannot be packaged in an acquired source snapshot")
    return {"settlement_count": len(data["settlements"]), "settlement_geometry_count": sum(row["geometry"] is not None for row in data["settlements"]),
            "projects_count": len(data["projects"]), "mapped_objects_count": len(data["spatial"]["features"]),
            "geographic_unit_count": len(units), "historical_observation_count": len(observations)}


def validate_inventory(raw):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if reader.fieldnames != INVENTORY_FIELDS:
        raise ValueError("Inventory does not have the documented public schema")
    rows = list(reader)
    names = set()
    for row in rows:
        if None in row or any(value is None for value in row.values()) or not row["dataset_name"] or row["dataset_name"] in names or row["access_status"] not in STATUSES:
            raise ValueError("Inventory has incomplete rows, duplicate names or invalid access status")
        names.add(row["dataset_name"])
    if not rows:
        raise ValueError("Public inventory is empty")
    return len(rows)


def validate_originals(data_root, report_raw, snapshot_counts):
    report = json.loads(report_raw)
    if report.get("valid") is not True or report.get("errors") != [] or not isinstance(report.get("downloads"), list) or not report["downloads"]:
        raise ValueError("Run validate_datasets.py successfully before staging")
    key_map = {"settlements": "settlement_count", "projects": "projects_count", "geographic_units": "geographic_unit_count", "indicators": "historical_observation_count"}
    for table, key in key_map.items():
        record = report.get("datasets", {}).get(table)
        if record and record.get("record_count") != snapshot_counts[key]:
            raise ValueError("Validation receipt is stale for " + table + "; rerun validate_datasets.py")
    checked, total = {}, 0
    for row in report["downloads"]:
        name = row.get("path", "")
        parts = PurePosixPath(name).parts
        if len(parts) < 4 or parts[:2] != ("data", "raw") or row.get("checksum_valid") is not True:
            raise ValueError("Validation receipt contains an unsafe or unverified original")
        if name in checked:
            if checked[name]["sha256"] != row.get("sha256") or checked[name]["bytes"] != row.get("bytes"):
                raise ValueError("Conflicting original source checksums")
            continue
        path = safe_source(data_root, "/".join(parts[1:]))
        raw = read_bounded(path, min(MAX_BYTES, MAX_SOURCE_BYTES - total))
        total += len(raw)
        if len(raw) != row.get("bytes") or digest(raw) != row.get("sha256"):
            raise ValueError("Missing or modified original source: " + name)
        checked[name] = {"path": name, "bytes": len(raw), "sha256": digest(raw)}
    return sorted(checked.values(), key=lambda row: row["path"])


def validate_overlay(payloads, checked, expected_bounds=None):
    present = set(payloads) & OVERLAY
    if not present:
        return
    if present != OVERLAY:
        raise ValueError("Historical map image and metadata must be staged together")
    row = json.loads(payloads["processed/sra_pilot_overlay.json"])
    image = payloads["processed/sra_pilot_overlay.png"]
    if not isinstance(row, dict) or row.get("synthetic") is not False:
        raise ValueError("Historical overlay must retain its non-synthetic source flag")
    source = next((item for item in checked if item["path"] == row.get("source_path")), None)
    if source is None:
        raise ValueError("Historical overlay has no matching validated original source")
    shared_validate_overlay(row, image, expected_source_sha256=source["sha256"], expected_bounds=expected_bounds)
    try:
        with Image.open(io.BytesIO(image)) as parsed:
            parsed.verify()
        with Image.open(io.BytesIO(image)) as parsed:
            parsed.load()
            if parsed.format != "PNG" or parsed.size != (row["width"], row["height"]):
                raise ValueError("PNG image cannot be parsed consistently")
    except (OSError, ValueError) as exc:
        raise ValueError("Historical overlay PNG cannot be parsed") from exc
    for alias, expected in (("filename", "sra_pilot_overlay.png"), ("sha256", digest(image)), ("bytes", len(image))):
        if alias in row and row[alias] != expected:
            raise ValueError("Historical overlay alias fields disagree")


def verify_bundle(directory, max_bytes=MAX_BYTES, check_name=True):
    directory = Path(directory)
    manifest_raw = read_bounded(directory / "manifest.json", 2 * 1024 * 1024)
    manifest = json.loads(manifest_raw)
    if not isinstance(manifest, dict):
        raise ValueError("Invalid bundle manifest schema")
    identifier = manifest.get("bundle_id")
    identity = {key: value for key, value in manifest.items() if key != "bundle_id"}
    if identifier != digest(canonical(identity)) or manifest.get("schema_version") != 1:
        raise ValueError("Bundle manifest identity changed")
    if check_name and directory.name != identifier:
        raise ValueError("Bundle directory name does not match its content identity")
    files = manifest.get("files", {})
    if not isinstance(files, dict):
        raise ValueError("Invalid bundle file schema")
    names = set(files)
    if not REQUIRED <= names or names - REQUIRED - OVERLAY or (names & OVERLAY and names & OVERLAY != OVERLAY):
        raise ValueError("Bundle contains an unsupported file list")
    expected = names | {"manifest.json"}
    actual = set()
    for path in directory.rglob("*"):
        relative = path.relative_to(directory).as_posix()
        if path.is_symlink() or (path.is_dir() and relative not in {"processed", "metadata"}):
            raise ValueError("Unsafe or unexpected bundle path")
        if path.is_file():
            actual.add(relative)
    if actual != expected:
        raise ValueError("Unexpected or missing bundle files")
    payloads, total = {}, 0
    for name, item in files.items():
        raw = read_bounded(safe_source(directory, name), max_bytes - total)
        total += len(raw)
        if len(raw) != item.get("bytes") or digest(raw) != item.get("sha256"):
            raise ValueError("Bundle file is missing or modified: " + name)
        payloads[name] = raw
    validate_snapshot(payloads["processed/urban_real.json"])
    validate_inventory(payloads["metadata/dataset_inventory.csv"])
    validate_overlay(payloads, manifest["validation"]["originals"], json.loads(payloads["processed/urban_real.json"])["metadata"].get("pilot_bbox"))
    for path in [directory, *directory.rglob("*")]:
        expected_mode = 0o755 if path.is_dir() else 0o644
        if stat.S_IMODE(path.stat().st_mode) != expected_mode:
            raise ValueError("Bundle requires 0755 public directories and 0644 public files")
    return manifest


def write_tar(directory, destination, names):
    with destination.open("xb") as stream:
        with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as archive:
                for name in ["metadata", "processed", *sorted(names)]:
                    path = directory / name
                    info = tarfile.TarInfo(name)
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ""
                    info.mode = 0o755 if path.is_dir() else 0o644
                    info.type = tarfile.DIRTYPE if path.is_dir() else tarfile.REGTYPE
                    info.size = 0 if path.is_dir() else path.stat().st_size
                    if path.is_dir():
                        archive.addfile(info)
                    else:
                        with path.open("rb") as source:
                            archive.addfile(info, source)
    destination.chmod(0o644)


def stage(data_root=ROOT / "data", output=ROOT / ".runtime/public-data-bundles", max_bytes=MAX_BYTES):
    data_root, output = Path(data_root), Path(output)
    if not 1 <= max_bytes <= MAX_BYTES:
        raise ValueError("Payload size limit must be between 1 byte and 64 MiB")
    if data_root.is_symlink() or any(path.is_symlink() for path in [output, *output.parents]) or output.resolve().is_relative_to(data_root.resolve()):
        raise ValueError("Staging output must be a separate, non-symlinked directory")
    payloads, total = {}, 0
    for name in sorted(REQUIRED | OVERLAY):
        path = safe_source(data_root, name)
        if name in OVERLAY and not path.exists():
            continue
        raw = read_bounded(path, min(max_bytes - total, 10_000_000 if name.endswith(".png") else max_bytes))
        total += len(raw)
        payloads[name] = raw
    counts = validate_snapshot(payloads["processed/urban_real.json"])
    inventory_count = validate_inventory(payloads["metadata/dataset_inventory.csv"])
    report_raw = read_bounded(safe_source(data_root, "metadata/validation.json"), 2 * 1024 * 1024)
    checked = validate_originals(data_root, report_raw, counts)
    validate_overlay(payloads, checked, json.loads(payloads["processed/urban_real.json"])["metadata"].get("pilot_bbox"))
    files = {name: {"bytes": len(raw), "sha256": digest(raw)} for name, raw in sorted(payloads.items())}
    identity = {"schema_version": 1, "purpose": "Acquired public source snapshot only; no operational records or raw originals",
                "data_dir": "/data/processed", "inventory_path": "/data/metadata/dataset_inventory.csv", "files": files,
                "validation": {"receipt_sha256": digest(report_raw), "snapshot_counts": counts, "inventory_rows": inventory_count, "originals": checked,
                               "boundary": "Local checksum, schema, geometry and original-geography checks; not field validation, government certification or a reuse licence"}}
    identifier = digest(canonical(identity))
    manifest = {**identity, "bundle_id": identifier}
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".stage.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        directory = output / identifier
        archive = output / (identifier + ".tar.gz")
        if directory.exists():
            if verify_bundle(directory, max_bytes) != manifest:
                raise ValueError("Existing content-addressed bundle differs; refusing to overwrite it")
        else:
            temporary = Path(tempfile.mkdtemp(prefix=".stage-", dir=output))
            try:
                temporary.chmod(0o755)
                for name, raw in {**payloads, "manifest.json": canonical(manifest)}.items():
                    path = temporary / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if path.parent != temporary:
                        path.parent.chmod(0o755)
                    with path.open("xb") as stream:
                        stream.write(raw)
                    path.chmod(0o644)
                verify_bundle(temporary, max_bytes, check_name=False)
                temporary.rename(directory)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
        temporary_archive = output / (".archive-" + identifier + ".tmp")
        if temporary_archive.exists():
            raise ValueError("Unfinished staging archive exists; inspect it before retrying")
        try:
            write_tar(directory, temporary_archive, set(files) | {"manifest.json"})
            archive_raw = read_bounded(temporary_archive, MAX_BYTES + 4 * 1024 * 1024)
            if archive.exists():
                if archive.is_symlink() or digest(read_bounded(archive, MAX_BYTES + 4 * 1024 * 1024)) != digest(archive_raw):
                    raise ValueError("Existing staging archive was modified; refusing to overwrite it")
            else:
                temporary_archive.rename(archive)
        finally:
            temporary_archive.unlink(missing_ok=True)
    return {"bundle_id": identifier, "directory": str(directory), "archive": str(archive), "archive_bytes": len(archive_raw),
            "archive_sha256": digest(archive_raw), "files": files, "snapshot_counts": counts, "originals_checked": len(checked)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=ROOT / ".runtime/public-data-bundles")
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    parser.add_argument("--verify", type=Path, help="Verify an existing bundle directory without accessing originals or writing files")
    args = parser.parse_args()
    try:
        result = verify_bundle(args.verify, args.max_bytes) if args.verify else stage(args.data_root, args.output, args.max_bytes)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise SystemExit("Public-data staging failed: " + str(exc)) from exc


if __name__ == "__main__":
    main()
