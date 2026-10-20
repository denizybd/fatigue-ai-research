"""Independent enumeration/arithmetic oracles; generated numbers only."""
from itertools import product
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.v6_metrics import risk_bounds,paired_risk_change_bounds,paired_cost_bounds
from src.v6_metrics import paired_ledger_cost_bounds,source_means,source_bootstrap


def main():
    qvalues=[-np.inf,-5.,0.,1.,3.,4.,6.,np.inf]
    pairs=0;single=0
    for endpoint,a,b,event in product([-3.,0.,3.],qvalues,qvalues,[0,1]):
        if event:
            futures=np.asarray([endpoint])
        else:
            cuts=sorted({endpoint,*[q for q in [a,b] if np.isfinite(q) and q>endpoint]})
            futures=[np.nextafter(endpoint,np.inf),np.inf]
            for i,c in enumerate(cuts):
                if c>endpoint:futures.extend([c,np.nextafter(c,np.inf)])
                if i+1<len(cuts):futures.append((c+cuts[i+1])/2)
            futures=np.asarray(futures)
        loss_a=(futures<a).astype(float);loss_b=(futures<b).astype(float)
        change=loss_a-loss_b
        np.testing.assert_array_equal(paired_risk_change_bounds(a,b,endpoint,event),
            [change.min(),change.max()]);pairs+=1
        for q,loss in [(a,loss_a),(b,loss_b)]:
            np.testing.assert_array_equal(risk_bounds(q,endpoint,event),[loss.min(),loss.max()]);single+=1
    for endpoint,event in product([-3.,0.,3.],[0,1]):
        np.testing.assert_array_equal(risk_bounds(np.nan,endpoint,event),[0.,1.])
        np.testing.assert_array_equal(paired_risk_change_bounds(np.nan,3.,endpoint,event),[-1.,1.])
    # Independently enumerate all common/exclusive per-specimen interval corners.
    rng=np.random.default_rng(719)
    max_cost_error=0.;cost_cases=0
    for n_common,n_new,n_ref in product(range(3),range(3),range(3)):
        keys=[f'g{i}' for i in range(n_common+n_new+n_ref)]
        for repetition in range(4):
            lower=rng.uniform(.1,100.,len(keys));upper=lower+rng.uniform(0,100.,len(keys))
            bounds={k:(float(a),float(b)) for k,a,b in zip(keys,lower,upper)}
            newkeys=keys[:n_common+n_new]
            refkeys=keys[:n_common]+keys[n_common+n_new:]
            candidates=[];changes=[]
            for bits in product([0,1],repeat=len(keys)):
                actual={k:bounds[k][bit] for k,bit in zip(keys,bits)}
                new=sum(actual[k] for k in newkeys);ref=sum(actual[k] for k in refkeys)
                candidates.append(new/ref if ref else (1. if new==0 else np.inf));changes.append(new-ref)
            got=paired_ledger_cost_bounds({k:bounds[k] for k in newkeys},{k:bounds[k] for k in refkeys})
            expected=[min(changes),max(changes),min(candidates),max(candidates)]
            actual=[got[k] for k in ['change_lower','change_upper','ratio_lower','ratio_upper']]
            np.testing.assert_allclose(actual,expected,rtol=2e-14,atol=2e-13)
            finite=np.isfinite(actual)&np.isfinite(expected)
            error=np.abs(np.asarray(actual)[finite]-np.asarray(expected)[finite])
            max_cost_error=max(max_cost_error,float(np.max(error[np.isfinite(error)],initial=0)))
            cost_cases+=1
    assert paired_ledger_cost_bounds({'same':(1.,100.)},{'same':(1.,100.)})['ratio_upper']==1.
    assert paired_ledger_cost_bounds({'same':(1.,100.)},{'same':(1.,100.)})['change_upper']==0.
    for _ in range(100):
        a,b=rng.uniform(.1,10.,2);A,B=np.asarray([a,b])+rng.uniform(0,10.,2)
        x=paired_cost_bounds(a,A,b,B)
        ratios=[c/d for c,d in product([a,A],[b,B])]
        np.testing.assert_allclose([x['ratio_lower'],x['ratio_upper']],[min(ratios),max(ratios)],atol=0,rtol=0)
    # Loop-based weighting oracle: unequal conditions, seeds and query counts.
    rows=[];oracle={}
    for f,nconditions in [('a',1),('b',2),('c',4)]:
        conditions=[]
        for condition in range(nconditions):
            seeds=[]
            for seed in range(1+condition):
                values=rng.normal(size=1+condition+seed*2)
                seeds.append(float(sum(values)/len(values)))
                for query,value in enumerate(values):rows.append(dict(group_id=f,dataset_id=f+str(condition),seed=seed,v=value))
            conditions.append(sum(seeds)/len(seeds))
        oracle[f]=sum(conditions)/len(conditions)
    frame=pd.DataFrame(rows);means=source_means(frame,'v',strict=True)
    np.testing.assert_allclose(means.loc[list(oracle)],list(oracle.values()),rtol=0,atol=1e-15)
    # An explicit missing value propagates under strict weighting.
    frame.loc[frame.group_id.eq('b').idxmax(),'v']=np.nan
    assert np.isnan(source_means(frame,'v',strict=True).loc['b'])
    x=np.asarray(list(oracle.values()))
    got=source_bootstrap(x)
    boot_rng=np.random.default_rng(231)
    boot=[]
    for ids in boot_rng.integers(0,len(x),(2000,len(x))):boot.append(sum(float(x[j]) for j in ids)/len(x))
    np.testing.assert_allclose([got['lo95'],got['hi95']],np.quantile(boot,[.025,.975]),atol=1e-15,rtol=0)
    assert source_bootstrap(x)==source_bootstrap(x)
    assert np.isnan(source_bootstrap([1.,np.nan,3.])['lo95'])
    assert np.isnan(source_bootstrap([1.])['lo95'])
    receipt=dict(status='PASS',single_risk_checks=single,paired_same_Y_risk_checks=pairs,
        missing_quantile_worst_case_convention=True,joint_shared_cost_corner_cases=cost_cases,
        max_joint_cost_corner_error=max_cost_error,rectangular_cost_corner_cases=100,
        identical_shared_censored_support_exact_ratio_one=True,
        independent_query_seed_condition_family_weighting=True,
        independent_source_bootstrap_2000_seed231=True,strict_missing_source_interval_suppressed=True,
        physical_validation=False,actual_fatigue_fits=0,
        metrics_source_sha256=hashlib.sha256((ROOT/'src/v6_metrics.py').read_bytes()).hexdigest())
    (ROOT/'literature/v6_ml/metrics_independent_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
