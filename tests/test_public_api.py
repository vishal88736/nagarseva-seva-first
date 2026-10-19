"""SQLite/API workflow tests; fixtures do not represent real field observations."""
import base64
from datetime import datetime, timezone
import json

from fastapi.testclient import TestClient
import pytest
from model.api.urban import create_app
from model.src.urban_planning import DEFAULT_WEIGHTS

NOW=lambda:datetime.now(timezone.utc).isoformat()


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('NAGARSEVA_OFFICER_KEY','fixture-key')
    monkeypatch.setenv('URBANSAARTHI_EVIDENCE_STORAGE','sqlite')
    source=tmp_path/'processed';source.mkdir()
    metadata={"synthetic":False,"settlement_count":1,"settlement_geometry_count":0,"projects_count":1,"mapped_objects_count":1,"limitations":[]}
    settlement={"id":"source-label","source_id":"ME_TEST","name":"Fixture label","geometry":None,"administrative_area":"Test","source":"https://example.test/map","source_date":"2024","data_completeness":0,"indicators":{k:None for k in DEFAULT_WEIGHTS},"synthetic":False}
    project={"id":"fixture-project","source_id":None,"settlement_id":None,"scheme_name":"Fixture project","project_status":"unknown","source_date":None,"source_url":"https://example.test/schemes","geometry":None}
    spatial={"type":"FeatureCollection","features":[{"type":"Feature","id":"node/1","properties":{"category":"amenity","name":"=formula-test"},"geometry":{"type":"Point","coordinates":[72.92,19.06]}}]}
    (source/'urban_real.json').write_text(json.dumps({"metadata":metadata,"settlements":[settlement],"projects":[project],"spatial":spatial,"indicators":[]}))
    app=create_app(tmp_path/'api.sqlite3',source)
    c=TestClient(app); c.headers['X-Officer-Key']='fixture-key'
    yield c


def work(client):
    payload={"settlement_id":"source-label","intervention_type":"water","description":"Fixture water repair","planned_start":"2026-01-01","planned_end":"2026-01-02","estimated_cost":100,"actor":"contractor","target_value":8,"measurement_unit":"hours/day"}
    r=client.post('/urban/data/interventions',json=payload); assert r.status_code==201,r.text
    return r.json()


def transition(client,item,action):
    return client.post(f"/urban/data/interventions/{item['id']}/actions",json={"action":action,"actor":"contractor","notes":"Fixture workflow action"})


def evidence(client,item,actor='inspector'):
    r=client.post(f"/urban/data/interventions/{item['id']}/evidence",json={"filename":"fixture.txt","content_type":"text/plain","content_base64":base64.b64encode(b'fixture inspection').decode(),"actor":actor,"notes":"Test-only inspection evidence"})
    assert r.status_code==201,r.text
    return r.json()


def verification(ev,**changes):
    return {"verification_type":"inspection","evidence_reference":ev['id'],"outcome":"passed","verifier_reference":"reviewer","observed_at":NOW(),"measured_value":8,"functioning_confirmed":True,"notes":"Fixture review only",**changes}


def test_public_listing_detail_pagination_and_missing_observations(client):
    assert client.get('/urban/data/health').json()['synthetic'] is False
    assert client.get('/urban/data/settlements?page_size=1').json()['total']==1
    assert client.get('/urban/data/settlements?page=2').json()['items']==[]
    assert client.get('/urban/data/settlements?page_size=0').status_code==422
    assert client.get('/urban/data/settlements/missing').status_code==404
    row=client.post('/urban/data/priority',json={}).json()['items'][0]
    assert row['score'] is row['rank'] is None and row['coverage_pct']==0 and row['upper']==100
    assert client.get('/urban/data/indicators').json()['items']==[]
    assert client.get('/urban/data/projects').json()['items'][0]['settlement_id'] is None


def test_spatial_layers_bbox_and_input_validation(client):
    assert client.get('/urban/data/spatial?category=amenity').json()['total']==1
    assert client.get('/urban/data/spatial?category=settlement').json()['total']==0
    assert client.get('/urban/data/spatial?category=project').json()['total']==0
    assert client.get('/urban/data/spatial?bbox=73,20,74,21').json()['total']==0
    for q in ['category=DROP TABLE','bbox=bad','bbox=nan,0,1,2','bbox=180,0,-180,1','limit=10001','offset=-1','category=amenity,settlement']:
        assert client.get('/urban/data/spatial?'+q).status_code==422


