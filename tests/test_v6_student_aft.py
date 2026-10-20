"""Synthetic mathematical checks only; no real fatigue data are loaded/fitted."""
import numpy as np
import pandas as pd
import pytest
from scipy.integrate import quad
from scipy.optimize._numdiff import approx_derivative
from scipy.special import expit
from scipy.stats import multivariate_normal, norm, t

from src.v6_student_aft import (CensoredStudentAFT, StudentAFTConfig,
    censored_t_parts, intercept_posterior, student_aft_grid)


def frame(s=(-1.,0.,1.), y=None, event=None, condition='target'):
    d=pd.DataFrame(dict(log_stress=2.3+.15*np.asarray(s),load_ratio=-1.,
                        dataset_id=condition,group_id='synthetic',
                        row_id=[f'{condition}_{i}' for i in range(len(s))]))
    if y is not None:
        d['log_life']=y
        d['event']=np.ones(len(s)) if event is None else event
    return d


def configured(nu=4, tau=.3, scatter='constant', mean='linear', scale=.25):
    """Known population parameters, not a fit to any data."""
    m=CensoredStudentAFT(StudentAFTConfig(nu,scatter,mean,tau))
    m.stress_center_,m.stress_sd_=2.3,.15
    m.ratio_median_,m.ratio_center_=-1.,-1.
    m.knots_=np.array([-.4,.4]) if mean=='two_knots' else np.array([])
    slopes=np.array([.45]) if mean=='linear' else np.array([.2,.6,.35])
    m.params_=np.r_[5.8,np.log(np.expm1(slopes)),.1,np.log(scale)]
    if scatter=='loglinear':m.params_=np.r_[m.params_,.2]
    return m


@pytest.mark.parametrize('nu',[4,10,np.inf])
def test_density_survival_and_gradients_match_independent_distributions(nu):
    mu=np.array([5.,5.5,6.,6.5]);sigma=np.array([.2,.5,.3,.7])
    y=np.array([5.2,6.1,5.1,8.]);event=np.array([1,0,1,0])
    ll,dm,ds=censored_t_parts(mu,sigma,y,event,nu)
    law=norm if np.isinf(nu) else t(nu)
    expected=np.where(event==1,law.logpdf((y-mu)/sigma)-np.log(sigma),law.logsf((y-mu)/sigma))
    np.testing.assert_allclose(ll,expected,atol=3e-14)
    eps=1e-5
    numeric_mu=(censored_t_parts(mu+eps,sigma,y,event,nu)[0]-
                censored_t_parts(mu-eps,sigma,y,event,nu)[0])/(2*eps)
    numeric_scale=(censored_t_parts(mu,sigma*np.exp(eps),y,event,nu)[0]-
                   censored_t_parts(mu,sigma*np.exp(-eps),y,event,nu)[0])/(2*eps)
    np.testing.assert_allclose(dm,numeric_mu,rtol=2e-8,atol=2e-8)
    np.testing.assert_allclose(ds,numeric_scale,rtol=2e-8,atol=2e-8)


def test_student_survival_extreme_tail_stays_finite():
    ll,dm,ds=censored_t_parts(0.,1.,1e50,0,10)
    assert np.isfinite(ll) and ll < -1000
    assert np.isfinite(dm) and dm>0
    assert abs(ds-10)<1e-10
    # This underflows as a probability, but not as a log likelihood.
    assert np.exp(ll)==0


@pytest.mark.parametrize('tau',[.1,.3,1.,3.])
def test_gaussian_failure_posterior_matches_exact_multivariate_density(tau):
    mu=np.array([5.,5.5,6.]);sigma=np.array([.1,.35,.7])
    y=np.array([5.3,5.7,6.8]);event=np.ones(3)
    p=intercept_posterior(mu,sigma,y,event,np.inf,tau)
    v=1/(1/tau**2+np.sum(1/sigma**2))
    mean=v*np.sum((y-mu)/sigma**2)
    lm=multivariate_normal.logpdf(y-mu,cov=np.diag(sigma**2)+tau**2*np.ones((3,3)))
    np.testing.assert_allclose([p['mean'],p['variance'],p['log_marginal']],
                               [mean,v,lm],atol=2e-10)
    assert p['tail_mass_bound']<2e-8
    assert p['quadrature_relative_error']<2e-8


