"""Synthetic algebra/integration checks only; no fatigue campaign is fitted."""
import copy

import numpy as np
import pandas as pd
import pytest
from numpy.polynomial.hermite import hermgauss
from scipy.special import logsumexp, ndtr

from src.v3_rfl import NormalNormalRFL
from src.v6_rfl_adapter import JointRFLTargetAdapter, proposed_joint_rfl_prior_grid


def population(nodes=96):
    p=NormalNormalRFL(nodes=nodes)
    p.params_=np.array([5.,-3.,-.2,np.log(.4),2.,np.log(.12)])
    p.log_stress_ref_=2.2;p.ratio_center_=.1;p.ratio_median_=.1
    p.sigma_=.4;p.tau_gamma_=.12;p._fallback=None
    return p


def frame(stress,ids=None,y=None,event=None,condition='synthetic_target'):
    n=len(stress)
    return pd.DataFrame(dict(row_id=ids or [f'q{i}' for i in range(n)],dataset_id=condition,
        log_stress=np.log10(stress),load_ratio=.1,
        log_life=np.zeros(n) if y is None else y,
        event=np.ones(n,int) if event is None else event))


def supports():
    return frame([170.,200.,240.],['s0','s1','s2'],[6.,5.5,5.2],[0,1,1])


def independent_hermite(pop,su,sv,support,query,at,order=64):
    """Independent product-prior Hermite integral, not adapter's nested rule."""
    x,w=hermgauss(order);w=w/np.sqrt(np.pi)
    u=x*np.sqrt(2)*su if su else np.array([0.])
    wu=w if su else np.array([1.])
    v=x*np.sqrt(2)*sv if sv else np.array([0.])
    wv=w if sv else np.array([1.])
    logj=[];cdf=[];score=[];mass=[]
    for value,weight in zip(v,wv):
        p=copy.copy(pop);p.params_=pop.params_.copy();p.params_[4]+=value
        if support is not None and len(support):
            kernel=p._kernel(p._x(support))
            pdf,sf=p._logparts(kernel,support.log_life.to_numpy(),u)
            ll=np.where(support.event.to_numpy()[:,None]==1,pdf,sf).sum(axis=0)
        else:ll=np.zeros(len(u))
        logj.append(ll+np.log(wu)+np.log(weight))
        k=p._kernel(p._x(query));mass.append(np.exp(k['logmass']))
        z=(np.asarray(at)[:,None,None]-k['mu'][:,None,:]-u[None,:,None])/k['sigma']
        cdf.append(np.exp(k['logmass'])[:,None]*np.sum(pop._w*ndtr(z),axis=2))
        pdf,sf=p._logparts(k,query.log_life.to_numpy(),u)
        score.append(np.where(query.event.to_numpy()[:,None]==1,pdf,sf))
    logj=np.asarray(logj);lm=logsumexp(logj);weight=np.exp(logj-lm)
    return dict(log_marginal=float(lm),
        u_mean=float(np.sum(weight*u[None,:])),v_mean=float(np.sum(weight*v[:,None])),
        cdf=np.sum(np.asarray(cdf)*weight[:,None,:],axis=(0,2)),
        finite_mass=np.sum(np.asarray(mass)*weight.sum(axis=1)[:,None],axis=0),
        log_score=logsumexp(np.asarray(score)+logj[:,None,:],axis=(0,2))-lm)


def test_cold_gaussian_convolution_and_literal_infinite_mass():
    p=population();a=JointRFLTargetAdapter(p,.3,.1)
    q=frame([60.,120.,220.]);at=np.array([8.,6.,5.])
    ref=independent_hermite(p,.3,.1,None,q,at,80)
    assert np.max(np.abs(a.predict_cdf(at,q)-ref['cdf']))<3e-6
    assert np.max(np.abs(a.failure_probability(q)-ref['finite_mass']))<1e-12
    assert np.isposinf(a.predict_quantiles(q)[0,0])
    assert np.array_equal(a.predict_cdf(np.inf,q),np.ones(3))
    assert np.array_equal(a.predict_cdf(-np.inf,q),np.zeros(3))
    assert np.max(np.abs(a.predict_cdf(1000.,q)-a.failure_probability(q)))<1e-12
    assert a.last_prediction_receipt_['k0_analytic_convolution']


