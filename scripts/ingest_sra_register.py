"""Extract the official 2024 cluster register without inventing map geometries.

The PDF is a printed table, not a vector GIS export. Poppler word coordinates
keep the area column distinct when long names overlap it in the source PDF.
"""
from __future__ import annotations

import argparse
from collections import Counter
import math
import re
import subprocess
import xml.etree.ElementTree as ET

from data_common import Downloader, DownloadError, META, PROCESSED, ROOT, inventory, utcnow, write_json

REGISTER_URL = "https://media.sra.gov.in/sra-automation/sra-website/content/1731566774802_3204_Slum%20Cluster%202024.pdf"
FIELDS = ["Sr.no", "Cluster_ID", "Ward", "Village_Division", "Taluka", "Slum_Name", "Shape_Area (Sq.mtrs)"]


def parse_register_xml(text, retrieved_at, source_url=REGISTER_URL):
    """Parse only the verified seven-column PDF layout; reject incomplete rows.

    Column limits are derived from this document's observed print layout and
    validated against repeated header positions on every page. A changed layout
    requires review, rather than shifting cells into a plausible but wrong field.
    """
    root = ET.fromstring(text)
    pages = root.findall(".//{*}page")
    if not pages:
        raise ValueError("Register PDF has no word-coordinate pages")
    records, source_ids, serials = [], set(), set()
    for page_number, page in enumerate(pages, 1):
        words = [(word.text or "", float(word.attrib["xMin"]), float(word.attrib["xMax"]), float(word.attrib["yMin"])) for word in page.findall(".//{*}word")]
        page_text = " ".join(word[0] for word in words)
        if not all(label in page_text for label in ("CLUSTER", "2024", "Cluster_ID", "Village_Division", "Slum_Name", "Shape_Area")):
            raise ValueError(f"Missing expected register title/header on page {page_number}")
        header = {word[0]: word[1] for word in words if word[0] in ("Cluster_ID", "Ward", "Taluka", "Slum_Name")}
        if any(abs(header.get(label, -1000) - x) > 3 for label, x in (("Cluster_ID", 123.3), ("Ward", 188.8), ("Taluka", 358.4), ("Slum_Name", 456.4))):
            raise ValueError("Register column coordinates changed; manual review required")
        # Source serials define row baselines; group neighbouring words by y.
        anchors = [(int(word), y) for word, x, _, y in words if x < 112 and y > 130 and re.fullmatch(r"\d+", word)]
        if not anchors:
            raise ValueError(f"Register page {page_number} has no numbered rows")
        for serial, y in anchors:
            cells = [[] for _ in range(6)]
            for word, x, xmax, wy in sorted(words, key=lambda row: row[1]):
                if abs(wy - y) > 1:
                    continue
                column = next((i for i, limit in enumerate((115, 178, 221, 339, 407)) if x < limit), 5)
                cells[column].append((word, x, xmax))
            leading = [" ".join(word[0] for word in cell) for cell in cells[:5]]
            if leading[0] != str(serial) or not re.fullmatch(r"[A-Z]{1,3}_\d{3}[A-Z]?", leading[1]):
                raise ValueError(f"Invalid source identity on page {page_number}, serial {serial}")
            if any(not value for value in leading[2:]):
                raise ValueError(f"Missing administrative column on serial {serial}")
            name_parts, area_candidates, overflow = [], [], False
            for word, x, xmax in cells[5]:
                area = re.search(r"(\d+\.\d{2})$", word) if x > 550 else None
                if area:
                    area_candidates.append(float(area[1]))
                    word = word[:area.start()]
                if word:
                    name_parts.append(word)
                    overflow = overflow or xmax > 556
            if len(area_candidates) != 1 or not math.isfinite(area_candidates[0]) or area_candidates[0] <= 0:
                raise ValueError(f"Missing or ambiguous printed area on serial {serial}")
            name_raw = " ".join(name_parts).strip()
            if not name_raw:
                raise ValueError(f"Missing name cell on serial {serial}")
            source_id = leading[1]
            if serial in serials:
                raise ValueError("Duplicate register serial")
            serials.add(serial)
            source_ids.add(source_id)
            records.append({"id": "sra-map-" + source_id, "source_id": source_id,
                            "name": None if name_raw == "<Null>" else name_raw, "name_raw": name_raw,
                            "administrative_area": leading[2], "ward": leading[2], "village": leading[3], "taluka": leading[4],
                            "shape_area_sq_m": area_candidates[0], "source_serial": serial, "source_page": page_number,
                            "name_overflow_in_source": overflow, "geometry": None, "source": source_url, "source_url": source_url,
                            "source_date": "2024", "source_date_basis": "SLUM CLUSTER LIST 2024 document title; individual observation dates unknown",
                            "retrieved_at": retrieved_at, "synthetic": False, "record_type": "published_cluster_register",
                            "limitations": ["Historical published register; individual observation date, legal status and current boundaries not established",
                                            "Printed area is an attribute; no polygon is acquired or reconstructed"] +
                                           (["Long name overlaps the area column in the source PDF; underlying text retained, verify spelling against original"] if overflow else [])})
    records.sort(key=lambda row: row["source_serial"])
    if serials != set(range(1, len(records) + 1)):
        raise ValueError("Register serial sequence is incomplete")
    counts = Counter(row["source_id"] for row in records)
    duplicates = {source_id: count for source_id, count in counts.items() if count > 1}
    # Preserve source defects visibly. Ambiguous published IDs must not collapse
    # into one settlement or participate in an identifier join.
    for row in records:
        row["source_id_unique"] = counts[row["source_id"]] == 1
        if not row["source_id_unique"]:
            row["id"] = f"sra-register-{row['source_id']}-row-{row['source_serial']}"
            row["limitations"].append("Duplicate Cluster_ID in published register; source-row-specific local identity; excluded from identifier joins")
    return records, {"record_count": len(records), "unique_source_ids": len(source_ids), "pages": len(pages),
                     "duplicate_source_ids": duplicates, "duplicate_source_id_rows": sum(duplicates.values()),
                     "missing_name_count": sum(row["name"] is None for row in records),
                     "name_overflow_count": sum(row["name_overflow_in_source"] for row in records),
                     "ward_counts": dict(Counter(row["ward"] for row in records)), "valid_geometry_count": 0,
                     "method": "Poppler word-coordinate extraction; validated repeated header positions, consecutive serials, official IDs, administrative cells and one positive decimal area per row"}