@pytest.mark.parametrize('nu',[4,10])
@pytest.mark.parametrize('event',[[1,1,1],[0,0,0],[1,0,1]])
def test_student_posterior_matches_independent_direct_quad(nu,event):
    mu=np.array([5.3,5.5,5.9]);sigma=np.array([.2,.3,.4]);y=np.array([5.8,6.,6.1])
    p=intercept_posterior(mu,sigma,y,event,nu,.7)
    def integrand(u,power=0):
        z=(y-mu-u)/sigma
        likelihood=np.prod(np.where(np.asarray(event)==1,t.pdf(z,nu)/sigma,t.sf(z,nu)))
        return likelihood*norm.pdf(u,scale=.7)*u**power
    integral=[quad(lambda u:integrand(u,k),-12,12,epsabs=1e-11,limit=250)[0] for k in range(3)]
    mean=integral[1]/integral[0];var=integral[2]/integral[0]-mean**2
    np.testing.assert_allclose([p['log_marginal'],p['mean'],p['variance']],
                               [np.log(integral[0]),mean,var],atol=2e-9)
    assert p['proper_prior'] and np.isclose(p['weight'].sum(),1)
    if not any(event):
        assert p['mean']>0 and p['log_marginal']<0


def test_separated_heavy_tail_posterior_modes_are_not_laplace_collapsed():
    # With a narrow residual scale and one observation on either side, a t
    # posterior has two separated peaks; one Gaussian around a mode fails.
    mu=np.zeros(2);sigma=np.repeat(.05,2);y=np.array([-2.,2.]);event=np.ones(2)
    p=intercept_posterior(mu,sigma,y,event,4,3.)
    def f(u,k=0):
        return np.prod(t.pdf((y-u)/sigma,4)/sigma)*norm.pdf(u,scale=3.)*u**k
    z=quad(f,-30,30,points=[-2,0,2],epsabs=1e-13,limit=400)[0]
    second=quad(lambda u:f(u,2),-30,30,points=[-2,0,2],epsabs=1e-13,limit=400)[0]/z
    assert abs(p['mean'])<1e-10
    np.testing.assert_allclose([p['log_marginal'],p['variance']],[np.log(z),second],atol=3e-8)
    assert p['variance']>3 and np.sum(p['weight'][p['u']<0])>.49


@pytest.mark.parametrize('tau',[.1,3.])
def test_empty_support_prior_is_proper_and_wide_prior_predictive_is_resolved(tau):
    p=intercept_posterior([],[],[],[],4,tau)
    np.testing.assert_allclose([p['mean'],p['variance'],p['log_marginal']],[0,tau*tau,0])
    m=configured(np.inf,tau,scale=.05)
    q=frame((-1.,0.,1.))
    mu=m._evaluate(q)[0]
    levels=np.array([.01,.1,.5,.9,.99])
    predicted=m.predict_quantiles(q,alphas=levels)
    expected=mu[:,None]+np.hypot(.05,tau)*norm.ppf(levels)[None,:]
    np.testing.assert_allclose(predicted,expected,atol=3e-8)
    assert m.last_prediction_receipt_['query_outcomes_read'] is False


@pytest.mark.parametrize('nu',[4,10,np.inf])
def test_quantile_inversion_pdf_derivative_and_censor_score(nu):
    m=configured(nu,1.,scatter='loglinear',mean='two_knots')
    q=frame((-2.,-.5,.5,2.))
    s=frame((-.8,.8),y=[6.4,5.7],event=[0,1])
    levels=[.01,.1,.5,.9]
    quantiles=m.predict_quantiles(q,s,levels)
    for j,level in enumerate(levels):
        np.testing.assert_allclose(m.predict_cdf(quantiles[:,j],q,s),level,atol=4e-10)
    np.testing.assert_array_equal(m.predict_cdf(np.inf,q,s),np.ones(len(q)))
    np.testing.assert_array_equal(m.predict_cdf(-np.inf,q,s),np.zeros(len(q)))
    q['log_life']=quantiles[:,1];q['event']=1
    eps=1e-5
    derivative=(m.predict_cdf(q.log_life+eps,q,s)-m.predict_cdf(q.log_life-eps,q,s))/(2*eps)
    np.testing.assert_allclose(np.exp(m.predict_log_score(q,s)),derivative,rtol=3e-7)
    q['event']=0
    np.testing.assert_allclose(np.exp(m.predict_log_score(q,s)),1-m.predict_cdf(q.log_life,q,s),atol=3e-14)


def test_student_no_support_predictive_matches_direct_normal_convolution():
    m=configured(4,3.,scale=.05);q=frame((0.,))
    for y in [2.5,5.8,7.4]:
        expected=quad(lambda u:t.cdf((y-5.8-u)/.05,4)*norm.pdf(u,scale=3.),
                      -30,30,points=[y-5.8],epsabs=1e-11,limit=300)[0]
        np.testing.assert_allclose(m.predict_cdf(y,q),expected,atol=2e-9)


def test_gaussian_selected_failures_predictive_includes_natural_and_posterior_variance():
    m=configured(np.inf,.3,scale=.25);q=frame((0.,))
    s=frame((0.,0.),y=[6.2,6.4])
    variance=1/(1/.3**2+2/.25**2)
    shift=variance*((6.2-5.8)+(6.4-5.8))/.25**2
    expected=5.8+shift+norm.ppf(.1)*np.sqrt(.25**2+variance)
    np.testing.assert_allclose(m.predict_quantiles(q,s)[0,0],expected,atol=2e-9)
    # Plugging in the posterior mean and dropping its variance is overconfident.
    plug_in=5.8+shift+norm.ppf(.1)*.25
    assert expected<plug_in-.02


