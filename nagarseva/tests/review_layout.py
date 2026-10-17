"""Read-only layout audit against a running local demo; no records are written."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from weather_fixture import weather_fixture

PAGES = ['home', 'dashboard', 'pocket', 'simulator', 'optimizer', 'assurance', 'resident', 'admin', 'methodology', 'pilot', 'sources']
STATES = [(screen, 'default') for screen in PAGES] + [('resident', 'eligibility'), ('resident', 'status'), ('pilot', 'evaluation'), ('pilot', 'setup'), ('simulator', 'expanded'), ('admin', 'access'), ('methodology', 'dark'), ('simulator', 'dark'), ('sources', 'dark'), ('sources', 'stale'), ('sources', 'unavailable')]
AUDIT = r"""() => {
  const texts = [], overflow = [], walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const rect = r => ({left:r.left, right:r.right, top:r.top, bottom:r.bottom});
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const element = node.parentElement, text = node.textContent.trim();
    if (!text || !element || element.closest('script,style,option,svg defs,[aria-hidden="true"]')) continue;
    const closed = element.closest('details:not([open])');
    if (closed && !closed.querySelector(':scope > summary')?.contains(element)) continue;
    const style = getComputedStyle(element);
    if (style.visibility !== 'visible' || style.display === 'none' || !element.getClientRects().length) continue;
    const range = document.createRange(); range.selectNodeContents(node);
    for (const original of range.getClientRects()) {
      let r = rect(original);
      for (let ancestor=element; ancestor; ancestor=ancestor.parentElement) {
        const css = getComputedStyle(ancestor), bounds=ancestor.getBoundingClientRect();
        if (/hidden|clip|auto|scroll/.test(css.overflowX)) {r.left=Math.max(r.left,bounds.left);r.right=Math.min(r.right,bounds.right)}
        if (/hidden|clip|auto|scroll/.test(css.overflowY)) {r.top=Math.max(r.top,bounds.top);r.bottom=Math.min(r.bottom,bounds.bottom)}
      }
      if (r.right-r.left > 1 && r.bottom-r.top > 1) texts.push({r,text:text.slice(0,100),element,selector:element.tagName.toLowerCase()+'.'+String(element.className?.baseVal ?? element.className).replaceAll(' ','.')});
    }
  }
  const collisions=[];
  for(let i=0;i<texts.length;i++) for(let j=i+1;j<texts.length;j++) {
    const a=texts[i],b=texts[j];
    if(a.element===b.element || a.element.contains(b.element) || b.element.contains(a.element)) continue;
    if(a.element.closest('.leaflet-marker-pane') && b.element.closest('.leaflet-marker-pane')) continue;
    const width=Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left), height=Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top);
    if(width > 3 && height > 3) collisions.push({a:a.text,b:b.text,selectors:[a.selector,b.selector],overlap:[Math.round(width),Math.round(height)]});
  }
  for(const element of document.querySelectorAll('h1,h2,h3,.metric,.rank-item,.classification,.tornado-row,.service-card-title,.panel-heading,.section-heading,.topbar,.role-entry,.record-facts')) {
    const bounds=element.getBoundingClientRect();
    if(bounds.right>innerWidth+1 && !element.closest('.table-scroll,.leaflet-pane')) overflow.push({selector:element.className,text:element.textContent.slice(0,100),right:Math.round(bounds.right)});
  }
  return {width:innerWidth,documentWidth:document.documentElement.scrollWidth,collisions,overflow};
}"""


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:5173')
    parser.add_argument('--matrix',action='store_true')
    parser.add_argument('--assert-clean',action='store_true')
    args=parser.parse_args()
    output=Path('/tmp/nagarseva-layout-review');output.mkdir(exist_ok=True)
    cases=[(1366,'en'),(1024,'en'),(390,'hi')]
    if args.matrix: cases=[(width,language) for width in [320,390,768,1024,1366] for language in ['en','hi','mr']]
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for width,language in cases:
            context=browser.new_context(viewport={'width':width,'height':900})
            # Never generate automated map-tile traffic against the public OSM service.
            context.route('https://tile.openstreetmap.org/**',lambda route: route.abort())
            context.add_init_script("localStorage.setItem('nagarseva-language',"+json.dumps(language)+")")
            page=context.new_page()
            errors=[];page.on('pageerror',lambda error: errors.append(str(error)))
            for screen,state in STATES:
                page.unroute('**/api/context/*/weather')
                page.route('**/api/context/*/weather',lambda route, request: route.fulfill(json=weather_fixture(state if state in ['stale','unavailable'] else 'cached')))
                page.goto(args.url+f'/#{screen}/NS-0001')
                page.wait_for_selector('.page-pad')
                page.locator('.lang-select select').select_option(language)
                if screen == 'resident' and state != 'default': page.locator('.resident-tabs button').nth(2 if state == 'eligibility' else 1).click()
                if screen == 'pilot' and state != 'default': page.locator('.resident-tabs button').nth(1 if state == 'evaluation' else 2).click()
                if state == 'expanded': page.locator('.household-card details').evaluate_all('(elements)=>elements.forEach(e=>e.open=true)')
                if state == 'access': page.locator('.officer-access').evaluate('(element)=>element.open=true')
                if state == 'dark': page.locator('.theme-button').click()
                page.evaluate('window.scrollTo(0,0)')
                page.evaluate('document.fonts.ready')
                page.wait_for_timeout(250)
                if screen == 'sources':
                    if state == 'unavailable': page.wait_for_function("document.querySelector('.forecast-panel .note')?.textContent.length > 10")
                    else: page.wait_for_selector('.forecast-day')
                if screen == 'optimizer': page.wait_for_function("!document.querySelector('.empty-state[role=status]')",timeout=30000)
                result=page.evaluate(AUDIT)
                result.update(screen=screen,language=language,state=state)
                if result['collisions'] or result['overflow'] or result['documentWidth']>width+1:
                    page.screenshot(path=str(output/f'{screen}-{state}-{width}-{language}.png'),full_page=True)
                    print(json.dumps(result,ensure_ascii=False),flush=True)
                results.append(result)
            if errors: raise AssertionError(errors)
            context.close()
        browser.close()
    (output/'report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    failures=[r for r in results if r['collisions'] or r['overflow'] or r['documentWidth']>r['width']+1]
    print(json.dumps({'cases':len(results),'flagged_cases':len(failures),'report':str(output/'report.json')}))
    if args.assert_clean and failures: raise SystemExit(1)


if __name__=='__main__':main()