def test_weight_validation(client):
    for weights in [{k:0 for k in DEFAULT_WEIGHTS},{'water':1},{**DEFAULT_WEIGHTS,'risk':-1},{**DEFAULT_WEIGHTS,'risk':True}]:
        assert client.post('/urban/data/priority',json={'weights':weights}).status_code==422


def test_auth_is_required_for_operational_records_and_no_demo_leak(client,monkeypatch):
    assert client.get('/urban/data/interventions',headers={'X-Officer-Key':''}).status_code==401
    monkeypatch.delenv('NAGARSEVA_OFFICER_KEY')
    assert client.get('/urban/data/interventions').status_code==503
    assert client.get('/urban/data/settlements').status_code==200


def test_no_snapshot_is_a_real_empty_state_and_does_not_seed_synthetic_records(tmp_path):
    c=TestClient(create_app(tmp_path/'empty.sqlite3',tmp_path/'unavailable'))
    assert c.get('/urban/data/settlements').json()['items']==[]
    assert c.get('/urban/data/health').json()['snapshot_loaded'] is False


def test_intervention_update_conflict_and_persistence(client):
    item=work(client)
    assert transition(client,item,'report_complete').status_code==409
    r=client.patch('/urban/data/interventions/'+item['id'],json={'description':'Revised fixture plan','actor':'planner'})
    assert r.status_code==200 and r.json()['description']=='Revised fixture plan'
    assert client.patch('/urban/data/interventions/'+item['id'],json={'planned_end':'2025-01-01','actor':'planner'}).status_code==422
    assert client.get('/urban/data/interventions').json()['items'][0]['description']=='Revised fixture plan'
    client.app.state.public.sync_snapshot()
    assert len(client.get('/urban/data/interventions').json()['items'])==1
    assert len(client.get('/urban/data/settlements').json()['items'])==1
    assert client.get('/urban/state').json()['works']==[]


def test_complete_never_automatically_verifies_and_review_requires_evidence(client):
    item=work(client)
    assert transition(client,item,'start').status_code==200
    assert transition(client,item,'report_complete').json()['status']=='reported_complete'
    assert client.get('/urban/data/overview').json()['awaiting_verification']==1
    assert transition(client,item,'request_verification').json()['status']=='awaiting_verification'
    ev=evidence(client,item)
    for changes in [{'verifier_reference':'contractor'},{'verifier_reference':'inspector'},{'measured_value':7},{'functioning_confirmed':False},{'observed_at':'2011-01-01T00:00:00+00:00'}]:
        assert client.post(f"/urban/data/interventions/{item['id']}/verifications",json=verification(ev,**changes)).status_code==422
    r=client.post(f"/urban/data/interventions/{item['id']}/verifications",json=verification(ev))
    assert r.status_code==201,r.text
    assert client.get('/urban/data/interventions').json()['items'][0]['status']=='verified'
    assert len(client.get('/urban/data/verifications').json()['items'])==1
    assert client.post(f"/urban/data/interventions/{item['id']}/actions",json={'action':'start','actor':'contractor','notes':'Fixture attempt'}).status_code==409


def test_complaint_disputes_verified_work_and_resolving_does_not_reverify(client):
    item=work(client)
    for action in ['start','report_complete','request_verification']: assert transition(client,item,action).status_code==200
    ev=evidence(client,item)
    assert client.post(f"/urban/data/interventions/{item['id']}/verifications",json=verification(ev)).status_code==201
    complaint=client.post('/urban/data/complaints',json={'settlement_id':'source-label','intervention_id':item['id'],'service_type':'water','description':'Fixture issue reappeared'}).json()
    assert client.get('/urban/data/interventions').json()['items'][0]['status']=='requiring_reinspection'
    assert client.post(f"/urban/data/interventions/{item['id']}/verifications",json=verification(ev)).status_code==409
    assert client.patch('/urban/data/complaints/'+complaint['id'],json={'status':'resolved','actor':'officer','resolution_details':'Response recorded for fixture'}).status_code==200
    assert client.get('/urban/data/interventions').json()['items'][0]['status']=='requiring_reinspection'
    assert client.post(f"/urban/data/interventions/{item['id']}/verifications",json=verification(ev)).status_code==422
    fresh=evidence(client,item)
    assert client.post(f"/urban/data/interventions/{item['id']}/verifications",json=verification(fresh,verification_type='reinspection')).status_code==201


