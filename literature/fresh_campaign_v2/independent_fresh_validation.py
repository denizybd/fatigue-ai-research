"""Independent parser audit: HTMLParser DOM, decimal arithmetic, CSV joins.
Does not import acquisition or transformation modules. No model fitting.
"""
from pathlib import Path
from html.parser import HTMLParser
from decimal import Decimal
from datetime import datetime
from collections import defaultdict,Counter
import csv,json,hashlib
R=Path(__file__).resolve().parents[2];D=R/'data/external_v2/trombley2025';L=R/'literature/fresh_campaign_v2'
class Node:
 def __init__(self,tag='',attrs=(),parent=None):self.tag=tag;self.attrs=dict(attrs);self.children=[];self.parent=parent;self.parts=[]
 def text(self):return ' '.join(' '.join(self.parts).split())
class DOM(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.root=Node();self.cur=self.root;self.nodes=[]
 def handle_starttag(self,t,a):
  n=Node(t,a,self.cur);self.cur.children.append(n);self.nodes.append(n)
  if t not in ['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']:self.cur=n
 def handle_endtag(self,t):
  n=self.cur
  while n.parent and n.tag!=t:n=n.parent
  if n.parent:self.cur=n.parent
 def handle_data(self,s):
  n=self.cur
  while n:n.parts.append(s);n=n.parent

def parse(id):
 p=D/f'entity_{id}.html';h=DOM();h.feed(p.read_text());a=defaultdict(set)
 for n in h.nodes:
  if 'attribute-row' in n.attrs.get('class','').split():
   fields=[c.text() for c in n.children if c.tag=='div']
   assert len(fields)==2,(id,fields)
   a[fields[0].rstrip(':')].add(fields[1])
 names=[n.text().removeprefix('Sample: ').strip() for n in h.nodes if n.tag=='h3' and n.text().startswith('Sample:')]
 assert len(names)==1,(id,names)
 return names[0],a

def val(a,k):
 assert len(a[k])==1,(k,a[k]);return next(iter(a[k]))
def dec(a,k):return Decimal(val(a,k).split()[0])

def read(name):
 with (D/name).open() as f:return list(csv.DictReader(f))
allrows=read('fatigue_all_conditions.csv');asbuilt=read('fatigue_asbuilt_available129.csv');attrs=json.loads((D/'specimen_attributes.json').read_text())
byid={r['entity_id']:r for r in attrs};assert len(byid)==157
checks=[];failures=[]
for row in allrows:
 id=row['repository_entity_id'];name,a=parse(id)
 expected={'specimen_id':name,'event':str({'Failure':1,'Runout':0}[val(a,'Runout or Failure?')]),'runout':str({'Failure':0,'Runout':1}[val(a,'Runout or Failure?')]),'test_date_author':val(a,'Test Date'),'condition_author':val(a,'Condition')}
 for k,v in expected.items():assert row[k]==v,(id,k,row[k],v)
 numeric={'stress_max_MPa':dec(a,'Max Stress'),'cycles_observed':dec(a,'Number of Cycles'),'load_ratio':dec(a,'R Ratio'),'nominal_diameter_mm':dec(a,'Gauge Size'),'power':dec(a,'Laser Power Used'),'scan_speed':dec(a,'Velocity'),'layer_thickness':dec(a,'Layer Thickness')}
 numeric['stress_amplitude']=numeric['stress_max_MPa']*(Decimal(1)-numeric['load_ratio'])/Decimal(2)
 for k,v in numeric.items():assert Decimal(row[k])==v,(id,k,row[k],str(v))
 # Separately extracted original attribute JSON must match DOM sets for fatigue keys.
 for k in ['Max Stress','Number of Cycles','R Ratio','Runout or Failure?','Condition','Sample Geometry','Test Date']:
  assert set(byid[id]['attributes'][k])==a[k],(id,k)
 expectedcid=f'trombley2025_d{numeric["nominal_diameter_mm"]:g}_{expected["condition_author"].split(" - ")[0]}'
 # Decimal formatting preserves .0; normalize to numeric author representation.
 expectedcid=f'trombley2025_d{float(numeric["nominal_diameter_mm"]):g}_{expected["condition_author"].split(" - ")[0]}'
 assert row['condition_id']==expectedcid,(id,row['condition_id'],expectedcid)
 checks.append({'entity_id':id,'specimen_id':name,'numeric_fields_checked':len(numeric),'categorical_fields_checked':len(expected),'source_url':row['source_url'],'html_sha256':hashlib.sha256((D/f'entity_{id}.html').read_bytes()).hexdigest(),'status':'PASS'})
assert len(allrows)==154 and len(asbuilt)==129
allids={r['repository_entity_id'] for r in allrows};abids={r['repository_entity_id'] for r in asbuilt};assert len(allids)==154 and len(abids)==129
assert all(r['condition_author']=='a - As-Built' for r in asbuilt)
assert abids=={r['repository_entity_id'] for r in allrows if r['condition_author']=='a - As-Built'}
for row in asbuilt:assert row==next(r for r in allrows if r['repository_entity_id']==row['repository_entity_id'])
missing=[]
for id in sorted(set(byid)-allids):
 name,a=parse(id);assert not a['Max Stress'] or not a['Number of Cycles'];missing.append({'entity_id':id,'specimen_id':name,'missing_stress':not bool(a['Max Stress']),'missing_cycles':not bool(a['Number of Cycles'])})
assert {r['entity_id'] for r in missing}=={'67563','67624','67625'}
conditioncounts=Counter(r['condition_id'] for r in asbuilt);assert sorted(conditioncounts.values())==[40,44,45]
with (L/'independent_fresh_row_checks.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(checks[0]));w.writeheader();w.writerows(checks)
receipt={'status':'PASS','audit_implementation':'Independent HTMLParser DOM + Decimal numeric conversion; no import of regex acquisition/preparation functions','fatigue_records_checked':len(allrows),'asbuilt_records_checked':len(asbuilt),'numeric_comparisons':sum(r['numeric_fields_checked'] for r in checks),'categorical_comparisons':sum(r['categorical_fields_checked'] for r in checks),'source_attribute_json_crosschecks':154*7,'asbuilt_condition_counts':dict(conditioncounts),'missing_entities':missing,'asbuilt_test_date_range':[min(datetime.strptime(r['test_date_author'],'%m/%d/%Y') for r in asbuilt).date().isoformat(),max(datetime.strptime(r['test_date_author'],'%m/%d/%Y') for r in asbuilt).date().isoformat()],'distinct_specimen_names':len({r['specimen_id'] for r in allrows}),'limits':'Internal independent extraction arithmetic, not independent experiments or external scientific replication. Public author metadata can itself contain errors; no raw machine files accessed. Article advertises130 but only129 publiclycomplete asbuilt records.'}
(L/'independent_fresh_validation.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
