"""Public prototype reporting persists without claiming official municipal submission."""
from datetime import datetime, timedelta, timezone
import base64

from fastapi.testclient import TestClient
import pytest
from model.api.urban import create_app


def payload(**changes):
    return {'category':'water','description':'TEST ONLY: interrupted water supply','ward':'Test ward','location':None,'latitude':None,'longitude':None,'report_date':datetime.now(timezone.utc).date().isoformat(),**changes}


@pytest.fixture
def app(tmp_path,monkeypatch):
    monkeypatch.setenv('NAGARSEVA_OFFICER_KEY','test-only-officer')
    monkeypatch.setenv('URBANSAARTHI_EVIDENCE_STORAGE','sqlite')
    return create_app(tmp_path/'test.sqlite3',tmp_path/'no-source')


def test_anonymous_report_persists_and_is_explicitly_not_an_official_submission(app):
    with TestClient(app) as client:
        response=client.post('/urban/data/issues',json=payload(),headers={'Idempotency-Key':'test-unique-key-0001'})
        assert response.status_code==201,response.text
        issue=response.json();assert issue['id'].startswith('ISS-') and issue['status']=='submitted'
        assert issue['official_submission'] is False and issue['verification_status']=='self_reported'
        assert client.get('/urban/data/issues/'+issue['id']).json()==issue
        assert client.get('/urban/data/issues/summary').json()['open']==1
        assert client.get('/urban/data/overview').json()['settlements_loaded']==0
    with TestClient(create_app(app.state.store.path,app.state.public.data_dir)) as reopened:
        assert reopened.get('/urban/data/issues/'+issue['id']).json()['id']==issue['id']
        assert reopened.get('/urban/data/issues').json()['total']==1


def test_idempotent_submission_does_not_duplicate_records_and_conflicts_are_explicit(app):
    with TestClient(app) as client:
        headers={'Idempotency-Key':'test-unique-key-0002'}
        first=client.post('/urban/data/issues',json=payload(),headers=headers)
        second=client.post('/urban/data/issues',json=payload(),headers=headers)
        assert first.status_code==201 and second.status_code==200
        assert first.json()['id']==second.json()['id']
        assert client.get('/urban/data/issues').json()['total']==1
        assert client.post('/urban/data/issues',json=payload(description='TEST ONLY: different report'),headers=headers).status_code==409


@pytest.mark.parametrize('changes',[{'category':'unsupported'},{'description':'short'},{'latitude':19.05},{'longitude':72.9},{'latitude':19.12345,'longitude':72.9},{'latitude':True,'longitude':72.9},{'latitude':91,'longitude':72.9},{'report_date':(datetime.now(timezone.utc)+timedelta(days=2)).date().isoformat()},{'official_submission':True}])
def test_issue_validation_rejects_bad_data(app,changes):
    with TestClient(app) as client:
        assert client.post('/urban/data/issues',json=payload(**changes),headers={'Idempotency-Key':'test-validation-key'}).status_code==422
        assert client.get('/urban/data/issues').json()['total']==0


def test_status_changes_require_officer_access_and_do_not_verify_a_service(app):
    with TestClient(app) as client:
        issue=client.post('/urban/data/issues',json=payload(category='electricity'),headers={'Idempotency-Key':'test-unique-key-0003'}).json()
        update={'status':'under_review','note':'TEST ONLY review','reviewer_reference':'test-reviewer'}
        url='/urban/data/issues/'+issue['id']
        assert client.patch(url,json=update).status_code==401
        assert client.patch(url,json=update,headers={'X-Officer-Key':'test-only-officer'}).json()['status']=='under_review'
        resolved=client.patch(url,json={**update,'status':'resolved'},headers={'X-Officer-Key':'test-only-officer'}).json()
        assert resolved['status']=='resolved' and resolved['official_submission'] is False
        assert 'history' not in resolved and 'reviewer_reference' not in resolved
        assert client.get('/urban/data/issues/summary').json()['open']==0
        assert client.get('/urban/data/overview').json()['verified_interventions']==0
        assert client.get('/urban/data/issues?category=electricity&status=resolved').json()['total']==1
        assert client.get('/urban/data/issues?page_size=101').status_code==422


def test_optional_images_need_consent_storage_type_validation_and_private_access(app,monkeypatch):
    image={'filename':'../../test.png','content_type':'image/png','content_base64':base64.b64encode(b'\x89PNG\r\n\x1a\nTEST ONLY').decode(),'consent':True}
    with TestClient(app) as client:
        headers={'Idempotency-Key':'test-unique-key-0004'}
        assert client.post('/urban/data/issues',json=payload(attachment={**image,'consent':False}),headers=headers).status_code==422
        assert client.post('/urban/data/issues',json=payload(attachment={**image,'content_base64':base64.b64encode(b'NOT PNG').decode()}),headers=headers).status_code==422
        created=client.post('/urban/data/issues',json=payload(attachment=image),headers=headers)
        assert created.status_code==201,created.text
        issue=created.json();assert issue['attachment']['filename']=='test.png' and 'content_base64' not in created.text
        assert client.get('/urban/data/issues/'+issue['id']+'/image').status_code==401
        assert client.get('/urban/data/issues/'+issue['id']+'/image',headers={'X-Officer-Key':'test-only-officer'}).content.startswith(b'\x89PNG')
        monkeypatch.delenv('URBANSAARTHI_EVIDENCE_STORAGE')
        assert client.post('/urban/data/issues',json=payload(attachment=image),headers={'Idempotency-Key':'test-unique-key-0005'}).status_code==503


def test_public_issue_export_escapes_formula_cells_and_keeps_scope_and_missing_values(app):
    with TestClient(app) as client:
        client.post('/urban/data/issues',json=payload(description='=TEST ONLY formula text',latitude=0,longitude=0),headers={'Idempotency-Key':'test-unique-key-0006'})
        exported=client.get('/urban/data/issues/report.csv')
        assert exported.status_code==200 and "'=TEST ONLY" in exported.text
        assert 'official_submission' in exported.text and 'False' in exported.text
        assert 'idempotency_key' not in exported.text and 'content_base64' not in exported.text
        assert client.get('/urban/data/issues/missing').status_code==404
