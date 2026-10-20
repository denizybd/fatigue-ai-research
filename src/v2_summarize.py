"""Source-balanced summaries and prespecified paired phase-2 contrasts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.v2_prepare import ROOT

KEYS=['panel','model','k','bound','group_id','seed','dataset_id']


def curve_metrics(d):
    b=d.log_lower.to_numpy(float);y=d.log_life.to_numpy(float);e=d.event.to_numpy(int)
    available=~np.isnan(b);n=len(d)
    if not available.any():
        return {'n_query':n,'n_available':0,'availability':0.,'risk_lower':np.nan,
                'risk_upper':np.nan,'mean_log_lower':np.nan,'mean_safe_gap':np.nan,
                'below1':np.nan,'below100':np.nan,'below10000':np.nan,'vacuous':np.nan}
    b,y,e=b[available],y[available],e[available]
    known=(e==1)&(b>y);unknown=(e==0)&(b>y)
    gap=y-b
    # This gap is endpoint minus lower bound, not true-life prediction error.
    return {'n_query':n,'n_available':len(b),'availability':len(b)/n,
            'risk_lower':known.mean(),'risk_upper':(known|unknown).mean(),
            'mean_log_lower':b.mean(),'mean_safe_gap':gap.mean(),
            'severe_risk_lower':np.mean((e==1)&(b>y+np.log10(2))),
            'severe_risk_upper':np.mean(b>y+np.log10(2)),
            'below1':np.mean(b<0),'below100':np.mean(b<2),'below10000':np.mean(b<4),
            'vacuous':np.mean(np.isneginf(b))}


def paired_interval(values,seed=231,replicates=2000):
    x=np.asarray(values,float)
    if len(x)<2 or not np.all(np.isfinite(x)):
        return [np.nan,np.nan]
    rng=np.random.default_rng(seed)
    q=np.quantile(x[rng.integers(0,len(x),(replicates,len(x)))].mean(1),[.025,.975])
    return q.tolist()


def summarize(folder):
    folder=Path(folder);d=pd.read_csv(folder/'predictions.csv')
    rows=[]
    for keys,g in d.groupby(KEYS,sort=True):
        rows.append(dict(zip(KEYS,keys))|curve_metrics(g))
    curves=pd.DataFrame(rows);curves.to_csv(folder/'curve_metrics.csv',index=False)
    numeric=[c for c in curves if c not in KEYS+['n_query','n_available']]
    sources=curves.groupby(KEYS[:-1],as_index=False)[numeric].mean()
    sources.to_csv(folder/'source_seed_metrics.csv',index=False)
    source_avg=sources.groupby(KEYS[:-2],as_index=False)[numeric].mean()
    source_avg.to_csv(folder/'source_metrics.csv',index=False)
    summary=source_avg.groupby(['panel','model','k','bound'],as_index=False)[numeric].mean()
    counts=source_avg.groupby(['panel','model','k','bound']).agg(
        n_sources=('group_id','size'),n_available_sources=('risk_upper','count')).reset_index()
    summary=summary.merge(counts,on=['panel','model','k','bound'])
    summary.to_csv(folder/'summary.csv',index=False)
    paired=[]
    # Compare support counts on exactly the same rows, then aggregate within
    # curve, within source, and over seed. No changing query denominators.
    join=['panel','seed','model','bound','group_id','dataset_id','row_id']
    for (panel,model,bound),g in d.groupby(['panel','model','bound']):
        zero=g[g.k==0][join+['log_lower','log_life','event']]
        for k in sorted(set(g.k)-{0}):
            z=zero.merge(g[g.k==k][join+['log_lower']],on=join,suffixes=('_0','_k'),validate='one_to_one')
            assert len(z)==len(zero)
            b0=z.log_lower_0.to_numpy();bk=z.log_lower_k.to_numpy();y=z.log_life.to_numpy();e=z.event.to_numpy()
            ok=(~np.isnan(b0))&(~np.isnan(bk))
            z['available_pair']=ok.astype(float)
            z['log_gain']=np.where(ok,bk-b0,np.nan)
            z['risk_upper_diff']=np.where(ok,(bk>y).astype(float)-(b0>y).astype(float),np.nan)
            z['risk_lower_diff']=np.where(ok,((bk>y)&(e==1)).astype(float)-((b0>y)&(e==1)).astype(float),np.nan)
            actual_failure=((bk>y).astype(float)-(b0>y).astype(float))
            z['true_risk_change_lo']=np.where(ok,np.where(e==1,actual_failure,
                -((b0>bk)&(b0>y)).astype(float)),np.nan)
            z['true_risk_change_hi']=np.where(ok,np.where(e==1,actual_failure,
                ((bk>b0)&(bk>y)).astype(float)),np.nan)
            cm=z.groupby(['group_id','seed','dataset_id'],as_index=False)[
                ['log_gain','risk_upper_diff','risk_lower_diff','true_risk_change_lo',
                 'true_risk_change_hi','available_pair']].mean()
            sm=cm.groupby(['group_id','seed'],as_index=False).mean(numeric_only=True)
            av=sm.groupby('group_id').mean(numeric_only=True)
            for metric in ['log_gain','risk_upper_diff','risk_lower_diff',
                           'true_risk_change_lo','true_risk_change_hi']:
                values=av[metric].to_numpy();ci=paired_interval(values)
                paired.append({'panel':panel,'model':model,'bound':bound,'k':k,
                    'metric':metric,'mean':float(np.mean(values)),'lo95':ci[0],'hi95':ci[1],
                    'n_sources':len(values),'availability_pair':av.available_pair.mean()})
    contrasts=pd.DataFrame(paired);contrasts.to_csv(folder/'paired_contrasts.csv',index=False)
    target=summary[(summary.panel=='A')&(summary.model=='hierarchical')&
                   (summary.bound=='endpoint_calibrated')&(summary.k==3)]
    select=contrasts[(contrasts.panel=='A')&(contrasts.model=='hierarchical')&
                    (contrasts.bound=='endpoint_calibrated')&(contrasts.k==3)]
    if len(target)==1 and len(select):
        gain=select[select.metric=='log_gain'].iloc[0]
        risk=select[select.metric=='risk_upper_diff'].iloc[0]
        true_risk=select[select.metric=='true_risk_change_hi'].iloc[0]
        tests={'observed_risk_upper_le_10pct':bool(target.iloc[0].risk_upper<=.1),
               'risk_increase_upper95_le_2pp':bool(risk.hi95<=.02),
               'true_risk_change_upper95_le_2pp':bool(true_risk.hi95<=.02),
               'gain_lower95_gt_1p25x':bool(gain.lo95>np.log10(1.25))}
        verdict={'criterion':tests,'all_pass':all(tests.values()),
                 'note':'Descriptive internal source bootstrap; not arbitrary-process reliability certification.'}
        (folder/'primary_claim.json').write_text(json.dumps(verdict,indent=2)+'\n')
    print(summary.to_string(index=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',nargs='?',default=str(ROOT/'results/v2/main'))
    summarize(p.parse_args().folder)
