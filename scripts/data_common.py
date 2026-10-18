"""Bounded public downloads, immutable originals, provenance and GIS validation."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

import httpx
from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform
from shapely.validation import explain_validity

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
META = DATA / "metadata"
PROCESSED = DATA / "processed"
INVENTORY_FIELDS = "dataset_name publisher source_url retrieved_at observation_date publication_date geography resolution format record_count fields licence access_status validation_status intended_use limitations".split()
PILOT_BBOX = (72.90, 19.04, 72.94, 19.08)  # Govandi / M-East context; not a ward boundary


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False, encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, allow_nan=False, indent=2)
        name = f.name
    os.replace(name, path)


class DownloadError(ValueError):
    pass


class Downloader:
    """Reuse a checksum-verified cache; --refresh creates a new dated snapshot.

    Raw response bytes are content addressed and never overwritten. Failures never
    replace a successful cache entry. No credentials/cookies or TLS overrides.
    """
    def __init__(self, source, refresh=False, transport=None, max_bytes=25_000_000):
        self.source, self.refresh, self.max_bytes = source, refresh, max_bytes
        self.raw = DATA / "raw" / source
        self.raw.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(timeout=httpx.Timeout(35, connect=10), follow_redirects=True,
                                   headers={"User-Agent": "UrbanSaarthiResearch/1.0 (public data pilot; bounded requests)"},
                                   transport=transport)

    def close(self):
        self.client.close()

    def fetch(self, url, key, params=None, method="GET", form=None, suffix=".json"):
        if not url.startswith("https://"):
            raise DownloadError("Only HTTPS public sources are supported")
        identity = hashlib.sha256(json.dumps([url, params, method, form], sort_keys=True).encode()).hexdigest()[:16]
        entry = META / "requests" / f"{self.source}-{key}-{identity}.json"
        cached = json.loads(entry.read_text()) if entry.exists() else None
        if cached and not self.refresh and cached.get("path"):
            path = ROOT / cached["path"]
            if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == cached["sha256"]:
                return path.read_bytes(), cached
            raise DownloadError("Cached original is missing or modified; use --refresh to reacquire")
        info = {"url": url, "params": params, "method": method, "retrieved_at": utcnow()}
        try:
            with self.client.stream(method, url, params=params, data=form) as response:
                info.update(http_status=response.status_code, final_url=str(response.url),
                            content_type=response.headers.get("content-type"), last_modified=response.headers.get("last-modified"))
                response.raise_for_status()
                if int(response.headers.get("content-length") or 0) > self.max_bytes:
                    raise DownloadError("Response exceeds download size limit")
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise DownloadError("Response exceeds download size limit")
                    chunks.append(chunk)
            raw = b"".join(chunks)
            if not raw.strip():
                raise DownloadError("Empty response")
            sha = hashlib.sha256(raw).hexdigest()
            path = self.raw / f"{key}-{sha[:16]}{suffix}"
            if not path.exists():
                with path.open("xb") as file:
                    file.write(raw)
            info.update(path=str(path.relative_to(ROOT)), sha256=sha, bytes=size, access_status="downloaded")
            if cached and cached != info:
                write_json(entry.with_name(entry.stem + "-" + hashlib.sha256(json.dumps(cached, sort_keys=True).encode()).hexdigest()[:12] + ".json"), cached)
            write_json(entry, info)
            return raw, info
        except (httpx.HTTPError, ValueError, OSError) as exc:
            info.update(access_status="authentication_required" if info.get("http_status") in (401, 403) else "failed",
                        error=f"{type(exc).__name__}: {exc}")
            # Separate failure log; retain last successful request.
            write_json(entry.with_name(entry.stem + "-failure.json"), info)
            raise DownloadError(info["error"]) from exc

    def json(self, url, key, params=None, method="GET", form=None):
        raw, info = self.fetch(url, key, params, method, form)
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise DownloadError("Expected JSON; response was not parseable JSON") from exc
        if not isinstance(data, dict) or data.get("error"):
            raise DownloadError(f"Source returned error: {data.get('error') if isinstance(data, dict) else 'not an object'}")
        return data, info


def inventory(**row):
    """Replace only this pipeline's named row, serializing concurrent source tasks."""
    path = ROOT / "research/dataset_inventory.csv"
    path.parent.mkdir(exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    with (META / "inventory.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old = list(csv.DictReader(path.open())) if path.exists() else []
        if old and set(old[0]) != set(INVENTORY_FIELDS):
            legacy = path.with_name("dataset_inventory_legacy.csv")
            if not legacy.exists():
                legacy.write_bytes(path.read_bytes())
            old = []
        row = {key: row.get(key, "") for key in INVENTORY_FIELDS}
        for key in ("fields", "limitations"):
            if isinstance(row[key], (list, dict)):
                row[key] = json.dumps(row[key], ensure_ascii=False)
        old = [item for item in old if item["dataset_name"] != row["dataset_name"]] + [row]
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False, newline="") as out:
            writer = csv.DictWriter(out, fieldnames=INVENTORY_FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(sorted(old, key=lambda item: item["dataset_name"]))
            name = out.name
        os.replace(name, path)


def validate_features(collection, id_field=None, expected_types=None):
    if not isinstance(collection, dict) or collection.get("type") != "FeatureCollection" or not isinstance(collection.get("features"), list):
        raise ValueError("Expected a GeoJSON FeatureCollection")
    # GeoJSON is WGS84. A declared conflicting CRS must be transformed explicitly.
    crs = collection.get("crs", {}).get("properties", {}).get("name", "EPSG:4326")
    if crs not in ("EPSG:4326", "urn:ogc:def:crs:OGC:1.3:CRS84", "urn:ogc:def:crs:EPSG::4326"):
        raise ValueError(f"Expected WGS84 GeoJSON, got {crs}")
    seen, problems, fields, missing = set(), [], set(), {}
    geometries = 0
    for index, feature in enumerate(collection["features"]):
        props = feature.get("properties")
        if not isinstance(props, dict):
            problems.append({"row": index, "error": "Missing property object"})
            continue
        fields.update(props)
        identifier = props.get(id_field) if id_field else feature.get("id", props.get("source_id"))
        if identifier is None or str(identifier) in seen:
            problems.append({"row": index, "error": "Missing or duplicate identifier", "id": identifier})
        seen.add(str(identifier))
        for key, value in props.items():
            if value is None or value == "":
                missing[key] = missing.get(key, 0) + 1
        try:
            geom = shape(feature.get("geometry"))
            if geom.is_empty or not geom.is_valid:
                raise ValueError(explain_validity(geom))
            if expected_types and geom.geom_type not in expected_types:
                raise ValueError("Unexpected geometry type: " + geom.geom_type)
            x1, y1, x2, y2 = geom.bounds
            if not (-180 <= x1 <= x2 <= 180 and -90 <= y1 <= y2 <= 90):
                raise ValueError("Coordinates outside WGS84 bounds")
            geometries += 1
        except (ValueError, TypeError, AttributeError) as exc:
            problems.append({"row": index, "id": identifier, "error": str(exc)})
    return {"record_count": len(collection["features"]), "valid_geometry_count": geometries,
            "unique_id_count": len(seen), "fields": sorted(fields), "null_or_blank_counts": missing,
            "crs": "EPSG:4326", "errors": problems, "valid": not problems}


def reproject_geometry(geometry, source_crs, target_crs="EPSG:4326"):
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    return mapping(transform(transformer.transform, shape(geometry)))


def strict_spatial_join(features, units, unit_id="id"):
    """Whole geometry containment only. Ambiguous/border-crossing features stay null."""
    result = []
    for feature in features:
        geom = shape(feature["geometry"])
        matches = [unit["properties"][unit_id] for unit in units if shape(unit["geometry"]).covers(geom)]
        result.append({"source_id": feature.get("id", feature["properties"].get("source_id")),
                       "unit_id": matches[0] if len(matches) == 1 else None,
                       "method": "whole_geometry_covered_by_unique_unit", "matches": len(matches)})
    return result
