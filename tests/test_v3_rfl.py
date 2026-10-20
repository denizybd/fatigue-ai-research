"""Independent synthetic checks; these are not external campaign validation."""
import numpy as np
import pandas as pd
import pytest
from scipy.integrate import quad
from scipy.stats import norm

from src.v3_rfl import NormalNormalRFL


def model(nodes=128, tau_shift=0.):
    m = NormalNormalRFL(nodes=nodes, shift_prior_sd=tau_shift)
    m.ratio_median_, m.ratio_center_ = -1., -1.
    m.log_stress_ref_ = np.log10(250.)
    m.params_ = np.array([5.3, -3.5, .1, np.log(.3), np.log10(150.), np.log(.12)])
    m.sigma_ = .3
    return m


def frame(stress=(180., 250., 350.), life=None, event=None):
    d = pd.DataFrame({'log_stress': np.log10(stress), 'load_ratio': -1.,
                      'group_id': 'synthetic'})
    if life is not None:
        d['log_life'] = life
        d['event'] = 1 if event is None else event
    return d


def direct_cdf(m, stress, y):
    a, b, c, logsigma, mugamma, logtau = m.params_
    tau, sigma = np.exp(logtau), np.exp(logsigma)
    zlimit = (np.log10(stress)-mugamma)/tau
    def integrand(z):
        gamma = 10**(mugamma+tau*z)
        mu = a+b*np.log10((stress-gamma)/(10**m.log_stress_ref_))
        return norm.pdf(z)*norm.cdf((y-mu)/sigma)
    return quad(integrand, -12, zlimit, epsabs=2e-11, epsrel=2e-9, limit=200)[0]


def test_cdf_matches_independent_direct_normal_integral():
    m = model(192)
    q = frame()
    y = np.array([6.4, 6., 5.2])
    expected = np.array([direct_cdf(m, s, yy) for s, yy in zip((180.,250.,350.), y)])
    np.testing.assert_allclose(m.predict_cdf(y, q), expected, rtol=2e-5, atol=2e-7)


def test_atom_and_infinite_quantile_are_exact():
    m = model()
    q = frame((100.,150.,250.))
    finite_mass = norm.cdf((q.log_stress-np.log10(150.))/.12)
    np.testing.assert_allclose(m.failure_probability(q), finite_mass, atol=2e-16)
    np.testing.assert_allclose(m.predict_cdf(1000., q), finite_mass, atol=2e-15)
    np.testing.assert_array_equal(m.predict_cdf(np.inf, q), np.ones(3))
    medians = m.predict_location(q)
    assert np.isinf(medians[0]) and np.isinf(medians[1])
    assert np.isfinite(medians[2])
    alpha = float(m.failure_probability(frame((100.,)))[0])
    assert np.isinf(m.predict_quantiles(frame((100.,)), alphas=(alpha,))[0,0])


def test_quantile_inversion_and_stress_monotonicity():
    m = model(192)
    q = frame(np.geomspace(100, 500, 30))
    quantiles = m.predict_quantiles(q, alphas=(.01,.1,.5,.9))
    for j, alpha in enumerate((.01,.1,.5,.9)):
        finite = np.isfinite(quantiles[:,j])
        np.testing.assert_allclose(m.predict_cdf(quantiles[finite,j], q.loc[finite]), alpha,
                                   atol=2e-9)
        assert np.all(np.diff(quantiles[finite,j]) <= 0)


def test_density_is_cdf_derivative_and_censor_survival_is_correct():
    m = model(192)
    q = frame((250.,), life=[6.], event=[1])
    delta = 1e-4
    derivative = (m.predict_cdf(6.+delta,q)-m.predict_cdf(6.-delta,q))/(2*delta)
    np.testing.assert_allclose(np.exp(m.predict_log_score(q)), derivative, rtol=2e-7)
    q['event'] = 0
    np.testing.assert_allclose(np.exp(m.predict_log_score(q)), 1-m.predict_cdf(6.,q), atol=2e-14)


def test_no_support_shift_is_exact_normal_convolution():
    m = model(192, .6)
    reference = model(192)
    reference.params_[3] = np.log(np.hypot(.3,.6))
    np.testing.assert_allclose(m.predict_cdf(6.,frame()), reference.predict_cdf(6.,frame()), atol=1e-15)
    np.testing.assert_allclose(m.predict_quantiles(frame()), reference.predict_quantiles(frame()), atol=1e-10)


