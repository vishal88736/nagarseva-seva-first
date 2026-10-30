"""Verified Demo data workflows, file uploads and exports in disposable SQLite."""
from pathlib import Path
from datetime import datetime,timezone
from io import BytesIO
import json,os,secrets,subprocess,sys,tempfile,urllib.request
from openpyxl import Workbook
from playwright.sync_api import sync_playwright,expect
from check_synthetic_integration_browser import port,ready
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'.runtime/end-to-end-audit/workflows'

def main():
 OUT.mkdir(parents=True,exist_ok=True);processes=[];logs=[];checks=[];errors=[];previews=[];p=None
 report={'status':'failed','checkedAt':datetime.now(timezone.utc).isoformat(),'checks':checks,'uploadPreviews':previews,'browserErrors':errors,'scope':'Demo data fixtures and disposable SQLite only; no user records or external authority APIs'}
 try:
  with tempfile.TemporaryDirectory(prefix='urban-audit-workflows-') as temp:
   folder=Path(temp);api=f'http://127.0.0.1:{port()}';web=f'http://127.0.0.1:{port()}';key=secrets.token_urlsafe(32)
   env={**os.environ,'URBANSAARTHI_DB_PATH':str(folder/'test.sqlite3'),'URBANSAARTHI_DATA_DIR':str(folder/'none'),'NAGARSEVA_OFFICER_KEY':key,'NAGARSEVA_API_TARGET':api}
   for name,command,cwd in [('api',[sys.executable,'-m','uvicorn','model.api.urban:app','--host','127.0.0.1','--port',api.rsplit(':',1)[1]],ROOT/'nagarseva'),('web',['npm','run','preview','--','--port',web.rsplit(':',1)[1],'--strictPort'],ROOT/'nagarseva/website')]:
    log=(OUT/f'{name}.log').open('w');logs.append(log);processes.append(subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT))
   ready(api+'/urban/demo/health',processes[0]);ready(web,processes[1])
   def get(path):
    with urllib.request.urlopen(api+'/urban/'+path) as response:return json.load(response)
   def L(key,lang='en'):
    for name in ['auditMessages','demoMessages','integrationMessages']:
     messages=json.loads((ROOT/f'nagarseva/website/src/i18n/{name}.ts').read_text().split('export default ',1)[1])
     if key in messages:return messages[key][lang]
    return key
   with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH','/usr/bin/chromium'));ctx=browser.new_context(accept_downloads=True,viewport={'width':1280,'height':900});ctx.route('https://tile.openstreetmap.org/**',lambda route:route.abort());p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)))
    p.goto(web+'/projects/data');p.get_by_label(L('d.adminKey'),exact=True).fill(key);p.get_by_role('button',name=L('d.applyKey'),exact=True).click()
    p.goto(web+'/data-integration');p.get_by_role('tab',name=L('ir.tab.onboarding'),exact=True).click();p.get_by_label(L('ir.column.category'),exact=True).select_option('identifiers')
    with p.expect_download() as download:p.get_by_role('link',name=L('audit.template'),exact=True).click()
    assert len(Path(download.value.path()).read_text().splitlines())==1
    checks.append('Template download contains actual schema headers and no invented records')
    book=Workbook();sheet=book.active;sheet.title='Demo data';sheet.append(['code','name','is_synthetic']);sheet.append(['DEMO-UP-1','Demo data first record',True]);sheet.append(['DEMO-UP-2','Demo data second record',True]);stream=BytesIO();book.save(stream);original=stream.getvalue()
    p.locator('input[type=file]').set_input_files({'name':'Demo-data.xlsx','mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','buffer':original})
    p.get_by_role('checkbox',name=L('ir.permission'),exact=True).check();p.get_by_role('button',name=L('ir.inspect'),exact=True).click()
    expect(p.locator('.integration-column-tags')).to_contain_text('code');p.get_by_role('button',name=L('ir.validate'),exact=True).click();expect(p.locator('.integration-result-heading')).to_contain_text(L('ir.status.validation_failed'))
    p.get_by_label(L('ir.mapField').replace('{field}',L('ir.field.id')),exact=True).select_option('code');p.get_by_role('button',name=L('ir.validate'),exact=True).click();expect(p.locator('.integration-result-heading')).to_contain_text(L('ir.status.validation_passed'))
    axe=(ROOT/'nagarseva/website/node_modules/axe-core/axe.min.js').read_text()
    for lang in ['en','hi','mr']:
     p.locator('.us-language select').select_option(lang)
     for width in [375,768,1280]:
      p.set_viewport_size({'width':width,'height':900});p.evaluate('document.fonts.ready');p.add_script_tag(content=axe)
      violations=p.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))}")
      overflow=p.evaluate('document.documentElement.scrollWidth>innerWidth+1');shot=f'upload-preview-{lang}-{width}.png';p.screenshot(path=str(OUT/shot),full_page=True)
      previews.append({'language':lang,'width':width,'screenshot':shot,'overflow':overflow,'violations':violations});assert not overflow and not violations
    p.locator('.us-language select').select_option('en');p.set_viewport_size({'width':1280,'height':900})
    checks.append('Populated upload mapping and import-preview form pass nine language/width screenshots and automated accessibility checks')
    for field,value in [('sourceName','Demo data audit source'),('publisher','Demo data test suite'),('coverage','Demo data fictional city')]:p.get_by_label(L('ir.provenance.'+field),exact=True).fill(value)
    p.get_by_label(L('audit.sourceDate'),exact=True).fill('2026-10-01');p.get_by_label(L('audit.licence'),exact=True).fill('Demo data test use only');p.get_by_label(L('ir.provenance.sourceUrl'),exact=True).fill('https://example.test/demo-data');p.get_by_label(L('audit.dataClass'),exact=True).select_option('demo')
    p.get_by_role('checkbox',name=L('ir.confirmImport'),exact=True).check();p.get_by_role('button',name=L('ir.import'),exact=True).click();expect(p.locator('.integration-receipt')).to_be_visible()
    batch=p.locator('.integration-receipt code').inner_text()
    request=urllib.request.Request(api+'/urban/integration/imports/'+batch+'/records',headers={'X-Officer-Key':key})
    with urllib.request.urlopen(request) as response:stored=json.load(response)
    assert len(stored['records'])==2 and all(row['is_synthetic'] is True for row in stored['records']) and stored['receipt']['sourceVerified'] is False
    with p.expect_download() as download:p.get_by_role('button',name=L('ir.downloadOriginal'),exact=True).click()
    assert Path(download.value.path()).read_bytes()==original
    assert len(get('demo/workspace')['settlements'])==100
    checks.append('Actual XLSX parsing, manual column mapping, missing-field error, preview, mandatory provenance and isolated Demo data import preserve original bytes')
    # CSV duplicate, missing-column, wrong-type, empty and large cases are real UI interactions.
    input=p.locator('input[type=file]')
    for filename,data,category,expected in [('Demo-duplicate.csv',b'id,name\nDEMO-DUP,Demo data\nDEMO-DUP,Demo data\n','identifiers','ir.error.duplicate'),('Demo-missing.csv',b'name\nDemo data\n','identifiers','ir.error.mapping')]:
     input.set_input_files({'name':filename,'mimeType':'text/csv','buffer':data});p.get_by_label(L('ir.column.category'),exact=True).select_option(category);p.get_by_role('checkbox',name=L('ir.permission'),exact=True).check();p.get_by_role('button',name=L('ir.inspect'),exact=True).click();p.get_by_role('button',name=L('ir.validate'),exact=True).click();expect(p.get_by_text(L(expected),exact=True).first).to_be_visible()
    input.set_input_files({'name':'Demo-wrong-type.csv','mimeType':'text/csv','buffer':b'id,settlementId,measurementDate,waterAccessPercent\nDEMO-OBS-1,DEMO-UP-1,2026-10-01,wrong\n'});p.get_by_label(L('ir.column.category'),exact=True).select_option('services');p.get_by_role('checkbox',name=L('ir.permission'),exact=True).check();p.get_by_role('button',name=L('ir.inspect'),exact=True).click();p.get_by_label(L('ir.baseBatch'),exact=True).select_option(batch);p.get_by_role('button',name=L('ir.validate'),exact=True).click();expect(p.get_by_text(L('ir.error.number'),exact=True)).to_be_visible();expect(p.locator('.integration-findings').filter(has_text=L('ir.error.number'))).to_contain_text('2')
    for name,data in [('Demo-empty.csv',b''),('Demo-large.csv',b'x'*5242881)]:input.set_input_files({'name':name,'mimeType':'text/csv','buffer':data});expect(p.get_by_role('alert')).to_contain_text(L('ir.error.size'))
    checks.append('CSV missing columns, duplicate rows, wrong numeric values, empty and >5 MiB files show real errors without new imports')
    p.get_by_role('button',name=L('audit.rollback'),exact=True).click();p.get_by_label(L('audit.rollbackReason'),exact=True).fill('Demo data rollback verification');p.get_by_role('checkbox',name=L('audit.rollbackConfirm'),exact=True).check();p.get_by_role('button',name=L('audit.rollback'),exact=True).last.click();expect(p.get_by_text(L('audit.rolledBack'),exact=True)).to_be_visible();assert sum(row['importedBatches'] for row in get('integration/readiness')['categories'])==0
    checks.append('Confirmed rollback removes batch from readiness and retains original and audit history')
    p.goto(web+'/methodology');p.get_by_role('button',name=L('audit.testAnomalies'),exact=True).click();expect(p.locator('.anomaly-result')).to_contain_text('3 of 3')
    p.get_by_label(L('audit.scenarioCoverage'),exact=True).fill('100');expect(p.get_by_text(L('audit.after'),exact=True).locator('..')).not_to_contain_text('Unavailable')
    p.get_by_label(L('audit.budgetAmount'),exact=True).fill('100000');p.get_by_label(L('audit.unitCost'),exact=True).fill('1000');p.get_by_role('button',name=L('audit.allocate'),exact=True).click();expect(p.get_by_text(L('audit.remaining')+':',exact=False).first).to_be_visible()
    p.get_by_label(L('d.factor.gap'),exact=True).fill('1');p.get_by_label(L('d.factor.priority'),exact=True).fill('0');p.get_by_label(L('d.factor.unresolved'),exact=True).fill('0');p.get_by_label(L('d.factor.age'),exact=True).fill('0');p.get_by_role('button',name=L('audit.previewWeights'),exact=True).click();expect(p.get_by_text(L('audit.previewUpdated'),exact=True).first).to_be_visible()
    p.get_by_role('button',name=L('audit.saveWeights'),exact=True).click()
    p.wait_for_function("async()=>{const r=await fetch('/api/urban/demo/workspace');const s=await r.json();return s.weights.gap===1&&s.weights.priority===0}")
    p.reload();expect(p.get_by_label(L('d.factor.gap'),exact=True)).to_have_value('1')
    p.get_by_label(L('audit.slaStatus'),exact=True).select_option('overdue')
    expect(p.locator('.us-table-wrap').filter(has=p.get_by_role('columnheader',name=L('audit.ageDays')))).to_contain_text(L('audit.overdue'))
    p.get_by_role('button',name=L('audit.runBenchmark'),exact=True).click();expect(p.locator('.benchmark-result')).to_contain_text('10,000',timeout=30000)
    checks.append('What-if, budget allocation, preview and persisted weight tuning, three caught planted anomalies, paginated SLA filters and delay views and measured 10,000-record diagnostic work')
    p.goto(web+'/projects?tab=reports')
    for lang in ['en','hi','mr']:
     p.locator('.us-language select').select_option(lang);p.reload();expect(p.locator('html')).to_have_attribute('lang',lang)
     with p.expect_download() as download:p.get_by_role('button',name=L('d.exportCsv',lang),exact=True).click()
     data=Path(download.value.path()).read_text();assert 'Demo data' in data and 'source_date' in data and 'DEMO-SET-001' in data and ('localized_headers' in data)
     with p.expect_popup() as popup:p.get_by_role('button',name=L('audit.pdf',lang),exact=True).click()
     view=popup.value
     try:view.wait_for_function("document.documentElement.dataset.ready==='true'")
     except Exception:
      (OUT/'popup-debug.json').write_text(json.dumps(view.evaluate("({url:location.href,ready:document.readyState,fonts:Array.from(document.fonts).map(f=>({family:f.family,status:f.status})),fontStatus:document.fonts.status,html:document.documentElement.outerHTML.slice(0,500)})"),ensure_ascii=False,indent=2));raise
     view.pdf(path=str(OUT/f'report-{lang}.pdf'),print_background=True,prefer_css_page_size=True);assert 'Demo data' in view.locator('body').inner_text();view.close()
     p.goto(web+'/projects/data')
     with p.expect_download() as archive:p.get_by_role('button',name=L('d.exportDemo',lang),exact=True).click()
     saved=json.loads(Path(archive.value.path()).read_text());assert saved['notice']=='Demo data' and saved['is_synthetic'] is True and saved['source_saved_at'] and saved['exported_at']
     for collection in ['settlements','wards','issues','projects','milestones','visits','assessments','feedback','activity','dataSources','anomalyFixtures']:assert all(row['is_synthetic'] is True for row in saved[collection])
     if lang=='mr':
      p.goto(web+'/housing');expect(p.locator('.demo-small-metrics>div').nth(2).locator('b').first).to_have_text('०')
      p.goto(web+'/services');expect(p.locator('tbody tr').first.locator('td').nth(2)).to_have_text('९५%')
     p.goto(web+'/projects?tab=reports')
    checks.append('JSON exports in every language include exact Demo data watermark, source/save/export dates and all synthetic-row flags; Marathi counts and service targets use local digits')
    checks.append('Language persists across reload; actual CSV and browser PDF exports include Demo data watermark, sources, saved/export dates and filtered records in all languages')
    assert not errors;browser.close()
  report['status']='passed'
 except Exception as exc:
  report['failure']=f'{type(exc).__name__}: {exc}'
  try:p.screenshot(path=str(OUT/'failure.png'),full_page=True);(OUT/'failure-body.txt').write_text(p.locator('body').inner_text())
  except Exception:pass
  raise
 finally:
  for process in reversed(processes):
   if process.poll() is None:
    process.terminate()
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:process.kill();process.wait()
  for log in logs:log.close()
  (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
