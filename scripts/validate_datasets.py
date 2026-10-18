"""Audit acquired originals, counts, schemas and geometries; write actual results."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import sys
from data_common import META, PROCESSED, ROOT, strict_spatial_join, utcnow, validate_features, write_json


def validate():
    report = {"checked_at": utcnow(), "errors": [], "downloads": [], "datasets": {}}
    for path in sorted((META / "requests").glob("*.json")):
        info = json.loads(path.read_text())
        if not info.get("path"):
            continue
        raw = ROOT / info["path"]
        valid = raw.is_file() and hashlib.sha256(raw.read_bytes()).hexdigest() == info["sha256"]
        report["downloads"].append({"path": info["path"], "url": info["url"], "bytes": info["bytes"], "sha256": info["sha256"], "retrieved_at": info["retrieved_at"], "checksum_valid": valid})
        if not valid:
            report["errors"].append("Missing or modified original: " + info["path"])
    for path in sorted(PROCESSED.glob("*.geojson")):
        quality = validate_features(json.loads(path.read_text()))
        report["datasets"][path.name] = quality
        if not quality["valid"]:
            report["errors"].append(path.name + ": geometry/ID validation failed")
    snapshot = PROCESSED / "urban_real.json"
    if snapshot.exists():
        data = json.loads(snapshot.read_text())
        for table in ("settlements", "projects", "indicators"):
            rows = data[table]
            if len({r["id"] for r in rows}) != len(rows):
                report["errors"].append("Duplicate snapshot IDs in " + table)
            report["datasets"][table] = {"record_count": len(rows), "fields": sorted(set(k for row in rows for k in row))}
        report["datasets"]["settlements"]["geometry_count"] = sum(r["geometry"] is not None for r in data["settlements"])
        report["datasets"]["projects"]["reliably_joined_count"] = sum(p["settlement_id"] is not None for p in data["projects"])
        report["datasets"]["projects"]["status_counts"] = dict(Counter(p["project_status"] for p in data["projects"]))
        report["datasets"]["projects"]["source_fields"] = sorted({k for p in data["projects"] for k in p.get("source_attributes", {})})
        report["datasets"]["projects"]["blank_or_dash_source_counts"] = dict(Counter(k for p in data["projects"] for k, value in p.get("source_attributes", {}).items() if value in (None, "", "-")))
        if any(r.get("synthetic") is not False for r in data["settlements"] + data["projects"]):
            report["errors"].append("Unlabelled or synthetic records in acquired snapshot")
        osm = data["spatial"]["features"]
        report["osm_category_counts"] = dict(Counter(f["properties"]["category"] for f in osm))
        report["osm_amenity_tags"] = dict(Counter(f["properties"]["tags"].get("amenity") for f in osm if f["properties"]["tags"].get("amenity")))
        # Context-only QA join: exact, unique containment; never an SRA/household join.
        units = [f for f in osm if f["properties"]["category"] == "residential_context" and f["geometry"]["type"] in ("Polygon", "MultiPolygon")]
        for f in units:
            f["properties"]["id"] = f["id"]
        amenities = [f for f in osm if f["properties"]["category"] in ("amenity", "transport", "water_infrastructure")]
        joined = strict_spatial_join(amenities, units)
        report["context_join"] = {"method": "Whole geometry covered by exactly one mapped OSM residential polygon; no SRA or Census allocation", "input_count": len(joined),
                                  "unique_matches": sum(r["unit_id"] is not None for r in joined), "unmatched_or_ambiguous": sum(r["unit_id"] is None for r in joined)}
        write_json(PROCESSED / "osm_residential_context_join.json", {"metadata": report["context_join"], "rows": joined})
    report["valid"] = not report["errors"]
    write_json(META / "validation.json", report)
    # A portable manifest contains no raw source data, private records or secrets.
    write_json(ROOT / "research/acquisition_results.json", report)
    inventory_path = ROOT / "research/dataset_inventory.csv"
    if inventory_path.exists():
        (META / "dataset_inventory.csv").write_bytes(inventory_path.read_bytes())
    print(json.dumps({"valid": report["valid"], "downloads_checked": len(report["downloads"]), "osm_category_counts": report.get("osm_category_counts"), "context_join": report.get("context_join"), "errors": report["errors"]}, indent=2))
    return report


if __name__ == "__main__":
    sys.exit(0 if validate()["valid"] else 1)
