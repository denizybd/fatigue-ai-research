"""Summarize saved test predictions; no model or gate optimization."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import pandas as pd
from scipy.stats import norm
from src.evaluation import risk_metrics
ROOT=Path(__file__).resolve().parents[1]

def cell(p,a,policy):
    out=dict(seed=int(p.seed.iloc[0]),group_id=p.group_id.iloc[0],model=p.model.iloc[0],bound=p.bound.iloc[0],scheme=p.scheme.iloc[0],policy=policy)
    for factor in [1.,2.]:
        m=risk_metrics(p.log_lower.to_numpy(),p.log_life.to_numpy(),p.event.to_numpy(),a,factor)
        out.update({(k if factor==1 else 'severe_'+k):v for k,v in m.items()})
    out['runout_fraction']=float(p.loc[a,'runout'].mean()) if np.any(a) else np.nan
    out['median_log_stress']=float(p.loc[a,'log_stress'].median()) if np.any(a) else np.nan
    out['conservatism_decades']=float((p.loc[a,'mu']-p.loc[a,'log_lower']).median()) if np.any(a) else np.nan
    out['median_log_lower']=float(p.loc[a,'log_lower'].median()) if np.any(a) else np.nan
    out['zero_bound_fraction']=float(np.isneginf(p.loc[a,'log_lower']).mean()) if np.any(a) else np.nan
    out['increasing_life_with_stress_fraction']=float((p.loc[a,'stress_slope']>0).mean()) if np.any(a) else np.nan
    fail=a&(p.event.to_numpy()==1)
    out['failure_mae']=float(np.mean(np.abs(p.loc[fail,'mu']-p.loc[fail,'log_life']))) if np.any(fail) else np.nan
    out['failure_rmse']=float(np.sqrt(np.mean((p.loc[fail,'mu']-p.loc[fail,'log_life'])**2))) if np.any(fail) else np.nan
    return out

def build_cells(p):
    rows=[]
    for key,t in p.groupby(['scheme','seed','group_id','model','bound'],sort=True):
        rows.append(cell(t,np.ones(len(t),bool),'all'))
        if key[-2:]!=('linear','endpoint_pooled'): continue
        for score in ['distance','instability','combined']:
            for frac in [.5,.8]:
                rows.append(cell(t,t[f'accept_{score}_{frac}'].to_numpy(bool),f'operational_{score}_{frac}'))
                k=int(np.ceil(frac*len(t)));mask=np.zeros(len(t),bool)
                # Raw records can be sorted by life/stress: ties must not inherit
                # that order. Hashing IDs gives fixed outcome-blind tie breaks.
                tie=np.array([int(hashlib.sha256(f'{rid}|{key[1]}'.encode()).hexdigest()[:16],16) for rid in t.row_id],dtype=np.uint64)
                mask[np.lexsort((tie,t[score].to_numpy()))[:k]]=True
                rows.append(cell(t,mask,f'matched_{score}_{frac}'))
        for frac in [.5,.8]:
            # Same source count as every matched score,20 outcome-blind realizations.
            sub=[];k=int(np.ceil(frac*len(t)))
            for b in range(20):
                order=np.random.default_rng(int(key[1])+10000+b).permutation(len(t))
                a=np.zeros(len(t),bool);a[order[:k]]=True;sub.append(cell(t,a,f'matched_random_{frac}'))
            sub=pd.DataFrame(sub);v=sub.iloc[0].to_dict()
            for c in sub.select_dtypes(include='number').columns: v[c]=float(sub[c].mean())
            rows.append(v)
    return pd.DataFrame(rows)

def aggregate(cells):
    # The source, not seed or row, is the resampling unit.
    keys=['scheme','model','bound','policy']
    cols=['risk_lower','risk_upper','severe_risk_lower','severe_risk_upper','availability','conservatism_decades','runout_fraction','median_log_stress','failure_mae','failure_rmse','zero_bound_fraction','increasing_life_with_stress_fraction']
    rows=[];rng=np.random.default_rng(9821)
    for key,z in cells.groupby(keys):
        by=z.groupby('group_id')[cols].mean();r=dict(zip(keys,key));r['sources']=len(by);r['sources_with_any_acceptance']=int(z.groupby('group_id').accepted.max().gt(0).sum())
        for c in cols:
            v=by[c].to_numpy();v=v[np.isfinite(v)]
            if len(v):
                means=v[rng.integers(0,len(v),(2000,len(v)))].mean(axis=1)
                r[c]=float(v.mean());r[c+'_ci_low'],r[c+'_ci_high']=np.quantile(means,[.025,.975])
            else:r[c]=r[c+'_ci_low']=r[c+'_ci_high']=np.nan
        r['pooled_risk_lower']=float(z.known_danger.sum()/z.accepted.sum()) if z.accepted.sum() else np.nan
        r['pooled_risk_upper']=float((z.known_danger.sum()+z.unknown_runouts.sum())/z.accepted.sum()) if z.accepted.sum() else np.nan
        rows.append(r)
    return pd.DataFrame(rows)

def contrasts(cells):
    z=cells[(cells.model=='linear')&(cells.bound=='endpoint_pooled')]
    cols=['risk_lower','risk_upper','severe_risk_lower','severe_risk_upper','conservatism_decades','availability']
    by=z.groupby(['scheme','group_id','policy'])[cols].mean().reset_index();rows=[]
    rng=np.random.default_rng(3284)
    for scheme,s in by.groupby('scheme'):
        for frac in [.5,.8]:
            a=s[s.policy==f'matched_combined_{frac}'].set_index('group_id')
            for score in ['distance','instability','random']:
                b=s[s.policy==f'matched_{score}_{frac}'].set_index('group_id');joint=a.index.intersection(b.index);aa=a.loc[joint];bb=b.loc[joint]
                diff=aa.risk_lower.to_numpy()-bb.risk_lower.to_numpy();boot=diff[rng.integers(0,len(diff),(2000,len(diff)))].mean(axis=1)
                rows.append(dict(scheme=scheme,fraction=frac,comparison=f'combined minus {score}',sources=len(joint),known_violation_difference=diff.mean(),ci_low=np.quantile(boot,.025),ci_high=np.quantile(boot,.975),
                    risk_difference_identification_lower=float((aa.risk_lower-bb.risk_upper).mean()),risk_difference_identification_upper=float((aa.risk_upper-bb.risk_lower).mean()),
                    severe_known_difference=float((aa.severe_risk_lower-bb.severe_risk_lower).mean())))
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--folder',default='results/primary');args=ap.parse_args();out=ROOT/args.folder
    p=pd.read_csv(out/'predictions.csv');cells=build_cells(p);cells.to_csv(out/'source_seed_metrics.csv',index=False)
    summary=aggregate(cells);summary.to_csv(out/'summary.csv',index=False);contrasts(cells).to_csv(out/'paired_contrasts.csv',index=False)
    # Likelihood and failure error reported once per model, not copied across bounds.
    q=p[p.bound=='model_q10'].copy();z=(q.log_life-q.mu)/q.sigma;q['nll']=np.where(q.event==1,-norm.logpdf(z)+np.log(q.sigma),-norm.logsf(z))
    q.groupby(['scheme','model','group_id','seed']).nll.mean().groupby(['scheme','model']).mean().to_csv(out/'censored_nll.csv')
    print(summary[['model','bound','policy','risk_lower','risk_upper','availability','conservatism_decades']].to_string(index=False))

if __name__=='__main__':main()