def test_query_outcomes_do_not_affect_predictions_and_support_changes_do():
    m=configured(4,1.)
    q=frame((-1.,1.),y=[-100.,100.],event=[0,1]);s=frame((0.,),y=[6.5],event=[0])
    predicted=m.predict_quantiles(q,s)
    q['log_life']=np.nan;q['event']=np.nan
    np.testing.assert_array_equal(m.predict_quantiles(q,s),predicted)
    p=m.support_posterior(s)
    assert m.support_posterior(s.copy()) is p
    s.loc[0,'log_life']=7.
    assert m.support_posterior(s)['mean']>p['mean']
    assert not np.array_equal(m.predict_quantiles(q,s),predicted)


def test_monotone_piecewise_mean_and_explicit_heteroscedasticity():
    m=configured(4,.3,scatter='loglinear',mean='two_knots')
    q=frame(np.linspace(-4,4,100))
    mu,sigma,_,_=m._evaluate(q)
    assert np.all(np.diff(mu)<0) and np.all(np.diff(sigma)>0)
    # Scatter can make a lower quantile nonmonotone. No full predictive
    # monotonicity guarantee is asserted for a heteroscedastic location model.
    assert len(m.knots_)==2


def test_population_objective_analytic_gradient_matches_finite_difference():
    m=configured(4,.3,scatter='loglinear',mean='two_knots')
    d=frame((-1.,-.6,-.1,.3,.7,1.2),y=[6.5,6.3,6.2,5.8,5.9,5.2],event=[0,1,1,0,1,1])
    ix=[np.arange(3),np.arange(3,6)]
    value,gradient=m._objective(m.params_,d,ix)
    numeric=approx_derivative(lambda p:m._objective(p,d,ix)[0],m.params_,method='3-point').reshape(-1)
    np.testing.assert_allclose(gradient,numeric,rtol=2e-5,atol=2e-5)
    assert np.isfinite(value)


def test_synthetic_training_emits_multistart_and_train_only_receipts():
    rng=np.random.default_rng(7702)
    n_conditions=4;n_per=12
    stress=np.tile(np.linspace(-1.7,1.7,n_per),n_conditions)
    condition=np.repeat(np.arange(n_conditions),n_per)
    y=6.-.5*stress+np.repeat([-.25,.15,-.1,.3],n_per)+rng.standard_t(4,len(stress))*.15
    event=(y<6.5).astype(int)
    d=frame(stress,y=np.minimum(y,6.5),event=event)
    d['dataset_id']=[f'synthetic{i}' for i in condition]
    d['row_id']=[f'synthetic_{i}' for i in range(len(d))]
    m=CensoredStudentAFT(StudentAFTConfig(4,'loglinear','two_knots',.3),max_iter=180).fit(d)
    r=m.fit_receipt_
    assert r['success'] and len(r['starts'])==2
    assert r['training_rows']==48 and r['training_conditions']==4
    assert r['target_slope_or_scatter_updated'] is False
    assert r['population_parameter_uncertainty_integrated'] is False
    assert r['max_tail_mass_bound']<2e-8 and r['max_quadrature_relative_error']<2e-8
    np.testing.assert_allclose(m.knots_,np.quantile((d.log_stress-d.log_stress.mean())/d.log_stress.std(ddof=0),[1/3,2/3]))
    before=(m.stress_center_,m.stress_sd_,m.knots_.copy())
    q=frame((-10.,10.));m.predict_quantiles(q)
    np.testing.assert_array_equal(m.knots_,before[2])
    assert m.stress_center_==before[0] and m.stress_sd_==before[1]


def test_grid_and_validation():
    grid=student_aft_grid()
    assert len(grid)==48 and len(set(grid))==48
    assert {c.prior_sd for c in grid}=={.1,.3,1.,3.}
    for kwargs in [dict(nu=2),dict(prior_sd=0),dict(scatter='wrong'),dict(mean='wrong')]:
        with pytest.raises(ValueError):StudentAFTConfig(**kwargs)
    m=configured()
    for levels in [(0,),(-1,),(),(np.nan,)]:
        with pytest.raises(ValueError):m.predict_quantiles(frame(),alphas=levels)
    with pytest.raises(ValueError):m.predict_cdf(np.nan,frame())
    with pytest.raises(ValueError):m.predict_quantiles(frame(condition='other'),frame((0,),y=[6.]))
    with pytest.raises(ValueError):CensoredStudentAFT().fit(frame(y=[6,6,6],event=[0,0,0]))
    with pytest.raises(ValueError):intercept_posterior([0],[0],[0],[0])
    with pytest.raises(ValueError):CensoredStudentAFT().fit(frame(y=[6,6,6]),sample_weight=np.ones(3))
