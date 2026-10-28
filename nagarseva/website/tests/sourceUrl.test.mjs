import assert from 'node:assert/strict'
import {test} from 'node:test'
import {sourceUrl} from '../src/urban/sourceUrl.ts'

test('Only web source URLs become links; source labels, credentials and executable URLs remain text',()=>{
 assert.equal(sourceUrl('https://example.test/source'),'https://example.test/source')
 for(const value of ['Source supplied by user','javascript:alert(1)','data:text/html,hello','file:///home/test/input.csv','https://user:private@example.test/','',null])assert.equal(sourceUrl(value),undefined)
})
