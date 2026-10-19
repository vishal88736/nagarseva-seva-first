"""Public pagination boundaries; source network is not used by these fixtures."""
import pytest

from ingest_sra_projects import parse_listing, read_public_pages, next_public_page
from test_sra_sources import FakeDownloader, listing


def multiple_rows(page):
    return page.replace(b'</tr><tr><td colspan=', b'</tr><tr><td>2</td><td>Shared</td><td>M-E</td><td>Address</td><td>1-A</td><td>Deonar</td></tr><tr><td colspan=', 1)


def test_duplicate_content_within_a_page_is_preserved_with_all_rows_flagged():
    raw = multiple_rows(listing(1, same_name=True))
    rows, _, metadata = read_public_pages(FakeDownloader([raw]), delay_seconds=0)
    assert len(rows) == len({row['id'] for row in rows}) == 2
    assert metadata['duplicate_content_rows'] == 2
    assert not any(row['source_content_unique'] for row in rows)
    assert all(row['source_id'] is None for row in rows)


def test_exact_response_page_hash_stops_an_actual_response_loop():
    first = listing(1, 2)
    rows, _, metadata = read_public_pages(FakeDownloader([first, first]), delay_seconds=0)
    assert len(rows) == 1 and not metadata['complete']
    assert metadata['unique_page_response_count'] == 1
    assert 'Repeated public response page' in metadata['pagination_error']


@pytest.mark.parametrize('second', [b'', b'<html>login</html>', listing(2).replace(b'Address</th>', b'Changed</th>')])
def test_empty_login_or_changed_schema_keeps_only_checked_previous_pages(second):
    rows, _, metadata = read_public_pages(FakeDownloader([listing(1, 2), second]), delay_seconds=0)
    assert len(rows) == 1 and not metadata['complete'] and metadata['pagination_error']


def test_malformed_advertised_pager_is_not_a_confirmed_end():
    raw = listing(1, 2).replace(b'Page$2', b'Page$bad')
    rows, _, metadata = read_public_pages(FakeDownloader([raw]), delay_seconds=0)
    assert len(rows) == 1 and not metadata['complete']
    assert 'Malformed advertised' in metadata['pagination_error']


def test_missing_hidden_page_state_refuses_the_postback():
    raw = listing(1, 2).replace(b'name="__VIEWSTATE"', b'name="missing"')
    rows, _, metadata = read_public_pages(FakeDownloader([raw]), delay_seconds=0)
    assert len(rows) == 1 and not metadata['complete'] and '__VIEWSTATE' not in str(metadata.get('requests', []))
    assert 'page state missing' in metadata['pagination_error']


def test_real_grid_requires_consistent_active_pager_marker():
    raw = listing(1, 2).replace(b'<table><tr><th>', b'<table id="gvScheme"><tr><th>', 1)
    with pytest.raises(ValueError, match='active-page marker'):
        next_public_page(raw, 1)
    raw = raw.replace(b'<td>0</td>', b'<td><span>1</span></td>', 1)
    assert next_public_page(raw, 1)[1]['__EVENTARGUMENT'] == 'Page$2'


def test_row_limit_preserves_whole_checked_pages_without_slicing_a_source_page():
    second = multiple_rows(listing(2, same_name=True)).replace(b'<td>2</td><td>Shared', b'<td>3</td><td>Shared', 1)
    # The limit is checked before the oversized second-page sequence is imported.
    rows, _, metadata = read_public_pages(FakeDownloader([listing(1, 2), second]), max_rows=1, delay_seconds=0)
    assert len(rows) == 1 and not metadata['complete']
    assert 'row limit' in metadata['pagination_error']
    assert metadata['configured_max_rows'] == 1


@pytest.mark.parametrize('limit', [0, -1, 20_001, True, 1.5])
def test_row_limit_is_explicit_and_bounded(limit):
    with pytest.raises(ValueError, match='row limit'):
        read_public_pages(FakeDownloader([]), max_rows=limit)


def test_duplicate_source_serials_are_not_legitimate_distinct_content_rows():
    raw = multiple_rows(listing(1, same_name=True)).replace(b'<td>2</td><td>Shared', b'<td>1</td><td>Shared')
    with pytest.raises(ValueError, match='sequence repeated'):
        read_public_pages(FakeDownloader([raw]), delay_seconds=0)


def test_parser_default_still_rejects_unreviewed_duplicate_content():
    with pytest.raises(ValueError, match='Duplicate scheme row content'):
        parse_listing(multiple_rows(listing(1, same_name=True)), 'now')
