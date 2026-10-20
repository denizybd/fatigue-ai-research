"""Synthetic statistical/derivative checks; no real fatigue data are read."""

from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.optimize._numdiff import approx_derivative

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from models import LinearCensoredAFT, MLPCensoredAFT, _normal_nll_grad


def _example(seed=42, n=200):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 3))
    latent = 5.5 - 0.8 * X[:, 0] + 0.2 * X[:, 1] + rng.normal(scale=0.25, size=n)
    censor = rng.normal(6.0, 0.5, size=n)
    event = (latent <= censor).astype(float)
    return X, np.minimum(latent, censor), event


def test_scalar_likelihood_gradient_and_extreme_tail_finite():
    mu = np.array([2.0, 3.0, 4.0, -20.0, 30.0])
    y = np.array([2.3, 3.8, 3.7, 10.0, 10.0])
    event = np.array([1.0, 0.0, 1.0, 0.0, 0.0])
    weight = np.full(5, 0.2)
    theta = np.r_[mu, np.log(0.7)]
    val, d_mu, d_sigma = _normal_nll_grad(mu, theta[-1], y, event, weight)
    numeric = approx_derivative(lambda t: _normal_nll_grad(t[:-1], t[-1], y, event, weight)[0], theta).ravel()
    analytic = np.r_[d_mu, d_sigma]
    assert np.isfinite(val)
    np.testing.assert_allclose(analytic, numeric, rtol=2e-6, atol=2e-6)


@pytest.mark.parametrize("kind", ["linear", "mlp"])
def test_full_objective_gradient(kind):
    X, y, event = _example(n=17)
    weight = np.arange(1, 18, dtype=float)
    weight /= weight.sum()
    rng = np.random.default_rng(51)
    if kind == "linear":
        model = LinearCensoredAFT(l2=0.02)
        theta = np.r_[rng.normal(scale=0.1, size=X.shape[1]), 5.5, np.log(0.8)]
    else:
        model = MLPCensoredAFT(hidden_units=4, l2=0.02)
        theta = np.r_[rng.normal(scale=0.1, size=X.shape[1] * 4 + 8), 5.5, np.log(0.8)]
    value, analytic = model._objective(theta, X, y, event, weight)
    numeric = approx_derivative(lambda t: model._objective(t, X, y, event, weight)[0], theta).ravel()
    assert np.isfinite(value)
    np.testing.assert_allclose(analytic, numeric, rtol=2e-5, atol=2e-6)


def test_basquin_slope_recovery_with_right_censoring():
    rng = np.random.default_rng(7)
    log_stress = rng.uniform(2.1, 2.6, size=2400)
    X = (log_stress - 2.35)[:, None]
    latent = 5.8 - 5.0 * X[:, 0] + rng.normal(0, 0.22, size=len(X))
    cutoff = np.full(len(X), 6.2)
    event = (latent <= cutoff).astype(int)
    y = np.minimum(latent, cutoff)
    model = LinearCensoredAFT(l2=0.0).fit(X, y, event)
    assert model.status_.success
    assert abs(model.coef_[0] - (-5.0)) < 0.10
    assert abs(model.intercept_ - 5.8) < 0.03
    assert abs(model.sigma_ - 0.22) < 0.03


@pytest.mark.parametrize("constructor", [LinearCensoredAFT, MLPCensoredAFT])
def test_runouts_increase_location_relative_to_false_failures(constructor):
    # An intercept-only design with many high-life survivors. Correct survival
    # contributions must raise the estimate relative to false endpoint failures.
    X = np.zeros((100, 1))
    y = np.r_[np.linspace(4.5, 5.5, 50), np.full(50, 6.0)]
    event = np.r_[np.ones(50), np.zeros(50)]
    correct = constructor().fit(X, y, event)
    naive = constructor().fit(X, y, np.ones(100))
    assert correct.predict_location(X[:1])[0] > naive.predict_location(X[:1])[0] + 0.1
    assert np.isfinite(correct.sigma_)


@pytest.mark.parametrize("constructor", [LinearCensoredAFT, MLPCensoredAFT])
def test_finite_predictions_and_deterministic_repeat(constructor):
    X, y, event = _example()
    a = constructor().fit(X, y, event)
    b = constructor().fit(X, y, event)
    pred = a.predict_location(X[:20])
    assert np.all(np.isfinite(pred))
    assert a.sigma_ > 0
    np.testing.assert_array_equal(a.params_, b.params_)
    assert a.status_.to_dict()["n_iter"] > 0


def test_sample_weight_scaling_invariance():
    X, y, event = _example(n=70)
    weights = np.linspace(0.5, 2, len(y))
    a = LinearCensoredAFT().fit(X, y, event, sample_weight=weights)
    b = LinearCensoredAFT().fit(X, y, event, sample_weight=weights * 10)
    np.testing.assert_allclose(a.params_, b.params_, rtol=1e-8, atol=1e-8)


@pytest.mark.parametrize("constructor", [LinearCensoredAFT, MLPCensoredAFT])
def test_rejects_unidentified_and_invalid_inputs(constructor):
    X, y, event = _example(n=15)
    with pytest.raises(ValueError, match="failure"):
        constructor().fit(X, y, np.zeros_like(event))
    with pytest.raises(ValueError, match="finite"):
        constructor().fit(X * np.nan, y, event)
    with pytest.raises(ValueError, match="event"):
        constructor().fit(X, y, np.full_like(event, 0.5))
    with pytest.raises(RuntimeError, match="fit"):
        constructor().predict_location(X)
