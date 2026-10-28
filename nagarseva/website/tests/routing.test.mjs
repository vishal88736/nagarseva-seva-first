import assert from 'node:assert/strict'
import {test} from 'node:test'
import {MAIN_ROUTES,PATHS,routePage,activeSection} from '../src/urban/routing.ts'

test('Four primary routes resolve consistently and preserve deep links to existing tools',()=>{
 assert.equal(MAIN_ROUTES.length,4)
 for(const item of MAIN_ROUTES){assert.equal(routePage(item.path),item.id);assert.equal(activeSection(item.id),item.id)}
 assert.equal(routePage('/'), 'dashboard');assert.equal(routePage('/settlements/'),'settlements')
 assert.equal(routePage('/','#overview'),'dashboard');assert.equal(routePage('/','#explore'),'settlements')
 for(const page of ['prioritize','compare','assurance','data']){assert.equal(routePage(PATHS[page]),page);assert.equal(activeSection(page),'projects');assert.equal(routePage('/',`#${page}`),page)}
})
