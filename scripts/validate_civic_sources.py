"""Read-only integrity check for local civic sources; never downloads or imports.

Use --geometry/--metadata to validate a configured static historical layer.
The output records the time this command actually inspected the files.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from stage_historical_boundaries import ROOT, inspect
from ingest_sra_register import parse_register_xml


def validate(geometry: Path, metadata: Path, processed: Path):
    raw = geometry.read_bytes()
    parsed = json.loads(raw)
    manifest = json.loads(metadata.read_text())
    quality = inspect(raw)
    types = Counter((feature.get('geometry') or {}).get('type') for feature in parsed['features'])
    rings = [ring for feature in parsed['features'] if (feature.get('geometry') or {}).get('type') == 'Polygon' for ring in feature['geometry'].get('coordinates', [])]
    quality.update(geometry_types=dict(types), missing_geometry_count=sum(not feature.get('geometry') for feature in parsed['features']),
                   missing_properties_count=sum(not isinstance(feature.get('properties'),dict) for feature in parsed['features']),
                   unclosed_ring_count=sum(not ring or ring[0] != ring[-1] for ring in rings),sha256=hashlib.sha256(raw).hexdigest())
    if quality['sha256'] != manifest['sha256']:
        raise ValueError('GeoJSON checksum differs from its validation manifest')
    for key in ['source_feature_count','valid_feature_count','coordinate_count','polyno_non_null_count','bounds','excluded_features']:
        if quality[key] != manifest[key]:
            raise ValueError(f'Current source validation differs from recorded metadata: {key}')
    quality['expected_discrepancies'] = []
    expected = {'source_feature_count':2542,'coordinate_count':70404,'missing_geometry_count':0,'unclosed_ring_count':0}
    for key, value in expected.items():
        if quality[key] != value:
            quality['expected_discrepancies'].append({'field':key,'expected':value,'actual':quality[key]})
    quality['topology_note'] = 'Source contains topology-invalid polygons even though all rings are closed; these are excluded without repair.'
    result = {'validated_at':datetime.now(timezone.utc).isoformat(),'scope':'Local files, no network/download/import; not field verification','historical_boundaries':quality}
    kmls = sorted((ROOT/'data/raw/sra/boundaries-2015').glob('*.kml'))
    if kmls:
        kml = ET.fromstring(kmls[0].read_bytes()); ns={'k':'http://www.opengis.net/kml/2.2'}
        polyno=[item.text for item in kml.findall('.//k:SimpleData',ns) if item.attrib.get('name')=='polyno']
        result['original_kml']={'source_polyno_values':len(polyno),'unique_source_polyno_values':len(set(filter(None,polyno))),'identifier_scope':'Technical source references only; not SRA cluster IDs; not copied to GeoJSON','sha256':hashlib.sha256(kmls[0].read_bytes()).hexdigest(),'placemarks':len(kml.findall('.//k:Placemark',ns)),
                                'schema':[item.attrib for item in kml.findall('.//k:SimpleField',ns)]}
    registry = processed/'sra_cluster_register.json'
    if registry.exists():
        source=json.loads(registry.read_text()); meta=source['metadata']; pdf=ROOT/meta['path']
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != meta['sha256']:
            raise ValueError('Original SRA PDF checksum mismatch')
        xml=subprocess.run(['pdftotext','-bbox-layout',str(pdf),'-'],capture_output=True,text=True,check=True,timeout=60).stdout
        records, check=parse_register_xml(xml,meta['retrieved_at'])
        if records != source['records']:
            raise ValueError('Re-extracted PDF rows differ from the stored extraction')
        result['sra_register']={**check,'original_pdf_sha256':meta['sha256'],'extraction_reproduced':True,'manually_verified':False,'matched_to_2015':False}
    census = processed/'census_slum_pca_maharashtra.json'
    if census.exists():
        source=json.loads(census.read_text()); observations=json.loads((processed/'census_observations.json').read_text())
        result['census']={'reference_year':source['reference_year'],'pca_rows':len(source['records']),'source_columns':source['columns'],
                          'geographic_units':len(observations['geographic_units']),'observations':len(observations['indicators']),
                          'granularity':'Original state and town geographies','linked_to_polygons':False}
    projects = processed/'sra_projects.json'
    if projects.exists():
        source=json.loads(projects.read_text()); result['published_project_listings']={'rows':len(source['records']),'status_counts':dict(Counter(row.get('project_status','unknown') for row in source['records'])),
                     'scope':'Published source listings, not verified current redevelopment progress'}
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry',type=Path,default=ROOT/'nagarseva/website/public/data/mumbai_slum_clusters_2015.geojson')
    parser.add_argument('--metadata',type=Path,default=ROOT/'nagarseva/website/public/data/mumbai_slum_clusters_2015.metadata.json')
    parser.add_argument('--processed',type=Path,default=ROOT/'data/processed')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=validate(args.geometry,args.metadata,args.processed)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key: ({k:v for k,v in value.items() if k not in ['excluded_features','source_columns','ward_counts']} if isinstance(value,dict) else value) for key,value in result.items()},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