@pytest.mark.parametrize('su',[0.,.3])
def test_zero_v_exactly_reduces_to_original_scalar_adapter(su):
    p=population();p.shift_prior_sd=su
    a=JointRFLTargetAdapter(p,su,0.)
    q=frame([120.,220.]);s=supports()
    assert np.array_equal(a.predict_quantiles(q,s),p.predict_quantiles(q,s))
    assert np.array_equal(a.predict_cdf([6.,5.],q,s),p.predict_cdf([6.,5.],q,s))
    assert np.array_equal(a.predict_log_score(q,s),p.predict_log_score(q,s))
    assert a.last_prediction_receipt_['scalar_reduction']


def test_joint_posterior_matches_independent_product_hermite_integral():
    p=population();q=frame([120.,220.],y=[6.4,5.],event=[0,1]);s=supports()
    a=JointRFLTargetAdapter(p,.3,.05)
    at=np.array([6.5,5.]);actual=a.predict_cdf(at,q,s)
    receipt=a.last_prediction_receipt_.copy()
    ref=independent_hermite(p,.3,.05,s,q,at,80)
    assert np.max(np.abs(actual-ref['cdf']))<3e-6
    assert np.max(np.abs(a.predict_log_score(q,s)-ref['log_score']))<1e-5
    score_receipt=a.last_prediction_receipt_
    assert score_receipt['query_outcomes_used_only_for_numeric_likelihood_evaluation']
    assert not score_receipt['query_outcomes_used_for_fit_or_support_cache']
    assert not score_receipt['numerator_integrals_cached']
    assert abs(receipt['support_log_marginal']-ref['log_marginal'])<3e-6
    assert abs(receipt['posterior_u_mean']-ref['u_mean'])<3e-6
    assert abs(receipt['posterior_v_mean']-ref['v_mean'])<3e-6
    assert receipt['tail_mass_bound_v']<1e-10
    assert receipt['conditional_u_tail_bound_weighted']<1e-10
    assert receipt['max_quantile_log10_resolution_difference']<2e-4
    assert not receipt['query_outcomes_used_for_resolution']
    assert not receipt['target_posterior_is_Laplace']


def test_predictive_quantile_inverts_full_mixture_not_component_quantiles():
    p=population();q=frame([120.,220.]);s=supports()
    a=JointRFLTargetAdapter(p,.3,.1)
    values=a.predict_quantiles(q,s,(.1,.5))
    for j,alpha in enumerate([.1,.5]):
        assert np.max(np.abs(a.predict_cdf(values[:,j],q,s)-alpha))<3e-7
    assert np.all(values[:,0]<values[:,1])


def test_runout_shifts_fatigue_limit_even_with_life_prior_zero():
    p=population();q=frame([100.,150.]);s=frame([90.,95.],['s0','s1'],[7.,7.],[0,0])
    a=JointRFLTargetAdapter(p,0.,.1)
    before=a.failure_probability(q)
    after=a.failure_probability(q,s)
    assert a.last_prediction_receipt_['posterior_v_mean']>0.
    assert a.last_prediction_receipt_['posterior_u_mean']==0.
    assert np.all(after<before)
    ref=independent_hermite(p,0.,.1,s,q,np.array([7.,7.]),80)
    assert np.max(np.abs(after-ref['finite_mass']))<3e-6
    assert abs(a.last_prediction_receipt_['support_log_marginal']-ref['log_marginal'])<3e-6


def test_query_outcomes_never_enter_prediction_and_population_unchanged():
    p=population();before=p.params_.copy();s=supports();q=frame([120.,220.])
    a=JointRFLTargetAdapter(p,.3,.05)
    result=a.predict_quantiles(q,s)
    changed=q.copy();changed.log_life=[-100.,100.];changed.event=[1,0]
    assert np.array_equal(result,a.predict_quantiles(changed,s))
    assert np.array_equal(result,a.predict_quantiles(q,s.iloc[::-1]))
    assert np.array_equal(p.params_,before)
    assert p.shift_prior_sd==0.
    assert len(a._support_cache)==1


def test_revealing_runout_is_different_from_declaring_failure_at_stop():
    p=population();s=frame([120.],['s0'],[7.],[0]);q=frame([130.])
    a=JointRFLTargetAdapter(p,.2,.1)
    runout=a.predict_quantiles(q,s)[0,0]
    failure=s.copy();failure.event=1
    failed=a.predict_quantiles(q,failure)[0,0]
    assert runout>failed


