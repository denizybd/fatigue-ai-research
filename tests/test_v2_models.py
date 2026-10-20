"""Synthetic checks of censored random-intercept inference; no real data fits."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from scipy.integrate import quad
from scipy.optimize._numdiff import approx_derivative
from scipy.stats import norm
from v2_models import (CensoredBasquin,HierarchicalCensoredBasquin,
                       FixedSlopeShiftPredictor,intercept_posterior,_ll_parts)


def _frame(n=8):
    return pd.DataFrame({'log_stress':np.linspace(2.1,2.6,n),
                         'load_ratio':np.full(n,.1),'log_life':np.linspace(6,4,n),
                         'event':np.ones(n),'dataset_id':['c']*n,'group_id':['s']*n})


def _manual_hier(sigma=.2,tau=.7):
    h=HierarchicalCensoredBasquin(nodes=61)
    h.params_=np.array([5.,-4.,.2,np.log(sigma),np.log(tau)])
    h.sigma_=sigma;h.tau_=tau;h.center_=np.array([2.35,.1]);h.ratio_median_=.1
    return h


def test_all_failure_posterior_matches_normal_conjugacy_and_exact_marginal():
    mu=np.array([4.,5.,6.]);y=mu+np.array([.2,.5,.8]);s=.3;t=.7
    p=intercept_posterior(mu,y,np.ones(3),s,t)
    variance=1/(1/t**2+3/s**2)
    mean=variance*np.sum(y-mu)/s**2
    expected=quad(lambda u:np.prod(norm.pdf(y,mu+u,s))*norm.pdf(u,0,t),-8,8,
                  epsabs=1e-12)[0]
    np.testing.assert_allclose([p['mean'],p['variance']],[mean,variance],rtol=1e-12)
    np.testing.assert_allclose(np.exp(p['log_marginal']),expected,rtol=1e-10)


def test_mixed_posterior_matches_independent_adaptive_integration():
    mu=np.array([4.,5.,6.]);y=np.array([4.5,5.7,6.9]);e=np.array([1,0,0]);s=.2;t=1.
    p=intercept_posterior(mu,y,e,s,t,nodes=61)
    fun=lambda u:np.exp(_ll_parts(mu+u,s,y,e)[0].sum())*norm.pdf(u,0,t)
    mass=quad(fun,-10,10,epsabs=1e-13,epsrel=1e-10)[0]
    mean=quad(lambda u:u*fun(u),-10,10,epsabs=1e-13)[0]/mass
    np.testing.assert_allclose(np.exp(p['log_marginal']),mass,rtol=2e-8)
    np.testing.assert_allclose(p['mean'],mean,rtol=2e-8)


def test_all_runout_posterior_proper_and_higher_than_false_failure():
    mu=np.zeros(3);y=np.array([.3,.8,1.4])
    p=intercept_posterior(mu,y,np.zeros(3),.2,.7,nodes=61)
    false=intercept_posterior(mu,y,np.ones(3),.2,.7,nodes=61)
    assert np.isfinite(p['log_marginal']) and 0<p['variance']<.7**2
    assert p['mean']>false['mean']>0
    np.testing.assert_allclose(p['weight'].sum(),1,atol=1e-12)


def test_adaptive_nodes_stable_for_narrow_likelihood_far_from_prior_center():
    mu=np.zeros(20);y=np.full(20,2.);event=np.r_[np.ones(10),np.zeros(10)]
    a=intercept_posterior(mu,y,event,.02,2.,nodes=41)
    b=intercept_posterior(mu,y,event,.02,2.,nodes=81)
    np.testing.assert_allclose([a['mean'],a['variance'],a['log_marginal']],
                               [b['mean'],b['variance'],b['log_marginal']],rtol=1e-8,atol=1e-8)


def test_hierarchical_marginal_analytic_gradient():
    h=_manual_hier();f=_frame(8);X=np.column_stack((np.ones(8),
                         f[['log_stress','load_ratio']].to_numpy()-h.center_))
    y=np.array([5.7,5.9,5.3,5.5,4.8,4.9,4.1,4.3]);e=np.array([1,0,1,1,0,1,1,0])
    groups=[np.arange(4),np.arange(4,8)];weights=np.array([.5,.5]);p=h.params_
    val,analytic=h._hier_objective(p,X,y,e,groups,weights)
    numeric=approx_derivative(lambda z:h._hier_objective(z,X,y,e,groups,weights)[0],p).ravel()
    assert np.isfinite(val)
    np.testing.assert_allclose(analytic,numeric,rtol=3e-5,atol=2e-6)


def test_predictive_quantile_includes_posterior_uncertainty():
    h=_manual_hier();q=_frame();support=q.iloc[:3].copy()
    support['log_life']=h.predict_location(support)+.4
    raw=h.predict_quantiles(q,None,alphas=(.1,.5,.9))
    np.testing.assert_allclose(raw[:,0],h.predict_location(q)+norm.ppf(.1)*np.hypot(.2,.7))
    p=h.target_posterior(support);pred=h.predict_quantiles(q,support,alphas=(.1,.5,.9))
    expected=h.predict_location(q)+p['mean']+norm.ppf(.1)*np.sqrt(.2**2+p['variance'])
    np.testing.assert_allclose(pred[:,0],expected)
    assert np.all(np.diff(pred,axis=1)>0)
    assert np.all(np.diff(pred[:,0])<0)


def test_fixed_shift_records_unidentified_all_runout_no_fallback():
    h=_manual_hier();q=_frame();support=q.iloc[:3].copy();support['event']=0
    local=FixedSlopeShiftPredictor(h);pred=local.predict_quantiles(q,support)
    assert np.all(np.isnan(pred))
    assert local.last_prediction_receipt_['status']=='unidentified_all_runout'
    # Hierarchical proper prior remains well defined for the same supports.
    assert np.all(np.isfinite(h.predict_quantiles(q,support)))


def test_pooled_model_recovers_negative_slope_and_correct_scatter():
    rng=np.random.default_rng(19);n=700
    f=_frame(n);f['log_stress']=rng.uniform(2.1,2.6,n)
    truth=5.3-5*(f.log_stress-2.35)+rng.normal(0,.22,n)
    f['log_life']=np.minimum(truth,5.8);f['event']=(truth<=5.8).astype(int)
    p=CensoredBasquin(l2=0).fit(f)
    assert p.fit_receipt_['success']
    assert abs(p.params_[1]+5)<.15
    assert abs(p.sigma_-.22)<.025


def test_hierarchy_fit_recovers_between_condition_variability_synthetic():
    rng=np.random.default_rng(125);nc=20;nr=10;n=nc*nr
    f=_frame(n);f['dataset_id']=np.repeat([f'c{i}' for i in range(nc)],nr)
    f['group_id']=np.repeat([f's{i//2}' for i in range(nc)],nr)
    f['log_stress']=rng.uniform(2.1,2.6,n)
    shift=np.repeat(rng.normal(0,.55,nc),nr)
    latent=5.3-5*(f.log_stress-2.35)+shift+rng.normal(0,.18,n)
    f['log_life']=np.minimum(latent,6.);f['event']=(latent<=6.).astype(int)
    h=HierarchicalCensoredBasquin(l2=0,nodes=41).fit(f)
    assert h.fit_receipt_['success']
    assert abs(h.params_[1]+5)<.3
    assert abs(h.sigma_-.18)<.05
    assert .3<h.tau_<.9



def test_missing_ratio_uses_only_training_median_during_prediction():
    f=_frame(12);f['load_ratio']=np.r_[np.nan,np.nan,np.zeros(5),np.full(5,.2)]
    p=CensoredBasquin().fit(f)
    assert p.ratio_median_==.1 and p.fit_receipt_['ratio_missing_train']==2
    q=_frame(2);q['load_ratio']=[np.nan,999.]
    first=p.predict_location(q)[0]
    q['load_ratio']=[.1,-999.]
    assert p.predict_location(q)[0]==first
