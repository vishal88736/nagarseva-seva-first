"""Source-specific regressions use fixtures; live counts are recorded separately."""
import html

import pytest

from data_common import DownloadError
from ingest_sra_projects import next_public_page, parse_listing, read_public_pages
from ingest_sra_register import parse_register_xml


FIELDS = ["SrNo", "Scheme Name", "Ward Name", "Address", "CTS No", "Village"]


def listing(serial=1, next_page=None, same_name=False, nested=False):
    header = "".join(f"<th>{name}</th>" for name in FIELDS)
    row = "".join(f"<td>{value}</td>" for value in [serial, "Shared" if same_name else f"Scheme{serial}", "M-E", "Address", "1-A", "Deonar"])
    pager = f'''<tr><td colspan="6"><table><tr>{''.join(f'<td>{i}</td>' for i in range(6))}</tr></table></td></tr>'''
    link = f'''<a href="javascript:__doPostBack('gvScheme','Page${next_page}')">Next</a>''' if next_page else ""
    table = f"<table><tr>{header}</tr><tr>{row}</tr>{pager}</table>"
    if nested:
        table = f"<table><tr><td>{table}</td></tr></table>"
    return f'<form action="MainNewExplorer.aspx"><input type="hidden" name="__VIEWSTATE" value="state"/>{table}{link}</form>'.encode()


class FakeDownloader:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def fetch(self, url, key, **kwargs):
        self.calls.append((url, key, kwargs))
        result = self.pages[len(self.calls) - 1]
        if isinstance(result, Exception):
            raise result
        return result, {"retrieved_at": "2026-10-18T00:00:00Z", "path": f"page-{len(self.calls)}.html", "final_url": url}


def test_listing_ignores_layout_and_same_width_pager_tables():
    rows, _ = parse_listing(listing(nested=True), "now")
    assert len(rows) == 1 and rows[0]["source_row_number"] == "1"


def test_public_pagination_follows_only_advertised_actions_and_preserves_source_gaps():
    downloader = FakeDownloader([listing(1, 2), listing(3)])
    rows, _, metadata = read_public_pages(downloader, delay_seconds=0)
    assert len(rows) == 2 and metadata["complete"] and metadata["pages_retrieved"] == 2
    assert metadata["displayed_serial_gaps"] == [{"after": 1, "before": 3}]
    assert downloader.calls[1][2]["form"]["__EVENTARGUMENT"] == "Page$2"
    assert downloader.calls[1][2]["method"] == "POST"
    assert rows[1]["source_page"] == 2 and rows[1]["project_status"] == "unknown"


@pytest.mark.parametrize("second", [listing(1), DownloadError("fixture timeout")])
def test_public_pagination_stops_on_repeated_page_or_network_failure(second):
    rows, _, metadata = read_public_pages(FakeDownloader([listing(1, 2), second]), delay_seconds=0)
    assert len(rows) == 1 and not metadata["complete"] and metadata["pagination_error"]


def test_public_pagination_stops_at_explicit_limit_without_claiming_completion():
    downloader = FakeDownloader([listing(1, 2)])
    _, _, metadata = read_public_pages(downloader, max_pages=1, delay_seconds=0)
    assert not metadata["complete"] and len(downloader.calls) == 1
    with pytest.raises(ValueError):
        read_public_pages(downloader, max_pages=401)


def test_public_duplicate_content_is_retained_with_distinct_local_row_identity():
    downloader = FakeDownloader([listing(1, 2, same_name=True), listing(2, same_name=True)])
    rows, _, metadata = read_public_pages(downloader, delay_seconds=0)
    assert metadata["complete"] and metadata["duplicate_content_rows"] == 2
    assert len({row["id"] for row in rows}) == 2
    assert not any(row["source_content_unique"] for row in rows)
    assert rows[0]["source_id"] is rows[1]["source_id"] is None


def test_public_pagination_rejects_external_form_and_unadvertised_page():
    with pytest.raises(ValueError, match="Untrusted"):
        next_public_page(listing(1, 2).replace(b'MainNewExplorer.aspx', b'https://evil.test/post'), 1)
    with pytest.raises(ValueError, match="next sequential"):
        next_public_page(listing(1, 3), 1)


def register_xml(rows):
    words = []
    def word(text, x, y=125.4, xmax=None):
        words.append(f'<word xMin="{x}" xMax="{xmax if xmax is not None else x+10}" yMin="{y}">{html.escape(text)}</word>')
    for text, x in [("CLUSTER", 300), ("2024", 400), ("Cluster_ID", 123.3), ("Ward", 188.8), ("Village_Division", 245), ("Taluka", 358.4), ("Slum_Name", 456.4), ("Shape_Area", 580)]:
        word(text, x)
    for serial, source_id, name, area in rows:
        y = 138 + serial * 12
        for text, x in [(str(serial), 90), (source_id, 135), ("M/E", 190), ("DEONAR", 260), ("KURLA", 360)]:
            word(text, x, y)
        word(name, 410, y, 565 if name != "<Null>" else 440)
        if area is not None:
            word(area, 575, y)
    return '<html><body><doc><page>'+''.join(words)+'</page></doc></body></html>'


def test_register_preserves_nulls_areas_and_name_overflow_without_geometry():
    rows, quality = parse_register_xml(register_xml([(1, "ME_001", "NAME", "1402.11"), (2, "ME_002", "<Null>", "581.61")]), "now")
    assert rows[0]["shape_area_sq_m"] == 1402.11 and rows[0]["geometry"] is None
    assert rows[0]["name_overflow_in_source"] and rows[1]["name"] is None
    assert quality["missing_name_count"] == 1 and quality["unique_source_ids"] == 2


def test_register_publisher_duplicate_ids_are_preserved_and_excluded_from_joins():
    rows, quality = parse_register_xml(register_xml([(1, "MW_041", "A", "1.00"), (2, "MW_041", "B", "2.00")]), "now")
    assert quality["duplicate_source_ids"] == {"MW_041": 2}
    assert len({row["id"] for row in rows}) == 2
    assert not any(row["source_id_unique"] for row in rows)


@pytest.mark.parametrize("rows", [[(2, "ME_001", "A", "1.00")], [(1, "ME_001", "A", None)], [(1, "bad", "A", "1.00")]])
def test_register_rejects_incomplete_serials_missing_areas_and_bad_ids(rows):
    with pytest.raises(ValueError):
        parse_register_xml(register_xml(rows), "now")


def test_register_requires_review_when_source_columns_change():
    with pytest.raises(ValueError, match="coordinates changed"):
        parse_register_xml(register_xml([(1, "ME_001", "A", "1.00")]).replace('xMin="456.4"', 'xMin="470"'), "now")
