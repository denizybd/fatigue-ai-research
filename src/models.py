"""Small right-censored log10-normal accelerated-life models.

``y`` is log10(cycles); ``event=1`` means observed failure and ``event=0``
means right censoring at y. Neither estimator fits censored endpoints as failures.
Inputs must be finite and already encoded/scaled using training data only.

The models estimate conditional location and one common log10-life standard
deviation. They do not provide calibrated confidence/tolerance bounds, posterior
weight uncertainty, a monotonicity guarantee, or a causal process model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy.optimize import minimize
from scipy.special import log_ndtr


_LOG_2PI = float(np.log(2.0 * np.pi))


@dataclass(frozen=True)
class FitStatus:
    """Optimization receipt; success is numerical convergence, not validation."""

    success: bool
    status: int
    message: str
    n_iter: int
    n_function_evaluations: int
    objective: float
    gradient_inf_norm: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_training_data(X, y, event, sample_weight=None):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    event = np.asarray(event, dtype=float)
    if X.ndim != 2 or X.shape[0] == 0 or X.shape[1] == 0:
        raise ValueError("X must be a nonempty two-dimensional array")
    if y.ndim != 1 or event.ndim != 1 or len(y) != len(X) or len(event) != len(X):
        raise ValueError("y and event must be one-dimensional and match X rows")
    if not np.all(np.isfinite(X)) or not np.all(np.isfinite(y)):
        raise ValueError("X and y must contain only finite values")
    if not np.all(np.isin(event, [0.0, 1.0])):
        raise ValueError("event must equal 1 for failure or 0 for right censoring")
    if sample_weight is None:
        weight = np.ones(len(X), dtype=float)
    else:
        weight = np.asarray(sample_weight, dtype=float)
        if weight.ndim != 1 or len(weight) != len(X):
            raise ValueError("sample_weight must be one-dimensional and match X rows")
        if not np.all(np.isfinite(weight)) or np.any(weight < 0):
            raise ValueError("sample_weight must be finite and nonnegative")
    if weight.sum() <= 0:
        raise ValueError("sample_weight must have positive total weight")
    if np.sum(weight * event) <= 0:
        raise ValueError("at least one positive-weight failure is required for identification")
    return X, y, event, weight / weight.sum()


def _normal_nll_grad(mu, log_sigma, y, event, weight):
    """Return weighted-average negative log likelihood and derivatives.

    log_ndtr(-z) evaluates log survival stably. The inverse Mills ratio is
    computed in the log domain, avoiding division by a rounded-to-zero sf.
    Derivatives are with respect to each mu and the shared log(sigma).
    """

    sigma = np.exp(log_sigma)
    z = (y - mu) / sigma
    log_sf = log_ndtr(-z)
    log_pdf = -0.5 * z * z - 0.5 * _LOG_2PI
    hazard = np.exp(log_pdf - log_sf)
    failure_nll = 0.5 * z * z + log_sigma + 0.5 * _LOG_2PI
    censor_nll = -log_sf
    value = np.dot(weight, event * failure_nll + (1.0 - event) * censor_nll)
    d_mu = weight * (-event * z - (1.0 - event) * hazard) / sigma
    d_log_sigma = np.dot(weight, event * (1.0 - z * z) - (1.0 - event) * z * hazard)
    return float(value), d_mu, float(d_log_sigma)


def _status(result):
    return FitStatus(
        success=bool(result.success),
        status=int(result.status),
        message=str(result.message),
        n_iter=int(result.nit),
        n_function_evaluations=int(result.nfev),
        objective=float(result.fun),
        gradient_inf_norm=float(np.linalg.norm(result.jac, ord=np.inf)),
    )


class _CensoredAFTBase:
    def _check_config(self):
        if self.l2 < 0 or not np.isfinite(self.l2):
            raise ValueError("l2 must be finite and nonnegative")
        if not 0 < self.min_sigma < self.max_sigma < np.inf:
            raise ValueError("sigma bounds must satisfy 0 < min_sigma < max_sigma")
        if self.max_iter < 1:
            raise ValueError("max_iter must be positive")

    def _prediction_inputs(self, X):
        if not hasattr(self, "params_"):
            raise RuntimeError("fit must be called before prediction")
        X = np.asarray(X, dtype=float)
        if X.ndim != 2 or X.shape[1] != self.n_features_in_:
            raise ValueError("prediction X has the wrong feature dimension")
        if not np.all(np.isfinite(X)):
            raise ValueError("prediction X must be finite")
        return X

    def _optimize(self, theta, objective):
        bounds = [(None, None)] * len(theta)
        bounds[-1] = (float(np.log(self.min_sigma)), float(np.log(self.max_sigma)))
        result = minimize(
            objective,
            theta,
            method="L-BFGS-B",
            jac=True,
            bounds=bounds,
            options={"maxiter": self.max_iter, "ftol": 1e-10, "gtol": 1e-6, "maxls": 40},
        )
        if not np.isfinite(result.fun) or not np.all(np.isfinite(result.x)):
            raise FloatingPointError("optimizer produced nonfinite model parameters")
        self.params_ = result.x.copy()
        self.sigma_ = float(np.exp(self.params_[-1]))
        self.status_ = _status(result)
        self.converged_ = self.status_.success
        self.sigma_at_bound_ = bool(
            np.isclose(self.sigma_, self.min_sigma, rtol=1e-5)
            or np.isclose(self.sigma_, self.max_sigma, rtol=1e-5)
        )


class LinearCensoredAFT(_CensoredAFTBase):
    """Ridge-regularized lognormal AFT, including an unpenalized intercept.

    Objective = weighted mean censored NLL + l2/2 * ||coefficients||^2.
    No source indicators, target transformations, tuning or splitting are done
    here. ``coef_`` describes log10-life per unit of the supplied feature.
    """

    def __init__(self, l2=0.001, max_iter=500, min_sigma=0.001, max_sigma=5.0):
        self.l2 = float(l2)
        self.max_iter = int(max_iter)
        self.min_sigma = float(min_sigma)
        self.max_sigma = float(max_sigma)

    def _objective(self, theta, X, y, event, weight):
        coef, intercept, log_sigma = theta[:-2], theta[-2], theta[-1]
        mu = X @ coef + intercept
        value, d_mu, d_log_sigma = _normal_nll_grad(mu, log_sigma, y, event, weight)
        value += 0.5 * self.l2 * np.dot(coef, coef)
        grad = np.r_[X.T @ d_mu + self.l2 * coef, d_mu.sum(), d_log_sigma]
        return float(value), grad

    def fit(self, X, y, event, sample_weight=None):
        self._check_config()
        X, y, event, weight = _validate_training_data(X, y, event, sample_weight)
        self.n_features_in_ = X.shape[1]
        design = np.column_stack((X, np.ones(len(X))))
        # Weighted ridge on observed endpoints is initialization only; every
        # subsequent optimization step uses the proper censored likelihood.
        penalty = np.diag(np.r_[np.full(X.shape[1], self.l2), 0.0])
        lhs = design.T @ (weight[:, None] * design) + penalty
        rhs = design.T @ (weight * y)
        initial_coef = np.linalg.lstsq(lhs, rhs, rcond=None)[0]
        residual = y - design @ initial_coef
        initial_sigma = np.clip(np.sqrt(np.dot(weight, residual**2)), self.min_sigma * 2, self.max_sigma / 2)
        theta = np.r_[initial_coef, np.log(initial_sigma)]
        self._optimize(theta, lambda t: self._objective(t, X, y, event, weight))
        self.coef_ = self.params_[:-2].copy()
        self.intercept_ = float(self.params_[-2])
        return self

    def predict_location(self, X):
        X = self._prediction_inputs(X)
        return X @ self.coef_ + self.intercept_


class MLPCensoredAFT(_CensoredAFTBase):
    """One-hidden-layer tanh location model, shared lognormal scatter.

    Objective = weighted mean censored NLL + l2/2*(||W||^2+||v||^2).
    Hidden/output biases are unpenalized. Fit uses one deterministic seeded
    initialization and a bounded L-BFGS run; no best-of-seeds selection occurs.
    """

    def __init__(self, hidden_units=12, l2=0.01, seed=0, max_iter=500, min_sigma=0.001, max_sigma=5.0):
        self.hidden_units = int(hidden_units)
        self.l2 = float(l2)
        self.seed = int(seed)
        self.max_iter = int(max_iter)
        self.min_sigma = float(min_sigma)
        self.max_sigma = float(max_sigma)

    def _unpack(self, theta, n_features):
        h = self.hidden_units
        end_W = n_features * h
        W = theta[:end_W].reshape(n_features, h)
        b = theta[end_W:end_W + h]
        v = theta[end_W + h:end_W + 2 * h]
        intercept = theta[-2]
        return W, b, v, intercept, theta[-1]

    def _objective(self, theta, X, y, event, weight):
        W, b, v, intercept, log_sigma = self._unpack(theta, X.shape[1])
        hidden = np.tanh(X @ W + b)
        mu = hidden @ v + intercept
        value, d_mu, d_log_sigma = _normal_nll_grad(mu, log_sigma, y, event, weight)
        value += 0.5 * self.l2 * (np.sum(W * W) + np.dot(v, v))
        d_hidden_pre = (d_mu[:, None] * v) * (1.0 - hidden * hidden)
        grad_W = X.T @ d_hidden_pre + self.l2 * W
        grad_b = d_hidden_pre.sum(axis=0)
        grad_v = hidden.T @ d_mu + self.l2 * v
        grad = np.r_[grad_W.ravel(), grad_b, grad_v, d_mu.sum(), d_log_sigma]
        return float(value), grad

    def fit(self, X, y, event, sample_weight=None):
        self._check_config()
        if self.hidden_units < 1:
            raise ValueError("hidden_units must be positive")
        X, y, event, weight = _validate_training_data(X, y, event, sample_weight)
        self.n_features_in_ = X.shape[1]
        rng = np.random.default_rng(self.seed)
        W = rng.normal(scale=0.3 / np.sqrt(X.shape[1]), size=(X.shape[1], self.hidden_units))
        b = np.zeros(self.hidden_units)
        v = rng.normal(scale=0.1 / np.sqrt(self.hidden_units), size=self.hidden_units)
        intercept = float(np.dot(weight, y))
        initial_sigma = np.clip(np.sqrt(np.dot(weight, (y-intercept)**2)), self.min_sigma * 2, self.max_sigma / 2)
        theta = np.r_[W.ravel(), b, v, intercept, np.log(initial_sigma)]
        self._optimize(theta, lambda t: self._objective(t, X, y, event, weight))
        return self

    def predict_location(self, X):
        X = self._prediction_inputs(X)
        W, b, v, intercept, _ = self._unpack(self.params_, self.n_features_in_)
        return np.tanh(X @ W + b) @ v + intercept
