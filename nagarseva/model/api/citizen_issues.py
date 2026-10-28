"""Persist self-reported prototype issues; never submit to a municipal authority."""
from __future__ import annotations

import base64
import binascii
import csv
from datetime import date, datetime, timezone, timedelta
import hashlib
import io
import json
import math
import os
from pathlib import Path
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

CATEGORIES = Literal['water','sanitation','drainage','waste','access','electricity','other']
STATUSES = Literal['submitted','under_review','resolved']


class Attachment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    filename: str = Field(min_length=1,max_length=120)
    content_type: Literal['image/png','image/jpeg']
    content_base64: str = Field(max_length=2_800_000)
    consent: bool


class IssueInput(BaseModel):
    model_config = ConfigDict(extra='forbid',str_strip_whitespace=True,allow_inf_nan=False)
    category: CATEGORIES
    description: str = Field(min_length=10,max_length=2000)
    ward: str | None = Field(None,max_length=120)
    location: str | None = Field(None,max_length=300)
    latitude: float | None = Field(None,ge=-90,le=90,strict=True)
    longitude: float | None = Field(None,ge=-180,le=180,strict=True)
    report_date: date
    attachment: Attachment | None = None

    @model_validator(mode='after')
    def valid_report(self):
        if self.report_date > datetime.now(timezone(timedelta(hours=5,minutes=30))).date():
            raise ValueError('The report date cannot be in the future.')
        if bool(self.latitude is not None) != bool(self.longitude is not None):
            raise ValueError('Supply both coordinates or leave both blank.')
        for coordinate in (self.latitude,self.longitude):
            if coordinate is not None and (not math.isfinite(coordinate) or abs(coordinate-round(coordinate,3))>1e-9):
                raise ValueError('Use at most three decimal places for an approximate public location.')
        return self


class IssueUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid',str_strip_whitespace=True)
    status: STATUSES
    note: str = Field(min_length=5,max_length=1000)
    reviewer_reference: str = Field(min_length=2,max_length=80)


def now(): return datetime.now(timezone.utc).isoformat()


