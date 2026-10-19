"""Offline reviewed-table regression tests; live results in census_followup.md."""
from copy import deepcopy
import ssl

import pytest

from census_tables import (parse_slum_pca, pca_maharashtra, parse_housing, parse_water,
                           parse_water_electricity_latrine)
from data_common import Downloader
from ingest_census import historical_unit, observation


def pca_fixture():
    columns = ['State Code', 'Town Code', 'Area Name', 'No_HH', 'TOT_P', 'TOT_M', 'TOT_F', 'P_LIT', 'P_ILL', 'TOT_WORK_P', 'NON_WORK_P']
    columns += [f'other_count_{i}' for i in range(88 - len(columns))]
    row = ['27', '000000', 'MAHARASHTRA', 3, 12, 7, 5, 9, 3, 5, 7] + [0] * (88 - 11)
    town = row.copy(); town[:3] = ['27', '802794', 'Greater Mumbai (M Corp.) (Part)']
    return [{'name': 'PCA', 'rows': [columns, row, town]}]


def test_pca_retains_codes_fields_and_original_part_name():
    rows = pca_maharashtra(parse_slum_pca(pca_fixture()))
    assert len(rows) == 2 and len(rows[0]) == 88
    assert rows[1]['Town Code'] == '802794'
    assert rows[1]['Area Name'].endswith('(Part)')
    assert rows[1]['TOT_P'] == 12


@pytest.mark.parametrize('issue', ['headers', 'duplicate', 'noninteger', 'negative', 'bad_code', 'sex_total', 'component_total', 'state_total'])
def test_pca_rejects_invalid_source_records(issue):
    sheets = deepcopy(pca_fixture()); rows = sheets[0]['rows']
    if issue == 'headers': rows[0].pop()
    if issue == 'duplicate': rows.append(rows[1].copy())
    if issue == 'noninteger': rows[1][3] = 3.1
    if issue == 'negative': rows[1][-1] = -1
    if issue == 'bad_code': rows[1][0] = 27
    if issue == 'sex_total': rows[1][5] = 8
    if issue == 'component_total': rows[1][7] = 8
    if issue == 'state_total': rows[1][3] = 4
    with pytest.raises(ValueError): pca_maharashtra(parse_slum_pca(sheets))


def test_housing_exact_cells_and_subtotals():
    text = '''HH-1: SLUM HOUSEHOLDS BY THE CONDITION OF CENSUS HOUSES OCCUPIED BY THEM
Dilapidated
STATE - MAHARASHTRA 27
row 100 50 30 20 90 45 27 18 10 5 3 2 Total
STATE - ANDHRA PRADESH 28'''
    cells = parse_housing(text)
    assert len(cells) == 12 and cells[3]['value'] == 20 and cells[3]['denominator'] == 100
    with pytest.raises(ValueError, match='subtotals'): parse_housing(text.replace('100 50', '101 50'))


def test_water_dash_stays_missing_and_header_is_not_a_count_row():
    text = '''HH-6: SLUM HOUSEHOLDS BY MAIN SOURCE OF DRINKING WATER AND LOCATION
Tapwater
STATE - MAHARASHTRA 27
योग/Total
row 100 40 20 10 10 5 5 2 2 2 4 Total
row 50 25 10 5 5 3 2 - - - - Within the premises
row 30 10 5 3 3 1 3 1 1 1 2 Near the premises
row 20 5 5 2 2 1 0 1 1 1 2 Away
STATE - ANDHRA PRADESH 28'''
    cells = parse_water(text)
    assert len(cells) == 44 and sum(c['value'] is None for c in cells) == 4
    assert cells[0]['value'] == 100
    with pytest.raises(ValueError, match='subtotals'): parse_water(text.replace('100 40', '101 40'))


def test_joint_amenity_cells_are_counts_not_deficit_indices():
    text = '''HH-11: SLUM HOUSEHOLDS CLASSIFIED BY SOURCE AND LOCATION OF DRINKING WATER AND AVAILABLITY OF ELECTRICITY AND LATRINE
STATE - MAHARASHTRA 27
All sources
row 100 40 30 20 10 Total number of households
row 50 25 15 8 2 Within premises
row 30 10 10 5 5 Near premises
row 20 5 5 7 3 Away'''
    cells = parse_water_electricity_latrine(text)
    assert len(cells) == 20 and cells[0]['value'] == 100
    assert cells[3]['source_field'].endswith('electricity_unavailable_latrine_available')
    with pytest.raises(ValueError, match='subtotals'): parse_water_electricity_latrine(text.replace('100 40', '101 40'))


def test_historical_adapter_has_no_settlement_allocation_or_current_date():
    unit = historical_unit('27', '802794', 'Greater Mumbai (M Corp.) (Part)', 'https://example.test/catalogue')
    result = observation(unit, 'TOT_P', 12, 'population', 'https://example.test/table.xls', {'retrieved_at': '2026-10-18T00:00:00Z', 'path': 'raw.xls', 'sha256': 'fixture'}, '6190')
    assert result['settlement_id'] is None and result['observation_date'] is None
    assert result['reference_year'] == 2011 and result['unit'] == 'persons'
    assert result['verification_status'] == 'historical_published'
    assert unit['geometry'] is None and unit['name'].endswith('(Part)')


def test_downloader_cannot_disable_certificate_or_hostname_verification():
    with pytest.raises(ValueError, match='verification are required'): Downloader('test', verify=False)
    insecure = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    insecure.check_hostname = False
    with pytest.raises(ValueError, match='verification are required'): Downloader('test', verify=insecure)