def test_complaint_without_intervention_and_safe_export(client):
    r=client.post('/urban/data/complaints',json={'settlement_id':'source-label','service_type':'sanitation','description':'=FORMULA fixture description'})
    assert r.status_code==201
    out=client.get('/urban/data/reports/complaints.csv')
    assert out.status_code==200 and "'=FORMULA" in out.text
    assert client.get('/urban/data/reports/unknown.csv').status_code==422


def test_evidence_storage_signatures_and_unknown_record_errors(client,monkeypatch):
    item=work(client)
    monkeypatch.delenv('URBANSAARTHI_EVIDENCE_STORAGE')
    payload={'filename':'bad.png','content_type':'image/png','content_base64':'eA==','actor':'inspector','notes':'Test-only upload'}
    assert client.post(f"/urban/data/interventions/{item['id']}/evidence",json=payload).status_code==503
    monkeypatch.setenv('URBANSAARTHI_EVIDENCE_STORAGE','sqlite')
    assert client.post(f"/urban/data/interventions/{item['id']}/evidence",json=payload).status_code==422
    assert client.post('/urban/data/interventions/missing/evidence-references',json={'evidence_reference':'https://example.test/proof','actor':'inspector','notes':'Fixture evidence'}).status_code==404
    payload['content_type']='text/plain';payload['content_base64']='!!!'
    assert client.post(f"/urban/data/interventions/{item['id']}/evidence",json=payload).status_code==422
    ev=evidence(client,item)
    assert client.get('/urban/data/evidence/'+ev['id']+'/content').content==b'fixture inspection'


def obs(**kw):
    return {'settlement_id':'source-label','indicator_type':'water','value':80,'unit':'deficit_0_100','reference_year':datetime.now(timezone.utc).year,'observation_date':NOW(),'geographic_resolution':'settlement','source':'Fixture survey source','verification_status':'field_verified','inspector_reference':'inspector','reviewer_reference':'reviewer','method':'Test-only approved-index fixture','evidence_reference':'https://example.test/fixture',**kw}


def test_observations_preserve_missingness_year_and_geography(client):
    assert client.post('/urban/data/indicators',json=obs(id='test-observation')).status_code==201
    assert client.post('/urban/data/indicators',json=obs(id='test-observation')).status_code==409
    r=client.post('/urban/data/priority',json={}).json()['items'][0]
    assert r['score'] is None and r['coverage_pct']==30 and r['contributions']['water']==24
    for changes in [{'geographic_resolution':'ward'},{'value':101},{'reviewer_reference':'inspector'},{'settlement_id':'missing'},{'observation_date':'2011-01-01T00:00:00Z'}]:
        expected=404 if changes.get('settlement_id')=='missing' else 422
        assert client.post('/urban/data/indicators',json=obs(**changes)).status_code==expected
    assert client.post('/urban/data/indicators',json=obs(value=None,verification_status='reported')).status_code==201


def test_historical_state_counts_are_kept_out_of_settlement_priority(client):
    unit={'id':'census-2011-27','source_id':'27','name':'Maharashtra','resolution':'state','reference_year':2011,'source':'https://example.test/census'}
    assert client.post('/urban/data/geographic-units',json=unit).status_code==201
    value=obs(settlement_id=None,geographic_unit_id=unit['id'],indicator_type='households',value=100,unit='households',reference_year=2011,observation_date=None,geographic_resolution='state',verification_status='historical_published')
    assert client.post('/urban/data/indicators',json=value).status_code==201
    assert client.post('/urban/data/priority',json={}).json()['items'][0]['coverage_pct']==0
    assert client.get('/urban/data/indicators?geographic_unit_id='+unit['id']).json()['items'][0]['reference_year']==2011
    assert client.post('/urban/data/indicators',json={**value,'geographic_resolution':'ward'}).status_code==422


