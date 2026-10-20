"""Regenerate cross-analysis tables and output-scale diagnostics from CSVs."""
from pathlib import Path
import argparse,json,subprocess,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='results');args=ap.parse_args();base=ROOT/args.root
    mapping=pd.read_csv(ROOT/'data/processed/primary.csv').set_index('row_id').group_id.to_dict()
    p=pd.read_csv(base/'doi_only/predictions.csv');p.group_id=p.row_id.map(mapping)
    common=base/'doi_only_common_blocks';common.mkdir(exist_ok=True);p.to_csv(common/'predictions.csv',index=False)
    (common/'README.txt').write_text('Original DOI-only predictions reaggregated on primary29 provenance blocks. No refitting. Related curves may cross fitting/test folds. This restores the averaging population, not identical fitting/calibration composition.\n')
    subprocess.run([sys.executable,'-m','src.summarize','--folder',str(common.relative_to(ROOT))],cwd=ROOT,check=True,capture_output=True,text=True)
    rows=[]
    for name in ['primary','deduplicated','weak_edge','naive_censoring','random_rows','doi_only_common_blocks']:
        s=pd.read_csv(base/name/'summary.csv');s=s[(s.model=='linear')&(s.policy=='all')].copy();s['analysis']=name
        rows.append(s[['analysis','sources','bound','risk_lower','risk_upper','pooled_risk_lower','pooled_risk_upper','cohort_violation_lower','cohort_violation_upper','conservatism_decades','failure_mae']])
    pd.concat(rows,ignore_index=True).to_csv(base/'sensitivity_comparison.csv',index=False)
    p=pd.read_csv(base/'primary/predictions.csv');utility=[]
    for (model,bound),z in p.groupby(['model','bound']):
        utility.append(dict(model=model,bound=bound,pooled_log_bound_p10=float(z.log_lower.quantile(.1)),pooled_log_bound_p50=float(z.log_lower.quantile(.5)),pooled_log_bound_p90=float(z.log_lower.quantile(.9)),fraction_below_one_cycle=float((z.log_lower<0).mean())))
    pd.DataFrame(utility).to_csv(base/'life_bound_utility.csv',index=False)
    for name in ['primary','doi_only','random_rows','deduplicated','weak_edge','naive_censoring','mlp_extended']:
        rows=[]
        for f in sorted((base/name/'folds').glob('*.json')):
            d=json.loads(f.read_text());rows.extend(dict(file=f.name,**s) for s in d['fits'])
        pd.DataFrame(rows).to_csv(base/name/'fit_statuses.csv',index=False)
    print('Postprocessing complete:',base)

if __name__=='__main__':main()
