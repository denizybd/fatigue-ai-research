"""Independently recompute saved v2 summary and paired table arithmetic.
Pure scalar grouping for metrics; no import of root summary/evaluation code.
"""
from pathlib import Path
from collections import defaultdict
import json,csv,math,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'literature/fresh_campaign_v2'
FIELDS=['availability','risk_lower','risk_upper','mean_log_lower','mean_safe_gap','severe_risk_lower','severe_risk_upper','below1','below100','below10000','vacuous']
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def number(s):return float(s) if s else math.nan
def avg(xs):
 xs=[x for x in xs if not math.isnan(x)];return sum(xs)/len(xs) if xs else math.nan
def equal(a,b):return (math.isnan(a) and math.isnan(b)) or a==b or (math.isfinite(a) and math.isfinite(b) and abs(a-b)<2e-11)
def grouped_mean(data,keyfn,fields):
 groups=defaultdict(list)
 for key,row in data:groups[keyfn(key)].append(row)
 return [(key,{f:avg([r[f] for r in rows]) for f in fields}) for key,rows in sorted(groups.items())]
requested=set(sys.argv[1:])
prior=json.loads((OUT/'split_audit_result_tables.json').read_text()) if requested and (OUT/'split_audit_result_tables.json').exists() else {}
checks=[r for r in prior.get('checks',[]) if r['run'] not in requested]
selected=[r for r in prior.get('selected_panelA_raw_hierarchical_k3',[]) if r['run'] not in requested]
for folder in sorted((ROOT/'results/v2').iterdir()):
 if requested and folder.name not in requested:continue
 if not (folder/'summary.csv').exists() or not (folder/'predictions.csv').exists():continue
 rows=read(folder/'predictions.csv');g=defaultdict(list)
 for r in rows:
  key=(r['panel'],r['model'],int(r['k']),r['bound'],r['group_id'],int(r['seed']),r['dataset_id']);g[key].append(r)
 metrics=[]
 for key,rs in sorted(g.items()):
  available=[r for r in rs if not math.isnan(number(r['log_lower']))];n=len(available)
  if not n:m={f:math.nan for f in FIELDS};m['availability']=0.
  else:
   b=[number(r['log_lower']) for r in available];y=[number(r['log_life']) for r in available];event=[int(r['event']) for r in available]
   known=[int(e==1 and x>z) for x,z,e in zip(b,y,event)];upper=[int(x>z) for x,z in zip(b,y)]
   m={'availability':n/len(rs),'risk_lower':sum(known)/n,'risk_upper':sum(upper)/n,'mean_log_lower':sum(b)/n,'mean_safe_gap':sum(z-x for x,z in zip(b,y))/n,'severe_risk_lower':sum(e==1 and x>z+math.log10(2) for x,z,e in zip(b,y,event))/n,'severe_risk_upper':sum(x>z+math.log10(2) for x,z in zip(b,y))/n,'below1':sum(x<0 for x in b)/n,'below100':sum(x<2 for x in b)/n,'below10000':sum(x<4 for x in b)/n,'vacuous':sum(x==-math.inf for x in b)/n}
  metrics.append((key,m))
 source_seed=grouped_mean(metrics,lambda k:k[:-1],FIELDS);source=grouped_mean(source_seed,lambda k:k[:-1],FIELDS);summary=grouped_mean(source,lambda k:k[:-1],FIELDS)
 expected=dict(summary);saved=read(folder/'summary.csv');comparisons=0;maxdiff=0.
 for r in saved:
  key=(r['panel'],r['model'],int(r['k']),r['bound']);m=expected[key]
  for f in FIELDS:
   a,b=m[f],number(r[f]);assert equal(a,b),(folder.name,key,f,a,b);comparisons+=1
   if math.isfinite(a) and math.isfinite(b):maxdiff=max(maxdiff,abs(a-b))
  ss=[m for k,m in source if k[:-1]==key];assert int(r['n_sources'])==len(ss);assert int(r['n_available_sources'])==sum(not math.isnan(m['risk_upper']) for m in ss)
 # Pair exact rows and independently bound censored signed risk changes.
 pindex={tuple(r[f] for f in ['panel','model','bound','group_id','seed','dataset_id','row_id'])+(int(r['k']),):r for r in rows}
 assert len(pindex)==len(rows),'duplicatepredictionkey'
 contrast=defaultdict(list)
 for key,r in pindex.items():
  k=key[-1]
  if k==0:continue
  r0=pindex[key[:-1]+(0,)];b0=number(r0['log_lower']);bk=number(r['log_lower']);y=number(r['log_life']);e=int(r['event']);available=not math.isnan(b0) and not math.isnan(bk)
  if available:
   diff=float(bk>y)-float(b0>y)
   values={'log_gain':bk-b0,'risk_upper_diff':diff,'risk_lower_diff':diff*e,'true_risk_change_lo':diff if e else -float(b0>bk and b0>y),'true_risk_change_hi':diff if e else float(bk>b0 and bk>y),'availability_pair':1.}
  else:values={f:math.nan for f in ['log_gain','risk_upper_diff','risk_lower_diff','true_risk_change_lo','true_risk_change_hi']};values['availability_pair']=0.
  panel,model,bound,group,seed,curve,rowid,_=key;contrast[(panel,model,bound,k,group,seed,curve)].append(values)
 metrics2=list(next(iter(contrast.values()))[0]);c=[(key,{f:avg([v[f] for v in vals]) for f in metrics2}) for key,vals in sorted(contrast.items())]
 sseed=grouped_mean(c,lambda k:k[:-1],metrics2);sav=grouped_mean(sseed,lambda k:k[:-1],metrics2)
 lookup=defaultdict(dict)
 for key,m in sav:
  for f in metrics2:lookup[key[:4]+(f,)][key[4]]=m[f]
 ncontrast=0
 for r in read(folder/'paired_contrasts.csv'):
  key=(r['panel'],r['model'],r['bound'],int(r['k']),r['metric']);values=np.array([x for s,x in sorted(lookup[key].items())]);mean=float(np.mean(values));assert equal(mean,number(r['mean'])),(folder.name,key,'mean',mean,r['mean'])
  if len(values)>=2 and np.isfinite(values).all():
   rng=np.random.default_rng(231);samples=rng.integers(0,len(values),size=(2000,len(values)));lo,hi=np.quantile(values[samples].mean(axis=1),[.025,.975])
  else:lo,hi=math.nan,math.nan
  assert equal(lo,number(r['lo95'])) and equal(hi,number(r['hi95'])),(folder.name,key,'CI',lo,hi,r['lo95'],r['hi95'])
  assert len(values)==int(r['n_sources']);ncontrast+=3
  if key[0]=='A' and key[1]=='hierarchical' and key[2]=='raw' and key[3]==3:selected.append({'run':folder.name,**r})
 checks.append({'run':folder.name,'prediction_rows':len(rows),'summary_cells_checked':comparisons,'paired_cells_checked':ncontrast,'max_summary_abs_difference':maxdiff,'status':'PASS'})
receipt={'status':'PASS','checks':checks,'selected_panelA_raw_hierarchical_k3':selected,'independence':'Pure scalar independent metric aggregation from saved predictions; NumPy used only for declared bootstrapresampling. No rootmetricmodule imported. No new model fit or sourcevalidation claimed.'}
(OUT/'split_audit_result_tables.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
