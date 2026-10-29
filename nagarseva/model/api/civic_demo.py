"""One deterministic synthetic workspace, isolated from historical/operational tables.

All changes are SQLite transactions with optimistic revisions and idempotency keys.
No government datasets, geocoding, external services or inferred eligibility.
"""
from __future__ import annotations
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import random
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Annotated

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from shapely.geometry import shape

SERVICES = ('water','sanitation','drainage','waste','electricity','access')
CATEGORIES = (*SERVICES, 'other')
ISSUE_STATUSES = ('open','acknowledged','in_progress','resolved','closed')
PROJECT_STAGES = ('assessment','planning','consultation','approval','implementation','completed','on_hold')
COLLECTIONS = ('settlements','wards','issues','projects','milestones','visits','assessments','feedback','activity','dataSources','anomalyFixtures')
IST = timezone(timedelta(hours=5, minutes=30))

def now(): return datetime.now(timezone.utc).isoformat()
def today(): return datetime.now(IST).date()
def uid(prefix): return 'DEMO-'+prefix+'-'+secrets.token_hex(6).upper()
def fail(code): raise HTTPException(422,code)

def anomaly_fixtures(state):
    """Separate planted test scenarios; never written into active settlement values."""
    return [{'id':'DEMO-ANOMALY-01','settlementId':state['settlements'][0]['id'],'overrides':{'populationEstimate':state['settlements'][0]['householdEstimate']*9},'expectedRule':'household_ratio','sourceType':'synthetic','is_synthetic':True},
            {'id':'DEMO-ANOMALY-02','settlementId':state['settlements'][1]['id'],'overrides':{'waterAccessPercent':5},'expectedRule':'low_coverage','sourceType':'synthetic','is_synthetic':True},
            {'id':'DEMO-ANOMALY-03','settlementId':state['settlements'][2]['id'],'overrides':{'sanitationAccessPercent':None},'expectedRule':'missing_coverage','sourceType':'synthetic','is_synthetic':True}]

def mark_synthetic(state):
    state['is_synthetic']=True;state['cityName']=f'Demo City {state["seed"]}'
    for collection in COLLECTIONS:
        for row in state.get(collection,[]):
            if row.get('sourceType')!='synthetic':raise ValueError('demo.error.synthetic')
            row['is_synthetic']=True
            for event in row.get('history',[]):event['is_synthetic']=True
            for event in row.get('indicatorHistory',[]):event['is_synthetic']=True

