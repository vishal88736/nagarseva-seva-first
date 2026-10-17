"""Bounded, public-source acquisition and an actual npm advisory snapshot."""
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request
import zipfile
import io

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'research/acquired'
OUT.mkdir(parents=True, exist_ok=True)
NOW = datetime.now(timezone.utc).isoformat()
UA = 'UrbanSaarthiResearch/1.0 (+https://github.com/vishal88736/nagarseva-seva-first)'

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

def get(url, limit=8_000_000):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=45) as response:
        raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('Source exceeds the acquisition size cap')
        return raw

audit = subprocess.run(['npm', 'audit', '--json', '--package-lock-only', '--ignore-scripts'], cwd=ROOT/'nagarseva/website', capture_output=True, text=True)
try:
    report = json.loads(audit.stdout)
except ValueError:
    report = {'error': audit.stderr[-2000:]}
if not (ROOT/'integration/security-audit-before.json').exists():
    write(ROOT/'integration/security-audit-before.json', {'checked_at': NOW, 'exit_code': audit.returncode, 'report': report})
print('NPM_AUDIT', json.dumps(report, separators=(',', ':')))
for package in ['vite@6.4', '@vitejs/plugin-react@4', 'postcss@8', 'tailwindcss@3', 'recharts@2']:
    result = subprocess.run(['npm', 'view', package, 'version', '--json'], capture_output=True, text=True)
    print('NPM_VERSION', package, result.stdout.strip(), result.stderr.strip())

query = '[out:json][timeout:25][maxsize:16777216];(way[highway](19.047,72.912,19.063,72.930);nwr[amenity~"^(school|hospital|clinic|toilets|drinking_water)$"](19.047,72.912,19.063,72.930);node[highway=bus_stop](19.047,72.912,19.063,72.930););out body geom;'
endpoint = 'https://overpass.private.coffee/api/interpreter'
url = endpoint + '?' + urllib.parse.urlencode({'data': query})
metadata = {'accessed_at': NOW, 'endpoint': endpoint, 'query': query, 'bbox_wsen': [72.912,19.047,72.930,19.063], 'publisher': 'OpenStreetMap contributors via Overpass API', 'licence': 'ODbL 1.0', 'licence_url': 'https://www.openstreetmap.org/copyright', 'attribution': '© OpenStreetMap contributors', 'purpose': 'Small candidate Mumbai context extract. No settlement identification or household-service inference.', 'field_validation': False}
try:
    raw = get(url)
    source = json.loads(raw)
    if source.get('remark'):
        raise ValueError('Incomplete Overpass response: ' + source['remark'])
    features = []
    allowed = {'name','highway','amenity','foot','access','surface','sidewalk','wheelchair','opening_hours','public_transport'}
    for element in source['elements']:
        tags = {k:v for k,v in element.get('tags', {}).items() if k in allowed}
        geometry = None
        if element['type'] == 'node':
            geometry = {'type':'Point','coordinates':[element['lon'],element['lat']]}
        elif element['type'] == 'way' and element.get('geometry'):
            points = [[p['lon'],p['lat']] for p in element['geometry'] if 'lon' in p and 'lat' in p]
            if len(points) >= 2:
                geometry = {'type':'LineString','coordinates':points}
        # Relation geometries are deliberately withheld until a topology-aware importer exists.
        if geometry:
            features.append({'type':'Feature','id':f"{element['type']}/{element['id']}", 'properties':{**tags,'source':'OpenStreetMap','status':'mapped; not field verified'}, 'geometry':geometry})
    metadata.update(status='acquired', response_sha256=hashlib.sha256(raw).hexdigest(), response_bytes=len(raw), osm_base_timestamp=source.get('osm3s',{}).get('timestamp_osm_base'), source_elements=len(source['elements']), exported_features=len(features), omitted_elements=len(source['elements'])-len(features), geometry_counts=dict(Counter(f['geometry']['type'] for f in features)), limitations=['May be incomplete or outdated. Map presence is not legal/public access or functional service.', 'No settlement boundaries, water reliability, household counts, risk labels or project completion observations.', 'Way geometries can extend beyond the selection box. Amenity polygons are retained as outlines, not snapped entrances.', 'Relations are omitted. No real routing or settlement ranking is calculated from this extract.'])
    write(OUT/'mumbai-context.geojson', {'type':'FeatureCollection','metadata':metadata,'features':features})
except Exception as exc:
    metadata.update(status='failed',error=f'{type(exc).__name__}: {exc}')
history_path = OUT/'mumbai-context-attempts.json'
history = json.loads(history_path.read_text()) if history_path.exists() else []
previous = OUT/'mumbai-context-access.json'
if previous.exists() and not history: history.append(json.loads(previous.read_text()))
history.append(metadata)
write(history_path, history)
write(OUT/'mumbai-context-access.json', metadata)
print('PUBLIC_CONTEXT',json.dumps(metadata))

template_url = 'https://sevainnovationchallenge.in/assets/Seva-First-Innovation-Challenge-PPT-Template.pptx'
receipt = {'source_url':template_url,'accessed_at':NOW,'purpose':'Official submission template, unchanged acquisition'}
try:
    raw = get(template_url)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        assert '[Content_Types].xml' in z.namelist()
    digest = hashlib.sha256(raw).hexdigest()
    receipt.update(status='acquired',bytes=len(raw),sha256=digest)
    print('OFFICIAL_TEMPLATE_BEGIN',digest,len(raw),flush=True)
    encoded=base64.b64encode(raw).decode()
    for start in range(0,len(encoded),8192):
        print('OFFICIAL_TEMPLATE_PART',encoded[start:start+8192],flush=True)
    print('OFFICIAL_TEMPLATE_END',digest,flush=True)
except Exception as exc:
    receipt.update(status='failed',error=f'{type(exc).__name__}: {exc}')
write(OUT/'official-template-access.json',receipt)
print('OFFICIAL_TEMPLATE_RECEIPT',json.dumps(receipt))
