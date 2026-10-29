"""All current routes, 3 languages and 3 widths, using a disposable SQLite workspace.
Saves screenshots and axe findings. No user workspace mutations or fabricated records.
"""
from datetime import datetime,timezone
from pathlib import Path
import json,os,re,secrets,subprocess,sys,tempfile,time,urllib.request
from playwright.sync_api import sync_playwright,expect
from check_synthetic_integration_browser import port,ready
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.runtime/end-to-end-audit/browser'
PAGES=[('dashboard','/dashboard'),('settlements','/settlements'),('issue','/report-issue'),('projects','/projects'),('reports','/projects?tab=reports'),('visits','/visits'),('housing','/housing'),('services','/services'),('community','/projects?tab=community'),('management','/projects/data'),('methodology','/methodology'),('comparison','/projects/scenarios'),('priorities','/projects/priorities'),('assurance','/projects/assurance'),('integration','/data-integration'),('onboarding','/data-integration'),('governance','/data-integration'),('settlement-detail','/settlements?settlement=DEMO-SET-001'),('issue-management','/report-issue?status=unresolved'),('issue-detail','/report-issue?issue=DEMO-ISS-001'),('project-detail','/projects?project=DEMO-PROJ-001'),('visit-scheduling','/visits?new=1&settlement=DEMO-SET-001'),('visit-detail','/visits?visit=DEMO-VISIT-001')]

def main():
 OUT.mkdir(parents=True,exist_ok=True);processes=[];logs=[];records=[];errors=[]
 result={'status':'failed','checkedAt':datetime.now(timezone.utc).isoformat(),'pages':records,'browserErrors':errors,'scope':'Production Chromium, temporary SQLite, WCAG automated checks plus manual screenshot review; not native-speaker certification'}
 try:
  with tempfile.TemporaryDirectory(prefix='urban-full-audit-') as folder:
   folder=Path(folder);api=f'http://127.0.0.1:{port()}';web=f'http://127.0.0.1:{port()}';key=secrets.token_urlsafe(32)
   env={**os.environ,'URBANSAARTHI_DB_PATH':str(folder/'audit.sqlite3'),'URBANSAARTHI_DATA_DIR':str(folder/'no-real-source'),'NAGARSEVA_OFFICER_KEY':key,'NAGARSEVA_API_TARGET':api}
   for name,command,cwd in [('api',[sys.executable,'-m','uvicorn','model.api.urban:app','--host','127.0.0.1','--port',api.rsplit(':',1)[1]],ROOT/'nagarseva'),('web',['npm','run','preview','--','--port',web.rsplit(':',1)[1],'--strictPort'],ROOT/'nagarseva/website')]:
    log=(OUT/f'{name}.log').open('w');logs.append(log);processes.append(subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT))
   ready(api+'/urban/demo/health',processes[0]);ready(web,processes[1])
   axe=(ROOT/'nagarseva/website/node_modules/axe-core/axe.min.js').read_text()
   with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH','/usr/bin/chromium'))
    context=browser.new_context();context.route('https://tile.openstreetmap.org/**',lambda route:route.abort());page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    for lang in ['en','hi','mr']:
     page.goto(web+'/dashboard');page.locator('.us-language select').select_option(lang);page.reload();expect(page.locator('html')).to_have_attribute('lang',lang)
     for width in [375,768,1280]:
      page.set_viewport_size({'width':width,'height':900})
      for name,path in PAGES:
       page.goto(web+path);expect(page.locator('.demo-mode')).to_be_visible();expect(page.locator('main h1')).to_be_visible();expect(page.locator('main .us-panel').first).to_be_visible()
       if name in ['dashboard','settlements']:expect(page.locator('.leaflet-container')).to_be_visible()
       if name in ['onboarding','governance']:page.locator('.integration-tabs [role=tab]').nth(1 if name=='onboarding' else 2).click()
       
       if name in ['issue-detail','project-detail','visit-scheduling','visit-detail']:expect(page.get_by_role('dialog')).to_be_visible()
       page.evaluate('document.fonts.ready');fonts=page.evaluate("document.fonts.check('16px \"Urban Devanagari\"','मराठी हिंदी')")
       text=page.locator('body').inner_text();missing=re.findall(r'\b(?:audit|d|ir)\.[A-Za-z][A-Za-z0-9_.]*',text)
       overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
       page.add_script_tag(content=axe)
       violations=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))}")
       shot=f'{lang}-{width}-{name}.png';page.screenshot(path=str(OUT/shot),full_page=True)
       records.append({'page':name,'path':path,'language':lang,'width':width,'screenshot':shot,'overflow':overflow,'missingKeys':missing,'fontReady':fonts,'violations':violations})
       (OUT/'progress.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    # Keyboard focus must remain within the mobile navigation until closed.
    page.goto(web+'/dashboard');page.set_viewport_size({'width':375,'height':900});page.locator('.us-mobile-nav').click()
    expect(page.locator('#civic-navigation')).to_have_attribute('role','dialog')
    for _ in range(14):
     page.keyboard.press('Tab');assert page.evaluate("document.getElementById('civic-navigation').contains(document.activeElement)")
    page.keyboard.press('Escape');expect(page.locator('.us-mobile-nav')).to_be_focused()
    result['keyboardNavigation']='passed';browser.close()
   result['status']='passed' if not errors and all(not row['overflow'] and not row['missingKeys'] and (row['language']=='en' or row['fontReady']) and not row['violations'] for row in records) else 'failed'
 finally:
  for process in reversed(processes):
   if process.poll() is None:
    process.terminate()
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:process.kill();process.wait()
  for log in logs:log.close()
  (OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
  print(json.dumps({'status':result['status'],'pages':len(records),'failures':sum(bool(row['violations'] or row['overflow'] or row['missingKeys']) for row in records),'browserErrors':errors},indent=2))
 if result['status']!='passed':raise AssertionError('Browser audit failed; inspect result.json for actual violations')
if __name__=='__main__':main()
