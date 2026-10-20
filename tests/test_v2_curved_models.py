"""Synthetic derivative, continuity and uncertainty checks for curvature."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from scipy.optimize._numdiff import approx_derivative
from scipy.stats import norm
from src.v2_curved_models import (CensoredCurvedBasquin,HierarchicalCurvedBasquin,
                                  _marginal_objective)


def frame(n=16):
    return pd.DataFrame({'log_stress':np.linspace(2.1,2.6,n),'load_ratio':np.full(n,.1),
                         'log_life':np.linspace(6,4,n),'event':np.tile([1,1,0,1],n//4),
                         'dataset_id':np.repeat(['a','b'],n//2),'group_id':np.repeat(['s','t'],n//2)})


def manual():
    h=HierarchicalCurvedBasquin(nodes=61)
    h.center_=np.array([2.35,.1]);h.knot_=2.35;h.ratio_median_=.1
    h.params_=np.array([5.,-2.,-6.,.1,np.log(.2),np.log(.7)])
    h.sigma_=.2;h.tau_=.7
    return h


def test_generic_hierarchical_objective_gradient_mixed_censoring():
    f=frame();h=manual();X=h.design(f);y=f.log_life.to_numpy();e=f.event.to_numpy()
    groups=[np.arange(8),np.arange(8,16)];weights=np.array([.5,.5]);p=h.params_
    value,analytic=_marginal_objective(p,X,y,e,groups,weights,.001,61)
    numeric=approx_derivative(lambda z:_marginal_objective(z,X,y,e,groups,weights,.001,61)[0],p).ravel()
    assert np.isfinite(value)
    np.testing.assert_allclose(analytic,numeric,rtol=3e-5,atol=2e-6)


def test_pooled_curved_objective_gradient():
    f=frame();h=manual();X=h.design(f);p=h.params_[:-1]
    w=np.ones(len(f))/len(f)
    pooled=CensoredCurvedBasquin()
    value,analytic=pooled._curved_objective(p,X,f.log_life.to_numpy(),f.event.to_numpy(),w)
    numeric=approx_derivative(lambda z:pooled._curved_objective(z,X,f.log_life.to_numpy(),f.event.to_numpy(),w)[0],p).ravel()
    assert np.isfinite(value)
    np.testing.assert_allclose(analytic,numeric,rtol=3e-5,atol=2e-6)


def test_continuous_negative_slopes_on_both_sides_of_knot_and_target_updates():
    h=manual();q=frame(16);q['log_stress']=np.r_[2.35-1e-8,2.35,2.35+1e-8,np.linspace(2.4,2.6,13)]
    mu=h.predict_location(q)
    assert abs(mu[0]-mu[1])<1e-7 and abs(mu[2]-mu[1])<1e-7
    assert np.all(np.diff(mu)<0)
    support=q.iloc[:3].copy();support['dataset_id']='new';support['event']=1
    support['log_life']=h.predict_location(support)+.4
    post=h.target_posterior(support)
    pred=h.predict_quantiles(q,support,alphas=(.1,.5))
    expected=mu+post['mean']+norm.ppf(.1)*np.sqrt(h.sigma_**2+post['variance'])
    np.testing.assert_allclose(pred[:,0],expected)
    assert np.all(np.diff(pred[:,0])<0)
    before=h.knot_;q['log_stress']+=10;h.predict_quantiles(q,support)
    assert h.knot_==before


def test_curved_population_fit_recovers_two_slopes_and_uses_training_knot():
    rng=np.random.default_rng(37);n=600
    f=frame(n);f['log_stress']=rng.uniform(2.1,2.6,n);t=f.log_stress-np.median(f.log_stress)
    truth=5.3-2*np.minimum(t,0)-6*np.maximum(t,0)+rng.normal(0,.17,n)
    f['event']=(truth<=5.7).astype(int);f['log_life']=np.minimum(truth,5.7)
    pooled=CensoredCurvedBasquin(l2=0).fit(f)
    assert pooled.fit_receipt_['success']
    assert pooled.knot_==np.median(f.log_stress)
    np.testing.assert_allclose(pooled.params_[1:3],[-2.,-6.],atol=.35)


def test_hierarchical_curved_fit_and_all_runout_prediction_finite():
    rng=np.random.default_rng(137);nc=16;nr=12;n=nc*nr
    f=frame(n);f['log_stress']=rng.uniform(2.1,2.6,n)
    f['dataset_id']=np.repeat([f'c{i}' for i in range(nc)],nr)
    f['group_id']=np.repeat([f's{i//2}' for i in range(nc)],nr)
    t=f.log_stress-2.35
    truth=(5.3-2*np.minimum(t,0)-6*np.maximum(t,0)
           +np.repeat(rng.normal(0,.5,nc),nr)+rng.normal(0,.17,n))
    f['event']=(truth<=5.9).astype(int);f['log_life']=np.minimum(truth,5.9)
    h=HierarchicalCurvedBasquin(l2=0,nodes=41).fit(f)
    assert h.fit_receipt_['success'] and np.all(h.params_[1:3]<0)
    assert .10<h.sigma_<.25 and .2<h.tau_<.9
    support=f.iloc[:3].copy();support['event']=0
    assert np.all(np.isfinite(h.predict_quantiles(f.iloc[3:8],support)))