def test_2d_adapter_changes_finite_life_mass_after_selected_support():
    p=population();a=JointRFLTargetAdapter(p,.1,.15)
    q=frame([60.]);s=frame([90.,95.],['s0','s1'],[7.,7.],[0,0])
    initial=a.failure_probability(q)[0]
    updated=a.failure_probability(q,s)[0]
    assert updated<initial
    assert np.isposinf(a.predict_quantiles(q,s)[0,0])
    assert a.predict_cdf(np.inf,q,s)[0]==1.


@pytest.mark.parametrize('su,sv',[(-.1,.1),(.1,-.1),(np.nan,.1)])
def test_invalid_priors_rejected(su,sv):
    with pytest.raises(ValueError):JointRFLTargetAdapter(population(),su,sv)


@pytest.mark.parametrize('kwargs',[dict(tail_tolerance=np.nan),dict(cdf_tolerance=np.inf),dict(evidence_tolerance=0.)])
def test_invalid_numerical_tolerances_rejected(kwargs):
    with pytest.raises(ValueError):JointRFLTargetAdapter(population(),.3,.1,**kwargs)


def test_identity_overlap_and_nonphysical_fallback_rejected():
    p=population();a=JointRFLTargetAdapter(p,.3,.05);s=supports()
    with pytest.raises(ValueError):a.predict_quantiles(s,s)
    p._fallback=object()
    with pytest.raises(ValueError):JointRFLTargetAdapter(p,.3,.05)


def test_grid_is_ten_source_supplied_prior_combinations():
    grid=proposed_joint_rfl_prior_grid(.4)
    assert len(grid)==10
    assert sorted(set(x['life_prior_sd'] for x in grid))==[.1,.2,.4,.8,1.6]
    assert sorted(set(x['fatigue_limit_prior_sd'] for x in grid))==[.05,.15]


@pytest.mark.parametrize('events',[[0,1,1],[1,1,1],[0,0,0]])
def test_global_pruning_preserves_conditional_u_marginal(events):
    p=population();s=supports();s.event=events
    a=JointRFLTargetAdapter(p,.3,.1);shifted=a._at_v(.05)
    expected=shifted._posterior_uncached(s)
    actual=a._conditional_u(shifted,s)
    assert abs(actual['log_marginal']-expected['log_marginal'])<3e-6
    assert abs(actual['mean']-expected['mean'])<3e-6
    assert abs(actual['variance']-expected['variance'])<3e-6
    assert actual['tail_mass_bound']<1e-10
    assert actual['u_intervals_evaluated']<=actual['u_intervals_total']


def test_quadrature_limit_fails_explicitly_instead_of_returning_an_untested_mode():
    a=JointRFLTargetAdapter(population(),.3,.15,max_v_nodes=32)
    with pytest.raises(FloatingPointError):a.predict_quantiles(frame([120.]),supports())


def test_event_specific_likelihood_equals_frozen_both_branch_likelihood():
    p=population();a=JointRFLTargetAdapter(p,.3,.1);s=supports()
    k=p._kernel(p._x(s));u=np.array([-3.,-.2,0.,.4,4.])
    pdf,sf=p._logparts(k,s.log_life.to_numpy(),u)
    expected=np.where(s.event.to_numpy()[:,None]==1,pdf,sf)
    actual=a._observation_loglikelihood(k,s.log_life.to_numpy(),s.event.to_numpy(),u)
    assert np.max(np.abs(actual-expected))<2e-12


def test_fast_score_and_far_tail_evidence_fallback_are_same_predictive_model():
    p=population();p.params_[4]=-12.
    q=frame([160.,220.],y=[5.5,14.],event=[1,1]);s=supports()
    a=JointRFLTargetAdapter(p,.3,.05)
    score=a.predict_log_score(q,s);receipt=a.last_prediction_receipt_.copy()
    exact_numeric=a._predict_log_score_evidence_ratio(q,s)
    assert np.max(np.abs(score-exact_numeric))<2e-5
    assert 1 in receipt['evidence_ratio_fallback_rows']
    assert len(a._support_cache)==1
    assert not receipt['query_outcomes_used_for_fit_or_support_cache']
