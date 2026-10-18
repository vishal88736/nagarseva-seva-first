"""Build an honest app snapshot from locally acquired, validated data only."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
from data_common import DATA, META, PROCESSED, ROOT, PILOT_BBOX, inventory, utcnow, validate_features, write_json

KEYS = ("water", "sanitation", "housing", "access", "risk")


def build():
    settlements = []
    pdfs = sorted((DATA / "raw/sra").glob("cluster-map-document-*.pdf"))
    if pdfs:
        # Select the manifest's active snapshot, not filename order when refreshed.
        manifest = json.loads((META / "sra_layers.json").read_text())
        request = manifest.get("cluster-map-document", {})
        path = ROOT / request["path"] if request.get("path") else pdfs[-1]
        text = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True, check=True, timeout=30).stdout
        if "GPS SURVEY 2024" not in text.upper() or "SLUM CLUSTER" not in text.upper():
            raise ValueError("Unexpected SRA map title; manual review required")
        labels = re.findall(r"\bME_\d{3}\b", text)
        identifiers = sorted(set(labels))
        extraction = {"source_url": request.get("url"), "raw_path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "retrieved_at": request.get("retrieved_at"), "reference_year": 2024, "reference_year_basis": "GPS Survey 2024 in map title; individual feature observation dates unknown",
                      "method": "Exact printed text tokens matching ME_[three digits]; unique labels, not a complete digital settlement registry",
                      "label_occurrences": len(labels), "unique_pilot_labels": len(identifiers), "geometries": 0,
                      "limitations": "No georeferencing or boundary digitisation; missing map text is not evidence of settlement absence; names unavailable; no current administrative crosswalk"}
        write_json(META / "sra_pdf_extraction.json", extraction)
        for identifier in identifiers:
            settlements.append({"id": "sra-map-" + identifier, "source_id": identifier, "name": "Map label " + identifier,
                                "geometry": None, "administrative_area": "M/E map-prefix context; current ward crosswalk unverified",
                                "source": request.get("url"), "source_date": "2024", "source_date_basis": extraction["reference_year_basis"],
                                "retrieved_at": request.get("retrieved_at"), "synthetic": False, "record_type": "printed_map_label",
                                "data_completeness": 0, "indicators": {key: None for key in KEYS}, "households": None,
                                "limitations": [extraction["limitations"]]})
        inventory(dataset_name="SRA GPS Survey 2024 map: M/E printed labels", publisher="SRA Mumbai / DSLR GIS Cell", source_url=request.get("url"),
                  retrieved_at=request.get("retrieved_at"), observation_date="2024 per document title; per-cluster dates unavailable", publication_date="PDF creation metadata 2024-05-30; publication date unknown",
                  geography="M/E prefix labels in Greater Mumbai map", resolution="Printed map identifier; no machine-readable geometry", format="PDF -> exact text labels", record_count=len(identifiers),
                  fields=["source_id", "map_title", "reference_year", "source_url"], licence="Not established; local research only pending reuse review", access_status="downloaded",
                  validation_status="PDF signature, text/title, unique identifiers and rendered overview checked; no geometry validation possible", intended_use="Source-labelled settlement lookup and data-collection planning",
                  limitations=extraction["limitations"])
        inventory(dataset_name="SRA cluster-map-document", publisher="SRA Mumbai", source_url=request.get("url"), retrieved_at=request.get("retrieved_at"),
                  observation_date="2024 map title", publication_date="Publication unknown; PDF created 2024-05-30", geography="Greater Mumbai", resolution="1:40000 map; not imported vector polygons",
                  format="PDF", record_count=1, fields="Map title, legend, printed cluster labels", licence="Not established", access_status="downloaded",
                  validation_status="Parsed with pdftotext and rendered for visual inspection", intended_use="Reference document and label extraction", limitations="PDF map is not a georeferenced GIS dataset; no digitised geometries")
    # Prefer an acquired vector cluster layer over PDF-only records, without merging vintages.
    sra_path = META / "sra_ingestion.json"
    if sra_path.exists():
        layers = json.loads(sra_path.read_text()).get("layers", [])
        candidates = sorted((row for row in layers if "cluster" in row["layer"]["name"].lower()), key=lambda row: row["layer"]["name"], reverse=True)
        if candidates:
            layer = candidates[0]
            features = json.loads(Path(layer["path"]).read_text())
            if not validate_features(features, layer["layer"]["object_id_field"])["valid"]:
                raise ValueError("SRA active layer validation failed")
            settlements = []
            for f in features["features"]:
                source_id = str(f["properties"][layer["layer"]["object_id_field"]])
                settlements.append({"id": f"sra-layer-{layer['layer']['id']}-{source_id}", "source_id": source_id,
                                    "name": str(f["properties"].get("name") or f["properties"].get("slum_name") or "Source feature " + source_id),
                                    "geometry": f["geometry"], "administrative_area": None, "source": layer["request"]["url"], "source_date": None,
                                    "source_date_basis": "Layer version: " + layer["layer"]["name"] + "; individual observation date unknown", "retrieved_at": layer["request"]["retrieved_at"],
                                    "synthetic": False, "record_type": "source_polygon", "data_completeness": 0,
                                    "indicators": {key: None for key in KEYS}, "households": None, "limitations": ["Layer currency and reuse terms require confirmation; not legal recognition"]})
    projects_path = PROCESSED / "sra_projects.json"
    projects = json.loads(projects_path.read_text())["records"] if projects_path.exists() else []
    osm_path = PROCESSED / "osm_pilot.geojson"
    osm = json.loads(osm_path.read_text()) if osm_path.exists() else {"type": "FeatureCollection", "features": []}
    if not validate_features(osm)["valid"]:
        raise ValueError("OSM snapshot validation failed")
    # Real observations require a reviewed geography adapter; no current cluster measurements acquired.
    indicators = []
    metadata = {"title": "UrbanSaarthi acquired public data", "built_at": utcnow(), "synthetic": False, "pilot_bbox": PILOT_BBOX,
                "geographic_scope": "Govandi bounded OSM context; M/E printed map labels; Mumbai SRA first-page scheme facts",
                "settlement_record_type": settlements[0]["record_type"] if settlements else "none",
                "settlement_count": len(settlements), "settlement_geometry_count": sum(s["geometry"] is not None for s in settlements),
                "projects_count": len(projects), "mapped_objects_count": len(osm["features"]),
                "mapped_object_categories": dict(Counter(f["properties"]["category"] for f in osm["features"])),
                "real_pilot_approved": False, "licence": "Source-specific; SRA reuse rights not established; OSM ODbL-1.0",
                "limitations": ["No current cluster water, sanitation, drainage, housing or risk baseline acquired.", "Historical source dates remain historical. No Census values assigned to clusters.",
                                "Printed labels have no acquired geometry; they are not geocoded using names or CTS strings.", "Mapped objects do not establish facility operation or reliable household access.",
                                "Projects are first-page published facts with unknown phase and no defensible settlement join."]}
    write_json(PROCESSED / "urban_real.json", {"metadata": metadata, "settlements": settlements, "projects": projects, "indicators": indicators, "spatial": osm})
    print(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    build()
