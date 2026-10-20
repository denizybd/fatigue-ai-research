"""Compare all frozen prediction and summary CSVs with an end-to-end replay."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def compare(a,b,keys):
    x=pd.read_csv(a).sort_values(keys).reset_index(drop=True);y=pd.read_csv(b).sort_values(keys).reset_index(drop=True)
    if list(x.columns)!=list(y.columns) or len(x)!=len(y):return {'pass':False,'rows_a':len(x),'rows_b':len(y),'reason':'schema/row count'}
    numeric=x.select_dtypes(include='number').columns;maxdiff=0.;fail=[]
    for c in x.columns:
        if c in numeric:
            aa=x[c].to_numpy(float);bb=y[c].to_numpy(float)
            if not np.allclose(aa,bb,rtol=1e-12,atol=1e-12,equal_nan=True):fail.append(c)
            finite=np.isfinite(aa)&np.isfinite(bb)
            if finite.any():maxdiff=max(maxdiff,float(np.max(np.abs(aa[finite]-bb[finite]))))
        elif not x[c].fillna('__NA__').equals(y[c].fillna('__NA__')):fail.append(c)
    return {'pass':not fail,'rows':len(x),'max_absolute_numeric_difference':maxdiff,'failed_columns':fail,'sha256_original':hashlib.sha256(a.read_bytes()).hexdigest(),'sha256_replay':hashlib.sha256(b.read_bytes()).hexdigest()}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',default='results');ap.add_argument('--replay',default='results/full_reproduction');args=ap.parse_args();base=ROOT/args.baseline;replay=ROOT/args.replay
    r={}
    for name in ['primary','doi_only','random_rows','deduplicated','weak_edge','naive_censoring','mlp_extended']:
        r[name]={'predictions':compare(base/name/'predictions.csv',replay/name/'predictions.csv',['seed','fold','model','bound','row_id']),
                 'summaries':compare(base/name/'summary.csv',replay/name/'summary.csv',['scheme','model','bound','policy'])}
    passed=all(v['predictions']['pass'] and v['summaries']['pass'] for v in r.values())
    report={'all_prediction_and_summary_checks_pass':passed,'comparisons':r,'scope':'All7 frozen experiment configurations, all3seeds; within pinned local environment. Not external experimental validation.'}
    (base/'full_reproduction_comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if not passed:raise SystemExit(1)

if __name__=='__main__':main()
