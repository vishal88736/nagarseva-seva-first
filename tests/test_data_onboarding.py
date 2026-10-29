"""Actual parsing, mapping and controlled import, using explicitly synthetic files."""
import base64
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from model.api.urban import create_app

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('NAGARSEVA_OFFICER_KEY','test-import-key')
    with TestClient(create_app(tmp_path/'test.sqlite3',tmp_path/'no-real-source')) as client:yield client

def file(text,name='TEST-ONLY.csv'):
    raw=text.encode() if isinstance(text,str) else text
    return {'filename':name,'contentBase64':base64.b64encode(raw).decode(),'permissionAccepted':True}
def mapped(text='id,name\nTEST-1,Demo File Settlement\n',**changes):return {**file(text),'category':'identifiers','mapping':{'id':'id','name':'name'},'crsConfirmed':False,'settlementBatchId':None,**changes}
def import_payload(payload):
    raw=base64.b64decode(payload['contentBase64'])
    return {**payload,'confirm':True,'expectedSha256':hashlib.sha256(raw).hexdigest(),'sourceName':'TEST ONLY synthetic source','publisher':'TEST ONLY demo publisher','sourceUrl':'https://example.test/demo-data','sourceDate':'2026-10-01','licence':'Demo data - test use','dataClass':'demo','publicationYear':None,'coverage':'TEST ONLY illustrative records'}
def do_import(client,payload):return client.post('/urban/integration/imports',json=import_payload(payload),headers={'X-Officer-Key':'test-import-key'})
def square():return {'type':'Feature','properties':{'Cluster_ID':'TEST-1','Slum_Name':'Demo File Settlement','Ward':'TEST WARD'},'geometry':{'type':'Polygon','coordinates':[[[72.87,19.05],[72.88,19.05],[72.88,19.06],[72.87,19.06],[72.87,19.05]]]}}

def test_no_real_dataset_is_claimed_connected(client):
    data=client.get('/urban/integration/readiness').json()
    assert data['activeAdapter']=='sqlite-synthetic' and data['externalConnected'] is False
    assert len(data['categories'])==7 and all(row['status']=='not_provided' for row in data['categories'])
    assert client.get('/urban/integration/imports').status_code==401


def test_actual_csv_inspection_quotes_bom_rows_and_no_storage(client):
    raw='\ufeffid,name,notes\r\nTEST-1,"Demo, Test","quoted\nmultiline"\r\n'.encode()
    response=client.post('/urban/integration/inspect',json=file(raw));assert response.status_code==200,response.text
    inspection=response.json();assert inspection['recordCount']==1 and inspection['columns']==['id','name','notes']
    assert inspection['bytes']==len(raw) and inspection['sha256']==hashlib.sha256(raw).hexdigest() and inspection['stored'] is False
    result=client.post('/urban/integration/validate',json=mapped(raw)).json()
    assert result['valid'] and result['preview'][0]['name']=='Demo, Test'
    with client.app.state.store.connection() as db:assert db.execute('SELECT COUNT(*) FROM civic_import_batches').fetchone()[0]==0

@pytest.mark.parametrize('payload',[{**file('id,name\nX,Y'),'permissionAccepted':False},file('data','test.kml'),file(b''),file(b'\xff'),file('id,id\nX,Y'),file('id,name\nX,Y,Z'),file('{not json','test.geojson'),file('{}','test.json'),file('id,name\n'+('x'*(5*1024*1024)))] )
def test_unsupported_invalid_or_oversize_sources_do_not_import(client,payload):
    response=client.post('/urban/integration/inspect',json=payload)
    assert response.status_code==422 or response.status_code==200 and response.json()['errorCount']>0
    assert client.get('/urban/integration/readiness').json()['categories'][0]['recordCount']==0


