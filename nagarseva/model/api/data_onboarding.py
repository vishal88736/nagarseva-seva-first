"""Controlled CSV/GeoJSON onboarding. No external fetches or active-adapter switch.

Original bytes and mapped records are stored only after validation, permission
attestation, explicit import confirmation and existing officer-key authorization.
Schema validation is not independent source verification.
"""
from __future__ import annotations
import base64
import binascii
import csv
from datetime import datetime,timezone,date,timedelta
import hashlib
import io
import json
import math
from pathlib import Path
import secrets
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter,Header,HTTPException
from fastapi.responses import Response
from pydantic import BaseModel,ConfigDict,Field
from .file_formats import read_xlsx
from shapely.geometry import shape
from shapely.errors import GEOSException
from shapely.validation import explain_validity

CATEGORIES=('boundaries','identifiers','housing','services','projects','issues','visits')
MAX_BYTES=5*1024*1024
MAX_ROWS=5000
# A deliberately bounded, explicit import contract. Unmapped fields remain in the original.
FIELDS={
 'boundaries':{'id':'required','name':'required','geometry':'geometry','ward':'text','village':'text','taluka':'text','sourceYear':'year'},
 'identifiers':{'id':'required','name':'required','ward':'text','village':'text','taluka':'text','latitude':'latitude','longitude':'longitude','sourceYear':'year'},
 'housing':{'id':'required','settlementId':'required','householdCount':'integer','assessmentDate':'date','housingCondition':'text','notes':'text'},
 'services':{'id':'required','settlementId':'required','measurementDate':'date','waterAccessPercent':'percent','sanitationAccessPercent':'percent','drainageCoveragePercent':'percent','wasteCollectionPercent':'percent','electricityAccessPercent':'percent','roadAccessPercent':'percent'},
 'projects':{'id':'required','settlementId':'required','name':'required','stage':'text','status':'text','progressPercent':'percent','estimatedBudget':'number','startDate':'date','expectedCompletionDate':'date','agency':'text'},
 'issues':{'id':'required','settlementId':'required','category':'required','status':'required','createdAt':'date','resolvedAt':'date','description':'text'},
 'visits':{'id':'required','settlementId':'required','scheduledDate':'date','visitType':'required','status':'required','owner':'text','notes':'text'},
}
REQUIRED={key:[field for field,kind in fields.items() if kind=='required'] for key,fields in FIELDS.items()}
REQUIRED['boundaries'].append('geometry');REQUIRED['housing']+=['householdCount','assessmentDate'];REQUIRED['services'].append('measurementDate');REQUIRED['issues'].append('createdAt');REQUIRED['visits'].append('scheduledDate')
ALIASES={
 'id':['id','Cluster_ID','settlement_id','cluster_id','project_id','issue_id','visit_id','assessment_id'],
 'name':['name','Slum_Name','settlement_name','project_name'], 'settlementId':['settlementId','settlement_id','Cluster_ID','cluster_id'],
 'ward':['Ward','ward_id','ward'], 'village':['Village_Division','village'], 'taluka':['Taluka'],
 'geometry':['@geometry','geometry','polygon'], 'latitude':['latitude','lat'], 'longitude':['longitude','lon','lng'],
 'householdCount':['householdCount','households','No_HH'], 'measurementDate':['measurementDate','measurement_date','observed_at'],
 'assessmentDate':['assessmentDate','assessment_date'], 'scheduledDate':['scheduledDate','scheduled_date'],
}

