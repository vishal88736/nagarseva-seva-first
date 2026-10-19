"""Verified upstream history survives authorized source cleanup in CI receipts."""
import hashlib
import importlib.util
import json

import pytest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/merge_payload.py'
spec = importlib.util.spec_from_file_location('merge_payload', SCRIPT)
merge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge)


def test_manifest_preserves_original_checksums_and_reports_removed_files(tmp_path):
    original = b'original source\n'
    original_sha = hashlib.sha256(original).hexdigest()
    names = ['unchanged.py', 'edited.py', 'dead.py']
    metadata = {'upstream_files': {name: {'git_sha': merge.git_hash(original)} for name in names}}
    manifest = {'files': {name: {'sha256': original_sha, 'bytes': len(original)} for name in names}}
    (tmp_path / 'unchanged.py').write_bytes(original)
    (tmp_path / 'edited.py').write_bytes(b'active implementation\n')
    assert merge.annotate_current_sources(manifest, metadata, tmp_path) == ['dead.py']
    assert manifest['files']['unchanged.py']['modified_during_integration'] is False
    assert manifest['files']['edited.py']['modified_during_integration'] is True
    removed = manifest['files']['dead.py']
    assert removed['removed_since_acquisition'] is True
    assert removed['current_sha256'] is None
    assert removed['sha256'] == original_sha
    assert removed['upstream_git_sha'] == merge.git_hash(original)
    assert manifest['source_files_removed_since_acquisition'] == ['dead.py']
    # Receipts are safe to refresh repeatedly and record a later restoration.
    (tmp_path / 'dead.py').write_bytes(original)
    assert merge.annotate_current_sources(manifest, metadata, tmp_path) == []
    assert removed['removed_since_acquisition'] is False
    assert removed['current_sha256'] == original_sha


def test_report_distinguishes_upstream_validated_checkout_and_trigger(tmp_path, monkeypatch):
    upstream, checkout, trigger = '1' * 40, '2' * 40, '3' * 40
    source = b'Test original source\n'
    (tmp_path / 'source.py').write_bytes(source)
    metadata = {'upstream_commit': upstream, 'upstream_files': {'source.py': {'git_sha': merge.git_hash(source)}}}
    for name in ['integration', '.merge-work']:
        (tmp_path / name).mkdir()
    metadata_path = tmp_path / 'bootstrap.json'
    metadata_path.write_text(json.dumps(metadata))
    (tmp_path / '.merge-work/backend-tests.txt').write_text('12 passed in 1s\n')
    (tmp_path / 'integration/status.json').write_text('{}')
    (tmp_path / 'integration/source-manifest.json').write_text(json.dumps({'files': {'source.py': {'sha256': hashlib.sha256(source).hexdigest()}}}))
    (tmp_path / 'README.md').write_text('See integration/ci-validation.json for checks.\n')
    monkeypatch.setattr(merge, 'ROOT', tmp_path)
    monkeypatch.setattr(merge, 'META', metadata_path)
    def revision(args, capture=False, **kwargs):
        assert args == ['git', 'rev-parse', 'HEAD'] and capture is True
        return checkout
    monkeypatch.setattr(merge, 'run', revision)
    monkeypatch.setenv('GITHUB_SHA', trigger)
    monkeypatch.setenv('GITHUB_RUN_ID', 'test-only')
    for outcome in ['DEPENDENCIES', 'BACKEND', 'FRONTEND', 'BROWSER']:
        monkeypatch.setenv(f'SEVA_{outcome}_OUTCOME', 'success')
    merge.report()
    receipt = json.loads((tmp_path / 'integration/ci-validation.json').read_text())
    assert receipt['source_commit'] == receipt['upstream_source_commit'] == upstream
    assert receipt['validated_checkout_commit'] == checkout
    assert receipt['triggering_commit'] == trigger
    assert 'not the checkout' in receipt['source_commit_scope']
    assert 'report time' in receipt['validated_checkout_commit_scope']
    assert receipt['backend_passed_count'] == 12
    status = json.loads((tmp_path / 'integration/status.json').read_text())
    assert status['validated_checkout_commit'] == checkout
    assert status['triggering_commit'] == trigger
    assert status['source_commit_scope'] == receipt['source_commit_scope']


@pytest.mark.parametrize('trigger', [None, '', 'not-a-sha', 'a' * 39, 'a' * 41, '$(private-command)', 'b' * 40 + '\n'])
def test_missing_or_invalid_trigger_sha_is_null_without_inventing_a_commit(monkeypatch, trigger):
    if trigger is None:
        monkeypatch.delenv('GITHUB_SHA', raising=False)
    else:
        monkeypatch.setenv('GITHUB_SHA', trigger)
    monkeypatch.setattr(merge, 'run', lambda *args, **kwargs: 'a' * 40)
    receipt = merge.validation_provenance({'upstream_commit': '1' * 40})
    assert receipt['triggering_commit'] is None
    assert receipt['validated_checkout_commit'] == 'a' * 40


def test_valid_sha_case_is_normalized_but_unavailable_checkout_fails_closed(monkeypatch):
    monkeypatch.setenv('GITHUB_SHA', 'C' * 40)
    monkeypatch.setattr(merge, 'run', lambda *args, **kwargs: 'B' * 40)
    receipt = merge.validation_provenance({'upstream_commit': '1' * 40})
    assert receipt['triggering_commit'] == 'c' * 40
    assert receipt['validated_checkout_commit'] == 'b' * 40
    monkeypatch.setattr(merge, 'run', lambda *args, **kwargs: 'short-ref')
    with pytest.raises(ValueError, match='validated checkout'):
        merge.validation_provenance({'upstream_commit': '1' * 40})
