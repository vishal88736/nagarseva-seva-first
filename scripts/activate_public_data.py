"""Connect a validated local public-data bundle to an existing SQLite workspace.

Preserves operational records and first backs up the database. A user-imported
workspace is never replaced. No network requests, geometry joins or new indicators.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from data_common import ROOT
from stage_public_data import stage, verify_bundle

sys.path.insert(0, str(ROOT / 'nagarseva'))
from model.api.public_store import PublicStore
from model.api.store import RecordStore


def copy_immutable(target, raw):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != raw:
            raise ValueError('Existing workspace input differs; choose a new input directory: ' + target.name)
    else:
        target.write_bytes(raw)
        target.chmod(0o600)


def activate(data_root: Path, workspace: Path, bundle_output: Path):
    data_root, workspace, bundle_output = map(Path, (data_root, workspace, bundle_output))
    result = stage(data_root, bundle_output)
    bundle = Path(result['directory']); manifest = verify_bundle(bundle)
    database = workspace / 'workspace.sqlite3'
    inputs = workspace / 'input'
    # Inspect before mutating. User imports take precedence over source mounts.
    active = None
    if database.exists():
        with sqlite3.connect(database) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'public_snapshots' in tables:
                row = db.execute('SELECT body FROM public_snapshots ORDER BY imported_at DESC, rowid DESC LIMIT 1').fetchone()
                active = json.loads(row[0]) if row else None
    if active and active.get('source_type') == 'user_import':
        raise ValueError('This workspace contains a user import. Use a separate workspace for acquired public data.')
    # Check all destinations before writing any input file.
    payloads = [(workspace / relative.replace('processed/', 'input/', 1), (bundle / relative).read_bytes()) for relative in manifest['files']]
    for target, raw in payloads:
        if target.exists() and target.read_bytes() != raw:
            raise ValueError('Workspace source changed; choose a separate workspace rather than overwrite input files')
    expected = hashlib.sha256((bundle / 'processed/urban_real.json').read_bytes()).hexdigest()
    receipt_path = workspace / 'public-data-activation.json'
    if active and active.get('snapshot_sha256') == expected and receipt_path.exists():
        return json.loads(receipt_path.read_text())
    workspace.mkdir(parents=True, exist_ok=True); workspace.chmod(0o700)
    backup = None
    if database.exists():
        backups = workspace / 'backups'; backups.mkdir(parents=True, exist_ok=True); backups.chmod(0o700)
        backup = backups / ('before-public-data-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.sqlite3')
        with sqlite3.connect(database) as source, sqlite3.connect(backup) as destination:
            source.backup(destination)
        backup.chmod(0o600)
    for target, raw in payloads:
        copy_immutable(target, raw)
    store = RecordStore(database)
    provider = PublicStore(store, inputs)
    metadata = provider.metadata()
    expected = hashlib.sha256((inputs / 'urban_real.json').read_bytes()).hexdigest()
    if metadata.get('snapshot_sha256') != expected:
        raise ValueError('The validated source snapshot did not become active')
    source_snapshot=json.loads((inputs/'urban_real.json').read_text())
    receipt = {'activated_at':datetime.now(timezone.utc).isoformat(),'bundle_id':manifest['bundle_id'],
               'snapshot_sha256':expected,'workspace':str(workspace),'backup':str(backup) if backup else None,
               'counts':result['snapshot_counts'],'originals_checked':result['originals_checked'],
               'source_vintages':{'register':source_snapshot['metadata'].get('settlement_reference'),'census':sorted({row['reference_year'] for row in source_snapshot.get('geographic_units',[])})},
               'historical_boundary_join_count':0,'current_service_indices_added':0}
    (workspace / 'public-data-activation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=ROOT/'data')
    parser.add_argument('--workspace',type=Path,default=ROOT/'.runtime/my-workspace')
    parser.add_argument('--bundle-output',type=Path,default=ROOT/'.runtime/public-data-bundles')
    args=parser.parse_args()
    try:
        print(json.dumps(activate(args.data_root,args.workspace,args.bundle_output),ensure_ascii=False,indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise SystemExit('Public-data activation failed: '+str(exc)) from exc


if __name__=='__main__': main()
