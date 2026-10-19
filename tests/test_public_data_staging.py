"""Public-only staging fixtures; these records are not government observations."""
from copy import deepcopy
import csv
import hashlib
import io
import json
from pathlib import Path
import stat
import tarfile

from PIL import Image
import pytest

from data_common import INVENTORY_FIELDS
from stage_public_data import MAX_BYTES, stage, verify_bundle


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def sources(tmp_path):
    data = tmp_path / 'data'
    for name in ['processed', 'metadata', 'raw/test']:
        (data / name).mkdir(parents=True, exist_ok=True)
    original = b'PUBLIC TEST ORIGINAL; not real observations\n'
    (data / 'raw/test/original.txt').write_bytes(original)
    unit = {'id': 'published-unit', 'source_id': 'TEST-CITY', 'name': 'Test City', 'source': 'https://example.test/census', 'resolution': 'city', 'reference_year': 2011}
    observation = {'id': 'published-observation', 'settlement_id': None, 'geographic_unit_id': unit['id'], 'indicator_type': 'population', 'value': 123,
                   'unit': 'persons', 'reference_year': 2011, 'observation_date': None, 'geographic_resolution': 'city', 'source': unit['source'],
                   'verification_status': 'historical_published', 'method': 'TEST ONLY published 2011 fixture; no current allocation'}
    settlement = {'id': 'source-label', 'source_id': 'TEST-LABEL', 'name': 'TEST ONLY source', 'data_completeness': 0, 'source': 'https://example.test/map', 'geometry': None, 'synthetic': False, 'indicators': {'water': None}}
    snapshot = {'metadata': {'synthetic': False, 'settlement_count': 1, 'settlement_geometry_count': 0, 'projects_count': 0, 'mapped_objects_count': 1, 'geographic_unit_count': 1, 'historical_observation_count': 1},
                'settlements': [settlement], 'projects': [], 'geographic_units': [unit], 'indicators': [observation],
                'spatial': {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': 'fixture-point', 'properties': {'category': 'amenity'}, 'geometry': {'type': 'Point', 'coordinates': [72.92, 19.06]}}]}}
    (data / 'processed/urban_real.json').write_text(json.dumps(snapshot))
    inventory = {key: '' for key in INVENTORY_FIELDS}
    inventory.update(dataset_name='TEST ONLY original', access_status='downloaded', record_count='1')
    with (data / 'metadata/dataset_inventory.csv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=INVENTORY_FIELDS)
        writer.writeheader(); writer.writerow(inventory)
    receipt = {'valid': True, 'errors': [], 'datasets': {'settlements': {'record_count': 1}, 'projects': {'record_count': 0}, 'geographic_units': {'record_count': 1}, 'indicators': {'record_count': 1}},
               'downloads': [{'path': 'data/raw/test/original.txt', 'bytes': len(original), 'sha256': sha(original), 'checksum_valid': True}]}
    (data / 'metadata/validation.json').write_text(json.dumps(receipt))
    return data, tmp_path / 'bundles', snapshot, receipt


def save_snapshot(sources, snapshot):
    (sources[0] / 'processed/urban_real.json').write_text(json.dumps(snapshot))


def overlay(sources):
    data = sources[0]
    stream = io.BytesIO()
    Image.new('RGBA', (2, 2), (255, 255, 255, 0)).save(stream, format='PNG')
    image = stream.getvalue()
    row = {'image_file': 'sra_pilot_overlay.png', 'image_bytes': len(image), 'image_sha256': sha(image), 'width': 2, 'height': 2,
           'analysis_allowed': False, 'synthetic': False, 'crs': 'EPSG:3857', 'bounds': [72.90, 19.04, 72.94, 19.08],
           'source_url': 'https://media.sra.gov.in/test-only-fixture.pdf', 'source_date': '2024', 'control_point_residual_m': [0, 0, 0, 0],
           'source_path': 'data/raw/test/original.txt', 'source_sha256': sources[3]['downloads'][0]['sha256']}
    (data / 'processed/sra_pilot_overlay.png').write_bytes(image)
    (data / 'processed/sra_pilot_overlay.json').write_text(json.dumps(row))
    return row


def test_content_addressed_bundle_is_rerunnable_deterministic_and_public_only(sources):
    data, output, _, _ = sources
    # Neighbouring private and raw files are never selected or recursively copied.
    (data / '.env').write_text('PRIVATE_DO_NOT_EXPORT')
    (data / 'records.sqlite3').write_bytes(b'PRIVATE_DO_NOT_EXPORT')
    (data / 'processed/field-evidence.txt').write_text('PRIVATE_DO_NOT_EXPORT')
    first = stage(data, output)
    second = stage(data, output)
    assert first == second and first['originals_checked'] == 1
    directory = Path(first['directory'])
    verified = verify_bundle(directory)
    assert verified['data_dir'] == '/data/processed'
    assert verified['inventory_path'] == '/data/metadata/dataset_inventory.csv'
    assert set(verified['files']) == {'processed/urban_real.json', 'metadata/dataset_inventory.csv'}
    with tarfile.open(first['archive']) as archive:
        assert set(archive.getnames()) == {'processed', 'metadata', 'manifest.json', *verified['files']}
        assert all(not item.issym() and not item.islnk() for item in archive.getmembers())
        for item in archive.getmembers():
            assert item.mode == (0o755 if item.isdir() else 0o644)
            if item.isfile():
                assert b'PRIVATE_DO_NOT_EXPORT' not in archive.extractfile(item).read()
    for file in directory.rglob('*'):
        assert stat.S_IMODE(file.stat().st_mode) == (0o755 if file.is_dir() else 0o644)


def test_changed_public_input_creates_a_new_bundle_without_overwriting_prior_output(sources):
    first = stage(sources[0], sources[1])
    old = Path(first['directory']) / 'processed/urban_real.json'
    original = old.read_bytes()
    snapshot = deepcopy(sources[2]); snapshot['metadata']['title'] = 'Reviewed new source snapshot'
    save_snapshot(sources, snapshot)
    second = stage(sources[0], sources[1])
    assert first['bundle_id'] != second['bundle_id']
    assert old.read_bytes() == original


@pytest.mark.parametrize('target', ['processed/urban_real.json', 'manifest.json', 'archive'])
def test_modified_existing_bundle_is_rejected_instead_of_silently_replaced(sources, target):
    result = stage(sources[0], sources[1])
    file = Path(result['archive']) if target == 'archive' else Path(result['directory']) / target
    file.write_bytes(b'MODIFIED')
    with pytest.raises((ValueError, json.JSONDecodeError)):
        stage(sources[0], sources[1])
    assert file.read_bytes() == b'MODIFIED'


def test_modified_original_is_rejected_before_writing_any_bundle(sources):
    (sources[0] / 'raw/test/original.txt').write_bytes(b'MODIFIED')
    with pytest.raises(ValueError, match='modified original'):
        stage(sources[0], sources[1])
    assert not sources[1].exists()


@pytest.mark.parametrize('change', ['duplicate', 'invalid_geometry', 'wrong_crs', 'historical_allocation', 'historical_year', 'current_field_index', 'operational_records', 'bad_count', 'synthetic'])
def test_snapshot_ids_geometry_crs_original_geography_and_public_only_rules(sources, change):
    data = deepcopy(sources[2])
    if change == 'duplicate': data['settlements'].append(data['settlements'][0])
    elif change == 'invalid_geometry': data['spatial']['features'][0]['geometry'] = {'type': 'Polygon', 'coordinates': [[[0,0],[1,1],[0,1],[1,0],[0,0]]]}
    elif change == 'wrong_crs': data['spatial']['crs'] = {'properties': {'name': 'EPSG:32643'}}
    elif change == 'historical_allocation': data['indicators'][0]['settlement_id'] = 'source-label'
    elif change == 'historical_year': data['indicators'][0]['reference_year'] = 2024
    elif change == 'current_field_index': data['settlements'][0]['indicators']['water'] = 60
    elif change == 'operational_records': data['surveys'] = [{'private': 'record'}]
    elif change == 'bad_count': data['metadata']['mapped_objects_count'] = 0
    elif change == 'synthetic': data['metadata']['synthetic'] = True
    save_snapshot(sources, data)
    with pytest.raises(ValueError):
        stage(sources[0], sources[1])


def test_unsafe_original_paths_symlinks_and_output_location_are_rejected(sources):
    receipt = deepcopy(sources[3]); receipt['downloads'][0]['path'] = 'data/raw/../../.env'
    (sources[0] / 'metadata/validation.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='Unsafe'):
        stage(sources[0], sources[1])
    (sources[0] / 'metadata/validation.json').write_text(json.dumps(sources[3]))
    original = sources[0] / 'raw/test/original.txt'
    original.unlink(); original.symlink_to(sources[0] / 'metadata/validation.json')
    with pytest.raises(ValueError, match='Symlink'):
        stage(sources[0], sources[1])
    with pytest.raises(ValueError, match='separate'):
        stage(sources[0], sources[0] / 'raw/bundles')


def test_bounded_size_and_stale_validation_receipt_are_rejected(sources):
    with pytest.raises(ValueError, match='size limit'):
        stage(sources[0], sources[1], max_bytes=1)
    with pytest.raises(ValueError, match='64 MiB'):
        stage(sources[0], sources[1], max_bytes=MAX_BYTES + 1)
    receipt = deepcopy(sources[3]); receipt['datasets']['settlements']['record_count'] = 0
    (sources[0] / 'metadata/validation.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='stale'):
        stage(sources[0], sources[1])


def test_optional_overlay_keeps_historical_context_and_source_hash(sources):
    overlay(sources)
    result = stage(sources[0], sources[1])
    assert len(result['files']) == 4
    assert verify_bundle(Path(result['directory']))['validation']['originals'][0]['path'] == 'data/raw/test/original.txt'


@pytest.mark.parametrize('change', ['checksum', 'bounds', 'crs', 'analysis', 'dimensions', 'unsafe_filename', 'source_hash', 'missing_pair'])
def test_inconsistent_or_unsafe_overlay_metadata_is_rejected(sources, change):
    row = overlay(sources)
    if change == 'checksum': row['image_sha256'] = '0' * 64
    elif change == 'bounds': row['bounds'] = [73, 20, 72, 19]
    elif change == 'crs': row['crs'] = 'EPSG:4326'
    elif change == 'analysis': row['analysis_allowed'] = True
    elif change == 'dimensions': row['width'] = 3
    elif change == 'unsafe_filename': row['image_file'] = '../../.env'
    elif change == 'source_hash': row['source_sha256'] = '0' * 64
    elif change == 'missing_pair': (sources[0] / 'processed/sra_pilot_overlay.png').unlink()
    (sources[0] / 'processed/sra_pilot_overlay.json').write_text(json.dumps(row))
    with pytest.raises(ValueError):
        stage(sources[0], sources[1])


def test_nested_uploaded_content_and_unexpected_bundle_files_are_rejected(sources):
    snapshot = deepcopy(sources[2]); snapshot['metadata']['content_base64'] = 'PRIVATE UPLOADED EVIDENCE'
    save_snapshot(sources, snapshot)
    with pytest.raises(ValueError, match='uploaded evidence'):
        stage(sources[0], sources[1])
    save_snapshot(sources, sources[2])
    result = stage(sources[0], sources[1])
    (Path(result['directory']) / 'private.sqlite3').write_bytes(b'PRIVATE DB')
    with pytest.raises(ValueError, match='Unexpected'):
        verify_bundle(Path(result['directory']))


def test_public_bundle_permission_regression_is_detected(sources):
    result = stage(sources[0], sources[1])
    (Path(result['directory']) / 'processed/urban_real.json').chmod(0o600)
    with pytest.raises(ValueError, match='0644'):
        verify_bundle(Path(result['directory']))
