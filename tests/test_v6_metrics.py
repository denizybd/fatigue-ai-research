from itertools import product
import numpy as np
import pandas as pd
import pytest
from src.v6_metrics import (risk_bounds,paired_risk_change_bounds,paired_cost_bounds,
    paired_ledger_cost_bounds,source_means,source_bootstrap)


def test_exact_paired_identification_matches_enumerated_admissible_futures():
    endpoint=6.;quantiles=[-np.inf,5.,6.,6.5,7.,np.inf]
    for a,b,e in product(quantiles,quantiles,[0,1]):
        future=np.array([endpoint]) if e else np.array([6.0000001,6.25,6.5,6.75,7.,8.,np.inf])
        outcomes=(future<a).astype(float)-(future<b).astype(float)
        low,high=paired_risk_change_bounds(a,b,endpoint,e)
        np.testing.assert_equal([low,high],[outcomes.min(),outcomes.max()])
        for q in (a,b):
            outcomes=(future<q).astype(float)
            np.testing.assert_equal(risk_bounds(q,endpoint,e),[outcomes.min(),outcomes.max()])
    assert paired_risk_change_bounds(np.nan,7,6,0)==(-1.,1.)
    assert risk_bounds(np.nan,6,0)==(0.,1.)


def test_paired_bounds_are_tighter_than_unpaired_when_both_incorrect_limits_agree():
    assert paired_risk_change_bounds(7.,7.,6.,0)==(0.,0.)
    lo,hi=risk_bounds(7.,6.,0)
    assert lo-hi==-1 and hi-lo==1


def test_cost_identification_ratios_and_zero_budget():
    x=paired_cost_bounds(3.,4.,5.,8.)
    assert x['change_lower']==-5 and x['change_upper']==-1
    assert x['ratio_lower']==3/8 and x['ratio_upper']==4/5
    assert x['savings_lower']==pytest.approx(.2) and x['savings_upper']==pytest.approx(.625)
    assert paired_cost_bounds(0,0,0,0)['ratio_upper']==1
    with pytest.raises(ValueError):paired_cost_bounds(2,1,1,2)


def test_source_weighting_does_not_count_query_multiplicity_as_more_sources():
    rows=[]
    for family,conditions in [('a',[1.,3.]),('b',[10.])]:
        for condition,value in enumerate(conditions):
            for seed in range(2):
                for query in range(1 if family=='a' else 20):
                    rows.append(dict(group_id=family,dataset_id=f'{family}{condition}',seed=seed,v=value+seed))
    d=pd.DataFrame(rows);m=source_means(d,'v')
    np.testing.assert_allclose(m.loc[['a','b']],[2.5,10.5])
    assert source_bootstrap(m)['mean']==6.5
    d.loc[0,'v']=np.nan
    assert np.isnan(source_means(d,'v',strict=True).loc['a'])
    assert np.isfinite(source_means(d,'v',strict=False).loc['a'])
    result=source_bootstrap([np.nan,1.,2.],strict=True)
    assert np.isnan(result['lo95']) and result['n_sources']==3 and result['n_finite_sources']==2


def test_shared_censor_cost_cancels_and_ratio_bounds_match_all_vertices():
    for shared,new_only,ref_only in product([(1.,10.),(5.,7.)],[(2.,4.),(8.,12.)],[(3.,7.),(1.,3.)]):
        new={'shared':shared,'new':new_only};ref={'shared':shared,'ref':ref_only}
        bounds=paired_ledger_cost_bounds(new,ref)
        corners=[((c+x)/(c+y),x-y) for c,x,y in product(shared,new_only,ref_only)]
        np.testing.assert_allclose([bounds['ratio_lower'],bounds['ratio_upper']],
            [min(x[0] for x in corners),max(x[0] for x in corners)])
        np.testing.assert_allclose([bounds['change_lower'],bounds['change_upper']],
            [min(x[1] for x in corners),max(x[1] for x in corners)])
    same={'a':(1,10),'b':(2,4)}
    bounds=paired_ledger_cost_bounds(same,same)
    assert bounds['ratio_lower']==bounds['ratio_upper']==1
    assert bounds['change_lower']==bounds['change_upper']==0
    assert paired_ledger_cost_bounds({}, {})['ratio_upper']==1
    with pytest.raises(ValueError):paired_ledger_cost_bounds({'a':(1,3)},{'a':(1,4)})
