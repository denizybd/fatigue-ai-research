"""Compare all frozen phase-2 result tables against a fresh end-to-end replay."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
import pandas as pd
from src.v2_package import RUNS
from src.v2_prepare import ROOT

def compare(replay):
    replay=Path(replay);items=[]
    for folder in RUNS:
        for name in ['predictions.csv','summary.csv','paired_contrasts.csv']:
            p=ROOT/'results/v2'/folder/name;q=replay/folder/name
            if not p.exists():continue
            if not q.exists():raise FileNotFoundError(q)
            x,y=pd.read_csv(p),pd.read_csv(q)
            if list(x.columns)!=list(y.columns) or x.shape!=y.shape:
                raise AssertionError((folder,name,x.shape,y.shape))
            maxdiff=0.;non_numeric_equal=True;nonfinite_equal=True
            for col in x:
                if pd.api.types.is_numeric_dtype(x[col]) and pd.api.types.is_numeric_dtype(y[col]):
                    a,b=x[col].to_numpy(float),y[col].to_numpy(float)
                    ok=np.isfinite(a)&np.isfinite(b)
                    if ok.any():maxdiff=max(maxdiff,float(np.max(np.abs(a[ok]-b[ok]))))
                    nonfinite_equal &= bool(np.array_equal(np.isnan(a),np.isnan(b)) and
                        np.array_equal(np.isposinf(a),np.isposinf(b)) and np.array_equal(np.isneginf(a),np.isneginf(b)))
                else:non_numeric_equal &= x[col].equals(y[col])
            items.append({'run':folder,'file':name,'rows':len(x),'byte_identical':p.read_bytes()==q.read_bytes(),
                'exact_values':x.equals(y),'max_numeric_difference':maxdiff,
                'non_numeric_equal':non_numeric_equal,'nonfinite_equal':nonfinite_equal,
                'original_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                'replay_sha256':hashlib.sha256(q.read_bytes()).hexdigest()})
    receipt={'runs':len(RUNS),'tables':len(items),
        'prediction_instances':sum(v['rows'] for v in items if v['file']=='predictions.csv'),
        'all_tables_byte_identical':all(v['byte_identical'] for v in items),
        'all_exact_values':all(v['exact_values'] for v in items),
        'max_numeric_difference':max(v['max_numeric_difference'] for v in items),
        'checks':items,'scope':'Same-code end-to-end computational replay, not independent experimental validation.'}
    (ROOT/'results/v2/full_replay_comparison.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='checks'},indent=2))
    if not (all(v['non_numeric_equal'] and v['nonfinite_equal'] for v in items) and receipt['max_numeric_difference']<1e-9):
        raise AssertionError('Replay differs; inspect comparison receipt')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replay',required=True);compare(p.parse_args().replay)
