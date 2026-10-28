"""Validate supplied 2015 boundaries and stage a display-only static reference layer.

No download, geometry repair, identifier recovery or join is performed. The exact
supplied GeoJSON is retained; a checksum-bound manifest lists excluded source rows.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import shapely
from shapely.geometry import shape
from shapely.validation import explain_validity

ROOT = Path(__file__).resolve().parents[1]
BASENAME = "mumbai_slum_clusters_2015"
MAX_BYTES = 10 * 1024 * 1024


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def preserve(path, raw):
    """Never overwrite a different source or staged asset."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError(f"Existing file differs; preserve it and choose another output directory: {path.name}")
    else:
        path.write_bytes(raw)


def inspect(raw):
    if not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("Boundary file must be nonempty and at most 10 MiB")
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        raise ValueError("Expected a GeoJSON FeatureCollection")
    features = data["features"]
    if not 0 < len(features) <= 10000 or data.get("crs"):
        raise ValueError("Expected 1-10000 features in WGS84 longitude/latitude GeoJSON")
    invalid, fields, positions, bounds, polyno = [], Counter(), 0, [], []
    for index, feature in enumerate(features, 1):
        try:
            if not isinstance(feature, dict) or feature.get("type") != "Feature" or not isinstance(feature.get("properties"), dict):
                raise ValueError("Expected Feature properties")
            geometry = feature.get("geometry")
            if not isinstance(geometry, dict) or geometry.get("type") != "Polygon":
                raise ValueError("Expected Polygon geometry")
            fields.update(feature["properties"].keys())
            polyno.append(feature["properties"].get("polyno"))
            rings = geometry.get("coordinates")
            if not isinstance(rings, list) or not rings:
                raise ValueError("Empty coordinates")
            for ring in rings:
                if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
                    raise ValueError("Unclosed or incomplete ring")
                for xy in ring:
                    if not isinstance(xy, list) or len(xy) not in (2, 3) or any(type(value) not in (int, float) or not math.isfinite(value) for value in xy):
                        raise ValueError("Invalid position")
                    if not (72.5 <= xy[0] <= 73.5 and 18.5 <= xy[1] <= 19.6):
                        raise ValueError("Position outside expected Mumbai longitude/latitude extent")
                    bounds.append(xy[:2]); positions += 1
            polygon = shape(geometry)
            if polygon.is_empty or not polygon.is_valid:
                raise ValueError(explain_validity(polygon))
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            invalid.append({"source_feature_number": index, "reason": str(exc)})
    if len(invalid) == len(features):
        raise ValueError("No valid reference polygons")
    return {
        "source_feature_count": len(features), "valid_feature_count": len(features) - len(invalid),
        "excluded_features": invalid, "coordinate_count": positions,
        "bounds": [min(xy[0] for xy in bounds), min(xy[1] for xy in bounds), max(xy[0] for xy in bounds), max(xy[1] for xy in bounds)],
        "fields": sorted(fields), "polyno_non_null_count": sum(value is not None for value in polyno),
        "topology_validator": "Shapely " + shapely.__version__,
    }


def stage(source_dir, output_dir, raw_dir):
    source_dir, output_dir, raw_dir = map(Path, (source_dir, output_dir, raw_dir))
    raw = (source_dir / (BASENAME + ".geojson")).read_bytes()
    quality = inspect(raw)
    resource_raw = (source_dir / "resource.json").read_bytes()
    resource = json.loads(resource_raw)["result"]
    if resource.get("name") != "Mumbai - Slum Clusters Map 2015":
        raise ValueError("Unexpected supplied resource metadata")
    kml_raw = (source_dir / (BASENAME + ".kml")).read_bytes()
    if len(kml_raw) > MAX_BYTES:
        raise ValueError("KML exceeds staging limit")
    # A local receipt timestamp is not a historical observation/download date.
    manifest = {
        "schema_version": 1, "id": "mumbai-slum-reference-2015", "reference_year": 2015,
        "record_type": "historical_reference_boundaries", "crs": "EPSG:4326", "analysis_allowed": False,
        "source_url": resource["url"], "source_catalog_url": "https://data.opencity.in/dataset/" + resource["package_id"] + "/resource/" + resource["id"],
        "publisher": "SRA Mumbai (as attributed by the supplied OpenCity catalogue metadata)",
        "source_attribution_key": "SRA Mumbai, via OpenCity (catalogue attribution)",
        "retrieved_at": None, "publication_date": None,
        "catalogue_modified_at": resource.get("last_modified"),
        "licence_claim": resource.get("license_id"), "licence_basis": "Supplied OpenCity catalogue claim; not an independently verified SRA licence",
        "sha256": digest(raw), "bytes": len(raw), "kml_sha256": digest(kml_raw), "kml_bytes": len(kml_raw),
        "staged_at": datetime.now(timezone.utc).isoformat(),
        "limitations": ["Historical reference boundaries — 2015. Not verified against the 2024 SRA cluster list.",
                        "No verified settlement names, SRA cluster IDs, ward IDs or village IDs in the supplied GeoJSON.",
                        "These boundaries do not establish current conditions, housing eligibility, redevelopment progress or service coverage.",
                        "No match to 2024 records or Census aggregates; polyno is only a technical source reference when present.",
                        "Topology-invalid source polygons are excluded without repair; original coordinates and attributes are retained."],
        **quality,
    }
    # Archive exact supplied bytes separately from public/static geometry.
    for name, content in ((BASENAME + ".geojson", raw), (BASENAME + ".kml", kml_raw), ("resource.json", resource_raw)):
        preserve(raw_dir / (digest(content)[:16] + "-" + name), content)
    target = output_dir / (BASENAME + ".geojson")
    manifest_path = output_dir / (BASENAME + ".metadata.json")
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        if previous.get("sha256") != manifest["sha256"]:
            raise ValueError("Existing boundary manifest refers to different input; choose another output directory")
        # Same bytes and validation are idempotent, including the first receipt time.
        manifest["staged_at"] = previous["staged_at"]
    manifest_raw = (json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    preserve(target, raw); preserve(manifest_path, manifest_raw)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=Path.home() / "UrbanSaarthi/data/boundaries")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "nagarseva/website/public/data")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw/sra/boundaries-2015")
    args = parser.parse_args()
    result = stage(args.source_dir, args.output_dir, args.raw_dir)
    print(json.dumps({key: result[key] for key in ("source_feature_count", "valid_feature_count", "coordinate_count", "polyno_non_null_count", "sha256", "bounds")}, indent=2))


if __name__ == "__main__":
    main()
