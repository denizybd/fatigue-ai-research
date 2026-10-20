"""Compare fresh phase3.1 replay with released source-audited calculations."""
import json
import pandas as pd
from src.v3_prepare import ROOT,digest

def compare():
    rows=[]
    for cap in ['1e7','1e6']:
        a=ROOT/('results/v3/identity_cap'+cap);b=ROOT/('results/v3/identity_portable_cap'+cap)
        ra=json.loads((a/'run_receipt.json').read_text())
        rb=json.loads((b/'run_receipt.json').read_text())
        fa={tuple(r['training_sources']):r['fits'] for r in ra['fits'].values()}
        fb={tuple(r['training_sources']):r['fits'] for r in rb['fits'].values()}
        assert fa==fb,'population fit parameters/diagnostics differ'
        for name in ['predictions.csv','selections.csv','summary.csv','paired_comparisons.csv','by_condition.csv','success_gates.csv']:
            x=pd.read_csv(a/name);y=pd.read_csv(b/name)
            # The cache signature hashes ALL CSV columns. Removing an unused
            # external table removes its all-empty training metadata columns,
            # changing this hash while every fit input/parameter stays identical.
            metadata=['fit_signature'] if name=='predictions.csv' else []
            pd.testing.assert_frame_equal(x.drop(columns=metadata),y.drop(columns=metadata),check_exact=True)
            rows.append({'cap':cap,'table':name,'rows':len(x),'exact_values':True,
              'excluded_cache_metadata_columns':metadata,
              'original_sha256':digest(a/name),'replay_sha256':digest(b/name)})
    receipt={'status':'PASS','tables':rows,'n_tables':len(rows),'max_numeric_difference':0,
      'population_fits_and_diagnostics_exact':True,
      'scope':'Same audited source gate; unused earlier campaign omitted. Scientific values exact; prediction cache hash differs because empty unrelated metadata columns were omitted. Not independent physical replication.'}
    p=ROOT/'results/v3/identity_portable_replay_comparison.json';p.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':'PASS','tables':len(rows),'max_numeric_difference':0}))
if __name__=='__main__':compare()
