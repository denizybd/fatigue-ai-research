"""Compare parent-isolated replay artifacts without executing experiment code."""
from pathlib import Path
import json,hashlib,datetime
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[3];FRESH=ROOT/'work/v4/fresh_replay';OUT=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
folders=['controlled_cap1e7','controlled_cap1e6','source_holdout_cap1e7','source_holdout_cap1e6'];checks=[];fitchecks=[];issues=[]
def strip_time(obj):
 if isinstance(obj,dict):return {k:strip_time(v) for k,v in obj.items() if k not in ['elapsed_seconds','created_utc','createdDate']}
 if isinstance(obj,list):return [strip_time(v) for v in obj]
 return obj
for folder in folders:
 old=ROOT/'results/v4'/folder;new=FRESH/'results/v4'/folder
 for p in sorted(old.rglob('*.csv')):
  q=new/p.relative_to(old)
  if not q.exists():issues.append(dict(folder=folder,file=str(p.relative_to(old)),issue='missing fresh file'));continue
  equal=sha(p)==sha(q);difference=0.;metadata=[]
  if not equal:
   a,b=pd.read_csv(p),pd.read_csv(q)
   assert a.shape==b.shape and list(a)==list(b),(p,q)
   for c in a:
    if pd.api.types.is_numeric_dtype(a[c]) and pd.api.types.is_numeric_dtype(b[c]):
     x,y=a[c].to_numpy(),b[c].to_numpy();assert np.array_equal(np.isnan(x),np.isnan(y)) and np.array_equal(np.isposinf(x),np.isposinf(y)) and np.array_equal(np.isneginf(x),np.isneginf(y))
     f=np.isfinite(x)&np.isfinite(y);difference=max(difference,float(np.max(np.abs(x[f]-y[f]))) if np.any(f) else 0.)
    elif not a[c].fillna('<NA>').equals(b[c].fillna('<NA>')):metadata.append(c)
   if difference or metadata:issues.append(dict(folder=folder,file=str(p.relative_to(old)),max_numeric_difference=difference,different_non_numeric_columns=metadata))
  checks.append(dict(folder=folder,file=str(p.relative_to(old)),byte_identical=equal,max_numeric_difference=difference,different_non_numeric_columns=metadata))
 a=json.loads((old/'run_receipt.json').read_text());b=json.loads((new/'run_receipt.json').read_text());equal=strip_time(a['fits'])==strip_time(b['fits']);fitchecks.append(dict(folder=folder,population_fit_parameters_and_diagnostics_equal_excluding_elapsed_times=equal,n_fitsets=len(a['fits'])));
 if not equal:issues.append(dict(folder=folder,issue='fit receipt values differ beyond elapsed times'))
r=dict(audited_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),verdict='PASS' if not issues else 'REVIEW',scope='Independent artifact comparison of parent-completed isolated fresh replay; this auditor did not fit or rerun models.',folders=folders,n_scientific_CSV_tables=len(checks),all_CSV_bytes_identical=all(x['byte_identical'] for x in checks),max_numeric_difference=max((x['max_numeric_difference'] for x in checks),default=0.),fit_parameters_and_diagnostics_match=all(x['population_fit_parameters_and_diagnostics_equal_excluding_elapsed_times'] for x in fitchecks),fit_checks=fitchecks,issues=issues,tables=checks,interpretation='Computational reproducibility only; not independent physical experiments or reliability confirmation.')
(OUT/'v4_fresh_replay_comparison.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='tables'},indent=2))
