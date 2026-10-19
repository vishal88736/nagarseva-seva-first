"""Read advertised public listing pages and catalogue links without authentication.

ASP.NET page number is not a stable scheme ID. Retain the source row identity and
use a local content hash, leaving settlement and current status explicitly null.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import re
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from data_common import Downloader, DownloadError, META, PROCESSED, inventory, utcnow, write_json

PORTAL = "https://dms.sra.gov.in/SRAPUBLIC/"
CATALOGUE = "https://www.data.gov.in/catalog/slum-rehabilitation-authority-brihanmumbai"


def parse_listing(raw, retrieved_at, allow_duplicate_content=False):
    soup = BeautifulSoup(raw, "html.parser")
    # Match the table's own header. A surrounding layout table or nested pager
    # also contains these strings but is not the source record table.
    required = {"Scheme Name", "Ward Name", "Address", "CTS No", "Village"}
    table = next((t for t in soup.find_all("table") if any(required.issubset({c.get_text(" ", strip=True) for c in row.find_all(["th", "td"], recursive=False)})
                 for row in t.find_all("tr") if row.find_parent("table") is t)), None)
    if table is None:
        raise ValueError("Expected public scheme table not present (login, empty response or changed schema)")
    rows = [row for row in table.find_all("tr") if row.find_parent("table") is table]
    header = next((r for r in rows if "Scheme Name" in r.get_text()), None)
    names = [c.get_text(" ", strip=True) for c in header.find_all(["th", "td"], recursive=False)] if header else []
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
        duplicate = identity in seen
        if duplicate and not allow_duplicate_content:
            raise ValueError("Duplicate scheme row content")
        seen.add(identity)
        records.append({"id": "sra-listing-" + identity + ("-row-" + item["SrNo"] if duplicate else ""), "source_id": None, "source_row_number": item.get("SrNo"),
                        "source_content_hash": identity, "source_content_unique": not duplicate,
                        "scheme_name": item["Scheme Name"], "administrative_area": item["Ward Name"], "address": item["Address"],
                        "cts_raw": item["CTS No"], "village": item["Village"], "source_attributes": facts,
                        "project_status": "unknown", "settlement_id": None, "geometry": None, "source_date": None,
                        "retrieved_at": retrieved_at, "source_url": PORTAL, "synthetic": False,
                        "join_status": "unmatched; CTS/village/ward require authoritative crosswalk; no fuzzy join"})
    if not records:
        raise ValueError("Scheme table contains no data rows")
    return records, names


def next_public_page(raw, current, base=PORTAL):
    """Replay only the portal's advertised same-origin ASP.NET pager action."""
    soup = BeautifulSoup(raw, "html.parser")
    form = soup.find("form")
    if form is None:
        raise ValueError("Public listing form missing")
    advertised = []
    for anchor in form.select("a[href]"):
        match = re.fullmatch(r"javascript:__doPostBack\('gvScheme','Page\$(\d+)'\)", anchor["href"])
        if "__doPostBack('gvScheme','Page$" in anchor["href"] and match is None:
            raise ValueError("Malformed advertised public page action")
        if match and int(match[1]) > current:
            advertised.append(int(match[1]))
    grid = form.find("table", id="gvScheme")
    if grid:
        pager_cells = [cell for cell in grid.find_all("td", colspan=True) if cell.find("table")]
        for pager in pager_cells:
            active = [int(span.get_text(strip=True)) for span in pager.find_all("span") if span.get_text(strip=True).isdigit()]
            if active != [current]:
                raise ValueError("Public pager active-page marker missing or inconsistent")
    if not advertised:
        return None
    if current + 1 not in advertised:
        raise ValueError("Portal does not advertise the next sequential page")
    target = urljoin(base, form.get("action") or base)
    if urlparse(target).netloc != urlparse(PORTAL).netloc or not urlparse(target).path.startswith("/SRAPUBLIC/"):
        raise ValueError("Untrusted form action; public pagination refused")
    fields = {item["name"]: item.get("value", "") for item in form.select("input[type=hidden][name]")}
    if "__VIEWSTATE" not in fields:
        raise ValueError("Expected ASP.NET public page state missing")
    fields.update(__EVENTTARGET="gvScheme", __EVENTARGUMENT=f"Page${current + 1}")
    fields.update({item["name"]: item.get("value", "") for item in form.select("input[type=text][name]")})
    for select in form.select("select[name]"):
        selected = select.find("option", selected=True) or select.find("option")
        fields[select["name"]] = selected.get("value", "") if selected else ""
    return target, fields