class FileInput(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    filename:str=Field(min_length=1,max_length=200)
    contentBase64:str=Field(max_length=7_000_000)
    permissionAccepted:bool=False
    sheetName:str | None=Field(default=None,max_length=100)
class MappingInput(FileInput):
    category:Literal['boundaries','identifiers','housing','services','projects','issues','visits']
    mapping:dict[str,str]=Field(default_factory=dict)
    crsConfirmed:bool=False
    settlementBatchId:str | None=None
class ImportInput(MappingInput):
    confirm:bool=False
    expectedSha256:str=Field(pattern=r'^[a-f0-9]{64}$')
    sourceName:str=Field(min_length=3,max_length=200)
    publisher:str=Field(min_length=2,max_length=160)
    sourceUrl:str=Field(min_length=8,max_length=1000)
    sourceDate:date
    licence:str=Field(min_length=3,max_length=1000)
    dataClass:Literal['demo','manually_provided']='manually_provided'
    publicationYear:int | None=Field(default=None,ge=1800,le=2200,strict=True)
    coverage:str=Field(min_length=3,max_length=300)


def issue(code,row=None,field=None,detail=None):return {'code':code,'row':row,'field':field,'detail':detail}
def reject(code):raise HTTPException(422,code)
def timestamp():return datetime.now(timezone.utc).isoformat()

def decode_file(payload):
    if not payload.permissionAccepted:reject('ir.error.permission')
    suffix=Path(payload.filename).suffix.lower()
    if suffix not in ('.csv','.geojson','.json','.xlsx'):reject('ir.error.type')
    try:raw=base64.b64decode(payload.contentBase64,validate=True)
    except (ValueError,binascii.Error) as exc:raise HTTPException(422,'ir.error.encoding') from exc
    if not 0<len(raw)<=MAX_BYTES:reject('ir.error.size')
    try:text=raw.decode('utf-8-sig') if suffix!='.xlsx' else ''
    except UnicodeDecodeError as exc:raise HTTPException(422,'ir.error.encoding') from exc
    errors=[];records=[];geometry=False;workbook={}
    if suffix=='.xlsx':
        records,columns,errors,workbook=read_xlsx(raw,payload.sheetName);fmt='XLSX'
    elif suffix=='.csv':
        try:
            reader=csv.reader(io.StringIO(text,newline=''),strict=True);columns=next(reader,[])
            if not columns or any(not key.strip() for key in columns) or len(set(columns))!=len(columns):reject('ir.error.columns')
            if len(columns)>100:reject('ir.error.columns')
            for index,values in enumerate(reader,1):
                if not values:continue
                if index>MAX_ROWS:reject('ir.error.limit')
                if len(values)!=len(columns):errors.append(issue('ir.error.rowWidth',reader.line_num));records.append({'@sourceRow':reader.line_num});continue
                records.append({**dict(zip(columns,values)),'@sourceRow':reader.line_num})
        except csv.Error as exc:raise HTTPException(422,'ir.error.csv') from exc
        fmt='CSV'
    else:
        try:
            document=json.loads(text,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
        except (ValueError,RecursionError) as exc:raise HTTPException(422,'ir.error.json') from exc
        if not isinstance(document,dict) or document.get('type')!='FeatureCollection' or not isinstance(document.get('features'),list):reject('ir.error.collection')
        if document.get('crs') is not None:errors.append(issue('ir.error.crs'))
        if len(document['features'])>MAX_ROWS:reject('ir.error.limit')
        columns=[]
        for index,feature in enumerate(document['features'],1):
            if not isinstance(feature,dict) or feature.get('type')!='Feature':errors.append(issue('ir.error.feature',index));records.append({});continue
            properties=feature.get('properties')
            if properties is not None and not isinstance(properties,dict):errors.append(issue('ir.error.properties',index))
            if not isinstance(properties,dict):properties={}
            if '@geometry' in properties or '@sourceRow' in properties:errors.append(issue('ir.error.reserved',index))
            record={**properties,'@geometry':feature.get('geometry')}
            geometry=geometry or feature.get('geometry') is not None
            for key in properties:
                if key not in columns:columns.append(key)
            records.append(record)
        if geometry:columns.append('@geometry')
        fmt='GeoJSON'
    if '@sourceRow' in columns:errors.append(issue('ir.error.reserved'))
    if not records:errors.append(issue('ir.error.empty'))
    if len(columns)>100:reject('ir.error.columns')
    metadata={'filename':Path(payload.filename.replace('\\','/')).name,'bytes':len(raw),'format':fmt,'recordCount':len(records),'columns':columns,'sha256':hashlib.sha256(raw).hexdigest(),'inspectedAt':timestamp(),'stored':False,'parserVersion':2,**workbook}
    return raw,records,metadata,errors


def geographic(geometry,row):
    errors=[];positions=[]
    if isinstance(geometry,str):
        try:geometry=json.loads(geometry)
        except (ValueError,RecursionError):return None,[],[issue('ir.error.geometry',row,'geometry')]
    if not isinstance(geometry,dict) or geometry.get('type') not in ('Polygon','MultiPolygon','Point'):
        return None,[],[issue('ir.error.geometry',row,'geometry')]
    def walk(value,depth=0):
        if depth>5 or not isinstance(value,list) or not value:raise ValueError()
        if isinstance(value[0],(int,float)) and not isinstance(value[0],bool):
            if len(value) not in (2,3) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in value) or not -180<=value[0]<=180 or not -90<=value[1]<=90:raise ValueError()
            positions.append(value[:2])
            if len(positions)>50000:raise ValueError()
        else:
            for child in value:walk(child,depth+1)
    try:
        walk(geometry.get('coordinates'))
        # Shapely closes rings automatically; reject an unclosed input before calling it.
        rings=geometry['coordinates'] if geometry['type']=='Polygon' else [ring for polygon in geometry['coordinates'] for ring in polygon] if geometry['type']=='MultiPolygon' else []
        for ring in rings:
            if len(ring)<4 or ring[0]!=ring[-1]:raise ValueError()
        value=shape(geometry)
        if value.is_empty or not value.is_valid:errors.append(issue('ir.error.geometry',row,'geometry',explain_validity(value)))
    except (ValueError,TypeError,KeyError,IndexError,RecursionError,GEOSException):errors.append(issue('ir.error.coordinates',row,'geometry'))
    return geometry,positions if not errors else [],errors


def suggestions(columns,category):
    normalized={key.lower().replace('_','').replace(' ',''):key for key in columns}
    result={}
    for field in FIELDS[category]:
        for name in ({'boundaries':['id','Cluster_ID','settlement_id','cluster_id'],'identifiers':['id','Cluster_ID','settlement_id','cluster_id'],'housing':['assessment_id','id'],'services':['observation_id','indicator_id','id'],'projects':['project_id','id'],'issues':['issue_id','complaint_id','id'],'visits':['visit_id','id']}[category] if field=='id' else [field,*ALIASES.get(field,[])]):
            candidate=normalized.get(name.lower().replace('_','').replace(' ',''))
            if candidate is not None:result[field]=candidate;break
    return result


def validate_mapping(payload,linked_ids=None):
    raw,records,metadata,errors=decode_file(payload);warnings=[];fields=FIELDS[payload.category]
    missing=[key for key in REQUIRED[payload.category] if not payload.mapping.get(key)]
    for key in missing:errors.append(issue('ir.error.mapping',field=key))
    used=[value for value in payload.mapping.values() if value]
    if len(set(used))!=len(used):errors.append(issue('ir.error.mappingDuplicate'))
    if any(key not in fields or value and value not in metadata['columns'] for key,value in payload.mapping.items()):errors.append(issue('ir.error.mapping'))
    if payload.category=='services' and not any(payload.mapping.get(key) for key,kind in fields.items() if kind=='percent'):errors.append(issue('ir.error.serviceMapping'))
    transformed=[];seen=set();positions=[]
    for record_index,record in enumerate(records,1):
        index=record.get('@sourceRow',record_index) if metadata['format'] in ('CSV','XLSX') else record_index
        row={}
        source_geometry=None
        if record.get('@geometry') is not None:
            source_geometry,points,problems=geographic(record['@geometry'],index);positions.extend(points);errors.extend(problems)
        for field,column in payload.mapping.items():
            if not column or field not in fields:continue
            value=record.get(column);kind=fields[field]
            if value is None or isinstance(value,str) and not value.strip():
                row[field]=None
                if field in REQUIRED[payload.category]:errors.append(issue('ir.error.missing',index,field))
                continue
            if kind=='geometry':
                mapped,points,problems=(source_geometry,[],[]) if column=='@geometry' else geographic(value,index);row[field]=mapped;positions.extend(points);errors.extend(problems)
                if mapped and mapped.get('type') not in ('Polygon','MultiPolygon'):errors.append(issue('ir.error.polygon',index,field))
                continue
            if kind in ('percent','integer','number','latitude','longitude','year'):
                try:
                    if isinstance(value,bool):raise ValueError()
                    number=float(value)
                    if not math.isfinite(number) or kind in ('number','integer') and number<0 or kind=='percent' and not 0<=number<=100 or kind=='latitude' and not -90<=number<=90 or kind=='longitude' and not -180<=number<=180 or kind=='year' and not 1800<=number<=2200 or kind in ('year','integer') and number!=int(number):raise ValueError()
                    row[field]=int(number) if kind in ('year','integer') else number
                except (ValueError,TypeError,OverflowError):errors.append(issue('ir.error.number',index,field))
            elif kind=='date':
                try:
                    if not isinstance(value,str):raise ValueError()
                    if len(value)==10:date.fromisoformat(value)
                    else:
                        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
                        if parsed.tzinfo is None:raise ValueError()
                    row[field]=value
                except ValueError:errors.append(issue('ir.error.date',index,field))
            else:
                if isinstance(value,(dict,list,bool)):errors.append(issue('ir.error.text',index,field));continue
                value=str(value)
                if len(value)>4000:errors.append(issue('ir.error.text',index,field));continue
                row[field]=value
                if field in ('id','settlementId') and value!=value.strip():errors.append(issue('ir.error.identifierWhitespace',index,field))
        identifier=row.get('id')
        if identifier:
            if identifier in seen:errors.append(issue('ir.error.duplicate',index,'id'))
            seen.add(identifier)
        if payload.category not in ('boundaries','identifiers'):
            if linked_ids is None:errors.append(issue('ir.error.linkBatch',index,'settlementId'))
            elif row.get('settlementId') not in linked_ids:errors.append(issue('ir.error.orphan',index,'settlementId'))
        if 'latitude' in row or 'longitude' in row:
            if row.get('latitude') is None or row.get('longitude') is None:errors.append(issue('ir.error.coordinatePair',index))
            else:positions.append([row['longitude'],row['latitude']])
        for start,end in [('startDate','expectedCompletionDate'),('createdAt','resolvedAt')]:
            if row.get(start) and row.get(end):
                try:
                    first=datetime.fromisoformat(row[start].replace('Z','+00:00'));last=datetime.fromisoformat(row[end].replace('Z','+00:00'))
                    if first.tzinfo is None:first=first.replace(tzinfo=timezone.utc)
                    if last.tzinfo is None:last=last.replace(tzinfo=timezone.utc)
                    if last<first:errors.append(issue('ir.error.chronology',index,end))
                except ValueError:pass
        allowed={'housing':{'housingCondition':('temporary','needs_repair','stable')},'issues':{'category':('water','sanitation','drainage','waste','electricity','access','other'),'status':('open','acknowledged','in_progress','resolved','closed')},'projects':{'stage':('assessment','planning','consultation','approval','implementation','completed','on_hold'),'status':('active','paused','completed','cancelled')},'visits':{'visitType':('housing','water','sanitation','drainage','waste','electricity','access','other'),'status':('scheduled','completed','cancelled')}}.get(payload.category,{})
        for field,values in allowed.items():
            if row.get(field) is not None and row[field] not in values:errors.append(issue('ir.error.enum',index,field))
        transformed.append(row)
    if positions and not payload.crsConfirmed:errors.append(issue('ir.error.confirmCrs'))
    if len(positions)>100000:errors.append(issue('ir.error.limit'))
    bounds=[min(p[0] for p in positions),min(p[1] for p in positions),max(p[0] for p in positions),max(p[1] for p in positions)] if positions else None
    if bounds and not (72.5<=bounds[0]<=73.5 and 18.5<=bounds[1]<=19.6 and 72.5<=bounds[2]<=73.5 and 18.5<=bounds[3]<=19.6):warnings.append(issue('ir.warning.extent'))
    if payload.category=='identifiers' and not positions:warnings.append(issue('ir.warning.noGeometry'))
    warnings.extend([issue('ir.warning.schemaOnly'),issue('ir.warning.isolated')])
    filled=sum(row.get(field) is not None and row.get(field)!='' for row in transformed for field in fields)
    required_filled=sum(row.get(field) is not None and row.get(field)!='' for row in transformed for field in REQUIRED[payload.category])
    completeness=round(filled/(len(transformed)*len(fields))*100,1) if transformed else 0
    required_completeness=round(required_filled/(len(transformed)*len(REQUIRED[payload.category]))*100,1) if transformed else 0
    return raw,transformed,{'completenessPercent':completeness,'requiredCompletenessPercent':required_completeness,**metadata,'category':payload.category,'bounds':bounds,'missingRequiredFields':missing,'errors':errors[:300],'errorCount':len(errors),'warnings':warnings,'valid':not errors,'preview':transformed[:10],'validatedAt':timestamp(),'mapping':payload.mapping,'status':'validation_passed' if not errors else 'validation_failed'}


def create_onboarding_router(store,admin_access):
    router=APIRouter(prefix='/urban/integration',tags=['Controlled data onboarding; no external connection'])
    with store.connection(write=True) as db:
        db.execute('CREATE TABLE IF NOT EXISTS civic_import_batches (id TEXT PRIMARY KEY,category TEXT NOT NULL,fingerprint TEXT UNIQUE NOT NULL,receipt TEXT NOT NULL,records TEXT NOT NULL,original BLOB NOT NULL)')
    def links(payload,db):
        if payload.category in ('boundaries','identifiers'):return None
        if not payload.settlementBatchId:return None
        found=db.execute("SELECT records FROM civic_import_batches WHERE id=? AND category IN ('boundaries','identifiers')",(payload.settlementBatchId,)).fetchone()
        if not found:raise HTTPException(422,'ir.error.linkBatch')
        receipt=db.execute('SELECT receipt FROM civic_import_batches WHERE id=?',(payload.settlementBatchId,)).fetchone()
        if json.loads(receipt[0]).get('rolledBackAt'):raise HTTPException(422,'audit.error.rolledBack')
        return {row['id'] for row in json.loads(found[0])}
    @router.get('/schema')
    def schema():return {'fields':FIELDS,'required':REQUIRED,'maxBytes':MAX_BYTES,'maxRows':MAX_ROWS,'formats':['CSV','GeoJSON','XLSX']}
    @router.get('/templates/{category}')
    def template(category:str):
        if category not in FIELDS:raise HTTPException(404,'ir.error.mapping')
        stream=io.StringIO();csv.writer(stream).writerow(FIELDS[category].keys())
        return Response(stream.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{category}-template.csv"'})
    @router.get('/readiness')
    def readiness():
        with store.connection() as db:
            rows=[json.loads(row[0]) for row in db.execute('SELECT receipt FROM civic_import_batches') if not json.loads(row[0]).get('rolledBackAt')]
        return {'activeAdapter':'sqlite-synthetic','externalConnected':False,'categories':[{'category':category,'status':'imported_demo' if any(row['category']==category for row in rows) else 'not_provided','importedBatches':sum(row['category']==category for row in rows),'recordCount':sum(row['recordCount'] for row in rows if row['category']==category)} for category in CATEGORIES]}
    @router.post('/inspect')
    def inspect(payload:FileInput):
        _,records,metadata,errors=decode_file(payload)
        bounds=[]
        for index,row in enumerate(records,1):
            if row.get('@geometry') is not None:
                _,points,problems=geographic(row['@geometry'],index);bounds.extend(points);errors.extend(problems)
        if len(bounds)>100000:errors.append(issue('ir.error.limit'))
        return {**metadata,'errors':errors[:300],'errorCount':len(errors),'bounds':[min(p[0] for p in bounds),min(p[1] for p in bounds),max(p[0] for p in bounds),max(p[1] for p in bounds)] if bounds else None,'suggestions':{category:suggestions(metadata['columns'],category) for category in CATEGORIES}}
    @router.post('/validate')
    def validate(payload:MappingInput,x_officer_key:str | None=Header(None)):
        if payload.settlementBatchId:admin_access(x_officer_key)
        with store.connection() as db:return validate_mapping(payload,links(payload,db))[2]
    @router.get('/imports')
    def imports(x_officer_key:str | None=Header(None)):
        admin_access(x_officer_key)
        with store.connection() as db:return {'items':[json.loads(row[0]) for row in db.execute('SELECT receipt FROM civic_import_batches ORDER BY rowid DESC')]}
    @router.post('/imports')
    def import_file(payload:ImportInput,x_officer_key:str | None=Header(None)):
        admin_access(x_officer_key)
        if not payload.confirm:reject('ir.error.confirmImport')
        if payload.sourceDate>datetime.now(timezone(timedelta(hours=5,minutes=30))).date():reject('audit.error.sourceDate')
        if payload.sourceUrl:
            parsed=urlparse(payload.sourceUrl)
            if parsed.scheme not in ('https','http') or not parsed.netloc or parsed.username or parsed.password:reject('ir.error.sourceUrl')
        with store.connection(write=True) as db:
            raw,records,result=validate_mapping(payload,links(payload,db))
            if result['sha256']!=payload.expectedSha256:raise HTTPException(409,'ir.error.changed')
            if not result['valid']:raise HTTPException(422,{'code':'ir.error.validation','validation':result})
            provenance={key:(str(getattr(payload,key)) if key=='sourceDate' else getattr(payload,key)) for key in ('sourceName','publisher','sourceUrl','sourceDate','licence','publicationYear','coverage')}
            fingerprint=hashlib.sha256(json.dumps([result['sha256'],payload.category,payload.mapping,payload.settlementBatchId,provenance,payload.dataClass],sort_keys=True).encode()).hexdigest()
            prior=db.execute('SELECT receipt FROM civic_import_batches WHERE fingerprint=?',(fingerprint,)).fetchone()
            if prior:
                receipt=json.loads(prior[0])
                if receipt.get('rolledBackAt'):raise HTTPException(409,'audit.error.rolledBack')
                return {**receipt,'replayed':True}
            records=[{**row,'is_synthetic':payload.dataClass=='demo'} for row in records]
            incoming={row['id'] for row in records}
            for previous,receipt in db.execute('SELECT records,receipt FROM civic_import_batches WHERE category=?',(payload.category,)):
                meta=json.loads(receipt)
                if not meta.get('rolledBackAt') and meta.get('settlementBatchId')==payload.settlementBatchId and incoming.intersection(row['id'] for row in json.loads(previous)):raise HTTPException(409,'ir.error.duplicateImported')
            identifier='IMPORT-'+secrets.token_hex(8).upper()
            receipt={**{key:result[key] for key in ('filename','bytes','format','recordCount','columns','sha256','category','bounds','validatedAt','mapping','completenessPercent','requiredCompletenessPercent')},'id':identifier,'status':'imported_demo','importedAt':timestamp(),'sourceVerified':False,'stored':True,'active':False,'settlementBatchId':payload.settlementBatchId,'parserVersion':2,'excelPercentColumns':result.get('excelPercentColumns',[]),'sheet':result.get('sheet'),'provenance':provenance,'dataClass':payload.dataClass,'is_synthetic':payload.dataClass=='demo','history':[{'action':'import','createdAt':timestamp()}]}
            db.execute('INSERT INTO civic_import_batches VALUES(?,?,?,?,?,?)',(identifier,payload.category,fingerprint,json.dumps(receipt),json.dumps(records,allow_nan=False),raw))
            return receipt
    @router.post('/imports/{identifier}/rollback')
    def rollback(identifier:str,payload:dict,x_officer_key:str | None=Header(None)):
        admin_access(x_officer_key)
        if payload.get('confirm') is not True or not isinstance(payload.get('reason'),str) or not 5<=len(payload['reason'].strip())<=1000:reject('audit.error.rollbackReason')
        with store.connection(write=True) as db:
            found=db.execute('SELECT receipt FROM civic_import_batches WHERE id=?',(identifier,)).fetchone()
            if not found:raise HTTPException(404,'ir.error.missingBatch')
            receipt=json.loads(found[0])
            if receipt.get('rolledBackAt'):return receipt
            children=[json.loads(row[0]) for row in db.execute('SELECT receipt FROM civic_import_batches')]
            if any(row.get('settlementBatchId')==identifier and not row.get('rolledBackAt') for row in children):raise HTTPException(409,'audit.error.dependentBatch')
            at=timestamp();receipt.update(rolledBackAt=at,status='rolled_back')
            receipt.setdefault('history',[]).append({'action':'rollback','createdAt':at,'reason':payload['reason'].strip()})
            db.execute('UPDATE civic_import_batches SET receipt=? WHERE id=?',(json.dumps(receipt),identifier))
            return receipt
    @router.get('/imports/{identifier}/original')
    def original(identifier:str,x_officer_key:str | None=Header(None)):
        admin_access(x_officer_key)
        with store.connection() as db:row=db.execute('SELECT original,receipt FROM civic_import_batches WHERE id=?',(identifier,)).fetchone()
        if not row:raise HTTPException(404,'ir.error.missingBatch')
        return Response(row[0],media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename="source-data"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
    @router.get('/imports/{identifier}/records')
    def imported_records(identifier:str,x_officer_key:str | None=Header(None)):
        admin_access(x_officer_key)
        with store.connection() as db:row=db.execute('SELECT records,receipt FROM civic_import_batches WHERE id=?',(identifier,)).fetchone()
        if not row:raise HTTPException(404,'ir.error.missingBatch')
        return {'records':json.loads(row[0]),'receipt':json.loads(row[1])}
    return router