@pytest.mark.parametrize('events', ([1,1,1], [0,0,0], [1,0,1]))
def test_global_shift_posterior_matches_independent_quad(events):
    m = model(96,.7)
    s = frame((190.,250.,350.), life=[6.7,6.,5.7], event=events)
    post = m.support_posterior(s)
    kernel = m._kernel(m._x(s))
    def integrand(u, power=0):
        pdf,sf = m._logparts(kernel,np.asarray(s.log_life),np.array([u]))
        logll = np.where(np.asarray(events)==1,pdf[:,0],sf[:,0]).sum()
        return np.exp(logll)*norm.pdf(u,scale=.7)*u**power
    z = quad(integrand,-9,9,epsabs=1e-11,limit=150)[0]
    mean = quad(lambda u: integrand(u,1),-9,9,epsabs=1e-11,limit=150)[0]/z
    var = quad(lambda u: integrand(u,2),-9,9,epsabs=1e-11,limit=150)[0]/z-mean**2
    np.testing.assert_allclose([post['mean'],post['variance'],post['log_marginal']],
                               [mean,var,np.log(z)],atol=2e-8)
    assert post['tail_mass_bound'] < 1e-10
    assert np.isclose(post['weight'].sum(),1)
    if not any(events):
        assert post['mean'] > 0


def test_support_cannot_change_fatigue_limit_atom_or_read_query_outcomes():
    m = model(96,.7)
    support = frame((250.,350.),life=[7.,6.],event=[0,1])
    q = frame((180.,250.),life=[-500.,500.],event=[0,1])
    a = m.predict_quantiles(q,support)
    q['log_life'],q['event'] = np.nan,np.nan
    np.testing.assert_array_equal(a,m.predict_quantiles(q,support))
    np.testing.assert_allclose(m.predict_cdf(1000.,q,support),m.failure_probability(q),atol=2e-15)


def test_support_cache_includes_revealed_endpoints_and_training_prior():
    m = model(96,.7)
    support = frame((250.,350.),life=[7.,6.],event=[0,1])
    a = m.support_posterior(support)
    assert m.support_posterior(support.copy()) is a
    support.loc[1,'log_life'] += 1
    b = m.support_posterior(support)
    assert abs(b['mean']-a['mean']) > .01
    m.shift_prior_sd = .1
    c = m.support_posterior(support)
    assert c['variance'] < b['variance']


def test_quadrature_stability_near_limit():
    q = frame((145.,150.,155.,180.,250.))
    a,b = model(96),model(192)
    np.testing.assert_allclose(a.predict_cdf(7.5,q),b.predict_cdf(7.5,q),atol=1e-5)
    np.testing.assert_allclose(a.predict_quantiles(q,alphas=(.05,.1)),
                               b.predict_quantiles(q,alphas=(.05,.1)),atol=4e-4)


def test_synthetic_fit_emits_training_only_multistart_receipt():
    rng = np.random.default_rng(41)
    stress = np.tile(np.linspace(180.,400.,12),8)
    gamma = 10**rng.normal(np.log10(140.),.1,len(stress))
    life = np.full(len(stress),8.)
    finite = gamma < stress
    life[finite] = 5.3-3.5*np.log10((stress[finite]-gamma[finite])/250.)+rng.normal(0,.25,finite.sum())
    event = (life < 7.5).astype(int)
    d = frame(stress,life=np.minimum(life,7.5),event=event)
    m = NormalNormalRFL(max_iter=250,nodes=48,shift_prior_sd=.4).fit(d)
    receipt=m.fit_receipt_
    assert len(receipt['starts']) == 3
    assert receipt['n_train'] == len(d)
    assert receipt['population_uncertainty_integrated'] is False
    assert len(receipt['bounds']) == 6
    assert m.params_[1] < 0
    assert receipt['success'] or receipt['fallback_active']
    assert np.all(np.isfinite(m.predict_quantiles(frame((250.,350.)))))


def test_input_validation():
    with pytest.raises(ValueError): NormalNormalRFL(shift_prior_sd=-1.)
    with pytest.raises(ValueError): model().predict_quantiles(frame(),alphas=(0.,))
    with pytest.raises(ValueError): model().predict_cdf(np.nan,frame())
