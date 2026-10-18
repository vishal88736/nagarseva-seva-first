"""Inspect actual public ArcGIS metadata; never infer IDs from historic listings."""
from __future__ import annotations
import argparse
import subprocess
from data_common import Downloader, DownloadError, META, ROOT, inventory, utcnow, write_json

MAP_URL = "https://umd.nic.in/sramap/rest/services/SRA/SRAMumbai/MapServer"
FEATURE_URL = MAP_URL.replace("MapServer", "FeatureServer")
GIS_URL = "https://sra.gov.in/details/sub-category/gis-mis-slum-data"
PDF_URL = "https://media.sra.gov.in/sra-automation/category/docs/1731408978437_4524_slum_cluster_ca_2024%20%281%29.pdf"


def inspect(refresh=False, base_url=MAP_URL):
    downloader = Downloader("sra", refresh)
    report = {"attempted_at": utcnow(), "service_url": base_url, "layers": [], "errors": [], "licence": "Not established; public access does not establish redistribution rights"}
    try:
        meta, request = downloader.json(base_url, "mapserver", {"f": "pjson"})
        report.update(service_metadata=meta, request=request)
        layers, layer_request = downloader.json(base_url + "/layers", "mapserver-layers", {"f": "pjson"})
        if not isinstance(layers.get("layers"), list):
            raise DownloadError("Missing layers array in service metadata")
        for layer in layers["layers"]:
            fields = layer.get("fields", [])
            oid = layer.get("objectIdField") or next((f["name"] for f in fields if f["type"] == "esriFieldTypeOID"), None)
            row = {"id": layer["id"], "name": layer["name"], "geometry_type": layer.get("geometryType"),
                   "fields": fields, "object_id_field": oid, "spatial_reference": layer.get("extent", {}).get("spatialReference", meta.get("spatialReference")),
                   "query_formats": layer.get("supportedQueryFormats", meta.get("supportedQueryFormats")),
                   "capabilities": layer.get("capabilities"), "max_record_count": layer.get("maxRecordCount", meta.get("maxRecordCount", 1000)),
                   "pagination": layer.get("advancedQueryCapabilities", {}).get("supportsPagination", False),
                   "editing_info": layer.get("editingInfo"), "description": layer.get("description")}
            if oid and layer.get("geometryType"):
                try:
                    count, _ = downloader.json(f"{base_url}/{layer['id']}/query", f"layer-{layer['id']}-count", {"f": "json", "where": "1=1", "returnCountOnly": "true"})
                    if not isinstance(count.get("count"), int):
                        raise DownloadError("Count query did not return a count")
                    row.update(query_supported=True, service_record_count=count["count"])
                except DownloadError as exc:
                    row.update(query_supported=False, query_error=str(exc))
            report["layers"].append(row)
        inventory(dataset_name="SRA GIS service metadata", publisher="SRA / NIC", source_url=base_url,
                  retrieved_at=request["retrieved_at"], geography="Mumbai service extent", resolution="Layer-specific",
                  format="ArcGIS JSON", record_count=len(report["layers"]), fields=["id", "name", "geometryType", "fields", "spatialReference"],
                  licence=report["licence"], access_status="metadata_only", validation_status="parsed actual service and layer metadata",
                  intended_use="Discover supported feature queries", limitations="Accessibility is not evidence of currency")
    except DownloadError as exc:
        report["errors"].append(str(exc))
        inventory(dataset_name="SRA GIS service metadata", publisher="SRA / NIC", source_url=base_url, retrieved_at=utcnow(),
                  access_status="failed", validation_status="No live layer metadata retrieved", intended_use="Settlement boundaries and GIS", limitations=str(exc))
    # Test the separately advertised FeatureServer endpoint independently.
    try:
        features, info = downloader.json(FEATURE_URL + "/layers", "featureserver-layers", {"f": "pjson"})
        report["feature_server"] = {"request": info, "metadata": features}
    except DownloadError as exc:
        report["errors"].append("FeatureServer: " + str(exc))
    for key, url, suffix in (("gis-page", GIS_URL, ".html"), ("cluster-map-document", PDF_URL, ".pdf")):
        try:
            raw, info = downloader.fetch(url, key, suffix=suffix)
            if suffix == ".pdf" and not raw.startswith(b"%PDF-"):
                raise DownloadError("Advertised PDF is not a PDF response")
            if suffix == ".pdf":
                parsed = subprocess.run(["pdftotext", str(ROOT / info["path"]), "-"], capture_output=True, text=True, timeout=30, check=True).stdout
                if "SLUM CLUSTER" not in parsed.upper():
                    raise DownloadError("PDF did not contain the expected map text")
            report[key] = info
            inventory(dataset_name="SRA " + key, publisher="SRA", source_url=url, retrieved_at=info["retrieved_at"],
                      geography="Mumbai", format=suffix[1:], access_status="downloaded",
                      validation_status="HTML parsed as text" if suffix == ".html" else "PDF signature and extracted title text checked; map is not a vector GIS export",
                      intended_use="Source context", licence="Not established", limitations="PDF boundaries are not machine-readable vector data")
        except (DownloadError, subprocess.SubprocessError, FileNotFoundError) as exc:
            inventory(dataset_name="SRA " + key, publisher="SRA", source_url=url, retrieved_at=utcnow(), access_status="failed", validation_status="not parsed", limitations=str(exc))
    write_json(META / "sra_layers.json", report)
    downloader.close()
    print(f"SRA: {len(report['layers'])} live layers; {len(report['errors'])} service errors")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    inspect(parser.parse_args().refresh)
