"""Generated-data controls: equivalence with frozen defaults and proper scoring."""
import numpy as np
import pandas as pd
from scipy.stats import norm
from src.v2_models import HierarchicalCensoredBasquin, FixedSlopeShiftPredictor
from src.v3_design import LocalSlopeControl
from src.v6_controls import LocalSlopeAdapter,MatchedInterceptAdapter,reference_candidate,control_grid


def model():
    m=HierarchicalCensoredBasquin()
    m.params_=np.array([6.,-5.,.2,np.log(.3),np.log(.5)])
    m.sigma_=.3;m.tau_=.5;m.center_=np.array([2.3,-1.]);m.ratio_median_=-1.
    return m


def frames():
    q=pd.DataFrame(dict(row_id=['q0','q1'],dataset_id='target',log_stress=[2.1,2.5],load_ratio=-1.))
    s=pd.DataFrame(dict(row_id=['s0','s1','s2'],dataset_id='target',log_stress=[2.2,2.3,2.4],
        load_ratio=-1.,log_life=[6.8,6.4,5.9],event=[0,1,1]))
    return q,s


def test_default_local_adapter_reproduces_frozen_quantiles_with_mixed_censoring():
    m=model();q,s=frames()
    for support in (None,s):
        np.testing.assert_allclose(LocalSlopeAdapter(m).predict_quantiles(q,support,(.1,.5,.9)),
            LocalSlopeControl(m).predict_quantiles(q,support,(.1,.5,.9)),atol=2e-14)


def test_prior_width_changes_only_adapter_and_preserves_frozen_model():
    m=model();q,s=frames();original=m.params_.copy()
    narrow=reference_candidate({'hierarchical':m},'hierarchical',.25)
    wide=reference_candidate({'hierarchical':m},'hierarchical',4.)
    assert m.tau_==.5 and narrow.tau_==.125 and wide.tau_==2.
    np.testing.assert_array_equal(m.params_,original)
    assert np.all(wide.predict_quantiles(q)[:,0]<narrow.predict_quantiles(q)[:,0])
    small=LocalSlopeAdapter(m,.25).posterior(None)[1]
    large=LocalSlopeAdapter(m,4.).posterior(None)[1]
    np.testing.assert_allclose(large,small*256.)


def test_matched_intercept_default_and_all_runout_unavailability():
    m=model();q,s=frames();new=MatchedInterceptAdapter(m)
    np.testing.assert_allclose(new.predict_quantiles(q),m.predict_quantiles(q))
    np.testing.assert_allclose(new.predict_quantiles(q,s),FixedSlopeShiftPredictor(m).predict_quantiles(q,s))
    s['event']=0
    assert np.isnan(new.predict_quantiles(q,s)).all()
    assert new.last_prediction_receipt_['status']=='unidentified_all_runout'


def test_density_and_survival_scores_are_consistent_with_predictive_normal():
    m=model();q,s=frames()
    for adapter in (LocalSlopeAdapter(m,.5),MatchedInterceptAdapter(m)):
        mu,sd=adapter.moments(q,s)
        q['log_life']=mu+sd*.7;q['event']=[1,0]
        expected=np.array([norm.logpdf(.7)-np.log(sd[0]),norm.logsf(.7)])
        np.testing.assert_allclose(adapter.predict_log_score(q,s),expected,atol=2e-14)
        np.testing.assert_allclose(adapter.predict_cdf(q.log_life,q,s),norm.cdf(.7),atol=2e-14)


def test_control_grid_has_no_fictitious_prior_for_flat_matched_control():
    grid=control_grid()
    assert len(grid)==22 and len({c['candidate_id'] for c in grid})==22
    assert len([c for c in grid if c['kind']=='matched_intercept'])==1
