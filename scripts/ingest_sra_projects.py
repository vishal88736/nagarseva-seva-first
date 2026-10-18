"""Read the public listing's first page and catalogue links without authentication.

ASP.NET page number is not a stable scheme ID. Retain the source row identity and
use a local content hash, leaving settlement and current status explicitly null.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from data_common import Downloader, DownloadError, META, PROCESSED, inventory, utcnow, write_json

PORTAL = "https://dms.sra.gov.in/SRAPUBLIC/"
CATALOGUE = "https://www.data.gov.in/catalog/slum-rehabilitation-authority-brihanmumbai"


def parse_listing(raw, retrieved_at):
    soup = BeautifulSoup(raw, "html.parser")
    table = next((t for t in soup.find_all("table") if all(s in t.get_text(" ", strip=True) for s in ("Scheme Name", "Ward Name", "CTS No"))), None)
    if table is None:
        raise ValueError("Expected public scheme table not present (login, empty response or changed schema)")
    rows = table.find_all("tr")
    header = next((r for r in rows if "Scheme Name" in r.get_text()), None)
    names = [c.get_text(" ", strip=True) for c in header.find_all(["th", "td"], recursive=False)] if header else []
    required = {"Scheme Name", "Ward Name", "Address", "CTS No", "Village"}
    if not required.issubset(names):
        raise ValueError("Scheme listing schema changed: " + repr(names))
    records, seen = [], set()
    for row in rows:
        cells = row.find_all("td", recursive=False)
        if len(cells) != len(names):
            continue
        item = dict(zip(names, (c.get_text(" ", strip=True) for c in cells)))
        if not item.get("Scheme Name") or item["Scheme Name"] == "Scheme Name":
            continue
        facts = {key: value for key, value in item.items() if key not in ("Action", "SrNo")}
        identity = hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()[:20]
        if identity in seen:
            raise ValueError("Duplicate scheme row content")
        seen.add(identity)
        records.append({"id": "sra-listing-" + identity, "source_id": None, "source_row_number": item.get("SrNo"),
                        "scheme_name": item["Scheme Name"], "administrative_area": item["Ward Name"], "address": item["Address"],
                        "cts_raw": item["CTS No"], "village": item["Village"], "source_attributes": facts,
                        "project_status": "unknown", "settlement_id": None, "geometry": None, "source_date": None,
                        "retrieved_at": retrieved_at, "source_url": PORTAL, "synthetic": False,
                        "join_status": "unmatched; CTS/village/ward require authoritative crosswalk; no fuzzy join"})
    if not records:
        raise ValueError("Scheme table contains no data rows")
    return records, names


def ingest(refresh=False):
    downloader = Downloader("sra", refresh)
    report = {"attempted_at": utcnow(), "errors": [], "listing_scope": "First public page only; not a full registry or ongoing-status extract"}
    try:
        raw, info = downloader.fetch(PORTAL, "public-projects", suffix=".html")
        records, fields = parse_listing(raw, info["retrieved_at"])
        write_json(PROCESSED / "sra_projects.json", {"records": records, "metadata": {**info, "scope": report["listing_scope"], "source_fields": fields}})
        report.update(record_count=len(records), fields=fields, request=info)
        inventory(dataset_name="SRA public scheme listing first page", publisher="SRA Brihanmumbai", source_url=PORTAL,
                  retrieved_at=info["retrieved_at"], geography="Mumbai; ward and village strings", resolution="Scheme row", format="HTML -> JSON", record_count=len(records), fields=fields,
                  licence="Not established; official portal reserves rights; local research only pending reuse review", access_status="downloaded", validation_status="Expected columns, row uniqueness and nonempty names checked",
                  intended_use="Attributed desk review of published scheme facts", limitations="First page only; no current status/date or geometry; local hash is not an official scheme identifier")
    except (DownloadError, ValueError) as exc:
        report["errors"].append(str(exc))
        inventory(dataset_name="SRA public scheme listing first page", publisher="SRA Brihanmumbai", source_url=PORTAL, retrieved_at=utcnow(), access_status="failed", validation_status="not parsed", limitations=str(exc))
    try:
        raw, info = downloader.fetch(CATALOGUE, "ogd-catalogue", suffix=".html")
        soup = BeautifulSoup(raw, "html.parser")
        catalogue_text = soup.get_text(" ", strip=True)
        links = [{"label": a.get_text(" ", strip=True), "url": urljoin(CATALOGUE, a["href"])} for a in soup.select("a[href]") if any(s in a["href"] for s in (".csv", ".xlsx", ".xls", "/resource/", "/download/"))]
        report["catalogue"] = {"request": info, "candidate_links": links, "title": soup.title.get_text() if soup.title else None,
                               "zip_download_disabled": bool(soup.select('a[aria-label=" Zip Download is not Available"]')),
                               "no_resource_result": "No Result Found" in catalogue_text, "sandbox_notice_present": "sandbox environment" in catalogue_text}
        # Follow only publicly advertised direct structured files, capped at five.
        for i, link in enumerate([l for l in links if urlparse(l["url"]).path.lower().endswith(".csv")][:5]):
            content, asset = downloader.fetch(link["url"], f"ogd-projects-{i}", suffix=".csv")
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            rows = list(reader)
            if not rows or not reader.fieldnames or len(reader.fieldnames) < 2:
                raise ValueError("Advertised OGD CSV failed schema validation")
            write_json(PROCESSED / f"sra_ogd_{i}.json", {"fields": reader.fieldnames, "records": rows, "request": asset, "status_scope": "Requires field-specific status interpretation; do not infer completion"})
            inventory(dataset_name="SRA OGD CSV " + str(i), publisher="Maharashtra SRA via OGD", source_url=link["url"], retrieved_at=asset["retrieved_at"],
                      format="CSV", record_count=len(rows), fields=reader.fieldnames, access_status="downloaded", validation_status="CSV parsed; status/geographic join not yet verified", intended_use="Published project context", limitations="Not joined or activated until identifiers/status definitions reviewed")
        inventory(dataset_name="SRA OGD catalogue", publisher="data.gov.in / Maharashtra SRA", source_url=CATALOGUE, retrieved_at=info["retrieved_at"],
                  format="HTML", fields=["candidate_links"], access_status="metadata_only", validation_status="HTML parsed; " + str(len(links)) + " candidate links",
                  publication_date="2025-09-09 catalogue label; resource publication date not locally verified",
                  intended_use="Discover ongoing projects CSV", limitations="Fetched page has no resource results, disabled ZIP and a sandbox notice; no downloadable project file verified. No API key requested or used")
    except (DownloadError, ValueError) as exc:
        report["errors"].append("OGD: " + str(exc))
        inventory(dataset_name="SRA OGD catalogue", publisher="data.gov.in / Maharashtra SRA", source_url=CATALOGUE, retrieved_at=utcnow(), access_status="failed", validation_status="not parsed", limitations=str(exc))
    write_json(META / "sra_projects_ingestion.json", report)
    downloader.close()
    print("SRA projects:", report.get("record_count", 0), "; errors:", len(report["errors"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    ingest(parser.parse_args().refresh)
