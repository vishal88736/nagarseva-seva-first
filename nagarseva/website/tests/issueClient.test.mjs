import assert from 'node:assert/strict'
import { test } from 'node:test'
import { confirmedIssue } from '../src/urban/issueClient.ts'

const saved = {id:'ISS-012345ABCDEF',category:'water',description:'TEST ONLY saved software report',status:'submitted',official_submission:false,verification_status:'self_reported',report_date:'2026-10-29',reported_at:'2026-10-29T00:00:00Z'}
test('An unexpected successful HTTP payload cannot confirm issue persistence',()=>{
  for(const value of [null,{},[],{...saved,id:undefined},{...saved,official_submission:true},{...saved,reported_at:'not a date'},{...saved,status:'invented'}]) assert.throws(()=>confirmedIssue(value),/persistenceUnconfirmed/)
})
test('A valid persisted issue retains its exact source response',()=>assert.equal(confirmedIssue(saved),saved))