def seed_demo(seed=96,settlement_count=100):
    """Pure fixed-seed fixtures. Fixture dates are scenario data, not event logs."""
    if not 100<=settlement_count<=20000:raise ValueError('demo.error.range')
    rng=random.Random(seed)
    state={key:[] for key in COLLECTIONS}
    state.update(schemaVersion=1,seed=seed,revision=1,lastSavedAt=None,sourceType='synthetic',
                 targets={'water':95,'sanitation':90,'drainage':85,'waste':90,'electricity':95,'access':90},
                 weights={'gap':.5,'priority':.2,'unresolved':.2,'age':.1})
    for i in range(24):
        state['wards'].append({'id':f'DEMO-WARD-{i+1:02}','name':f'Demo Ward {i+1:02}','locality':f'Demo Locality {i+1:02}','settlementCount':0,'sourceType':'synthetic'})
    width=max(10,math.ceil(math.sqrt(settlement_count)));height=math.ceil(settlement_count/width)
    for i in range(settlement_count):
        jitter_x=.001 if settlement_count==100 else min(.001,.12/width*.08)
        jitter_y=.001 if settlement_count==100 else min(.001,.24/height*.08)
        lon=round(72.818+(i%width)*(.12/width)+rng.uniform(-jitter_x,jitter_x),6)
        lat=round(18.995+(i//width)*(.24/height)+rng.uniform(-jitter_y,jitter_y),6)
        dx,dy=min(.0015,.036/width),min(.0012,.072/height)
        ring=[[lon-dx,lat-dy],[lon+dx,lat-dy],[lon+dx,lat+dy],[lon-dx,lat+dy],[lon-dx,lat-dy]]
        households=rng.randint(80,900);ward=state['wards'][i%24];ward['settlementCount']+=1
        metrics={key:rng.randint(30,98) for key in SERVICES}
        state['settlements'].append({'id':f'DEMO-SET-{i+1:03}','name':f'Demo Settlement {i+1:03}',
            'wardId':ward['id'],'locality':ward['locality'],'populationEstimate':households*rng.randint(3,5),'householdEstimate':households,
            'waterAccessPercent':metrics['water'],'sanitationAccessPercent':metrics['sanitation'],'wasteCollectionPercent':metrics['waste'],
            'drainageCoveragePercent':metrics['drainage'],'electricityAccessPercent':metrics['electricity'],'roadAccessPercent':metrics['access'],
            'housingCondition':('temporary','needs_repair','stable')[i%3],'householdsForAssessment':round(households*(.6 if i%3==0 else .3 if i%3==1 else .1)),
            'riskLevel':('high','medium','low')[i%3],'redevelopmentStatus':('assessment','planning','implementation','not_planned')[i%4],
            'latitude':lat,'longitude':lon,'geometry':{'type':'Polygon','coordinates':[ring]},'sourceType':'synthetic','indicatorHistory':[]})
    for i in range(60):
        status=ISSUE_STATUSES[i%5];category=CATEGORIES[i%7];created=f'2026-10-{1+i%20:02}T04:00:00+00:00'
        state['issues'].append({'id':f'DEMO-ISS-{i+1:03}','settlementId':state['settlements'][i%100]['id'],'category':category,
          'title':f'Demo Issue {i+1:03}','description':'Fictional service concern for exploring the demonstration workflow.',
          'priority':('high','medium','low')[i%3],'status':status,'createdAt':created,'updatedAt':created,
          'resolvedAt':f'2026-10-{22+i%3:02}T06:00:00+00:00' if status in ('resolved','closed') else None,
          'reporterDisplayName':'Demo participant','locationDescription':f'Demo location {i+1:03}','attachment':None,'assignedOwner':None,
          'history':[],'sourceType':'synthetic','seeded':True})
    for i in range(20):
        stage=PROJECT_STAGES[i%7];finished=stage=='completed'
        project={'id':f'DEMO-PROJ-{i+1:03}','settlementId':state['settlements'][i*5]['id'],'name':f'Demo Project {i+1:03}',
          'description':'Fictional housing and basic-service improvement scenario; no government approval or funding.',
          'stage':stage,'status':'completed' if finished else 'paused' if stage=='on_hold' else 'active',
          'progressPercent':100 if finished else rng.randint(5,85),'estimatedBudget':rng.randint(10,90)*100000,
          'startDate':'2026-09-01','expectedCompletionDate':'2026-10-01' if finished else '2027-09-01',
          'responsibleAgency':f'Demo Development Team {i%4+1:02}','lastUpdated':'2026-10-01T00:00:00+00:00','notes':'Synthetic planning scenario.','history':[],'sourceType':'synthetic'}
        state['projects'].append(project)
        for j in range(2):
            state['milestones'].append({'id':f'DEMO-MILE-{i*2+j+1:03}','projectId':project['id'],'name':f'Demo Milestone {j+1:02}',
              'plannedDate':'2026-09-15' if j==0 else project['expectedCompletionDate'],'status':'completed' if finished else 'planned',
              'completedDate':'2026-09-15' if finished else None,'notes':'Fictional milestone.','history':[],'sourceType':'synthetic'})
    for i in range(30):
        status=('scheduled','completed','cancelled')[i%3]
        state['visits'].append({'id':f'DEMO-VISIT-{i+1:03}','settlementId':state['settlements'][i*3]['id'],
          'scheduledDate':str(date(2026,11,1)+timedelta(days=i)) if status=='scheduled' else '2026-10-01',
          'visitType':('housing','water','sanitation','drainage','waste','electricity','access')[i%7],
          'assignedOfficer':f'Demo Officer {i%8+1:02}','status':status,'notes':'Fictional visit scenario; no public authority appointment.',
          'findings':{},'history':[],'updatedAt':'2026-10-01T00:00:00+00:00','sourceType':'synthetic','seeded':True})
    for key in ('settlements','issues','projects','visits'):
        state['dataSources'].append({'id':'DEMO-SOURCE-'+key.upper(),'name':key,'publisher':'UrbanSaarthi demonstration generator',
           'dataType':key,'recordCount':len(state[key]),'status':'synthetic','updatedAt':None,'isSynthetic':True,'sourceType':'synthetic'})
    state['anomalyFixtures']=anomaly_fixtures(state)
    mark_synthetic(state)
    return state


class Input(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True,allow_inf_nan=False)
class IssueInput(Input):
    settlementId:str
    category:Literal['water','sanitation','drainage','waste','electricity','access','other']
    title:str=Field(min_length=3,max_length=160)
    description:str=Field(min_length=10,max_length=2000)
    priority:Literal['low','medium','high']='medium'
    locationDescription:str=Field(min_length=3,max_length=300)
    attachment:dict | None=None
class ProjectInput(Input):
    settlementId:str
    name:str=Field(min_length=3,max_length=160)
    description:str=Field(min_length=10,max_length=2000)
    stage:Literal['assessment','planning','consultation','approval','implementation','completed','on_hold']='assessment'
    status:Literal['active','paused','completed','cancelled']='active'
    progressPercent:float=Field(default=0,ge=0,le=100,strict=True)
    estimatedBudget:float | None=Field(default=None,ge=0,le=1e12,strict=True)
    startDate:date
    expectedCompletionDate:date
    responsibleAgency:str=Field(min_length=5,max_length=120)
    notes:str=Field(default='',max_length=2000)
    @model_validator(mode='after')
    def dates(self):
        if self.expectedCompletionDate<self.startDate:raise ValueError('demo.error.date')
        if not self.responsibleAgency.startswith('Demo '):raise ValueError('demo.error.owner')
        if self.status=='completed' and (self.progressPercent!=100 or self.stage!='completed'):raise ValueError('demo.error.progress')
        return self
class VisitInput(Input):
    settlementId:str
    scheduledDate:date
    visitType:Literal['housing','water','sanitation','drainage','waste','electricity','access','other']
    assignedOfficer:str=Field(min_length=5,max_length=100)
    status:Literal['scheduled','completed','cancelled']='scheduled'
    notes:str=Field(default='',max_length=2000)
    findings:dict[str,Annotated[float,Field(ge=0,le=100,strict=True)]]=Field(default_factory=dict)
    @model_validator(mode='after')
    def findings_valid(self):
        if self.status=='completed' and self.scheduledDate>today():raise ValueError('demo.error.date')
        if not self.assignedOfficer.startswith('Demo '):raise ValueError('demo.error.owner')
        if any(key not in SERVICES or isinstance(v,bool) or not math.isfinite(v) or not 0<=v<=100 for key,v in self.findings.items()):raise ValueError('demo.error.range')
        return self
class MilestoneInput(Input):
    projectId:str
    name:str=Field(min_length=3,max_length=160)
    plannedDate:date
    status:Literal['planned','in_progress','completed','cancelled']='planned'
    completedDate:date | None=None
    notes:str=Field(default='',max_length=2000)
    @model_validator(mode='after')
    def completion(self):
        if (self.status=='completed') != (self.completedDate is not None):raise ValueError('demo.error.date')
        if self.completedDate and self.completedDate>today():raise ValueError('demo.error.date')
        return self
class AssessmentInput(Input):
    settlementId:str
    housingCondition:Literal['temporary','needs_repair','stable']
    householdCount:int=Field(ge=1,le=1000000,strict=True)
    improvementCategory:Literal['repair','water','sanitation','drainage','access','housing']
    priority:Literal['low','medium','high']='medium'
    status:Literal['draft','under_review','completed']='draft'
    assessmentDate:date
    notes:str=Field(min_length=5,max_length=2000)
class FeedbackInput(Input):
    settlementId:str
    projectId:str | None=None
    category:Literal['housing','services','redevelopment','participation','other']
    message:str=Field(min_length=10,max_length=2000)
class Command(Input):
    kind:str
    entityId:str | None=None
    payload:dict=Field(default_factory=dict)
    expectedRevision:int=Field(ge=1,strict=True)
    operationId:str=Field(min_length=16,max_length=100,pattern=r'^[A-Za-z0-9:_-]+$')

METRIC_FIELDS={'water':'waterAccessPercent','sanitation':'sanitationAccessPercent','drainage':'drainageCoveragePercent','waste':'wasteCollectionPercent','electricity':'electricityAccessPercent','access':'roadAccessPercent'}

def validate_workspace(state):
    """Validate stored edits as well as seeds. No silent repairs or ID reassignments."""
    if state.get('sourceType')!='synthetic':raise ValueError('demo.error.synthetic')
    ids={}
    all_ids=set()
    for collection in COLLECTIONS:
        ids[collection]=set()
        for row in state[collection]:
            identifier=row.get('id')
            if not isinstance(identifier,str) or not identifier.startswith('DEMO-') or identifier in all_ids:raise ValueError('demo.error.duplicate')
            if row.get('sourceType')!='synthetic' or row.get('is_synthetic') is not True:raise ValueError('demo.error.synthetic')
            all_ids.add(identifier);ids[collection].add(identifier)
    def stamp(value,optional=False):
        if value is None and optional:return None
        if not isinstance(value,str):raise ValueError('demo.error.date')
        try:parsed=datetime.fromisoformat(value)
        except ValueError as exc:raise ValueError('demo.error.date') from exc
        if parsed.tzinfo is None:raise ValueError('demo.error.date')
        return parsed
    stamp(state.get('lastSavedAt'),optional=True)
    for ward in state['wards']:
        if isinstance(ward.get('settlementCount'),bool) or ward.get('settlementCount')!=sum(row['wardId']==ward['id'] for row in state['settlements']):raise ValueError('demo.error.range')
    for settlement in state['settlements']:
        if settlement['wardId'] not in ids['wards']:raise ValueError('demo.error.relation')
        for field in ('householdEstimate','populationEstimate','householdsForAssessment'):
            if isinstance(settlement[field],bool) or not isinstance(settlement[field],int) or settlement[field]<(0 if field=='householdsForAssessment' else 1):raise ValueError('demo.error.range')
        if settlement['householdsForAssessment']>settlement['householdEstimate'] or settlement['populationEstimate']<settlement['householdEstimate']:raise ValueError('demo.error.range')
        if settlement['riskLevel'] not in ('low','medium','high') or settlement['redevelopmentStatus'] not in ('assessment','planning','implementation','not_planned') or settlement['housingCondition'] not in ('temporary','needs_repair','stable'):raise ValueError('demo.error.state')
        if any(isinstance(settlement[key],bool) or not isinstance(settlement[key],(int,float)) or not math.isfinite(settlement[key]) or abs(settlement[key])>limit for key,limit in [('latitude',90),('longitude',180)]):raise ValueError('demo.error.geometry')
        geometry=settlement['geometry']
        if geometry.get('type')!='Polygon' or not geometry.get('coordinates') or any(len(ring)<4 or ring[0]!=ring[-1] for ring in geometry['coordinates']):raise ValueError('demo.error.geometry')
        for field in METRIC_FIELDS.values():
            value=settlement.get(field)
            if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=100):raise ValueError('demo.error.range')
        polygon=shape(settlement['geometry'])
        if polygon.is_empty or not polygon.is_valid or polygon.geom_type!='Polygon' or polygon.bounds[0]<-180 or polygon.bounds[2]>180 or polygon.bounds[1]<-90 or polygon.bounds[3]>90:raise ValueError('demo.error.geometry')
    for collection in ('issues','projects','visits','assessments','feedback'):
        for row in state[collection]:
            if row['settlementId'] not in ids['settlements']:raise ValueError('demo.error.relation')
    for issue in state['issues']:
        if issue['status'] not in ISSUE_STATUSES or issue['category'] not in CATEGORIES or issue['priority'] not in ('low','medium','high'):raise ValueError('demo.error.state')
        IssueInput.model_validate({key:issue[key] for key in IssueInput.model_fields if key in issue})
        if stamp(issue['updatedAt'])<stamp(issue['createdAt']):raise ValueError('demo.error.date')
        resolved=stamp(issue.get('resolvedAt'),optional=True)
        if bool(resolved)!=(issue['status'] in ('resolved','closed')) or resolved and resolved<stamp(issue['createdAt']):raise ValueError('demo.error.date')
    for collection,model in [('projects',ProjectInput),('visits',VisitInput),('milestones',MilestoneInput),('assessments',AssessmentInput)]:
        for row in state[collection]:
            model.model_validate({key:row[key] for key in model.model_fields if key in row})
            stamp(row.get('lastUpdated' if collection=='projects' else 'updatedAt'),optional=True)
    for row in state['milestones']:
        if row['projectId'] not in ids['projects']:raise ValueError('demo.error.relation')
    for row in state['feedback']:
        FeedbackInput.model_validate({key:row[key] for key in FeedbackInput.model_fields if key in row})
        stamp(row['createdAt'])
        if row['status'] not in ('pending','reviewed','follow_up','resolved') or not isinstance(row['response'],str):raise ValueError('demo.error.state')
        if row.get('projectId'):
            project=next((p for p in state['projects'] if p['id']==row['projectId']),None)
            if not project or project['settlementId']!=row['settlementId']:raise ValueError('demo.error.relation')
    for source in state['dataSources']:
        if source.get('dataType') not in ('settlements','issues','projects','visits') or source.get('recordCount')!=len(state[source['dataType']]) or source.get('isSynthetic') is not True or source.get('status')!='synthetic':raise ValueError('demo.error.range')
        stamp(source.get('updatedAt'),optional=True)
    for event in state['activity']:
        stamp(event['createdAt'])
        if event['entityId'] not in all_ids and event['entityId'] not in ('DEMO-WORKSPACE','DEMO-SETTINGS'):raise ValueError('demo.error.relation')
    for collection in ('issues','projects','visits','milestones','assessments','feedback'):
        for row in state[collection]:
            for event in row.get('history',[]):
                if event.get('entityId')!=row['id'] or event.get('id') not in ids['activity']:raise ValueError('demo.error.relation')
                stamp(event['createdAt'])
    for fixture in state.get('anomalyFixtures',[]):
        if fixture['settlementId'] not in ids['settlements']:raise ValueError('demo.error.relation')
    for values in (state['targets'],state['weights']):
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in values.values()):raise ValueError('demo.error.range')
    if set(state['targets'])!=set(SERVICES) or any(v>100 for v in state['targets'].values()) or set(state['weights'])!={'gap','priority','unresolved','age'} or sum(state['weights'].values())<=0:raise ValueError('demo.error.range')
    return True


