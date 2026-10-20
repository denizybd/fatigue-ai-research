"""Retrieve publicly visible Materials Commons specimen pages; no login/download bypass.
Retain raw HTML and hashes. Extract labeled values, not plots. Dataset license unspecified.
This script performs no fits or prediction outcome analysis.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib, json, re, html, csv
import requests
ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'data/external_v2/trombley2025'
DEST.mkdir(parents=True,exist_ok=True)
BASE='https://materialscommons.org/public/datasets/2564'

def clean(s):
 return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',s))).strip()

def get(url,path):
 if not path.exists():
  r=requests.get(url,timeout=40);r.raise_for_status();path.write_bytes(r.content)
 return path.read_text()
index=get(BASE+'/entities',DEST/'entities_index.html')
links=re.findall(r'<a href="('+re.escape(BASE)+r'/entities/(\d+))">\s*(.*?)\s*</a>',index,re.S)
# repeated navigation is excluded by exact absolute entity links.
links=list({id:(url,id,clean(name)) for url,id,name in links}.values())

def fetch(t):
 url,id,name=t
 p=DEST/f'entity_{id}.html'
 s=get(url,p)
 # Each attribute-row contains a col-7 label, followed by a col-4 value.
 attrs={}
 for key,val in re.findall(r'<div class="attribute-row[^>]*>\s*<div class="col-7">(.*?)</div>\s*<div class="col-4">(.*?)</div>',s,re.S):
  key=clean(key).rstrip(':');val=clean(val)
  attrs.setdefault(key,[])
  if val not in attrs[key]:attrs[key].append(val)
 return {'entity_id':id,'specimen_name':name,'source_url':url,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'attributes':attrs}
with ThreadPoolExecutor(max_workers=4) as ex:
 records=list(ex.map(fetch,links))
records.sort(key=lambda r:int(r['entity_id']))
(DEST/'specimen_attributes.json').write_text(json.dumps(records,indent=2))
keys=['Gauge Size','Geometry','Source Lab','Machine','Source Powder','Build Orientation','Laser Power Used','Layer Thickness','Velocity','Laser Spot Size','Test Date','R Ratio','Max Stress','Sample Geometry','Condition','Number of Cycles','Runout or Failure?','Tests','Temperature','Heat Treatment','Build']
with (DEST/'specimen_attributes.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['entity_id','specimen_name','source_url']+keys);w.writeheader()
 for r in records:w.writerow({**{k:r[k] for k in ['entity_id','specimen_name','source_url']},**{k:' || '.join(r['attributes'].get(k,[])) for k in keys}})
manifest={'article_doi':'10.1038/s41598-025-97031-1','dataset_doi':'10.13011/m3-c93d-z035','dataset_title':'Dataset 1 - Concept Laser Samples','source_url':BASE,'accessed_utc':datetime.now(timezone.utc).isoformat(),'license':'No license specified on dataset landing; article CC BY4.0 does not automatically license repository records. Raw repository HTML retained locally; do not bundle/relicense in public deliverables.','retrieval':'Public GET entity pages; no authentication or archive download used.','specimen_entities':len(records),'files':[]}
for p in sorted(DEST.iterdir()):
 if p.is_file() and p.name!='manifest.json':manifest['files'].append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size})
(DEST/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'entities':len(records),'attribute_names':sorted(set().union(*(r['attributes'] for r in records))),'multiple_value_keys':[(r['entity_id'],k) for r in records for k,v in r['attributes'].items() if len(v)>1 and k not in ['From']]},indent=2))
