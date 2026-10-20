"""Paired training contrasts and inherited policy contrasts on one target program."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from src.v3_summarize import summarize,campaign_summary

def run(folder):
    folder=Path(folder);all_data=pd.read_csv(folder/'predictions.csv')
    metrics=[];policies=[]
    for regime,d in all_data.groupby('regime',sort=True):
        sub=folder/regime;sub.mkdir(exist_ok=True)
        d.to_csv(sub/'predictions.csv',index=False)
        summarize(sub)
        for name,target in [('summary.csv',metrics),('paired_comparisons.csv',policies)]:
            x=pd.read_csv(sub/name);x.insert(0,'regime',regime);target.append(x)
    pd.concat(metrics,ignore_index=True).to_csv(folder/'all_regime_summary.csv',index=False)
    pd.concat(policies,ignore_index=True).to_csv(folder/'all_policy_contrasts.csv',index=False)
    idx=['campaign_id','dataset_id','seed','row_id']
    keys=['regime','policy','model','k','cap']
    pieces=[];checks=[]
    for key,a in all_data.groupby(keys,sort=True):
        info=dict(zip(keys,key));a=a.set_index(idx).sort_index()
        b=all_data[(all_data.regime=='strict309')&(all_data.policy==info['policy'])&
            (all_data.model==info['model'])&(all_data.k==info['k'])&(all_data.cap==info['cap'])].set_index(idx).sort_index()
        assert a.index.equals(b.index),'training regimes must have identical queries'
        assert np.array_equal(a[['log_life','event','log_stress','support_cycles','n_support_failure']],
                              b[['log_life','event','log_stress','support_cycles','n_support_failure']])
        la,lb=a.log_lower.to_numpy(),b.log_lower.to_numpy();y=a.log_life.to_numpy();event=a.event.to_numpy()
        valid=~np.isnan(la)&~np.isnan(lb);finite=np.isfinite(la)&np.isfinite(lb)
        diff=(la>y).astype(float)-(lb>y).astype(float)
        c=a.reset_index()[['campaign_id','dataset_id','seed']].copy()
        for k,v in info.items():c[k]=v
        c['paired_availability']=valid.astype(float)
        c['paired_finite_availability']=finite.astype(float)
        c['log_life_gain']=np.where(finite,la-lb,np.nan)
        c['true_risk_change_lo']=np.where(valid,np.where(event==1,diff,-((lb>la)&(lb>y)).astype(float)),-1.)
        c['true_risk_change_hi']=np.where(valid,np.where(event==1,diff,((la>lb)&(la>y)).astype(float)),1.)
        pieces.append(c);checks.append(info|dict(pairs=len(a),queries_equal=True,observed_support_equal=True))
    c=pd.concat(pieces,ignore_index=True)
    summary=campaign_summary(c,['paired_availability','paired_finite_availability','log_life_gain',
                               'true_risk_change_lo','true_risk_change_hi'],keys)
    summary.to_csv(folder/'training_contrasts.csv',index=False)
    c.groupby(keys+['campaign_id','dataset_id','seed']).mean(numeric_only=True).to_csv(folder/'training_by_condition.csv')
    (folder/'training_pair_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps(dict(training_contrasts=len(summary),paired_checks=len(checks),source_programs=1)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');a=p.parse_args();run(a.folder)
