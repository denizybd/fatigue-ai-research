"""Reconstruct RBF queries, support exposure and reported means from saved facts.

Independent arithmetic check: no predictor, selector or summary module imports.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'data/processed/v5/rbf'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def balanced(frame, keys, metrics):
    # Each condition and repeated seed has equal weight within the one program.
    c = frame.groupby(keys+['dataset_id','seed'],dropna=False)[metrics].mean()
    c = c.groupby(keys+['seed'],dropna=False).mean()
    return c.groupby(keys,dropna=False).mean()


def audit(folder):
    folder=Path(folder)
    s=json.loads((BASE/'frozen_splits.json').read_text())
    t=pd.read_csv(BASE/'target.csv').set_index('row_id',drop=False)
    p=pd.read_csv(folder/'predictions.csv')
    selected=pd.read_csv(folder/'selections.csv')
    caps=p.cap.unique();assert len(caps)==1;cap=float(caps[0])
    assert len(p)==44160 and len(selected)==1200
    keys=['regime','panel','policy','model','k','cap']
    assert set(p.regime)=={'strict309','expanded441'} and p.model.nunique()==6
    assert p.policy.nunique()==4 and not p.log_lower.isna().any()
    assert p.campaign_id.nunique()==1
    seen=[];pred_keys=['dataset_id','seed','policy','k']
    cost_map={};selected_checks=[]
    for task in s['tasks']:
        did=task['dataset_id'];seed=task['seed']
        ranked=sorted(t[t.dataset_id.eq(did)].row_id,key=lambda rid:hashlib.sha256(
            f'v3-common-query|{seed}|{did}|{rid}'.encode()).hexdigest())
        nq=max(3,math.floor(.4*len(ranked)))
        assert task['query_ids']==ranked[:nq] and task['pool_ids']==ranked[nq:]
        assert not set(task['query_ids'])&set(task['pool_ids'])
        for policy in sorted(p.policy.unique()):
            seq=selected[(selected.dataset_id==did)&(selected.seed==seed)&(selected.policy==policy)].sort_values('k')
            assert len(seq)==max(task['ks']) and seq.row_id.is_unique
            assert seq.k.tolist()==list(range(1,len(seq)+1))
            assert set(seq.row_id)<=set(task['pool_ids'])
            chosen=[]
            for _,r in seq.iterrows():
                q=t.loc[r.row_id]
                life=float(q.N_failure_cycles if q.event else q.censor_lower_bound_cycles)
                lo=min(life,cap);hi=cap if q.event==0 else lo
                assert abs(r.cost_lower-lo)<=1e-6 and abs(r.cost_upper-hi)<=1e-6
                revealed_event=int(q.event==1 and life<=cap)
                assert r.revealed_event==revealed_event
                assert abs(r.revealed_log_life-math.log10(lo))<1e-12
                assert abs(r.stress_amplitude-q.stress_amplitude_mpa)<1e-9
                chosen.append(r.row_id)
                selected_checks.append((lo,hi,revealed_event))
            for k in task['ks']:
                ids=seq.row_id.tolist()[:k]
                source=t.loc[ids]
                lifetimes=np.where(source.event==1,source.N_failure_cycles,source.censor_lower_bound_cycles).astype(float)
                los=np.minimum(lifetimes,cap)
                his=np.where(source.event.to_numpy()==0,cap,los)
                nfail=int(np.sum((source.event.to_numpy()==1)&(lifetimes<=cap)))
                cost_map[(did,seed,policy,k)]=(sum(los),sum(his),nfail,
                    hashlib.sha256(json.dumps(ids).encode()).hexdigest())
                seen.append((did,seed,policy,k,len(task['query_ids'])))
    grouped=p.groupby(pred_keys,sort=False)
    assert len(grouped)==len(seen)
    for (did,seed,policy,k),d in grouped:
        task=next(x for x in s['tasks'] if x['dataset_id']==did and x['seed']==seed)
        assert len(d)==12*len(task['query_ids'])
        lo,hi,nfail,ids_sha=cost_map[(did,seed,policy,k)]
        assert np.allclose(d.support_cycles_lower,lo,rtol=0,atol=1e-6)
        assert np.allclose(d.support_cycles_upper,hi,rtol=0,atol=1e-6)
        assert (d.n_support_failure==nfail).all()
        assert (d.support_ids_sha256==ids_sha).all()
        for _,a in d.groupby(['regime','model']):
            assert set(a.row_id)==set(task['query_ids'])
            z=t.loc[a.row_id]
            assert np.array_equal(a.event,z.event) and np.allclose(a.log_life,z.log_life,rtol=0,atol=1e-12)
    for _,d in p[p.k.eq(0)].groupby(['regime','dataset_id','seed','model','row_id']):
        assert d.log_lower.nunique(dropna=False)==1
    # Absolute risk and utility: reconstruct directly from original query endpoints.
    a=p.copy();L=a.log_lower.to_numpy();y=a.log_life.to_numpy();e=a.event.to_numpy()
    f=np.isfinite(L)
    a['availability']=1.;a['finite_availability']=f.astype(float)
    a['positive_infinite']=np.isposinf(L).astype(float)
    a['known_risk']=((L>y)&(e==1)).astype(float)
    a['upper_risk']=(L>y).astype(float)
    a['finite_log_lower']=np.where(f,L,np.nan)
    a['failure_shortfall']=np.where((e==1)&f,np.maximum(y-L,0),np.nan)
    a['all_support_runout']=((a.k>0)&(a.n_support_failure==0)).astype(float)
    metrics=['availability','finite_availability','positive_infinite','known_risk','upper_risk',
        'finite_log_lower','failure_shortfall','support_cycles','all_support_runout']
    expected=balanced(a,keys,metrics)
    actual=pd.read_csv(folder/'all_regime_summary.csv').set_index(keys+['metric'])
    maximum=0.
    for idx,row in expected.iterrows():
        for name in metrics:
            got=actual.loc[tuple(idx)+(name,),'mean'];want=row[name]
            assert (math.isnan(got) and math.isnan(want)) or abs(got-want)<1e-9,(idx,name,got,want)
            if math.isfinite(got) and math.isfinite(want):maximum=max(maximum,abs(got-want))
    assert actual.n_campaigns.eq(1).all() and actual[['lo95','hi95']].isna().all().all()
    # Cost summaries from independently reconstructed cumulative bounds.
    bounds=balanced(a,keys,['support_cycles_lower','support_cycles_upper'])
    costs=pd.read_csv(folder/'policy_cost_savings_bounds.csv').set_index(keys)
    for idx,row in bounds.iterrows():
        random_idx=list(idx);random_idx[2]='random';baseline=bounds.loc[tuple(random_idx)]
        got=costs.loc[idx]
        assert abs(got.cost_lower-row.support_cycles_lower)<1e-6
        assert abs(got.cost_upper-row.support_cycles_upper)<1e-6
        if baseline.support_cycles_lower>0:
            lo=100*(1-row.support_cycles_upper/baseline.support_cycles_lower)
            hi=100*(1-row.support_cycles_lower/baseline.support_cycles_upper)
            assert abs(got.savings_percent_lower-lo)<1e-9 and abs(got.savings_percent_upper-hi)<1e-9
    if cap==5e6:assert np.allclose(p.support_cycles_lower,p.support_cycles_upper,rtol=0,atol=1e-6)
    # A/B pairing does not change candidate selection or query truth.
    pair=['panel','dataset_id','seed','row_id','policy','k','model','cap']
    aa=p[p.regime.eq('expanded441')].set_index(pair).sort_index()
    bb=p[p.regime.eq('strict309')].set_index(pair).sort_index()
    assert aa.index.equals(bb.index)
    for c in ['event','log_life','log_stress','support_ids_sha256','support_cycles_lower','support_cycles_upper']:
        assert np.array_equal(aa[c],bb[c]),c
    for regime in p.regime.unique():
        g=pd.read_csv(folder/regime/'success_gates.csv')
        assert (~g.gate_evaluable).all()
        assert g[['relative_success','absolute_reliability_supported','full_success']].isna().all().all()
    receipt=dict(status='PASS',cap=cap,predictions=len(p),selections=len(selected),
        tasks=len(s['tasks']),query_support_budget_groups=len(grouped),
        source_family_count=1,physical_independence_proven=False,
        source_truth_query_and_all_support_exposure_reconstructed=True,
        all_models_and_populations_share_supports=True,
        all_absolute_metric_cells_reconstructed=len(actual),maximum_absolute_metric_difference=maximum,
        cost_bounds_and_policy_savings_reconstructed=True,
        confidence_gates_explicitly_not_evaluable=True,
        input_hashes={x:sha(folder/x) for x in ['predictions.csv','selections.csv','all_regime_summary.csv','policy_cost_savings_bounds.csv']},
        audit_code_sha256=sha(__file__),
        limit='Arithmetic/source consistency; does not prove population validity or a second physical campaign.')
    (folder/'parent_independent_audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');args=p.parse_args();audit(args.folder)
