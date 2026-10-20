"""Map publicly displayed author specimen records into a fatigue schema.
No model fitting. Preserve all rows and exclusion reasons in audit files.
"""
from pathlib import Path
import json,re,csv,math,collections,hashlib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'data/external_v2/trombley2025';L=ROOT/'literature/fresh_campaign_v2'
records=json.loads((D/'specimen_attributes.json').read_text())
rows=[];exclusions=[]
def singleton(r,k):
 v=r['attributes'].get(k,[])
 if len(v)!=1:raise ValueError((r['entity_id'],k,v))
 return v[0]
def number(r,k):
 v=singleton(r,k);m=re.fullmatch(r'([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)\s*(?:MPa|mm|W|um|mm/s|kHz)?',v)
 if not m:raise ValueError((r['entity_id'],k,v))
 return float(m.group(1))
for r in records:
 a=r['attributes'];name=r['specimen_name']
 if 'Number of Cycles' not in a or 'Max Stress' not in a:
  exclusions.append({'entity_id':r['entity_id'],'specimen_name':name,'reason':'Missing Number of Cycles or Max Stress in public metadata; no imputation. Two hr/ar names are residual-stress-only; au name is incompletely recorded fatigue specimen.'});continue
 R=number(r,'R Ratio');stress=number(r,'Max Stress');N=number(r,'Number of Cycles');status=singleton(r,'Runout or Failure?')
 if status not in ['Failure','Runout']:raise ValueError(status)
 diameter=number(r,'Gauge Size');condition=singleton(r,'Condition');event=int(status=='Failure')
 rows.append({'row_id':'mc2564_e'+r['entity_id'],'specimen_id':name,'repository_entity_id':r['entity_id'],'source_id':'10.1038/s41598-025-97031-1','source_dataset_doi':'10.13011/m3-c93d-z035','condition_id':f'trombley2025_d{diameter:g}_{condition.split(" - ")[0]}','nominal_diameter_mm':diameter,'condition_author':condition,'source_url':r['source_url'],'cycles_observed':N,'stress_max_MPa':stress,'stress_amplitude':stress*(1-R)/2,'load_ratio':R,'event':event,'runout':1-event,'test_date_author':singleton(r,'Test Date'),'material':'316L','am_type':'L-PBF','test_type':'uniaxial ultrasonic','temperature_C':25,'temperature_provenance':'article room-temperature, numerical25C is conventional label not logged per specimen','frequency_hz':20000,'direction':90,'power':number(r,'Laser Power Used'),'scan_speed':number(r,'Velocity'),'layer_thickness':number(r,'Layer Thickness'),'surface':'as-built' if condition=='a - As-Built' else condition,'thermal':'NHT' if condition=='a - As-Built' else ('HT' if condition.startswith('h -') else 'NHT'),'measurement_provenance':'author-provided specimen metadata from public repository labeled fields; no plot digitization','failure_definition':'200Hz resonance frequency reduction; visible crack, not necessarily full fracture','batch_id':'unknown;4builds in article; name prefixes not certified as buildIDs','license':'repository dataset license unspecified; public access does not establish redistribution permission','log_life':math.log10(N),'log_stress':math.log10(stress*(1-R)/2)})
x=pd.DataFrame(rows);x.to_csv(D/'fatigue_all_conditions.csv',index=False)
primary=x[x.condition_author=='a - As-Built'].copy();primary.to_csv(D/'fatigue_asbuilt_available129.csv',index=False)
pd.DataFrame(exclusions).to_csv(D/'exclusions.csv',index=False)
# Source overlap: exact metadata (titles/authors) and conservative curve-coordinate screen.
hist=pd.read_csv(ROOT/'data/processed/ss316l_lpbf_all.csv')
raw=json.loads((ROOT/'data/raw/FatigueData-AM2022.json').read_text())['fatiguedata_am2022']['articles']
md=[]
for i,a in enumerate(raw):
 m=a['metadata'];authors=m.get('author',[])
 if any(re.search(r'trombley|birnbaum|allison,\s*john',au,re.I) for au in authors):md.append({'article_index':i,'metadata':m})
matchsettings=hist[(hist.power==370)&(hist.scan_speed==900)&(hist.layer_thickness==25)]
curve=[]
for cid,ext in primary.groupby('condition_id'):
 for hid,old in hist.groupby('dataset_id'):
  if not np.allclose(old.load_ratio.fillna(999),-1):continue
  candidates=[]
  for i,(_,a) in enumerate(ext.iterrows()):
   for j,(_,b) in enumerate(old.iterrows()):
    dn=abs(math.log(a.cycles_observed/b.cycles_observed));ds=abs(math.log(a.stress_amplitude/b.stress_amplitude))
    if a.runout==b.runout and dn<=math.log(1.02) and ds<=math.log(1.01):candidates.append((dn/math.log(1.02)+ds/math.log(1.01),i,j))
  useda=set();usedb=set()
  for score,i,j in sorted(candidates):
   if i not in useda and j not in usedb:useda.add(i);usedb.add(j)
  if useda:curve.append({'external_condition':cid,'historical_dataset':hid,'historical_source':old.source_id.iloc[0],'matched_unique_points':len(useda),'fraction_of_smaller':len(useda)/min(len(ext),len(old)),'n_external':len(ext),'n_historical':len(old),'same_stressratio':True,'note':'R/runout match and2%cycle/1%stress tolerance; coincidence not physicalidentity'})
pd.DataFrame(curve).to_csv(L/'historical_coordinate_screen.csv',index=False)
summary={'repository_entities':len(records),'fatigue_records':len(x),'asbuilt_records':len(primary),'nonfatigue_excluded':exclusions,'asbuilt_condition_counts':primary.groupby('condition_id').size().to_dict(),'all_condition_counts':x.groupby('condition_id').size().to_dict(),'asbuilt_failure_runout_counts':primary.groupby(['condition_id','event']).size().rename('n').reset_index().to_dict('records'),'asbuilt_minimum_stress':float(primary.stress_amplitude.min()),'asbuilt_maximum_stress':float(primary.stress_amplitude.max()),'duplicate_specimen_ids':int(x.specimen_id.duplicated().sum()),'duplicate_entity_ids':int(x.repository_entity_id.duplicated().sum()),'duplicate_exact_fatigue_coordinates_within_condition':int(primary.duplicated(['condition_id','stress_amplitude','cycles_observed','runout']).sum()),'exact_coordinate_duplicates_caveat':'distinct named specimens may legitimately share rounded endpoints; do not deduplicate automatically','dates':sorted(primary.test_date_author.unique()),'historical_shared_author_metadata':md,'historical_shared370W_900mms_25um_rows':len(matchsettings),'historical_coordinate_pairs_screened':len(curve),'historical_strong_candidate_reuse':[r for r in curve if r['matched_unique_points']>=5 and r['fraction_of_smaller']>=.85],'independence':'One external authorcampaign with3relatedasbuiltconditions,4reportedbuilds; dates as displayed inqualityreport; not2025new physicaltesting; physicalindependence beyondrecorded source notcertified','test_endpoint':'visiblecrack via200Hz frequencydrop,notfullfracture','license':'repository no license specified; articleCCBY4.0 separate; localanalysis only,exclude rawmetadata/HTML frompublicarchive pendinglicense'}
(L/'trombley_quality_and_provenance.json').write_text(json.dumps(summary,indent=2))
manifest=json.loads((D/'manifest.json').read_text());manifest['files']=[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in sorted(D.iterdir()) if p.is_file() and p.name!='manifest.json'];(D/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k not in ['dates']},indent=2))
