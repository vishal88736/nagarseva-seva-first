"""Reviewed Census 2011 table adapters; never allocate aggregates to settlements."""
from __future__ import annotations

import math
import re

PCA_REQUIRED = ['State Code', 'Town Code', 'Area Name', 'No_HH', 'TOT_P', 'TOT_M', 'TOT_F']
WATER_SOURCES = ['all_sources', 'tapwater_treated', 'tapwater_untreated', 'covered_well', 'uncovered_well', 'handpump', 'tubewell_borehole', 'spring', 'river_canal', 'tank_pond_lake', 'other_sources']
LOCATIONS = ['total', 'within_premises', 'near_premises', 'away']


def count(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or value != int(value):
        raise ValueError('Expected a non-negative integer count')
    return int(value)


def code(value, width):
    if not isinstance(value, str) or not re.fullmatch(r'\d{' + str(width) + '}', value):
        raise ValueError(f'Expected original zero-padded {width}-digit Census code')
    return value


def parse_slum_pca(sheets):
    """All original 88 columns retained; validate identifiers/counts/sex totals."""
    sheet = next((s for s in sheets if s['rows']), None)
    if not sheet:
        raise ValueError('No PCA table rows')
    header, *body = sheet['rows']
    if len(header) != 88 or len(set(header)) != 88 or not all(k in header for k in PCA_REQUIRED):
        raise ValueError('Unrecognized slum PCA schema; reviewed 88-column table required')
    records, seen = [], set()
    for row in body:
        if not any(v != '' and v is not None for v in row):
            continue
        if len(row) != len(header):
            raise ValueError('PCA row/header width mismatch')
        item = dict(zip(header, row))
        state, town = code(item['State Code'], 2), code(item['Town Code'], 6)
        if (state, town) in seen:
            raise ValueError('Duplicate Census geography identifier')
        seen.add((state, town))
        if not isinstance(item['Area Name'], str) or not item['Area Name'].strip():
            raise ValueError('Missing source geography name')
        for key in header[3:]:
            item[key] = count(item[key])
        if item['TOT_P'] != item['TOT_M'] + item['TOT_F']:
            raise ValueError('PCA population sex total mismatch')
        if item['TOT_P'] != item['P_LIT'] + item['P_ILL'] or item['TOT_P'] != item['TOT_WORK_P'] + item['NON_WORK_P']:
            raise ValueError('PCA population component mismatch')
        records.append(item)
    if not records:
        raise ValueError('No Census PCA data records')
    return records


def pca_maharashtra(records):
    rows = [r for r in records if r['State Code'] == '27']
    states = [r for r in rows if r['Town Code'] == '000000']
    if len(states) != 1 or not any(r['Town Code'] != '000000' for r in rows):
        raise ValueError('Missing Maharashtra state/town hierarchy')
    for key in ['No_HH', 'TOT_P', 'TOT_M', 'TOT_F']:
        if states[0][key] != sum(r[key] for r in rows if r['Town Code'] != '000000'):
            raise ValueError('Maharashtra state and town totals do not reconcile')
    return rows


def maharashtra_section(text):
    match = re.search(r'STATE\s*-\s*MAHARASHTRA\s+27', text)
    if not match:
        raise ValueError('Maharashtra state27 PDF section absent')
    following = text[match.end():]
    for next_state in re.finditer(r'(?:STATE|UNION TERRITORY)\s*-\s*([A-Z][A-Z &.-]*?)\s+(\d{2})\b', following):
        if next_state.group(1).strip() != 'MAHARASHTRA' or next_state.group(2) != '27':
            return following[:next_state.start()]
    return following


def numeric_row(line, width):
    # Layout extraction retains columns. A printed dash is unavailable/not
    # applicable in these tables and is deliberately never coerced to zero.
    cells = re.findall(r'(?<!\S)(?:\d[\d,]*|-)(?!\S)', line)
    if len(cells) != width:
        raise ValueError(f'Expected {width} numeric PDF cells, found {len(cells)}')
    return [None if v == '-' else int(v.replace(',', '')) for v in cells]


def parse_housing(text):
    if 'HH-1: SLUM HOUSEHOLDS BY THE CONDITION OF CENSUS HOUSES OCCUPIED BY THEM' not in text or 'Dilapidated' not in text:
        raise ValueError('Unrecognized HH1 PDF header')
    line = next((l for l in maharashtra_section(text).splitlines() if re.search(r'\bTotal\s*$', l)), None)
    if not line:
        raise ValueError('Maharashtra housing total missing')
    values = numeric_row(line, 12)
    for start in (0, 4, 8):
        if values[start] != sum(values[start + 1:start + 4]):
            raise ValueError('Housing condition subtotals do not reconcile')
    if values[0] != values[4] + values[8]:
        raise ValueError('Housing use subtotals do not reconcile')
    groups = ['all_housing_uses', 'residence', 'residence_cum_other_use']
    conditions = ['total', 'good', 'livable', 'dilapidated']
    return [{'source_field': f'{group}.{condition}', 'source_label': f'{group.replace("_", " ")}: {condition}', 'value': values[g * 4 + c], 'denominator': values[g * 4], 'indicator_type': 'housing', 'universe': 'Slum households enumerated in Houselisting and Housing Census 2011'} for g, group in enumerate(groups) for c, condition in enumerate(conditions)]


def parse_water(text):
    if 'HH-6: SLUM HOUSEHOLDS BY MAIN SOURCE OF DRINKING WATER AND LOCATION' not in text or 'Tapwater' not in text:
        raise ValueError('Unrecognized HH6 PDF header')
    section = maharashtra_section(text)
    labels = ['Total', 'Within the premises', 'Near the premises', 'Away']
    rows = []
    for label in labels:
        line = next((l for l in section.splitlines() if re.search(r'\b' + re.escape(label) + r'\s*$', l) and re.search(r'\d[\d,]+', l)), None)
        if line is None:
            raise ValueError('Missing Maharashtra water location row: ' + label)
        rows.append(numeric_row(line, 11))
    for values in rows:
        if values[0] != sum(v for v in values[1:] if v is not None):
            raise ValueError('Water source subtotals do not reconcile')
    if rows[0][0] != sum(r[0] for r in rows[1:]):
        raise ValueError('Water location subtotals do not reconcile')
    return [{'source_field': f'{location}.{source}', 'source_label': f'{location.replace("_", " ")}: {source.replace("_", " ")}', 'value': rows[l][s], 'denominator': rows[0][0], 'indicator_type': 'water', 'universe': 'Slum households enumerated in Houselisting and Housing Census 2011'} for l, location in enumerate(LOCATIONS) for s, source in enumerate(WATER_SOURCES)]


def parse_water_electricity_latrine(text):
    if 'HH-11: SLUM HOUSEHOLDS CLASSIFIED BY SOURCE AND LOCATION OF DRINKING WATER AND AVAILABLITY OF ELECTRICITY AND LATRINE' not in text:
        raise ValueError('Unrecognized HH11 PDF header')
    section = maharashtra_section(text)
    if 'All sources' not in section:
        raise ValueError('All sources row absent')
    # Reviewed first source group only; the remaining source groups stay in
    # immutable original/PDF text, rather than guessing continuation headers.
    section = section.split('All sources', 1)[1]
    labels = ['Total number of households', 'Within premises', 'Near premises', 'Away']
    rows = []
    for label in labels:
        line = next((l for l in section.splitlines() if re.search(r'\b' + re.escape(label) + r'\s*$', l)), None)
        if line is None:
            raise ValueError('Missing HH11 all-source location row: ' + label)
        values = numeric_row(line, 5)
        if values[0] != sum(values[1:]):
            raise ValueError('HH11 electricity/latrine subtotals do not reconcile')
        rows.append(values)
    if rows[0][0] != sum(r[0] for r in rows[1:]):
        raise ValueError('HH11 location subtotals do not reconcile')
    categories = ['total_households', 'electricity_available_latrine_available', 'electricity_available_latrine_unavailable', 'electricity_unavailable_latrine_available', 'electricity_unavailable_latrine_unavailable']
    return [{'source_field': f'all_sources.{location}.{category}', 'source_label': f'all water sources, {location.replace("_", " ")}: {category.replace("_", " ")}', 'value': rows[l][c], 'denominator': rows[0][0], 'indicator_type': 'sanitation', 'universe': 'Slum households enumerated in Houselisting and Housing Census 2011'} for l, location in enumerate(LOCATIONS) for c, category in enumerate(categories)]
