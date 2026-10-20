"""Frozen ID-defined RFL numerical sensitivity; no population refits."""
from pathlib import Path
import json,pickle
import numpy as np
import pandas as pd
from src.v3_rfl import NormalNormalRFL

root=Path(__file__).resolve().parents[2]
folder=root/'results/v3/final_cap1e7'
receipt=json.loads((folder/'run_receipt.json').read_text())
cohort=pd.read_csv(root/'data/processed/v3/common/cohort.csv').set_index('row_id',drop=False)
prediction=pd.read_csv(folder/'predictions.csv')
selection=pd.read_csv(folder/'selections.csv')
first={}
for t in sorted(receipt['tasks'],key=lambda t:(t['campaign_id'],t['dataset_id'],t['seed'])):
    if t['seed']==0:first.setdefault(t['campaign_id'],t)
rows=[];models={}
for campaign,t in first.items():
    pred=prediction[(prediction.dataset_id==t['dataset_id'])&(prediction.seed==0)&(prediction.model=='rfl')]
    signature=pred.fit_signature.iloc[0]
    if signature not in models:
        with (root/'work/v3/model_cache'/f'{signature}.pkl').open('rb') as f:low=pickle.load(f)['rfl']
        high=NormalNormalRFL(nodes=192,shift_prior_sd=low.shift_prior_sd)
        for name in ['params_','sigma_','tau_gamma_','ratio_median_','ratio_center_','log_stress_ref_']:
            setattr(high,name,getattr(low,name))
        models[signature]=(low,high)
    low,high=models[signature]
    for (policy,k),p in pred.groupby(['policy','k']):
        if k:
            s=selection[(selection.dataset_id==t['dataset_id'])&(selection.seed==0)&
                        (selection.policy==policy)&(selection.k<=k)].sort_values('k')
            support=cohort.loc[s.row_id].copy()
            support['log_life']=s.revealed_log_life.to_numpy()
            support['event']=s.revealed_event.to_numpy()
        else:support=cohort.iloc[:0].copy()
        query=cohort.loc[t['query_ids'],['row_id','log_stress','load_ratio']]
        a,b=[m.predict_quantiles(query,support)[:,0] for m in (low,high)]
        finite=np.isfinite(a)&np.isfinite(b)
        delta=np.abs(a[finite]-b[finite])
        rows.append({'campaign_id':campaign,'dataset_id':t['dataset_id'],'seed':0,
                     'policy':policy,'k':int(k),'n_quantiles':len(a),
                     'infinite_status_identical':bool(np.array_equal(np.isposinf(a),np.isposinf(b))),
                     'max_abs_log10_quantile_difference':float(delta.max()) if len(delta) else None})
result={'definition':'lexicographically first dataset and seed0 per campaign; all four policies and feasible budgets; population parameters unchanged',
        'orders':[96,192],'n_campaigns':len(first),'n_fit_sets':len(models),
        'n_quantiles':sum(r['n_quantiles'] for r in rows),
        'infinite_status_identical':all(r['infinite_status_identical'] for r in rows),
        'max_abs_log10_quantile_difference':max(r['max_abs_log10_quantile_difference'] or 0 for r in rows),
        'rows':rows}
(root/'literature/v3_methods/real_quadrature_sensitivity.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
