"""Campaign-weighted risk/utility with paired censoring identification limits."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

def campaign_summary(d,metrics,keys):
    rows=[]
    # Repeated splits are averaged within campaign, not counted as experiments.
    conditions=d.groupby(keys+['campaign_id','dataset_id','seed'],dropna=False)[metrics].mean()
    campaigns=conditions.groupby(keys+['campaign_id','seed'],dropna=False).mean()
    campaigns=campaigns.groupby(keys+['campaign_id'],dropna=False).mean()
    for values,g in campaigns.groupby(level=keys,dropna=False):
        if not isinstance(values,tuple):values=(values,)
        base=dict(zip(keys,values));base['n_campaigns']=len(g)
        for metric in metrics:
            x=g[metric].to_numpy();x=x[np.isfinite(x)]
            mean=float(x.mean()) if len(x) else np.nan
            if len(x)>=2:
                rng=np.random.default_rng(231)
                lo,hi=np.quantile(x[rng.integers(0,len(x),(2000,len(x)))].mean(1),[.025,.975])
            else:lo,hi=np.nan,np.nan
            rows.append(base|{'metric':metric,'mean':mean,'lo95':float(lo),'hi95':float(hi),
                              'n_finite_campaigns':len(x)})
    return pd.DataFrame(rows)

def summarize(folder):
    folder=Path(folder);d=pd.read_csv(folder/'predictions.csv')
    y=d.log_life.to_numpy();L=d.log_lower.to_numpy();e=d.event.to_numpy()
    available=~np.isnan(L);finite=np.isfinite(L)
    d['availability']=available.astype(float);d['finite_availability']=finite.astype(float)
    d['positive_infinite']=np.isposinf(L).astype(float)
    d['known_risk']=np.where(available,(L>y)&(e==1),0.).astype(float)
    d['upper_risk']=np.where(available,L>y,1.).astype(float)
    d['finite_log_lower']=np.where(finite,L,np.nan)
    d['failure_shortfall']=np.where((e==1)&finite,np.maximum(y-L,0),np.nan)
    d['all_support_runout']=((d.k>0)&(d.n_support_failure==0)).astype(float)
    metrics=['availability','finite_availability','positive_infinite','known_risk','upper_risk',
             'finite_log_lower','failure_shortfall','support_cycles','all_support_runout']
    keys=['panel','policy','model','k','cap']
    summary=campaign_summary(d,metrics,keys);summary.to_csv(folder/'summary.csv',index=False)
    d.groupby(keys+['campaign_id','dataset_id','seed'])[metrics].mean().to_csv(folder/'by_condition.csv')
    contrasts=[];query_checks=[]
    index=['campaign_id','dataset_id','seed','row_id']
    for key,g in d.groupby(keys):
        base=dict(zip(keys,key));a=g.set_index(index).sort_index()
        # Policy contrast and few-shot versus its exact common-query k0.
        for comparison in ['versus_random','versus_k0']:
            b=d[(d.panel==base['panel'])&(d.model==base['model'])&(d.cap==base['cap'])&
                (d.policy==('random' if comparison=='versus_random' else base['policy']))&
                (d.k==(base['k'] if comparison=='versus_random' else 0))].set_index(index)
            # k0 can include conditions with smaller max budget, so select matching a.
            assert set(a.index)<=set(b.index),'query identity mismatch'
            b=b.loc[a.index]
            assert np.array_equal(a.log_life.to_numpy(),b.log_life.to_numpy())
            assert np.array_equal(a.event.to_numpy(),b.event.to_numpy())
            query_checks.append(base|{'comparison':comparison,'n_pairs':len(a),'same_queries':True})
            la,lb=a.log_lower.to_numpy(),b.log_lower.to_numpy()
            y=a.log_life.to_numpy();event=a.event.to_numpy()
            valid=(~np.isnan(la))&(~np.isnan(lb));ff=np.isfinite(la)&np.isfinite(lb)
            diff=(la>y).astype(float)-(lb>y).astype(float)
            c=a.reset_index()[['panel','campaign_id','dataset_id','seed']].copy()
            for k,v in base.items():c[k]=v
            c['comparison']=comparison
            c['paired_availability']=valid.astype(float)
            c['paired_finite_availability']=ff.astype(float)
            c['log_life_gain']=np.where(ff,la-lb,np.nan)
            # For right-censored queries T>y; true interval indicator difference
            # is bounded using the ordering of the two proposed lower bounds.
            c['true_risk_change_lo']=np.where(valid,np.where(event==1,diff,
                -((lb>la)&(lb>y)).astype(float)),-1.)
            c['true_risk_change_hi']=np.where(valid,np.where(event==1,diff,
                ((la>lb)&(la>y)).astype(float)),1.)
            c['support_cycle_change']=a.support_cycles.to_numpy()-b.support_cycles.to_numpy()
            contrasts.append(c)
    contrast=pd.concat(contrasts,ignore_index=True)
    paired=campaign_summary(contrast,['paired_availability','paired_finite_availability','log_life_gain',
                'true_risk_change_lo','true_risk_change_hi','support_cycle_change'],keys+['comparison'])
    paired.to_csv(folder/'paired_comparisons.csv',index=False)
    (folder/'query_identity_checks.json').write_text(json.dumps(query_checks,indent=2)+'\n')
    gates=[]
    for key,g in paired[paired.comparison=='versus_random'].groupby(keys):
        base=dict(zip(keys,key));m=g.set_index('metric')
        absolute=summary
        for k,v in base.items():absolute=absolute[absolute[k]==v]
        absolute=absolute.set_index('metric')
        utility_lo=float(m.loc['log_life_gain','lo95'])
        risk_hi=float(m.loc['true_risk_change_hi','hi95'])
        absrisk_hi=float(absolute.loc['upper_risk','hi95'])
        availability=float(m.loc['paired_availability','mean'])
        gates.append(base|{'n_campaigns':int(g.n_campaigns.iloc[0]),
            'utility_gain_lo95':utility_lo,'true_risk_change_hi95':risk_hi,
            'absolute_upper_risk_hi95':absrisk_hi,'paired_availability':availability,
            'relative_success':bool(utility_lo>0 and risk_hi<=.02 and availability>=.95),
            'absolute_reliability_supported':bool(absrisk_hi<=.10),
            'full_success':bool(utility_lo>0 and risk_hi<=.02 and availability>=.95 and absrisk_hi<=.10)})
    pd.DataFrame(gates).to_csv(folder/'success_gates.csv',index=False)
    print(json.dumps({'prediction_rows':len(d),'query_identity_checks':len(query_checks),
        'query_pairs_checked':sum(x['n_pairs'] for x in query_checks),'summary_rows':len(summary),
        'paired_rows':len(paired),'relative_gates_passed':sum(x['relative_success'] for x in gates),
        'full_gates_passed':sum(x['full_success'] for x in gates)}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');a=p.parse_args();summarize(a.folder)
