"""Synthetic records and mutations use disposable SQLite; no user-source import."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import base64
import json
import pytest
from fastapi.testclient import TestClient
from model.api.urban import create_app
from model.api.civic_demo import seed_demo,validate_workspace,today

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('NAGARSEVA_OFFICER_KEY','test-demo-key')
    monkeypatch.setenv('URBANSAARTHI_EVIDENCE_STORAGE','sqlite')
    with TestClient(create_app(tmp_path/'test.sqlite3',tmp_path/'no-real-data')) as c:yield c

def state(client):return client.get('/urban/demo/workspace').json()
def command(client,kind,payload,identifier=None,token=None,admin=True,revision=None):
    current=state(client)
    return client.post('/urban/demo/commands',headers={'X-Officer-Key':'test-demo-key'} if admin else {},json={'kind':kind,'payload':payload,'entityId':identifier,'expectedRevision':revision or current['revision'],'operationId':token or f'test-command-{current["revision"]:08d}'})
def issue():return {'settlementId':'DEMO-SET-001','category':'water','title':'TEST ONLY demo water concern','description':'TEST ONLY fictional concern for this disposable test.','priority':'high','locationDescription':'TEST ONLY fictional landmark'}

def test_fixed_seed_geometry_and_relationship_integrity():
    first=seed_demo();assert first==seed_demo() and first!=seed_demo(97)
    assert {key:len(first[key]) for key in ['settlements','wards','issues','projects','visits','milestones','activity']}=={'settlements':100,'wards':24,'issues':60,'projects':20,'visits':30,'milestones':40,'activity':0}
    assert validate_workspace(first)
    from shapely.geometry import shape
    polygons=[shape(row['geometry']) for row in first['settlements']]
    assert all(polygon.is_valid for polygon in polygons)
    assert all(a.intersection(b).area==0 for i,a in enumerate(polygons) for b in polygons[i+1:])
    assert sum(row['settlementCount'] for row in first['wards'])==len(first['settlements'])
    for key in ['settlements','wards','issues','projects','visits','milestones']:assert all(row['sourceType']=='synthetic' for row in first[key])
    assert all(not row['history'] for row in first['issues'])

@pytest.mark.parametrize('change',[lambda s:s['settlements'].append(s['settlements'][0]),lambda s:s['settlements'][0].update(wardId='missing'),lambda s:s['settlements'][0].update(waterAccessPercent=101),lambda s:s['issues'][0].update(settlementId='missing'),lambda s:s['projects'][0].update(progressPercent=-1),lambda s:s['milestones'][0].update(projectId='missing'),lambda s:s['visits'][0].update(scheduledDate='invalid'),lambda s:s['targets'].update(water=True)])
def test_invalid_saved_entities_are_not_silently_repaired(change):
    data=seed_demo();change(data)
    with pytest.raises((ValueError,TypeError)):validate_workspace(data)


def test_issue_submission_persists_counts_history_and_exactly_once_retries(client):
    before=state(client)
    submitted=command(client,'createIssue',issue(),token='same-test-operation',admin=False)
    assert submitted.status_code==200,submitted.text
    after=submitted.json()['state'];identifier=submitted.json()['entityId']
    assert len(after['issues'])==61 and after['dataSources'][1]['recordCount']==61
    new=next(row for row in after['issues'] if row['id']==identifier)
    assert new['status']=='open' and new['sourceType']=='synthetic' and not new['seeded']
    assert len(new['history'])==1 and new['history'][0]['eventType']=='issue_created'
    assert len(after['activity'])==len(before['activity'])+1
    retry=command(client,'createIssue',issue(),token='same-test-operation',admin=False)
    assert retry.json()['replayed'] is True and len(retry.json()['state']['issues'])==61
    assert command(client,'createIssue',{**issue(),'title':'Different TEST ONLY content'},token='same-test-operation').status_code==409
    with TestClient(create_app(client.app.state.store.path,client.app.state.public.data_dir)) as reopened:assert any(row['id']==identifier for row in state(reopened)['issues'])


def test_issue_lifecycle_authorization_and_traceable_followup(client):
    identifier=command(client,'createIssue',issue(),admin=False).json()['entityId']
    assert command(client,'updateIssue',{'status':'resolved','notes':'TEST ONLY followup'},identifier,admin=False).status_code==401
    assert command(client,'updateIssue',{'status':'closed','notes':'TEST ONLY close too early'},identifier).status_code==422
    for status in ['acknowledged','in_progress','resolved','closed']:
        response=command(client,'updateIssue',{'status':status,'notes':'TEST ONLY follow-up note','assignedOwner':'Demo Officer 01'},identifier)
        assert response.status_code==200,response.text
    saved=next(row for row in state(client)['issues'] if row['id']==identifier)
    assert saved['status']=='closed' and saved['resolvedAt']
    assert [row['eventType'] for row in saved['history']]==['issue_created','issue_acknowledged','issue_in_progress','issue_resolved','issue_closed']
    assert saved['history'][1]['changes']['status']=={'before':'open','after':'acknowledged'}
    assert command(client,'updateIssue',{'status':'open','notes':'TEST ONLY reopen'},identifier).status_code==200
    assert next(row for row in state(client)['issues'] if row['id']==identifier)['resolvedAt'] is None

@pytest.mark.parametrize('patch',[{'settlementId':'missing'},{'description':'short'},{'title':''},{'priority':'official'},{'category':'unavailable'},{'sourceType':'official'}])
def test_bad_issues_do_not_add_records_or_activity(client,patch):
    before=state(client);response=command(client,'createIssue',{**issue(),**patch},admin=False)
    assert response.status_code in (404,422)
    after=state(client);assert before==after


def test_revision_conflict_does_not_overwrite_other_session(client):
    before=state(client);assert command(client,'createIssue',issue(),admin=False).status_code==200
    assert command(client,'createIssue',issue(),token='second-session-operation',revision=before['revision'],admin=False).status_code==409
    assert len(state(client)['issues'])==61


def test_project_and_milestone_updates_validate_dates_and_preserve_unresolved_issues(client):
    payload={'settlementId':'DEMO-SET-001','name':'Demo TEST project','description':'TEST ONLY fictional housing repair project','stage':'planning','status':'active','progressPercent':10,'estimatedBudget':50000,'startDate':'2026-01-01','expectedCompletionDate':'2027-01-01','responsibleAgency':'Demo TEST team','notes':'TEST ONLY'}
    result=command(client,'createProject',payload);assert result.status_code==200,result.text;identifier=result.json()['entityId']
    milestone=command(client,'createMilestone',{'projectId':identifier,'name':'Demo TEST milestone','plannedDate':'2026-12-01','status':'planned','completedDate':None,'notes':'TEST ONLY'})
    assert milestone.status_code==200,milestone.text;mid=milestone.json()['entityId']
    assert command(client,'updateMilestone',{'status':'completed','completedDate':None},mid).status_code==422
    assert command(client,'updateMilestone',{'status':'completed','completedDate':str(today())},mid).status_code==200
    issues=state(client)['issues']
    updated=command(client,'updateProject',{'stage':'completed','status':'completed','progressPercent':100},identifier)
    assert updated.status_code==200,updated.text
    assert updated.json()['state']['issues']==issues
    assert command(client,'updateProject',{'progressPercent':101},identifier).status_code==422
    assert command(client,'createProject',{**payload,'expectedCompletionDate':'2025-01-01'}).status_code==422


def test_visit_completion_does_not_implicitly_change_indicators(client):
    payload={'settlementId':'DEMO-SET-001','scheduledDate':str(today()),'visitType':'water','assignedOfficer':'Demo TEST officer','status':'scheduled','notes':'TEST ONLY visit','findings':{}}
    result=command(client,'createVisit',payload,admin=False);assert result.status_code==200,result.text;identifier=result.json()['entityId'];before=state(client)['settlements'][0]
    completed=command(client,'updateVisit',{'status':'completed','findings':{'water':96},'notes':'TEST ONLY measured fictional findings'},identifier)
    assert completed.status_code==200,completed.text
    assert completed.json()['state']['settlements'][0]==before
    assert command(client,'applyFindings',{'confirm':False,'notes':'TEST ONLY'},identifier).status_code==422
    applied=command(client,'applyFindings',{'confirm':True,'notes':'TEST ONLY explicit application'},identifier)
    assert applied.status_code==200,applied.text
    record=applied.json()['state']['settlements'][0]
    assert record['waterAccessPercent']==96 and record['indicatorHistory'][-1]['visitId']==identifier
    future={**payload,'scheduledDate':str(today()+timedelta(days=1))}
    cancelled=command(client,'createVisit',future,admin=False).json()['entityId']
    assert command(client,'updateVisit',{'status':'cancelled'},cancelled).status_code==200
    assert command(client,'updateVisit',{'status':'completed'},cancelled).status_code==422


def test_housing_and_community_records_use_valid_relations(client):
    assessment={'settlementId':'DEMO-SET-001','housingCondition':'needs_repair','householdCount':20,'improvementCategory':'repair','priority':'high','status':'under_review','assessmentDate':str(today()),'notes':'TEST ONLY aggregate assessment'}
    assert command(client,'createAssessment',assessment).status_code==200
    assert command(client,'createAssessment',{**assessment,'householdCount':1000000}).status_code==422
    feedback={'settlementId':'DEMO-SET-001','projectId':'DEMO-PROJ-001','category':'housing','message':'TEST ONLY anonymous synthetic feedback'}
    result=command(client,'createFeedback',feedback,admin=False);assert result.status_code==200,result.text
    identifier=result.json()['entityId']
    assert command(client,'updateFeedback',{'status':'resolved','response':'TEST ONLY demo followup response'},identifier).status_code==200
    assert command(client,'createFeedback',{**feedback,'projectId':'DEMO-PROJ-002'},admin=False).status_code==422


def test_reset_is_scoped_confirmed_and_restores_seed_counts(client):
    with client.app.state.store.connection(write=True) as db:db.execute("INSERT INTO urban_records VALUES('keep-unrelated','work','US-A','{}')")
    command(client,'createIssue',issue(),admin=False)
    assert command(client,'reset',{'confirm':False}).status_code==422
    assert command(client,'reset',{'confirm':True},admin=False).status_code==401
    result=command(client,'reset',{'confirm':True});assert result.status_code==200
    reset=result.json()['state'];assert len(reset['issues'])==60 and len(reset['activity'])==1 and reset['activity'][0]['eventType']=='reset'
    assert reset['settlements']==seed_demo()['settlements']
    with client.app.state.store.connection() as db:assert db.execute("SELECT COUNT(*) FROM urban_records WHERE id='keep-unrelated'").fetchone()[0]==1


def test_optional_photos_are_validated_and_private(client):
    image={'filename':'../../TEST.png','contentType':'image/png','base64':base64.b64encode(b'\x89PNG\r\n\x1a\nTEST ONLY').decode(),'consent':True}
    assert command(client,'createIssue',{**issue(),'attachment':{**image,'consent':False}},admin=False).status_code==422
    result=command(client,'createIssue',{**issue(),'attachment':image},admin=False);assert result.status_code==200,result.text;identifier=result.json()['entityId']
    assert 'base64' not in json.dumps(result.json())
    assert client.get('/urban/demo/attachments/'+identifier).status_code==401
    assert client.get('/urban/demo/attachments/'+identifier,headers={'X-Officer-Key':'test-demo-key'}).content.startswith(b'\x89PNG')

@pytest.mark.parametrize('change', [
    lambda state:state['settlements'][0].update(riskLevel='unsupported'),
    lambda state:state['settlements'][0].update(populationEstimate=-1),
    lambda state:state['settlements'][0].update(householdsForAssessment=999999),
    lambda state:state['wards'][0].update(settlementCount=999),
    lambda state:state['dataSources'][0].update(recordCount=999),
    lambda state:state['issues'][0].update(createdAt='2026-10-01'),
    lambda state:state['issues'][3].update(resolvedAt='2026-01-01T00:00:00+00:00'),
])
def test_stored_integrity_checks_counts_estimates_enums_and_dates(change):
    state=seed_demo();change(state)
    with pytest.raises(ValueError):validate_workspace(state)


def test_feedback_responses_have_actual_before_after_history(client):
    created=command(client,'createFeedback',{'settlementId':'DEMO-SET-001','category':'services','message':'TEST ONLY suggestion for service access.'},admin=False)
    identifier=created.json()['entityId']
    for status,response in [('reviewed','TEST ONLY first response.'),('resolved','TEST ONLY second response.')]:
        result=command(client,'updateFeedback',{'status':status,'response':response},identifier)
        assert result.status_code==200,result.text
    feedback=next(row for row in state(client)['feedback'] if row['id']==identifier)
    change=feedback['history'][-1]['changes']
    assert change['response']=={'before':'TEST ONLY first response.','after':'TEST ONLY second response.'}
    assert change['status']=={'before':'reviewed','after':'resolved'}