def add_event(state,event_type,entity_type,entity_id,at):
    event={'id':uid('EVENT'),'eventType':event_type,'entityType':entity_type,'entityId':entity_id,'message':event_type,'createdAt':at,'sourceType':'synthetic','is_synthetic':True}
    state['activity'].insert(0,event)
    return event


def create_demo_router(store,admin_access):
    router=APIRouter(prefix='/urban/demo',tags=['Synthetic civic demonstration'])
    with store.connection(write=True) as db:
        db.execute('CREATE TABLE IF NOT EXISTS civic_demo_workspace (id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS civic_demo_operations (id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,entity_id TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS civic_demo_attachments (issue_id TEXT PRIMARY KEY,content_type TEXT NOT NULL,content BLOB NOT NULL)')
        if not db.execute('SELECT 1 FROM civic_demo_workspace WHERE id=1').fetchone():
            state=seed_demo();at=now();state['lastSavedAt']=at
            for source in state['dataSources']:source['updatedAt']=at
            add_event(state,'initialized','workspace','DEMO-WORKSPACE',at);validate_workspace(state)
            db.execute('INSERT INTO civic_demo_workspace VALUES(1,?)',(json.dumps(state,allow_nan=False),))
        else:
            state=json.loads(db.execute('SELECT body FROM civic_demo_workspace WHERE id=1').fetchone()[0])
            if not state.get('is_synthetic') or 'anomalyFixtures' not in state:
                state.setdefault('anomalyFixtures',anomaly_fixtures(state));mark_synthetic(state)
                at=now();add_event(state,'metadata_updated','workspace','DEMO-WORKSPACE',at)
                state['revision']+=1;state['lastSavedAt']=at;validate_workspace(state)
                db.execute('UPDATE civic_demo_workspace SET body=? WHERE id=1',(json.dumps(state,allow_nan=False),))

    def read(db):
        state=json.loads(db.execute('SELECT body FROM civic_demo_workspace WHERE id=1').fetchone()[0])
        try:validate_workspace(state)
        except (ValueError,KeyError,TypeError) as exc:raise HTTPException(503,'demo.error.corrupt') from exc
        return state

    @router.get('/health')
    def health():return {'adapter':'sqlite-synthetic','synthetic':True,'adminConfigured':bool(os.getenv('NAGARSEVA_OFFICER_KEY')),'photoStorage':os.getenv('URBANSAARTHI_EVIDENCE_STORAGE')=='sqlite','timezone':'Asia/Kolkata','externalConnected':False}

    @router.get('/workspace')
    def workspace():
        try:
            with store.connection() as db:return read(db)
        except (ValueError,KeyError,TypeError) as exc:raise HTTPException(500,'demo.error.corrupt') from exc

    @router.get('/benchmark')
    def benchmark(count:int=10000):
        if not 1000<=count<=20000:fail('demo.error.range')
        import time
        start=time.perf_counter();sample=seed_demo(96,count);generated=time.perf_counter()
        validate_workspace(sample);validated=time.perf_counter()
        found=[row for row in sample['settlements'] if row['riskLevel']=='high']
        ranked=sorted(found,key=lambda row:(-sum(100-row[field] for field in METRIC_FIELDS.values()),row['id']))
        done=time.perf_counter()
        return {'is_synthetic':True,'label':'Demo data','recordCount':count,'filteredCount':len(found),'rankedCount':len(ranked),'generatedAt':now(),'generationMs':round((generated-start)*1000,2),'validationMs':round((validated-generated)*1000,2),'filterSortMs':round((done-validated)*1000,2),'totalMs':round((done-start)*1000,2),'persisted':False}

    @router.get('/attachments/{issue_id}')
    def attachment(issue_id:str,x_officer_key:str | None=Header(None)):
        admin_access(x_officer_key)
        with store.connection() as db:row=db.execute('SELECT content_type,content FROM civic_demo_attachments WHERE issue_id=?',(issue_id,)).fetchone()
        if not row:raise HTTPException(404,'demo.error.missing')
        return Response(row[1],media_type=row[0],headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Disposition':'attachment'})

    @router.post('/commands')
    def command(request:Command,x_officer_key:str | None=Header(None)):
        if request.kind not in ('createIssue','createVisit','createFeedback'):admin_access(x_officer_key)
        try:fingerprint=hashlib.sha256(json.dumps({'kind':request.kind,'entityId':request.entityId,'payload':request.payload},sort_keys=True,allow_nan=False).encode()).hexdigest()
        except ValueError as exc:raise HTTPException(422,'demo.error.range') from exc
        try:
            with store.connection(write=True) as db:
                state=read(db)
                old=db.execute('SELECT fingerprint,entity_id FROM civic_demo_operations WHERE id=?',(request.operationId,)).fetchone()
                if old:
                    if old[0]!=fingerprint:raise HTTPException(409,'demo.error.operation')
                    return {'state':state,'entityId':old[1],'replayed':True}
                if request.expectedRevision!=state['revision']:raise HTTPException(409,'demo.error.revision')
                payload=request.payload;kind=request.kind;identifier=request.entityId;at=now()
                def find(collection,identity):
                    row=next((row for row in state[collection] if row['id']==identity),None)
                    if not row:raise HTTPException(404,'demo.error.missing')
                    return row
                def link_settlement(row):find('settlements',row['settlementId'])
                def track(row,event,changes=None):
                    item=add_event(state,event,kind,row['id'],at);row.setdefault('history',[]).append({**item,'notes':payload.get('notes',''),'changes':changes or {}})
                if kind=='createIssue':
                    row=IssueInput.model_validate(payload).model_dump(mode='json');link_settlement(row);identifier=uid('ISS')
                    image=row.pop('attachment',None);attachment_meta=None
                    if image:
                        if os.getenv('URBANSAARTHI_EVIDENCE_STORAGE')!='sqlite':raise HTTPException(503,'demo.error.imageDisabled')
                        if image.get('consent') is not True:fail('demo.error.consent')
                        try:raw=base64.b64decode(image.get('base64',''),validate=True)
                        except (ValueError,TypeError) as exc:raise HTTPException(422,'demo.error.image') from exc
                        mime=image.get('contentType');prefix={'image/png':b'\x89PNG\r\n\x1a\n','image/jpeg':b'\xff\xd8\xff'}.get(mime)
                        if not prefix or not 0<len(raw)<=2097152 or not raw.startswith(prefix):fail('demo.error.image')
                        name=Path(str(image.get('filename','image')).replace('\\','/')).name[:120]
                        attachment_meta={'filename':name,'contentType':mime,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
                        db.execute('INSERT INTO civic_demo_attachments VALUES(?,?,?)',(identifier,mime,raw))
                    row.update(id=identifier,status='open',createdAt=at,updatedAt=at,resolvedAt=None,reporterDisplayName='Demo participant',assignedOwner=None,attachment=attachment_meta,history=[],sourceType='synthetic',seeded=False)
                    state['issues'].insert(0,row);track(row,'issue_created')
                elif kind=='updateIssue':
                    row=find('issues',identifier)
                    if not set(payload).issubset({'status','notes','assignedOwner'}) or not isinstance(payload.get('notes'),str) or not 3<=len(payload['notes'].strip())<=2000:fail('demo.error.notes')
                    status=payload.get('status',row['status'])
                    if status not in ISSUE_STATUSES:fail('demo.error.state')
                    transitions={'open':{'open','acknowledged','in_progress','resolved'},'acknowledged':{'acknowledged','in_progress','resolved'},'in_progress':{'in_progress','resolved','open'},'resolved':{'resolved','closed','open'},'closed':{'closed','open'}}
                    if status not in transitions[row['status']]:fail('demo.error.transition')
                    if payload.get('assignedOwner') and not str(payload['assignedOwner']).startswith('Demo '):fail('demo.error.owner')
                    before_status=row['status'];before_owner=row.get('assignedOwner')
                    row.update(status=status,updatedAt=at,resolvedAt=at if status=='resolved' and row['status']!='resolved' else row.get('resolvedAt') if status in ('resolved','closed') else None)
                    if 'assignedOwner' in payload:row['assignedOwner']=payload['assignedOwner'] or None
                    event={'acknowledged':'issue_acknowledged','in_progress':'issue_in_progress','resolved':'issue_resolved','closed':'issue_closed','open':'issue_reopened'}.get(status,'issue_updated') if status!=before_status else 'issue_assigned' if before_owner!=row.get('assignedOwner') else 'issue_follow_up'
                    track(row,event,{'status':{'before':before_status,'after':status},'assignedOwner':{'before':before_owner,'after':row.get('assignedOwner')}})
                elif kind in ('createProject','updateProject','createVisit','updateVisit','createMilestone','updateMilestone','createAssessment','updateAssessment'):
                    model,collection,prefix={'Project':(ProjectInput,'projects','PROJ'),'Visit':(VisitInput,'visits','VISIT'),'Milestone':(MilestoneInput,'milestones','MILE'),'Assessment':(AssessmentInput,'assessments','ASSESS')}[kind.replace('create','').replace('update','')]
                    creating=kind.startswith('create');previous=None if creating else find(collection,identifier)
                    if not set(payload).issubset(model.model_fields):fail('demo.error.fields')
                    before_values={key:previous[key] for key in model.model_fields if key in previous} if previous else {}
                    inputs={**({key:previous[key] for key in model.model_fields if key in previous} if previous else {}),**payload}
                    row=model.model_validate(inputs).model_dump(mode='json')
                    if collection=='milestones':find('projects',row['projectId'])
                    else:link_settlement(row)
                    if collection=='visits' and creating and (row['status']!='scheduled' or date.fromisoformat(row['scheduledDate'])<today()):fail('demo.error.date')
                    if collection=='assessments' and (date.fromisoformat(row['assessmentDate'])>today() or row['householdCount']>find('settlements',row['settlementId'])['householdEstimate']):fail('demo.error.range')
                    identifier=uid(prefix) if creating else identifier
                    if creating:
                        row.update(id=identifier,history=[],sourceType='synthetic',seeded=False);state[collection].insert(0,row)
                    else:previous.update(row);row=previous
                    row['lastUpdated' if collection=='projects' else 'updatedAt']=at
                    event=collection[:-1]+'_created' if creating else 'visit_'+row['status'] if collection=='visits' and row['status'] in ('completed','cancelled') else collection[:-1]+'_updated'
                    changes={key:{'before':before_values.get(key),'after':row.get(key)} for key in model.model_fields if not creating and before_values.get(key)!=row.get(key)}
                    track(row,event,changes)
                elif kind=='applyFindings':
                    visit=find('visits',identifier)
                    if visit['status']!='completed' or not visit['findings'] or not payload.get('confirm') or len(str(payload.get('notes','')).strip())<5:fail('demo.error.confirm')
                    settlement=find('settlements',visit['settlementId']);changes={}
                    for key,value in visit['findings'].items():
                        field=METRIC_FIELDS[key];changes[field]={'before':settlement[field],'after':value};settlement[field]=value
                    settlement['indicatorHistory'].append({'visitId':identifier,'changes':changes,'createdAt':at,'notes':payload['notes'],'is_synthetic':True})
                    add_event(state,'indicators_updated','settlement',settlement['id'],at)
                elif kind=='createFeedback':
                    row=FeedbackInput.model_validate(payload).model_dump(mode='json');link_settlement(row)
                    if row['projectId'] and find('projects',row['projectId'])['settlementId']!=row['settlementId']:fail('demo.error.relation')
                    identifier=uid('FEEDBACK');row.update(id=identifier,createdAt=at,status='pending',response='',reporterDisplayName='Anonymous demo participant',history=[],sourceType='synthetic');state['feedback'].insert(0,row);track(row,'feedback_created')
                elif kind=='updateFeedback':
                    row=find('feedback',identifier)
                    if set(payload)-{'status','response','notes'} or payload.get('status') not in ('pending','reviewed','follow_up','resolved') or not 3<=len(str(payload.get('response','')).strip())<=2000:fail('demo.error.notes')
                    before={'status':row['status'],'response':row['response']};row.update(status=payload['status'],response=payload['response'],updatedAt=at);track(row,'feedback_updated',{key:{'before':value,'after':row[key]} for key,value in before.items() if value!=row[key]})
                elif kind=='settings':
                    if set(payload)-{'targets','weights'}:fail('demo.error.fields')
                    for key in ('targets','weights'):
                        if key in payload:state[key]=payload[key]
                    identifier='DEMO-SETTINGS';add_event(state,'settings_updated','workspace',identifier,at)
                elif kind=='reset':
                    if payload.get('confirm') is not True:fail('demo.error.confirm')
                    revision=state['revision'];state=seed_demo();state['revision']=revision;identifier='DEMO-WORKSPACE'
                    db.execute('DELETE FROM civic_demo_attachments');db.execute('DELETE FROM civic_demo_operations');add_event(state,'reset','workspace',identifier,at)
                else:fail('demo.error.action')
                state['revision']+=1;state['lastSavedAt']=at
                for source in state['dataSources']:
                    source['recordCount']=len(state[source['dataType']]);source['updatedAt']=at
                mark_synthetic(state);validate_workspace(state)
                db.execute('UPDATE civic_demo_workspace SET body=? WHERE id=1',(json.dumps(state,allow_nan=False),))
                db.execute('INSERT INTO civic_demo_operations VALUES(?,?,?)',(request.operationId,fingerprint,identifier))
                return {'state':state,'entityId':identifier,'replayed':False}
        except HTTPException:raise
        except (ValueError,KeyError,TypeError) as exc:
            if 'demo.error.' in str(exc):
                import re
                match=re.search(r'demo\.error\.[A-Za-z]+',str(exc));raise HTTPException(422,match[0] if match else 'demo.error.fields') from exc
            raise HTTPException(422,'demo.error.fields') from exc
    return router
