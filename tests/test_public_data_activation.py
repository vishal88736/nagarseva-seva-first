"""Activation connects real source tables without replacing user or operational data."""
from pathlib import Path
import sqlite3
import json

import pytest
from test_public_data_staging import sources
from activate_public_data import activate
from model.api.public_store import PublicStore
from model.api.store import RecordStore


def test_activation_populates_database_and_source_mount_and_is_idempotent(sources):
    data,output,snapshot,_=sources
    workspace=output.parent/'workspace'
    result=activate(data,workspace,output)
    public=PublicStore(RecordStore(workspace/'workspace.sqlite3'),workspace/'input')
    assert len(public.settlements())==len(snapshot['settlements'])==1
    assert len(public.context()['observations'])==1
    assert len(public.projects())==0
    assert result['historical_boundary_join_count']==0
    assert result['current_service_indices_added']==0
    assert (workspace/'input/urban_real.json').is_file()
    assert (workspace/'metadata/dataset_inventory.csv').is_file()
    assert activate(data,workspace,output)==result
    assert not (workspace/'backups').exists()


def test_activation_backs_up_existing_database_and_retains_operational_rows(sources):
    data,output,_,_=sources;workspace=output.parent/'workspace';workspace.mkdir()
    store=RecordStore(workspace/'workspace.sqlite3');PublicStore(store,workspace/'input')
    with store.connection(write=True) as db:
        db.execute("INSERT INTO urban_records VALUES(?,?,?,?)",('local-existing','complaint','TEST',json.dumps({'id':'local-existing','text':'TEST ONLY retained'})))
    result=activate(data,workspace,output)
    assert Path(result['backup']).is_file()
    with sqlite3.connect(workspace/'workspace.sqlite3') as db: assert db.execute('SELECT COUNT(*) FROM urban_records WHERE id=?',('local-existing',)).fetchone()[0]==1
    assert activate(data,workspace,output)==result
    assert len(list((workspace/'backups').iterdir()))==1


def test_activation_refuses_to_replace_an_imported_workspace(sources):
    data,output,_,_=sources;workspace=output.parent/'workspace';workspace.mkdir()
    store=RecordStore(workspace/'workspace.sqlite3');PublicStore(store,workspace/'input')
    with store.connection(write=True) as db: db.execute('INSERT INTO public_snapshots VALUES(?,?,?)',('user-data','2099-01-01',json.dumps({'source_type':'user_import'})))
    with pytest.raises(ValueError,match='user import'):activate(data,workspace,output)
    assert not (workspace/'input/urban_real.json').exists()