def test_geojson_metadata_geometry_and_suggestions_use_only_actual_fields(client):
    document={'type':'FeatureCollection','features':[square()]};payload=file(json.dumps(document),'TEST.geojson')
    inspection=client.post('/urban/integration/inspect',json=payload).json()
    assert inspection['recordCount']==1 and inspection['format']=='GeoJSON'
    assert inspection['bounds']==[72.87,19.05,72.88,19.06]
    assert inspection['suggestions']['boundaries']=={'id':'Cluster_ID','name':'Slum_Name','geometry':'@geometry','ward':'Ward'}
    assert all(value in inspection['columns'] for value in inspection['suggestions']['boundaries'].values())
    mapped_geo={**payload,'category':'boundaries','mapping':inspection['suggestions']['boundaries'],'crsConfirmed':True,'settlementBatchId':None}
    validated=client.post('/urban/integration/validate',json=mapped_geo).json()
    assert validated['valid'] and validated['preview'][0]['id']=='TEST-1'
    assert validated['bounds']==inspection['bounds']
    mapped_geo['crsConfirmed']=False
    assert not client.post('/urban/integration/validate',json=mapped_geo).json()['valid']


def test_missing_mapping_duplicate_ids_and_bad_geometry_are_explicit(client):
    assert not client.post('/urban/integration/validate',json=mapped(mapping={'id':'id'})).json()['valid']
    result=client.post('/urban/integration/validate',json=mapped('id,name\nTEST-1,Demo One\nTEST-1,Demo Two\n')).json()
    assert result['errorCount']==1 and result['errors'][0]['code']=='ir.error.duplicate'
    malformed=square();malformed['geometry']['coordinates'][0].pop()
    payload={**file(json.dumps({'type':'FeatureCollection','features':[malformed]}),'bad.geojson'),'category':'boundaries','mapping':{'id':'Cluster_ID','name':'Slum_Name','geometry':'@geometry'},'crsConfirmed':True,'settlementBatchId':None}
    assert not client.post('/urban/integration/validate',json=payload).json()['valid']
    payload['category']='identifiers';payload['mapping']={'id':'Cluster_ID','name':'Slum_Name'}
    assert not client.post('/urban/integration/validate',json=payload).json()['valid'], 'Unmapped but present source geometry must still be checked'


def test_confirmed_import_preserves_bytes_provenance_and_active_demo(client):
    payload=mapped();body=import_payload(payload)
    assert client.post('/urban/integration/imports',json=body).status_code==401
    assert client.post('/urban/integration/imports',json={**body,'confirm':False},headers={'X-Officer-Key':'test-import-key'}).status_code==422
    created=do_import(client,payload);assert created.status_code==200,created.text
    receipt=created.json();assert receipt['recordCount']==1 and receipt['stored'] and not receipt['sourceVerified'] and not receipt['active']
    assert receipt['provenance']['publicationYear'] is None
    assert do_import(client,payload).json()['replayed'] is True
    original=client.get('/urban/integration/imports/'+receipt['id']+'/original',headers={'X-Officer-Key':'test-import-key'}).content
    assert original==base64.b64decode(payload['contentBase64'])
    assert len(client.get('/urban/demo/workspace').json()['settlements'])==100
    readiness=client.get('/urban/integration/readiness').json()
    assert next(row for row in readiness['categories'] if row['category']=='identifiers')['status']=='imported_demo' and not readiness['externalConnected']
    assert do_import(client,mapped('id,name\nTEST-1,Demo Conflicting Name')).status_code==409
    assert client.post('/urban/integration/imports',json={**body,'expectedSha256':'0'*64},headers={'X-Officer-Key':'test-import-key'}).status_code==409


def test_linked_services_validate_types_dates_ranges_and_foreign_keys(client):
    batch=do_import(client,mapped()).json()['id']
    def service(text):return {**file(text),'category':'services','mapping':{'id':'id','settlementId':'settlement_id','measurementDate':'date','waterAccessPercent':'coverage'},'crsConfirmed':False,'settlementBatchId':batch}
    valid=service('id,settlement_id,date,coverage\nTEST-OBS-1,TEST-1,2026-10-01,75\n')
    assert client.post('/urban/integration/validate',json=valid).status_code==401
    result=client.post('/urban/integration/validate',json=valid,headers={'X-Officer-Key':'test-import-key'}).json();assert result['valid'],result
    for text in ['id,settlement_id,date,coverage\nX,TEST-1,invalid,75','id,settlement_id,date,coverage\nX,TEST-1,2026-10-01,101','id,settlement_id,date,coverage\nX,DEMO-SET-001,2026-10-01,75']:
        result=client.post('/urban/integration/validate',json=service(text),headers={'X-Officer-Key':'test-import-key'}).json();assert not result['valid']
    assert do_import(client,valid).status_code==200


