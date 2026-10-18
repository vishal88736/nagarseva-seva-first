"""Verified upstream history survives authorized source cleanup in CI receipts."""
import hashlib
import importlib.util
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