def create_issue_router(provider, officer_access):
    router=APIRouter(prefix='/urban/data/issues',tags=['Prototype issue reports'])
    store=provider().store
    with store.connection(write=True) as db:
        db.executescript((Path(__file__).parent/'migrations/002_citizen_issues.sql').read_text())
        db.execute('INSERT OR IGNORE INTO public_schema_migrations VALUES(2,?)',(now(),))

    def public(row):
        # No attachment bytes, reviewer identities, tokens or machine paths in public responses.
        return {key:value for key,value in row.items() if key not in {'history','reviewer_reference'}}

    def find(identifier,db):
        row=db.execute('SELECT body FROM citizen_issues WHERE id=?',(identifier,)).fetchone()
        if not row: raise HTTPException(404,'Issue report not found.')
        return json.loads(row[0])

    @router.get('/summary')
    def summary():
        with store.connection() as db:
            counts=dict(db.execute('SELECT status,COUNT(*) FROM citizen_issues GROUP BY status').fetchall())
            recent=[public(json.loads(row[0])) for row in db.execute('SELECT body FROM citizen_issues ORDER BY reported_at DESC,id DESC LIMIT 5')]
        return {'total':sum(counts.values()),'open':counts.get('submitted',0)+counts.get('under_review',0),'by_status':{s:counts.get(s,0) for s in ('submitted','under_review','resolved')},'recent':recent,'official_submission':False}

    @router.get('')
    def listing(status: STATUSES | None = None, category: CATEGORIES | None = None, page: int = Query(1,ge=1), page_size: int = Query(20,ge=1,le=100)):
        clauses,values=[],[]
        if status: clauses.append('status=?');values.append(status)
        if category: clauses.append('category=?');values.append(category)
        where=' WHERE '+' AND '.join(clauses) if clauses else ''
        with store.connection() as db:
            total=db.execute('SELECT COUNT(*) FROM citizen_issues'+where,values).fetchone()[0]
            rows=db.execute('SELECT body FROM citizen_issues'+where+' ORDER BY reported_at DESC,id DESC LIMIT ? OFFSET ?',[*values,page_size,(page-1)*page_size]).fetchall()
        return {'items':[public(json.loads(row[0])) for row in rows],'total':total,'page':page,'page_size':page_size,'official_submission':False}

    @router.get('/report.csv')
    def report():
        with store.connection() as db: rows=[public(json.loads(row[0])) for row in db.execute('SELECT body FROM citizen_issues ORDER BY reported_at DESC,id DESC')]
        fields=['id','category','description','ward','location','report_date','reported_at','status','latitude','longitude','official_submission']
        buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=fields);writer.writeheader()
        for row in rows:
            writer.writerow({field:("'"+str(row[field]) if isinstance(row.get(field),str) and row[field].lstrip().startswith(('=','+','-','@')) else row.get(field)) for field in fields})
        return Response(buffer.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="urbansaarthi-reported-issues.csv"'})

    @router.post('')
    def create(payload: IssueInput, idempotency_key: str = Header(...,alias='Idempotency-Key',min_length=16,max_length=80,pattern=r'^[a-zA-Z0-9:_-]+$')):
        raw=payload.model_dump(mode='json');fingerprint=hashlib.sha256(json.dumps(raw,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        attachment=payload.attachment;content=None
        if attachment:
            if os.getenv('URBANSAARTHI_EVIDENCE_STORAGE') != 'sqlite': raise HTTPException(503,'Issue image storage is not configured. Submit without an image.')
            if not attachment.consent: raise HTTPException(422,'Permission is required before storing a supporting image.')
            try: content=base64.b64decode(attachment.content_base64,validate=True)
            except (ValueError,binascii.Error) as exc: raise HTTPException(422,'The supporting image is not valid base64.') from exc
            if not 0<len(content)<=2_097_152: raise HTTPException(422,'Supporting images must be nonempty and at most 2 MiB.')
            signature=b'\x89PNG\r\n\x1a\n' if attachment.content_type=='image/png' else b'\xff\xd8\xff'
            if not content.startswith(signature): raise HTTPException(422,'File signature does not match its declared type.')
        with store.connection(write=True) as db:
            existing=db.execute('SELECT request_sha256,body FROM citizen_issues WHERE idempotency_key=?',(idempotency_key,)).fetchone()
            if existing:
                if existing[0]!=fingerprint: raise HTTPException(409,'This submission key was already used for a different report. Start a new report.')
                return JSONResponse(public(json.loads(existing[1])),status_code=200)
            timestamp=now();identifier='ISS-'+secrets.token_hex(6).upper()
            row={**{k:v for k,v in raw.items() if k!='attachment'},'id':identifier,'status':'submitted','reported_at':timestamp,'updated_at':timestamp,'official_submission':False,'verification_status':'self_reported',
                 'attachment':{'filename':Path(attachment.filename.replace('\\','/')).name,'content_type':attachment.content_type,'sha256':hashlib.sha256(content).hexdigest()} if attachment else None,'history':[]}
            db.execute('INSERT INTO citizen_issues VALUES(?,?,?,?,?,?,?)',(identifier,idempotency_key,fingerprint,payload.category,'submitted',timestamp,json.dumps(row,ensure_ascii=False)))
            if content: db.execute('INSERT INTO citizen_issue_attachments VALUES(?,?,?,?,?)',(identifier,row['attachment']['filename'],attachment.content_type,hashlib.sha256(content).hexdigest(),content))
        return JSONResponse(public(row),status_code=201)

    @router.get('/{identifier}')
    def detail(identifier:str):
        with store.connection() as db: return public(find(identifier,db))

    @router.get('/{identifier}/image',dependencies=[Depends(officer_access)])
    def image(identifier:str):
        with store.connection() as db: row=db.execute('SELECT content_type,content FROM citizen_issue_attachments WHERE issue_id=?',(identifier,)).fetchone()
        if not row: raise HTTPException(404,'Supporting image not found.')
        return Response(row[1],media_type=row[0],headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Disposition':'attachment'})

    @router.patch('/{identifier}',dependencies=[Depends(officer_access)])
    def update(identifier:str,payload:IssueUpdate):
        with store.connection(write=True) as db:
            row=find(identifier,db);row['status']=payload.status;row['updated_at']=now()
            row.setdefault('history',[]).append({**payload.model_dump(),'at':row['updated_at']})
            row['resolution_note']=payload.note
            db.execute('UPDATE citizen_issues SET status=?,body=? WHERE id=?',(payload.status,json.dumps(row,ensure_ascii=False),identifier))
        return public(row)

    return router