def test_real_scenario_uses_hand_worked_costs_and_never_fabricates_access(client):
    option={'unit_cost_inr':100,'shared_works_inr':50,'months':6,'temporary_months':1,'disrupted_share':.2,'assumed_service_coverage_pct':80}
    payload={'households':10,'contingency_pct':10,'temporary_rent_per_month':20,'annual_maintenance_per_household':12,'options':[{**option,'kind':kind} for kind in ['upgrade','redevelop']]}
    r=client.post('/urban/data/scenarios/source-label',json=payload)
    assert r.status_code==200,r.text
    assert r.json()['options'][0]['total_cost_inr']==1199 and r.json()['access_available'] is False and r.json()['options'][0]['access']==[]
    assert client.post('/urban/data/scenarios/source-label',json={**payload,'households':None}).status_code==422
    assert client.post('/urban/data/scenarios/source-label',json={**payload,'include_relocation':True}).status_code==422


def test_field_survey_import_preserves_nulls_and_does_not_create_deficit_scores(client):
    survey={'survey_id':'fixture-survey','settlement_id':'source-label','observed_at':NOW(),'water_hours_per_day':4,'gps_latitude':19.06,'gps_longitude':72.92,'inspector_reference':'field-inspector','collection_platform':'ODK','protocol_reference':'Test-only field protocol'}
    assert client.get('/urban/data/surveys/schema').status_code==200
    r=client.post('/urban/data/surveys',json=survey);assert r.status_code==201,r.text
    assert client.post('/urban/data/surveys',json=survey).status_code==409
    assert len(client.get('/urban/data/indicators').json()['items'])==1
    assert client.get('/urban/data/indicators').json()['items'][0]['indicator_type']=='water_hours'
    assert client.post('/urban/data/priority',json={}).json()['items'][0]['coverage_pct']==0
    for changes in [{'survey_id':'second','gps_latitude':19.060123},{'survey_id':'second','water_hours_per_day':25},{'survey_id':'second','evidence_reference':'https://example.test/private-proof'},{'survey_id':'second','verification_status':'field_verified'},{'survey_id':'second','beneficiary_name':'not-collected'}]:
        assert client.post('/urban/data/surveys',json={**survey,**changes}).status_code==422


def test_reopening_a_resolved_complaint_removes_verified_status(client):
    item=work(client)
    for action in ['start','report_complete','request_verification']:transition(client,item,action)
    complaint=client.post('/urban/data/complaints',json={'settlement_id':'source-label','intervention_id':item['id'],'service_type':'water','description':'Fixture report before review'}).json()
    response={'status':'resolved','actor':'officer','resolution_details':'Fixture response only'}
    client.patch('/urban/data/complaints/'+complaint['id'],json=response)
    ev=evidence(client,item)
    assert client.post(f"/urban/data/interventions/{item['id']}/verifications",json=verification(ev)).status_code==201
    assert client.patch('/urban/data/complaints/'+complaint['id'],json={**response,'status':'reopened'}).status_code==200
    assert client.get('/urban/data/interventions').json()['items'][0]['status']=='requiring_reinspection'


def test_conflicting_equal_time_observations_remain_missing(client):
    timestamp=NOW()
    assert client.post('/urban/data/indicators',json=obs(value=80,observation_date=timestamp)).status_code==201
    assert client.post('/urban/data/indicators',json=obs(value=20,observation_date=timestamp)).status_code==201
    row=client.post('/urban/data/priority',json={}).json()['items'][0]
    assert row['coverage_pct']==0 and row['indicators']['water'] is None


def test_reviewed_observations_use_instants_not_timezone_string_order(client):
    from datetime import timedelta
    latest = datetime.now(timezone.utc) - timedelta(minutes=5)
    earlier = (latest - timedelta(minutes=20)).astimezone(timezone(timedelta(hours=5, minutes=30)))
    assert client.post('/urban/data/indicators',json=obs(value=80,observation_date=earlier.isoformat())).status_code==201
    assert client.post('/urban/data/indicators',json=obs(value=20,observation_date=latest.isoformat())).status_code==201
    assert client.post('/urban/data/priority',json={}).json()['items'][0]['indicators']['water']==20
    # The same instant in another timezone is still a conflict, not a newer reading.
    equivalent = latest.astimezone(timezone(timedelta(hours=5, minutes=30)))
    assert client.post('/urban/data/indicators',json=obs(value=40,observation_date=equivalent.isoformat())).status_code==201
    assert client.post('/urban/data/priority',json={}).json()['items'][0]['indicators']['water'] is None
