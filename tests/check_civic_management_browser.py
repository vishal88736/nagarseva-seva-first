"""Extended management workflow acceptance using only disposable synthetic data.

No mutations are sent to the user's default SQLite database. Requires existing
project Python/Playwright and Chromium; no dependencies are installed.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from zoneinfo import ZoneInfo
from playwright.sync_api import expect, sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.runtime/civic-management-browser'

def free_port():
    with socket.socket() as stream:
        stream.bind(('127.0.0.1',0));return stream.getsockname()[1]

def ready(url,process):
    for _ in range(100):
        if process.poll() is not None:raise RuntimeError('Owned test server exited')
        try:
            with urllib.request.urlopen(url,timeout=1) as response:
                if response.status==200:return
        except OSError:time.sleep(.2)
    raise RuntimeError('Test server timed out')

def main():
    OUT.mkdir(parents=True,exist_ok=True);checks=[];errors=[];processes=[];logs=[];pw=None;page=None
    report={'status':'failed','checkedAt':datetime.now(timezone.utc).isoformat(),'scope':'Disposable SQLite and browser workflows only','checks':checks,'browserErrors':errors}
    try:
        with tempfile.TemporaryDirectory(prefix='civic-management-test-') as temp:
            temp=Path(temp);key=secrets.token_urlsafe(32);api=f'http://127.0.0.1:{free_port()}';web=f'http://127.0.0.1:{free_port()}'
            env={**os.environ,'URBANSAARTHI_DB_PATH':str(temp/'data.sqlite3'),'URBANSAARTHI_DATA_DIR':str(temp/'no-real-data'),'NAGARSEVA_OFFICER_KEY':key,'NAGARSEVA_API_TARGET':api}
            for name,command,cwd in [('api',[sys.executable,'-m','uvicorn','model.api.urban:app','--host','127.0.0.1','--port',api.rsplit(':',1)[1]],ROOT/'nagarseva'),('web',['npm','run','dev','--','--port',web.rsplit(':',1)[1],'--strictPort'],ROOT/'nagarseva/website')]:
                log=(OUT/f'{name}.log').open('w');logs.append(log);processes.append(subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT))
            ready(api+'/urban/demo/health',processes[0]);ready(web,processes[1])
            def state():
                with urllib.request.urlopen(api+'/urban/demo/workspace') as response:return json.load(response)
            def operation(kind,payload,entity=None):
                body={'kind':kind,'payload':payload,'entityId':entity,'operationId':secrets.token_hex(16),'expectedRevision':state()['revision']}
                request=urllib.request.Request(api+'/urban/demo/commands',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-Officer-Key':key})
                with urllib.request.urlopen(request) as response:return json.load(response)
            def L(key):
                for name in ['demoMessages','integrationMessages']:
                    messages=json.loads((ROOT/f'nagarseva/website/src/i18n/{name}.ts').read_text().split('export default ',1)[1])
                    if key in messages:return messages[key]['en']
                return key
            pw=sync_playwright().start();browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH') or '/usr/bin/chromium')
            context=browser.new_context(viewport={'width':1440,'height':1000});context.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
            page=context.new_page();page.set_default_timeout(7000);page.on('pageerror',lambda error:errors.append(str(error)))
            def goto(path):
                page.goto(web+path);expect(page.locator('.demo-mode')).to_be_visible()
            def close():page.get_by_role('dialog').get_by_role('button',name='Close',exact=True).click()
            def save(expected=200):
                with page.expect_response(lambda response:response.url.endswith('/urban/demo/commands') and response.request.method=='POST') as response:
                    page.get_by_role('dialog').get_by_role('button',name='Save',exact=True).click()
                assert response.value.status==expected,response.value.text()
                return response.value.json()
            def enter_key(value):
                goto('/projects/data');page.get_by_label(L('d.adminKey'),exact=True).fill(value);page.get_by_role('button',name=L('d.applyKey'),exact=True).click()
            goto('/projects?new=1&settlement=DEMO-SET-001')
            expect(page.get_by_role('dialog')).to_be_visible()
            expect(page.get_by_role('dialog').locator('form')).to_have_count(0)
            close()
            checks.append('Anonymous project creation deep links explain access rather than exposing a save form')
            enter_key(key)
            goto('/projects?new=1&settlement=DEMO-SET-001')
            dialog=page.get_by_role('dialog');expect(dialog).to_be_visible()
            dialog.get_by_label(L('d.projectName'),exact=True).fill('Demo QA redevelopment project')
            dialog.get_by_label('Description',exact=True).fill('Synthetic software acceptance project, not a real redevelopment initiative.')
            dialog.get_by_label(L('d.startDate'),exact=True).fill('2026-10-01')
            dialog.get_by_label(L('d.endDate'),exact=True).fill('2027-10-01')
            dialog.get_by_label(L('d.demoBudget'),exact=True).fill('100000')
            created=save();project=next(row for row in created['state']['projects'] if row['id']==created['entityId'])
            expect(page.get_by_role('dialog')).to_contain_text(project['name']);assert len(state()['projects'])==21
            page.get_by_role('dialog').get_by_role('button',name=L('d.editProject'),exact=True).click()
            page.get_by_role('dialog').get_by_label(L('d.reportedProgress'),exact=True).fill('45')
            updated=save();assert next(row for row in updated['state']['projects'] if row['id']==project['id'])['progressPercent']==45
            close();page.reload();assert len(state()['projects'])==21
            checks.append('Project creation, progress update and reload persistence work through SQLite')
            enter_key('deliberately-invalid-test-key')
            goto('/projects?project='+project['id']);page.get_by_role('dialog').get_by_role('button',name=L('d.editProject'),exact=True).click()
            page.get_by_role('dialog').get_by_label(L('d.reportedProgress'),exact=True).fill('99')
            save(401);expect(page.get_by_role('dialog').get_by_role('alert')).to_be_visible()
            assert next(row for row in state()['projects'] if row['id']==project['id'])['progressPercent']==45
            close();enter_key(key)
            checks.append('A rejected administrator key gives a real error and cannot update project progress')
            goto('/projects?project='+project['id']);page.get_by_role('dialog').get_by_role('button',name=L('d.addMilestone'),exact=True).click()
            page.get_by_label(L('d.milestoneName'),exact=True).fill('Demo QA completed milestone')
            page.get_by_label(L('d.plannedDate'),exact=True).fill('2026-10-10')
            page.get_by_role('dialog').get_by_label('Status',exact=True).select_option('completed')
            save(422);assert len(state()['milestones'])==40
            page.get_by_label(L('d.completedDate'),exact=True).fill('2026-10-11')
            save();expect(page.get_by_role('dialog')).to_contain_text('Demo QA completed milestone');assert len(state()['milestones'])==41;close()
            checks.append('Completed milestones require actual completion dates; invalid saves do not create records')
            today=datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat();old_coverage=state()['settlements'][0]['waterAccessPercent']
            goto('/visits?new=1&settlement=DEMO-SET-001');page.get_by_label(L('d.scheduledDate'),exact=True).fill(today)
            page.get_by_label('Notes',exact=True).fill('Synthetic inspection findings test only.');created=save();visit=created['entityId']
            page.get_by_role('dialog').get_by_role('button',name=L('d.editVisit'),exact=True).click()
            page.get_by_role('dialog').get_by_label('Status',exact=True).select_option('completed')
            page.get_by_label(L('d.finding.water'),exact=True).fill('77')
            save();assert state()['settlements'][0]['waterAccessPercent']==old_coverage
            page.get_by_label(L('d.applyNotes'),exact=True).fill('Explicit synthetic indicator update for software testing.')
            page.get_by_role('dialog').get_by_role('checkbox').check()
            with page.expect_response(lambda response:response.url.endswith('/urban/demo/commands') and response.request.method=='POST') as applying:
                page.get_by_role('button',name=L('d.applyFindings'),exact=True).click()
            assert applying.value.status==200
            snapshot=state();assert snapshot['settlements'][0]['waterAccessPercent']==77 and len(snapshot['settlements'][0]['indicatorHistory'])==1
            close();checks.append('Completing a visit preserves indicators; explicit confirmed application persists a traceable update')
            goto('/housing?settlement=DEMO-SET-001');page.get_by_role('button',name=L('d.newAssessment'),exact=True).click()
            page.get_by_label(L('d.housingCondition'),exact=True).select_option('needs_repair')
            page.get_by_label(L('d.assessmentCount'),exact=True).fill('10')
            page.get_by_label(L('d.improvement'),exact=True).select_option('repair')
            page.get_by_label('Notes',exact=True).fill('Synthetic housing assessment for software testing only.')
            created=save();expect(page.get_by_role('dialog')).to_have_count(0);assessment=created['entityId']
            assert len(state()['assessments'])==1
            page.locator(f'tr[data-record-id="{assessment}"] .us-table-button').click()
            page.get_by_label(L('d.assessmentCount'),exact=True).fill('12');save();expect(page.get_by_role('dialog')).to_have_count(0)
            assert state()['assessments'][0]['householdCount']==12
            checks.append('Housing assessment creation and editing preserve the correct settlement and count')
            enter_key('')
            goto('/housing?settlement=DEMO-SET-001');page.locator(f'tr[data-record-id="{assessment}"] .us-table-button').click()
            expect(page.get_by_role('dialog')).to_contain_text('Synthetic housing assessment for software testing only.')
            expect(page.get_by_role('dialog')).to_contain_text('12')
            expect(page.get_by_role('dialog').locator('form')).to_have_count(0)
            close();enter_key(key)
            checks.append('Public housing assessment details remain readable while edits stay protected')
            created=operation('createFeedback',{'settlementId':'DEMO-SET-001','projectId':project['id'],'category':'redevelopment','message':'Synthetic feedback created for testing moderation and response history.'})
            feedback=created['entityId'];goto('/projects?tab=community');page.locator('.us-table-button').first.click()
            page.get_by_role('dialog').get_by_label('Status',exact=True).select_option('reviewed')
            page.get_by_label(L('d.adminResponse'),exact=True).fill('First synthetic administrative response.')
            save();expect(page.get_by_role('dialog')).to_contain_text('First synthetic administrative response.')
            page.get_by_label(L('d.adminResponse'),exact=True).fill('Second synthetic administrative response.')
            page.get_by_role('dialog').get_by_label('Status',exact=True).select_option('follow_up')
            save();close()
            current=next(row for row in state()['feedback'] if row['id']==feedback)
            assert current['status']=='follow_up' and len(current['history'])==3
            checks.append('Community moderation and response updates persist with genuine operation events')
            # Source review identified history-content loss; record evidence rather than falsely pass that detail.
            report['feedbackHistoryRetainsPriorResponse']='First synthetic administrative response.' in json.dumps(current['history'])
            assert report['feedbackHistoryRetainsPriorResponse'], 'Prior response was lost from feedback history'
            checks.append('Feedback history retains both administrative responses and status transitions')
            goto('/projects?tab=reports')
            page.get_by_label('Settlement',exact=True).select_option('DEMO-SET-001')
            summary=page.locator('.us-panel').filter(has=page.get_by_role('heading',name=L('d.coverage'),exact=True))
            def fact(name):return summary.locator('.us-facts>div').filter(has=page.locator('dt',has_text=name)).locator('dd')
            expect(fact(L('d.metric.settlements'))).to_have_text('1')
            expect(fact(L('d.metric.projects'))).to_have_text('2')
            expect(fact(L('d.metric.wards'))).to_have_text('1')
            expect(fact(L('d.metric.feedback'))).to_have_text('1')
            infrastructure=page.locator('.us-panel').filter(has=page.get_by_role('heading',name=L('d.infrastructure'),exact=True))
            expect(infrastructure.get_by_role('progressbar',name=L('d.value.water'),exact=True)).to_have_attribute('value','77')
            checks.append('Settlement-filtered reports scope summary counts and infrastructure to the same stored records')
            overdue_visit=next(row for row in state()['visits'] if row['status']=='scheduled')
            operation('updateVisit',{'scheduledDate':'2026-01-01'},overdue_visit['id'])
            expected_upcoming=sum(row['status']=='scheduled' and row['scheduledDate']>=today for row in state()['visits'])
            goto('/dashboard');page.locator('.demo-summary.visits').click()
            expect(page.get_by_label(L('d.from'),exact=True)).to_have_value(today)
            expect(page.locator('.workspace-pagination [role=status]')).to_contain_text(str(expected_upcoming))
            expect(page.locator(f'tr[data-record-id="{overdue_visit['id']}"]')).to_have_count(0)
            checks.append('Upcoming-visit dashboard action carries the same India-calendar date filter as its metric')
            goto('/visits')
            page.get_by_label(L('d.from'),exact=True).fill('2026-12-31')
            page.get_by_label(L('d.to'),exact=True).fill('2026-01-01')
            expect(page.get_by_role('alert')).to_have_text(L('demo.error.date'))
            expect(page.locator('.us-table-wrap tbody tr')).to_have_count(0)
            page.get_by_label(L('d.from'),exact=True).fill('')
            expect(page.get_by_role('alert')).to_have_count(0)
            checks.append('Inverted visit date ranges show an explicit validation error and recover on correction')
            goto('/report-issue')
            page.get_by_role('button',name=L('d.submitIssue'),exact=True).click()
            expect(page.locator('.demo-field-error')).to_have_count(5)
            english_errors=page.locator('.demo-field-error').all_text_contents()
            page.locator('.us-language select').select_option('hi')
            expect(page.locator('html')).to_have_attribute('lang','hi')
            assert page.locator('.demo-field-error').all_text_contents()!=english_errors
            assert all('required' not in value for value in page.locator('.demo-field-error').all_text_contents())
            page.locator('.us-language select').select_option('en')
            checks.append('Visible required-field errors change language immediately without resubmitting')
            assert not errors
            browser.close();report['status']='passed'
    except Exception as exc:
        report['failure']=f'{type(exc).__name__}: {exc}'
        if page is not None:
            try:page.screenshot(path=str(OUT/'failure.png'),full_page=True);(OUT/'failure-body.txt').write_text(page.locator('body').inner_text())
            except Exception:pass
        raise
    finally:
        if pw is not None:pw.stop()
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        for log in logs:log.close()
        (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