def read_public_pages(downloader, max_pages=400, delay_seconds=0.5, max_rows=20_000):
    if not isinstance(max_pages, int) or isinstance(max_pages, bool) or not 1 <= max_pages <= 400:
        raise ValueError("Public listing page limit must be between 1 and 400")
    if not 0 <= delay_seconds <= 10:
        raise ValueError("Public listing delay must be between zero and ten seconds")
    if not isinstance(max_rows, int) or isinstance(max_rows, bool) or not 1 <= max_rows <= 20_000:
        raise ValueError("Public listing row limit must be between 1 and 20000")
    started_at = utcnow()
    raw, request = downloader.fetch(PORTAL, "public-projects", suffix=".html")
    requests, rows, ids, gaps, content_rows, page_hashes = [], [], set(), [], {}, set()
    names = None
    complete, error = False, None
    for page in range(1, max_pages + 1):
        try:
            page_hash = hashlib.sha256(raw).hexdigest()
            if page_hash in page_hashes:
                raise ValueError("Repeated public response page; partial snapshot only")
            records, fields = parse_listing(raw, request["retrieved_at"], allow_duplicate_content=True)
            if len(rows) + len(records) > max_rows:
                raise ValueError("Public listing row limit reached; page retained raw but not partially imported")
            if names is not None and fields != names:
                raise ValueError("Public listing columns changed across pages")
            names = fields
            serials = [int(row["source_row_number"]) for row in records]
            previous_serial = int(rows[-1]["source_row_number"]) if rows else 0
            if serials != sorted(set(serials)) or serials[0] <= previous_serial:
                raise ValueError("Public page row sequence repeated or reversed; partial snapshot only")
            # The source itself skips some displayed serials (for example 100).
            # Preserve and report these gaps; they are not evidence of missing
            # fetched pages, nor a basis for inventing the absent scheme rows.
            for number in serials:
                if number > previous_serial + 1:
                    gaps.append({"after": previous_serial, "before": number})
                previous_serial = number
            for row in records:
                same = content_rows.setdefault(row["source_content_hash"], [])
                if same:
                    for previous in same:
                        previous["source_content_unique"] = False
                    row["source_content_unique"] = False
                    row["id"] = "sra-listing-" + row["source_content_hash"] + "-row-" + row["source_row_number"]
                if row["id"] in ids:
                    raise ValueError("Duplicate local row identity across public pages")
                row.update(source_page=page, source_raw_path=request["path"])
                ids.add(row["id"])
                same.append(row)
            rows.extend(records)
            page_hashes.add(page_hash)
            requests.append(request)
            following = next_public_page(raw, page, request.get("final_url", PORTAL))
            print(f"SRA listing page {page}: {len(records)} rows", flush=True)
            if following is None:
                complete = True
                break
            if page == max_pages:
                error = "Reached configured page limit while further public pages remain"
                break
            # Bounded sequential public navigation; no concurrent portal load.
            if request["retrieved_at"] >= started_at:
                time.sleep(delay_seconds)
            raw, request = downloader.fetch(following[0], f"public-projects-page-{page + 1}", method="POST", form=following[1], suffix=".html")
        except (DownloadError, ValueError) as exc:
            error = str(exc)
            break
    if not rows:
        raise ValueError(error or "Public listing contains no valid rows")
    duplicate_content = [{"content_hash": key, "displayed_source_rows": [row["source_row_number"] for row in items]} for key, items in content_rows.items() if len(items) > 1]
    return rows, names, {"requests": requests, "pages": len(requests), "pages_retrieved": len(requests), "complete": complete, "pagination_error": error, "displayed_serial_gaps": gaps,
                         "configured_max_pages": max_pages, "configured_max_rows": max_rows, "unique_page_response_count": len(page_hashes),
                         "retrieval_window": {"earliest_original_retrieved_at": min(item["retrieved_at"] for item in requests),
                                              "latest_original_retrieved_at": max(item["retrieved_at"] for item in requests)},
                         "duplicate_content_groups": duplicate_content, "duplicate_content_rows": sum(len(item["displayed_source_rows"]) for item in duplicate_content),
                         "scope": "All advertised public listing pages reached at retrieval; not an ongoing-status registry" if complete else "Partial public listing; navigation stopped before confirmed final page",
                         "ordering_limitation": "Live listing can change during pagination; increasing displayed serials and unique local row IDs checked, source serial gaps and duplicate content preserved, no server snapshot guarantee"}


def ingest(refresh=False, max_pages=400, delay_seconds=0.5):
    downloader = Downloader("sra", refresh)
    report = {"attempted_at": utcnow(), "errors": []}
    try:
        records, fields, pagination = read_public_pages(downloader, max_pages, delay_seconds)
        info = pagination["requests"][0]
        write_json(PROCESSED / "sra_projects.json", {"records": records, "metadata": {**info, **pagination, "source_fields": fields}})
        report.update(record_count=len(records), fields=fields, request=info, pagination=pagination, listing_scope=pagination["scope"])
        if pagination["pagination_error"]:
            report["errors"].append(pagination["pagination_error"])
        inventory(dataset_name="SRA public scheme listing paginated", publisher="SRA Brihanmumbai", source_url=PORTAL,
                  retrieved_at=info["retrieved_at"], geography="Mumbai; ward and village strings", resolution="Scheme row", format="HTML -> JSON", record_count=len(records), fields=fields,
                  licence="Not established; official portal reserves rights; local research only pending reuse review", access_status="downloaded", validation_status="Expected columns, local row-ID uniqueness, source duplicate-content groups and nonempty names checked",
                  intended_use="Attributed desk review of published scheme facts", limitations=pagination["scope"] + "; no current status/date or geometry; local hash is not an official scheme identifier. " + pagination["ordering_limitation"])
    except (DownloadError, ValueError) as exc:
        report["errors"].append(str(exc))
        inventory(dataset_name="SRA public scheme listing paginated", publisher="SRA Brihanmumbai", source_url=PORTAL, retrieved_at=utcnow(), access_status="failed", validation_status="not parsed; previous processed snapshot retained", limitations=str(exc))
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
    parser.add_argument("--max-pages", type=int, default=400, help="At most 400 public pages; continue only advertised sequential links")
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    args = parser.parse_args()
    ingest(args.refresh, args.max_pages, args.delay_seconds)