def test_source_url_cannot_be_a_fetch_or_credential_channel(client):
    for url in ['javascript:alert(1)','https://user:secret@example.test/file','file:///etc/passwd']:
        response=client.post('/urban/integration/imports',json={**import_payload(mapped()),'sourceUrl':url},headers={'X-Officer-Key':'test-import-key'})
        assert response.status_code==422

@pytest.mark.parametrize('change', [
    lambda feature:feature.update(properties=['not','a','property','object']),
    lambda feature:feature['geometry']['coordinates'][0].__setitem__(1,[181,19.05]),
    lambda feature:feature['geometry'].update(coordinates=[[[72.87,19.05],[72.88,19.06],[72.88,19.05],[72.87,19.06],[72.87,19.05]]]),
])
def test_invalid_geography_does_not_get_valid_bounds_or_import(client,change):
    feature=square();change(feature)
    payload={**file(json.dumps({'type':'FeatureCollection','features':[feature]}),'TEST.geojson'),'category':'boundaries','mapping':{'id':'Cluster_ID','name':'Slum_Name','geometry':'@geometry'},'crsConfirmed':True,'settlementBatchId':None}
    response=client.post('/urban/integration/validate',json=payload)
    assert response.status_code==200 and not response.json()['valid']
    assert do_import(client,payload).status_code==422


def test_missing_source_identifiers_are_not_synthesized(client):
    feature=square();feature['properties']={'polyno':None}
    payload={**file(json.dumps({'type':'FeatureCollection','features':[feature]}),'TEST.geojson'),'category':'boundaries','mapping':{'id':'polyno','geometry':'@geometry'},'crsConfirmed':True,'settlementBatchId':None}
    result=client.post('/urban/integration/validate',json=payload).json()
    assert not result['valid'] and result['preview'][0]['id'] is None
    assert 'name' in result['missingRequiredFields']
    assert not client.post('/urban/integration/validate',json=mapped('id,name\nTEST-1,   \n')).json()['valid']


def test_mapping_changes_use_actual_columns_without_implicit_values(client):
    payload=mapped('code,label\nTEST-2,Demo mapped row\n',mapping={'id':'code','name':'label'})
    result=client.post('/urban/integration/validate',json=payload).json()
    assert result['valid'] and result['preview']==[{'id':'TEST-2','name':'Demo mapped row'}]
    for mapping in [{'id':'absent','name':'label'},{'id':'code','name':'code'}]:
        assert not client.post('/urban/integration/validate',json={**payload,'mapping':mapping}).json()['valid']


def test_controlled_enums_and_date_order_are_not_inferred(client):
    batch=do_import(client,mapped()).json()['id']
    payload={**file('id,settlement_id,category,status,created,resolved\nTEST-ISSUE,TEST-1,water,open,2026-10-01T00:00:00Z,2026-10-02T00:00:00Z\n'),'category':'issues','mapping':{'id':'id','settlementId':'settlement_id','category':'category','status':'status','createdAt':'created','resolvedAt':'resolved'},'crsConfirmed':False,'settlementBatchId':batch}
    headers={'X-Officer-Key':'test-import-key'}
    assert client.post('/urban/integration/validate',json=payload,headers=headers).json()['valid']
    for raw,code in [('id,settlement_id,category,status,created,resolved\nTEST-ISSUE,TEST-1,water,not-an-enum,2026-10-01,2026-10-02','ir.error.enum'),('id,settlement_id,category,status,created,resolved\nTEST-ISSUE,TEST-1,water,open,2026-10-02,2026-10-01','ir.error.chronology')]:
        result=client.post('/urban/integration/validate',json={**payload,**file(raw)},headers=headers).json()
        assert not result['valid'] and any(error['code']==code for error in result['errors'])


def test_unconfigured_authorization_never_reports_an_import(client,monkeypatch):
    monkeypatch.delenv('NAGARSEVA_OFFICER_KEY')
    assert client.post('/urban/integration/imports',json=import_payload(mapped())).status_code==503
    assert all(row['status']=='not_provided' for row in client.get('/urban/integration/readiness').json()['categories'])
