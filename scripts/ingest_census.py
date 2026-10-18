"""Download official Census metadata and advertised assets, retaining 2011 geography.

No estimates are allocated from state/town/ward totals to settlement clusters.
Excel tables are preserved cell-for-cell; numerical observation adapters require
reviewed headers and explicit geography keys, not positional guesses.
"""
from __future__ import annotations
import argparse
from io import BytesIO
from pathlib import Path
import subprocess
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import xlrd
from openpyxl import load_workbook
from data_common import Downloader, DownloadError, META, PROCESSED, ROOT, inventory, utcnow, write_json

CATALOGUES = {
    "6190": "Census 2011 slum PCA", "11436": "Census 2011 slum house condition",
    "11448": "Census 2011 water electricity latrine", "11443": "Census 2011 slum drinking water",
}


def parse_workbook(raw, suffix):
    if suffix == ".xls":
        book = xlrd.open_workbook(file_contents=raw)
        sheets = [{"name": s.name, "rows": [s.row_values(i) for i in range(s.nrows)]} for s in book.sheets()]
    else:
        book = load_workbook(BytesIO(raw), read_only=True, data_only=True)
        sheets = [{"name": s.title, "rows": [[v.isoformat() if hasattr(v, "isoformat") else v for v in row] for row in s.iter_rows(values_only=True)]} for s in book]
    if not sheets or not any(s["rows"] for s in sheets):
        raise ValueError("Empty Census workbook")
    if sum(len(s["rows"]) for s in sheets) > 100_000:
        raise ValueError("Workbook exceeds pilot row limit")
    return sheets


def ingest(refresh=False):
    downloader = Downloader("census", refresh)
    report = {"attempted_at": utcnow(), "tables": [], "errors": [], "reference_year": 2011}
    for code, name in CATALOGUES.items():
        url = f"https://censusindia.gov.in/nada/index.php/catalog/{code}"
        entry = {"catalogue_id": code, "name": name, "source_url": url, "assets": []}
        try:
            raw, request = downloader.fetch(url, "catalogue-" + code, suffix=".html")
            soup = BeautifulSoup(raw, "html.parser")
            text = soup.get_text(" ", strip=True)
            if "2011" not in text or "Download" not in text or "Census" not in text:
                raise ValueError("Census catalogue content not present; refusing to treat an error page as metadata")
            links = list(dict.fromkeys(urljoin(url, a["href"]) for a in soup.select("a[href]") if urlparse(a["href"]).path.lower().endswith((".xls", ".xlsx", ".pdf"))))
            entry.update(request=request, advertised_assets=links, metadata_text=text)
            for i, asset_url in enumerate(links[:8]):
                suffix = Path(urlparse(asset_url).path).suffix.lower()
                try:
                    content, info = downloader.fetch(asset_url, f"table-{code}-{i}", suffix=suffix)
                    if suffix == ".pdf":
                        if not content.startswith(b"%PDF-"):
                            raise ValueError("Not a PDF")
                        output = subprocess.run(["pdftotext", "-layout", str(ROOT / info["path"]), "-"], capture_output=True, text=True, check=True, timeout=30).stdout
                        if len(output.strip()) < 50:
                            raise ValueError("No extractable Census table text; OCR/manual review required")
                        parsed = {"reference_year": 2011, "raw_text": output, "numeric_observations_activated": False, "request": info}
                        count = None
                        validation = "PDF text parsed; table values/geography not automatically validated or activated"
                    else:
                        sheets = parse_workbook(content, suffix)
                        parsed = {"reference_year": 2011, "sheets": sheets, "request": info, "numeric_observations_activated": False}
                        count = sum(len(s["rows"]) for s in sheets)
                        validation = "Workbook cells parsed; row count includes headers; geography adapter requires review"
                    write_json(PROCESSED / f"census_{code}_{i}.json", parsed)
                    entry["assets"].append({"request": info, "record_count": count, "validation": validation})
                    inventory(dataset_name=name + " asset " + str(i), publisher="ORGI Census of India", source_url=asset_url, retrieved_at=info["retrieved_at"],
                              observation_date="2011", geography="Source table geography retained; not allocated to clusters", resolution="Catalogue/table-specific", format=suffix[1:],
                              record_count=count, fields="Source cells or PDF text; reviewed numeric adapter not activated", licence="Asset-specific reuse terms not established", access_status="downloaded", validation_status=validation,
                              intended_use="Historical context only", limitations="2011 is not current; no cluster allocation; no inferred service reliability")
                except (DownloadError, ValueError, subprocess.SubprocessError) as exc:
                    entry.setdefault("errors", []).append({"url": asset_url, "error": str(exc)})
            inventory(dataset_name=name + " metadata", publisher="ORGI Census of India", source_url=url, retrieved_at=request["retrieved_at"], observation_date="2011",
                      format="HTML", access_status="metadata_only", validation_status="Catalogue text parsed; " + str(len(links)) + " advertised files", intended_use="Discover historical table and geography", limitations="Catalogue creation/modification dates are not observation dates")
        except (DownloadError, ValueError) as exc:
            entry["error"] = str(exc)
            report["errors"].append({"catalogue_id": code, "error": str(exc)})
            inventory(dataset_name=name + " metadata", publisher="ORGI Census of India", source_url=url, retrieved_at=utcnow(), observation_date="2011",
                      access_status="failed", validation_status="No local table parsed", intended_use="Historical context only", limitations=str(exc))
        report["tables"].append(entry)
    for key, url in (("population-finder", "https://censusindia.gov.in/census.website/data/population-finder"), ("dataful-maharashtra", "https://dataful.in/datasets/272/")):
        try:
            raw, info = downloader.fetch(url, key, suffix=".html")
            text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
            entry = {"request": info, "content_summary": text[:2000]}
            report[key] = entry
            inventory(dataset_name=key, publisher="ORGI" if key == "population-finder" else "Dataful / Factly (secondary convenience source)", source_url=url,
                      retrieved_at=info["retrieved_at"], observation_date="2011", format="HTML", access_status="metadata_only", validation_status="HTML parsed; no structured table obtained",
                      intended_use="Discovery only", limitations="No downloadable table verified; dynamic/registration access not bypassed; use official table for analysis")
        except DownloadError as exc:
            inventory(dataset_name=key, publisher="ORGI" if key == "population-finder" else "Dataful / Factly", source_url=url, retrieved_at=utcnow(), access_status="failed", validation_status="not parsed", limitations=str(exc))
    write_json(META / "census_ingestion.json", report)
    downloader.close()
    print("Census: ", sum(len(t["assets"]) for t in report["tables"]), "assets;", len(report["errors"]), "catalogue errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    ingest(parser.parse_args().refresh)
