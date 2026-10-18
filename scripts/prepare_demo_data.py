"""Validate the existing separate synthetic sandbox; never overwrite real data."""
import json
from data_common import ROOT, META, validate_features, write_json


def prepare():
    path = ROOT / "nagarseva/shared/urban-demo.json"
    data = json.loads(path.read_text())
    if not data["metadata"]["synthetic"] or not all(c["synthetic"] for c in data["clusters"]):
        raise ValueError("All sandbox records must be explicitly synthetic")
    collection = {"type": "FeatureCollection", "features": [{"type": "Feature", "id": c["id"], "properties": {}, "geometry": c["geometry"]} for c in data["clusters"]]}
    report = validate_features(collection, expected_types={"Polygon", "MultiPolygon"})
    if not report["valid"]:
        raise ValueError("Demo geometry validation failed")
    write_json(META / "demo_validation.json", {"path": str(path.relative_to(ROOT)), "synthetic": True, **report})
    print("Separate synthetic sandbox:", report["record_count"], "valid polygons")


if __name__ == "__main__":
    prepare()