def ingest(refresh=False):
    downloader = Downloader("sra", refresh)
    report = {"attempted_at": utcnow(), "errors": []}
    try:
        raw, info = downloader.fetch(REGISTER_URL, "cluster-list-2024", suffix=".pdf")
        if not raw.startswith(b"%PDF-"):
            raise ValueError("Register download is not a PDF")
        from pypdf import PdfReader
        pdf = PdfReader(ROOT / info["path"])
        created = pdf.metadata.creation_date if pdf.metadata else None
        xml = subprocess.run(["pdftotext", "-bbox-layout", str(ROOT / info["path"]), "-"], capture_output=True, text=True, check=True, timeout=60).stdout
        records, quality = parse_register_xml(xml, info["retrieved_at"])
        report.update(quality=quality, request=info)
        extraction_path = META / "sra_pdf_extraction.json"
        if extraction_path.exists():
            import json
            extraction = json.loads(extraction_path.read_text())
            # Exact source ID join only. No ward/name allocation or spatial claim.
            map_info = json.loads((META / "sra_layers.json").read_text()).get("cluster-map-document", {})
            if map_info.get("path"):
                text = subprocess.run(["pdftotext", str(ROOT / map_info["path"]), "-"], capture_output=True, text=True, check=True, timeout=30).stdout
                map_ids = set(re.findall(r"\bME_\d{3}\b", text))
                registry_ids = {row["source_id"] for row in records if row["source_id_unique"]}
                report["map_label_join"] = {"method": "exact Cluster_ID equals printed map label", "map_labels": len(map_ids), "matched": len(map_ids & registry_ids),
                                            "unmatched_map_ids": sorted(map_ids - registry_ids), "register_me_rows": sum(row["ward"] == "M/E" for row in records),
                                            "geometries": 0, "map_reference_year": extraction.get("reference_year")}
        metadata = {**info, **quality, "fields": FIELDS, "reference_year": 2024,
                    "publication_date": "Unknown; PDF creation metadata " + (created.isoformat() if created else "unavailable"),
                    "geographic_resolution": "Published cluster identifier; no acquired geometry", "licence": "Not established; local research only pending reuse review",
                    "map_label_join": report.get("map_label_join")}
        write_json(PROCESSED / "sra_cluster_register.json", {"records": records, "metadata": metadata})
        inventory(dataset_name="SRA published slum cluster register 2024", publisher="SRA Brihanmumbai", source_url=REGISTER_URL,
                  retrieved_at=info["retrieved_at"], observation_date="2024 document title; individual observation date unknown", publication_date=metadata["publication_date"],
                  geography="Greater Mumbai; source ward, village and taluka strings", resolution=metadata["geographic_resolution"], format="PDF -> validated word-coordinate table", record_count=len(records),
                  fields=FIELDS, licence=metadata["licence"], access_status="downloaded", validation_status=quality["method"],
                  intended_use="Attributed historical cluster lookup and exact-ID reference joins; field collection planning",
                  limitations=f"No polygons, household counts, current service measurements or legal-status inference. {quality['missing_name_count']} missing names; {quality['name_overflow_count']} name cells overlap source area column and require spelling review")
    except (DownloadError, ValueError, ET.ParseError, subprocess.SubprocessError, OSError, ImportError) as exc:
        report["errors"].append(str(exc))
        inventory(dataset_name="SRA published slum cluster register 2024", publisher="SRA Brihanmumbai", source_url=REGISTER_URL, retrieved_at=utcnow(),
                  access_status="failed", validation_status="Not activated; previous processed snapshot retained", limitations=str(exc))
    finally:
        downloader.close()
    write_json(META / "sra_register_ingestion.json", report)
    print("SRA register:", report.get("quality", {}).get("record_count", 0), "; errors:", report["errors"])
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    ingest(parser.parse_args().refresh)
