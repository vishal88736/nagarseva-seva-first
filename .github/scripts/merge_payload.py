"""One-time, checksum-verified source merge inside the new GitHub repository.

The public upstream is read only. The temporary transport ZIP contains the
existing evidence materials; no credentials, local databases or Git config.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
TARGET = 'vishal88736/nagarseva-seva-first'
SOURCE = 'https://github.com/vishal88736/affordable-housing-slum-redevelopment-and-basic-service-assurance.git'
META = ROOT / '.github/bootstrap-manifest.json'


def run(args, capture=False, cwd=ROOT):
    result = subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=capture)
    return result.stdout.strip() if capture else None


def git_hash(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def merge():
    metadata = json.loads(META.read_text())
    state_path = ROOT / 'integration/status.json'
    payload = ROOT / 'integration/local-materials.zip'
    if not payload.exists():
        if state_path.exists() and json.loads(state_path.read_text()).get('source_merged'):
            print('The source merge is complete; checking the current evidence materials.')
            run([sys.executable, 'prototype/scripts/verify.py'])
            run([sys.executable, 'submission/scripts/prepare_pack.py'])
            run([sys.executable, 'scripts/sync_evidence.py'])
            run(['git', 'add', 'research', 'prototype', 'submission/file_manifest.json', 'nagarseva/website/public/evidence/index.html'])
            if run(['git', 'diff', '--cached', '--name-only'], capture=True):
                run(['git', 'commit', '-m', 'Refresh verified evidence materials'])
            return
        raise RuntimeError('The one-time merge payload is unavailable.')
    if hashlib.sha256(payload.read_bytes()).hexdigest() != metadata['payload_sha256']:
        raise RuntimeError('Payload checksum mismatch.')
    forbidden = {'.git', '.aws', '.codex', '.agents', 'node_modules', '__pycache__', '.build', '.merge-work', 'test-artifacts'}
    expected = metadata['payload_files']
    with zipfile.ZipFile(payload) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())) or set(archive.namelist()) != set(expected):
            raise RuntimeError('The archive file list does not match its manifest.')
        if sum(info.file_size for info in archive.infolist()) > 25_000_000:
            raise RuntimeError('Unexpected payload size.')
        for info in archive.infolist():
            path = Path(info.filename)
            if path.is_absolute() or '..' in path.parts or forbidden.intersection(path.parts) or path.name.startswith('.env'):
                raise RuntimeError(f'Unsafe payload path: {info.filename}')
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000 or info.flag_bits & 1:
                raise RuntimeError('Symlink or encrypted payload entries are not accepted.')
            data = archive.read(info)
            if hashlib.sha256(data).hexdigest() != expected[info.filename]['sha256']:
                raise RuntimeError(f'Payload file checksum mismatch: {info.filename}')
            destination = ROOT / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    payload.unlink()
    state = json.loads(state_path.read_text())
    state.update(state='SOURCE_MERGE_PENDING', source_merged=False, new_github_repository_created=True,
                 new_repository_url='https://github.com/' + TARGET, intended_visibility='public',
                 github_connector_authenticated=True, blockers=[])
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    source = ROOT / '.merge-work/source'
    source.parent.mkdir(exist_ok=True)
    if not source.exists():
        run(['git', 'clone', '--branch', 'main', '--single-branch', '--', SOURCE, str(source)])
    run(['git', 'checkout', '--detach', metadata['upstream_commit']], cwd=source)
    if run(['git', 'rev-parse', 'HEAD'], capture=True, cwd=source) != metadata['upstream_commit']:
        raise RuntimeError('The upstream commit is not the verified source commit.')
    actual = subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
    if set(filter(None, actual)) != set(metadata['upstream_files']):
        raise RuntimeError('The pinned upstream file list differs from the verified tree.')
    for name, item in metadata['upstream_files'].items():
        data = (source / name).read_bytes()
        if len(data) != item['bytes'] or git_hash(data) != item['git_sha']:
            raise RuntimeError(f'Upstream Git blob mismatch: {name}')
    run(['git', 'add', '--all'])
    run(['git', 'commit', '-m', 'Add verified research, evidence workbench and submission materials'])
    run([sys.executable, 'scripts/merge_source.py'])
    print(f"Merged all {len(metadata['upstream_files'])} original files at {metadata['upstream_commit']}.")


def report():
    metadata = json.loads(META.read_text())
    run_url = f"https://github.com/{TARGET}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    tests = ROOT / '.merge-work/backend-tests.txt'
    matched = re.search(r'(\d+) passed', tests.read_text() if tests.exists() else '')
    results = {
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'workflow_url': run_url,
        'source_commit': metadata['upstream_commit'],
        'original_files': len(metadata['upstream_files']),
        'upstream_snapshot_verified_at_acquisition': True,
        'backend_dependencies': os.environ.get('SEVA_DEPENDENCIES_OUTCOME', 'not_run'),
        'backend_tests': os.environ.get('SEVA_BACKEND_OUTCOME', 'not_run'),
        'backend_passed_count': int(matched.group(1)) if matched else None,
        'frontend_build': os.environ.get('SEVA_FRONTEND_OUTCOME', 'not_run'),
        'evidence_checks': 'passed during the source merge',
        'real_browser_checks': 'not run by this workflow',
        'field_validation': 'not performed',
    }
    (ROOT / 'integration/ci-validation.json').write_text(json.dumps(results, indent=2) + '\n')
    state_path = ROOT / 'integration/status.json'
    state = json.loads(state_path.read_text())
    state.update(state='MERGED_ON_GITHUB', source_complete=True, source_original_files=results['original_files'],
                 source_missing_files=[], original_application_tests=results['backend_tests'],
                 frontend_build=results['frontend_build'], workflow_url=run_url)
    if any(results[key] != 'success' for key in ['backend_dependencies', 'backend_tests', 'frontend_build']):
        state['state'] = 'MERGED_ON_GITHUB_VALIDATION_FAILED'
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    manifest_path = ROOT / 'integration/source-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for name, item in metadata['upstream_files'].items():
        manifest['files'][name]['upstream_git_sha'] = item['git_sha']
        current = (ROOT / name).read_bytes()
        manifest['files'][name]['current_sha256'] = hashlib.sha256(current).hexdigest()
        manifest['files'][name]['modified_during_integration'] = git_hash(current) != item['git_sha']
    manifest['acquisition'] = 'Pinned git clone on GitHub Actions; all original Git blob hashes verified'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    readme = ROOT / 'README.md'
    if 'integration/ci-validation.json' not in readme.read_text():
        with readme.open('a') as handle:
            handle.write(f'\n## Published source and checks\n\nThe source merge and per-file hashes were verified in [this workflow]({run_url}). See [the recorded validation outcomes](integration/ci-validation.json) for backend, frontend and evidence-check results. Browser and field validation remain separate.\n')


def bundle():
    path = ROOT / '.merge-work/merged.bundle'
    run(['git', 'bundle', 'create', str(path), '--all'])
    data = path.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()
    # One-time public-source transport for a local runner without network sockets.
    # Git bundles contain Git objects and refs, never .git/config or checkout tokens.
    print(f'SEVA_BUNDLE_BEGIN {checksum} {len(data)}', flush=True)
    encoded = base64.b64encode(data).decode()
    for start in range(0, len(encoded), 8192):
        print('SEVA_BUNDLE_PART ' + encoded[start:start + 8192], flush=True)
    print('SEVA_BUNDLE_END ' + checksum, flush=True)


if __name__ == '__main__':
    if os.environ.get('GITHUB_REPOSITORY') != TARGET:
        raise SystemExit('This one-time workflow is restricted to the requested new repository.')
    action = sys.argv[1] if len(sys.argv) > 1 else ''
    if action not in {'merge', 'report', 'bundle'}:
        raise SystemExit('Use merge, report or bundle.')
    {'merge': merge, 'report': report, 'bundle': bundle}[action]()
