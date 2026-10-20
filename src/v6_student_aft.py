"""Right-censored hierarchical Student-t AFT; log10 stress and life throughout.

Condition random intercepts have a proper normal prior and are integrated, not
optimized as unpenalized dummy variables. Target predictions integrate only the
selected support likelihood and natural residual scatter. Population parameters
remain empirical-Bayes point estimates; this is not a fully Bayesian population
fit or a confidence/tolerance guarantee. No query outcomes enter prediction.
Finite-nu Student errors on log10 life imply infinite uncapped arithmetic mean
life; quantiles/CDF and capped expected testing cost remain well-defined. No
lognormal mean-life shortcut is exposed by this module.

The positive, adaptive Gauss-Legendre rule checks its own mass error and a
Gaussian-prior tail bound. It makes no log-concavity/Laplace assumption: a
Student-t random-intercept posterior can have multiple modes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from itertools import product
import hashlib
import json
import math

import numpy as np
from numpy.polynomial.hermite import hermgauss
from numpy.polynomial.legendre import leggauss
from scipy.optimize import brentq, minimize
from scipy.special import expit, gammaln, log_ndtr, logsumexp, ndtr, stdtr, stdtrit
from scipy.stats import norm

LOG2PI = float(np.log(2 * np.pi))


def _df(nu):
    if nu is None or nu in ('gaussian', 'Gaussian', 'normal'):
        return np.inf
    value = float(nu)
    if not (value > 2):
        raise ValueError('Student-t degrees of freedom must exceed two')
    return value


def _standard_logpdf(z, nu):
    z = np.asarray(z, float)
    if np.isinf(nu):
        return -.5 * z * z - .5 * LOG2PI
    c = gammaln((nu + 1) / 2) - gammaln(nu / 2) - .5 * np.log(nu * np.pi)
    # logaddexp avoids overflow in z**2 for extreme but finite arguments.
    with np.errstate(divide='ignore'):
        logterm = np.logaddexp(0., 2 * np.log(np.abs(z)) - np.log(nu))
    return c - .5 * (nu + 1) * logterm


def _standard_logsf(z, nu):
    z = np.asarray(z, float)
    if np.isinf(nu):
        return log_ndtr(-z)
    # stdtr is accurate in the ordinary domain. The leading asymptotic has
    # relative O(1/z**2) error; beyond1e8 it is below double precision and avoids
    # underflow of the incomplete-beta probability before taking its logarithm.
    a = np.abs(z)
    far = a > 1e8
    with np.errstate(divide='ignore', invalid='ignore'):
        ordinary = np.log(stdtr(nu, -a))
        c = gammaln((nu + 1) / 2) - gammaln(nu / 2) - .5 * np.log(nu * np.pi)
        asymptotic = c + .5 * (nu - 1) * np.log(nu) - nu * np.log(a)
        positive = np.where(far, asymptotic, ordinary)
        negative = np.log1p(-np.exp(positive))
    return np.where(z >= 0, positive, negative)


def censored_t_parts(mu, sigma, y, event, nu=4):
    """Per-observation log likelihood and analytic location/log-scale scores.

    event1 uses the continuous log10-life density; event0 uses survival at the
    observed endpoint. Scale is the t scale, not its standard deviation.
    Arrays follow ordinary NumPy broadcasting, including a quadrature dimension.
    """
    nu = _df(nu)
    mu, sigma, y, event = np.broadcast_arrays(
        np.asarray(mu, float), np.asarray(sigma, float),
        np.asarray(y, float), np.asarray(event, float))
    if (np.any(~np.isfinite(mu)) or np.any(~np.isfinite(sigma)) or
            np.any(sigma <= 0) or np.any(~np.isfinite(y)) or
            np.any(~np.isin(event, [0., 1.]))):
        raise ValueError('finite locations/endpoints, positive scales and binary events required')
    z = (y - mu) / sigma
    lp = _standard_logpdf(z, nu)
    ls = _standard_logsf(z, nu)
    hazard = np.exp(lp - ls)
    if np.isinf(nu):
        score_mu = z / sigma
        score_scale = z * z - 1
    else:
        # Stable forms also avoid squaring extreme residuals unnecessarily.
        with np.errstate(over='ignore', invalid='ignore'):
            ratio = 1 / (1 + (z * z) / nu)
            score_mu = ((nu + 1) / nu) * z * ratio / sigma
            score_scale = nu - (nu + 1) * ratio
        score_mu = np.where(np.isfinite(score_mu), score_mu, 0.)
    return (np.where(event == 1, lp - np.log(sigma), ls),
            np.where(event == 1, score_mu, hazard / sigma),
            np.where(event == 1, score_scale, z * hazard))


@lru_cache(maxsize=8)
def _legendre_rule(order):
    return leggauss(order)


def _log_abs_difference(a, b):
    maximum = np.maximum(a, b)
    with np.errstate(divide='ignore', invalid='ignore'):
        return maximum + np.log(-np.expm1(np.minimum(a, b) - maximum))


def intercept_posterior(mu, sigma, y, event, nu=4, prior_sd=.3,
                        tolerance=2e-8, order=12, max_nodes=65536,
                        resolution_scale=None):
    """Proper scalar random-intercept marginal and positive posterior rule.

    The residual density supremum gives K=product(maxpdf_i) over failures;
    censored terms are at most1. Omitted mass is bounded by
    K*P(|Normal(0,prior_sd)|>radius). This absolute bound is reported relative
    to the computed evidence and must be below tolerance. Interval refinement
    compares order and twice-order rules, including posterior moments.
    """
    nu = _df(nu)
    mu, sigma, y, event = [np.asarray(a, float).reshape(-1) for a in (mu, sigma, y, event)]
    if (len(mu) != len(y) or len(sigma) != len(y) or len(event) != len(y) or
            not np.isfinite(prior_sd) or prior_sd <= 0 or
            not (0 < tolerance < .01) or order < 4 or max_nodes < 256):
        raise ValueError('matching arrays, proper positive prior and valid integration settings required')
    if resolution_scale is not None and (not np.isfinite(resolution_scale) or resolution_scale <= 0):
        raise ValueError('predictive integration resolution must be finite and positive')
    if len(y) == 0 and resolution_scale is None:
        gx, gw = hermgauss(max(48, 2 * order))
        return dict(u=np.sqrt(2) * prior_sd * gx, weight=gw / np.sqrt(np.pi),
                    log_marginal=0., mean=0., variance=prior_sd ** 2,
                    tail_mass_bound=0., quadrature_relative_error=0.,
                    nodes=len(gx), radius=np.inf, proper_prior=True)
    # Validation is shared with the likelihood and occurs before adaptive work.
    censored_t_parts(mu, sigma, y, event, nu)
    residual = y - mu
    log_k = float(np.sum((_standard_logpdf(np.zeros(len(y)), nu) - np.log(sigma))[event == 1]))
    # Working normal location is only an interval anchor, never a posterior or
    # likelihood approximation. In particular no events are recoded as failures.
    precision = 1 / prior_sd ** 2 + np.sum(1 / sigma ** 2)
    working_mean = np.sum(residual / sigma ** 2) / precision
    working_sd = 1 / np.sqrt(precision)
    radius = max(8 * prior_sd, abs(working_mean) + 10 * working_sd)

    def evaluate(edges, n):
        gx, gw = _legendre_rule(n)
        half = np.diff(edges) / 2
        u = (edges[:-1, None] + half[:, None] * (gx[None, :] + 1)).ravel()
        prior = -.5 * (u / prior_sd) ** 2 - np.log(prior_sd) - .5 * LOG2PI
        ll = censored_t_parts(mu[:, None] + u[None, :], sigma[:, None],
                              y[:, None], event[:, None], nu)[0].sum(0)
        logw = ll + prior + np.log((half[:, None] * gw[None, :]).ravel())
        interval_logmass = logsumexp(logw.reshape(len(half), n), axis=1)
        return u, logw, interval_logmass

    for expansion in range(20):
        # Residual anchors protect separated Student-t modes. Larger training
        # conditions use17quantiles, support sets<=16 retain every endpoint.
        anchors = (np.unique(residual) if len(y) <= 16 else
                   np.quantile(residual, np.linspace(0, 1, 17)))
        narrow = np.r_[working_mean + working_sd * np.array([-8,-3,0,3,8]),
                       prior_sd * np.array([-4,-2,-1,0,1,2,4])]
        edges = np.unique(np.r_[-radius, radius, anchors, narrow])
        edges = edges[(edges >= -radius) & (edges <= radius)]
        if resolution_scale is not None:
            # Evidence/moment accuracy alone cannot certify a much sharper
            # future CDF kernel. Resolve it using QUERY COVARIATES only; this
            # changes numerical resolution, never fitted statistical parameters.
            segments = max(1, int(np.ceil(2*radius/(4*resolution_scale))))
            if segments*2*order > max_nodes:
                raise FloatingPointError('predictive kernel resolution exceeds quadrature budget')
            edges = np.unique(np.r_[edges,np.linspace(-radius,radius,segments+1)])
        for refinement in range(20):
            if (len(edges) - 1) * 2 * order > max_nodes:
                raise FloatingPointError('random-intercept quadrature node budget exceeded')
            u, logw, high = evaluate(edges, 2 * order)
            lo_u, lo_logw, low = evaluate(edges, order)
            lm = float(logsumexp(high))
            weights = np.exp(logw - lm)
            mean = float(weights @ u)
            variance = float(weights @ ((u - mean) ** 2))
            low_lm = float(logsumexp(low))
            low_weights = np.exp(lo_logw - low_lm)
            low_mean = float(low_weights @ lo_u)
            low_variance = float(low_weights @ ((lo_u - low_mean) ** 2))
            log_errors = _log_abs_difference(high, low)
            relative_error = float(np.exp(logsumexp(log_errors) - lm))
            moment_error = max(abs(mean-low_mean) / max(1., abs(mean)),
                               abs(variance-low_variance) / max(1., variance))
            if relative_error <= tolerance and moment_error <= tolerance:
                break
            # Refine intervals responsible for the discrepancy. Always refine
            # the largest-error interval if moment cancellation hides mass error.
            bad = np.exp(log_errors - lm) > tolerance / (2 * len(high))
            if not np.any(bad):
                bad[np.argmax(log_errors)] = True
            edges = np.unique(np.r_[edges, (edges[:-1] + edges[1:])[bad] / 2])
        else:
            raise FloatingPointError('random-intercept quadrature did not converge')
        log_tail = log_k + np.log(2.) + log_ndtr(-radius / prior_sd)
        tail_bound = float(np.exp(min(0., log_tail - lm)))
        if log_tail - lm <= np.log(tolerance):
            return dict(u=u, weight=weights, log_marginal=lm, mean=mean,
                        variance=variance, tail_mass_bound=tail_bound,
                        quadrature_relative_error=relative_error,
                        quadrature_moment_error=moment_error,
                        nodes=len(u), radius=radius, proper_prior=True)
        radius *= 1.5
    raise FloatingPointError('random-intercept prior tail bound did not converge')


@dataclass(frozen=True)
class StudentAFTConfig:
    """One fixed training/target model; selection belongs to training-only CV."""
    nu: float | str = 4.
    scatter: str = 'constant'
    mean: str = 'linear'
    prior_sd: float = .3

    def __post_init__(self):
        object.__setattr__(self, 'nu', _df(self.nu))
        if self.scatter not in ('constant', 'loglinear'):
            raise ValueError('scatter must be constant or loglinear')
        if self.mean not in ('linear', 'two_knots'):
            raise ValueError('mean must be linear or two_knots')
        if not np.isfinite(self.prior_sd) or self.prior_sd <= 0:
            raise ValueError('a proper, positive condition/target prior width is required')

    def receipt(self):
        d = asdict(self)
        d['nu'] = 'gaussian' if np.isinf(self.nu) else self.nu
        return d


def student_aft_grid():
    """The48prefit configurations; no observed outcomes are read here.

    Prior-width expansion to .1/.3/1/3 was requested before any real-data fit.
    """
    return [StudentAFTConfig(*values) for values in product(
        (4., 10., np.inf), ('constant', 'loglinear'),
        ('linear', 'two_knots'), (.1, .3, 1., 3.))]


class CensoredStudentAFT:
    """Empirical-Bayes monotone AFT with exact right-censored likelihood.

    Y=a+cR*(R-centerR)+spline(s)+u+exp(gamma0+gamma1*s)*T_nu,
    s=(logS-centerS)/sdS, u~Normal(0,prior_sd**2).
    Global point estimates maximize the sum of condition log marginals minus
    fixed regularization. Every row has unit likelihood weight. Dataset IDs
    denote working statistical conditions, not certified physical batches. Their
    marginal sum is a composite objective if conditions from a source depend on
    one another; physical independence is not certified by this model.
    """
    def __init__(self, config=None, *, max_iter=600, quadrature_tolerance=2e-8,
                 quadrature_order=12, max_quadrature_nodes=65536):
        self.config = StudentAFTConfig() if config is None else config
        if not isinstance(self.config, StudentAFTConfig):
            raise TypeError('config must be StudentAFTConfig')
        self.max_iter = int(max_iter)
        self.quadrature_tolerance = float(quadrature_tolerance)
        self.quadrature_order = int(quadrature_order)
        self.max_quadrature_nodes = int(max_quadrature_nodes)
        if self.max_iter < 1:
            raise ValueError('positive optimizer iteration budget required')
        self._posterior_cache = {}

    def _x(self, frame):
        stress = np.asarray(frame.log_stress, float)
        ratio = np.asarray(frame.load_ratio, float).copy()
        if np.any(~np.isfinite(stress)):
            raise ValueError('finite log stress is required')
        ratio[~np.isfinite(ratio)] = self.ratio_median_
        return (stress-self.stress_center_)/self.stress_sd_, ratio-self.ratio_center_

    @staticmethod
    def _outcomes(frame):
        y, event = np.asarray(frame.log_life, float), np.asarray(frame.event, float)
        if np.any(~np.isfinite(y)) or np.any(~np.isin(event, [0., 1.])):
            raise ValueError('finite log life and binary events required')
        return y, event

    def _basis(self, s):
        if self.config.mean == 'linear':
            return np.asarray(s)[:, None]
        k1, k2 = self.knots_
        # Recombination into three segment slopes yields their exact derivatives.
        h1 = np.maximum(s-k1, 0.)-max(-k1, 0.)
        h2 = np.maximum(s-k2, 0.)-max(-k2, 0.)
        return np.column_stack((s-h1, h1-h2, h2))

    @property
    def _n_slopes(self):
        return 1 if self.config.mean == 'linear' else 3

    def _evaluate(self, frame, parameters=None):
        p = self.params_ if parameters is None else np.asarray(parameters)
        s, ratio = self._x(frame)
        B = self._basis(s)
        ns = self._n_slopes
        raw = p[1:1+ns]
        slopes = -np.logaddexp(0., raw)
        mu = p[0]+B@slopes+p[1+ns]*ratio
        gamma0 = p[2+ns]
        gamma1 = p[3+ns] if self.config.scatter == 'loglinear' else 0.
        logscale = gamma0+gamma1*s
        if np.any(np.abs(logscale) > 650):
            raise FloatingPointError('stress extrapolation causes nonrepresentable scatter')
        sigma = np.exp(logscale)
        # Derivatives of location and log scatter wrt all fitted coordinates.
        Jmu = np.zeros((len(s), len(p)))
        Jmu[:, 0] = 1
        Jmu[:, 1:1+ns] = B*(-expit(raw))[None, :]
        Jmu[:, 1+ns] = ratio
        Jscale = np.zeros_like(Jmu)
        Jscale[:, 2+ns] = 1
        if self.config.scatter == 'loglinear':
            Jscale[:, 3+ns] = s
        return mu, sigma, Jmu, Jscale

    def _integrate(self, mu, sigma, y, event, resolution_scale=None):
        return intercept_posterior(mu, sigma, y, event, self.config.nu,
            self.config.prior_sd, self.quadrature_tolerance,
            self.quadrature_order, self.max_quadrature_nodes,resolution_scale)

    def _penalty(self, p):
        ns = self._n_slopes
        raw = p[1:1+ns]
        b = -np.logaddexp(0., raw)
        cr = p[1+ns]
        # Fixed weak ridge on physical segment coefficients, not the arbitrary
        # inverse-softplus coordinates. Intercept and gamma0 are unpenalized.
        value = .001*(b@b+cr*cr)
        gradient = np.zeros(len(p))
        gradient[1:1+ns] = .002*b*(-expit(raw))
        gradient[1+ns] = .002*cr
        if self.config.scatter == 'loglinear':
            value += .5*(p[-1]/.25)**2
            gradient[-1] = p[-1]/(.25**2)
        return float(value), gradient

    def _objective(self, p, frame, indices):
        mu, sigma, Jmu, Jscale = self._evaluate(frame, p)
        y, event = self._outcomes(frame)
        value, gradient = self._penalty(p)
        for ix in indices:
            post = self._integrate(mu[ix], sigma[ix], y[ix], event[ix])
            _, score_mu, score_scale = censored_t_parts(
                mu[ix, None]+post['u'][None, :], sigma[ix, None],
                y[ix, None], event[ix, None], self.config.nu)
            value -= post['log_marginal']
            gradient -= (Jmu[ix].T@(score_mu@post['weight'])+
                         Jscale[ix].T@(score_scale@post['weight']))
        if not np.isfinite(value) or np.any(~np.isfinite(gradient)):
            raise FloatingPointError('nonfinite Student-AFT training objective')
        return float(value), gradient

    def fit(self, frame, sample_weight=None):
        if sample_weight is not None:
            raise ValueError('this model uses proper unit-row likelihood; balance validation by source')
        y, event = self._outcomes(frame)
        if len(frame) < 3 or event.sum() == 0:
            raise ValueError('population fitting needs >=3observations and at least one failure')
        stress = np.asarray(frame.log_stress, float)
        if np.any(~np.isfinite(stress)):
            raise ValueError('finite training stress required')
        self.stress_center_ = float(stress.mean())
        self.stress_sd_ = float(stress.std(ddof=0))
        if self.stress_sd_ <= 1e-10:
            raise ValueError('population fitting requires training stress variation')
        ratio = np.asarray(frame.load_ratio, float)
        good_ratio = ratio[np.isfinite(ratio)]
        self.ratio_median_ = float(np.median(good_ratio)) if len(good_ratio) else 0.
        filled_ratio = np.where(np.isfinite(ratio), ratio, self.ratio_median_)
        self.ratio_center_ = float(filled_ratio.mean())
        s = (stress-self.stress_center_)/self.stress_sd_
        self.knots_ = np.quantile(s, [1/3, 2/3]) if self.config.mean == 'two_knots' else np.array([])
        if frame.dataset_id.isna().any():
            raise ValueError('training statistical condition IDs must not be missing')
        conditions = np.asarray(frame.dataset_id.astype(str))
        indices = [np.flatnonzero(conditions==c) for c in sorted(set(conditions))]
        if 'group_id' in frame:
            groups = np.asarray(frame.group_id.astype(str))
            if any(len(set(groups[ix])) != 1 for ix in indices):
                raise ValueError('one statistical condition must belong to one source family')
        # Failure-only linear regression is an initialization, never the final
        # likelihood; both starts use exactly the same censored objective.
        X = np.column_stack((np.ones(len(s)), s, filled_ratio-self.ratio_center_))
        initial = np.linalg.lstsq(X[event==1], y[event==1], rcond=None)[0]
        physical_slope = float(np.clip(-initial[1], .05, 4.))
        raw_slope = float(np.log(np.expm1(physical_slope)))
        residual = y-X@np.r_[initial[0], -physical_slope, initial[2]]
        init_scale = float(np.clip(np.std(residual[event==1]), .1, .8))
        ns = self._n_slopes
        starts = []
        for scale_multiplier in (1., 2.):
            p = np.r_[initial[0], np.repeat(raw_slope, ns), np.clip(initial[2], -10, 10),
                      np.log(min(1.5, init_scale*scale_multiplier))]
            if self.config.scatter == 'loglinear':
                p = np.r_[p, 0.]
            starts.append(p)
        bounds = [(None, None)]+[(None, None)]*ns+[(-20., 20.), (np.log(.05), np.log(2.))]
        if self.config.scatter == 'loglinear':
            bounds.append((-.5, .5))
        results = [minimize(self._objective, p, args=(frame, indices), jac=True,
                    method='L-BFGS-B', bounds=bounds,
                    options=dict(maxiter=self.max_iter, ftol=1e-10, gtol=1e-5, maxls=40))
                   for p in starts]
        successful = [r for r in results if r.success and np.isfinite(r.fun)]
        if not successful:
            # No alternative model, query data, hidden fallback, or silent use of
            # failed coefficients. The runner must record a fit failure.
            raise FloatingPointError('Student-AFT population fit failed: '+
                '; '.join(str(r.message) for r in results))
        best = min(successful, key=lambda r: r.fun)
        self.params_ = best.x.copy()
        self._posterior_cache.clear()
        mu, sigma, _, _ = self._evaluate(frame)
        certificates = [self._integrate(mu[ix], sigma[ix], y[ix], event[ix]) for ix in indices]
        self.fit_receipt_ = dict(success=True, config=self.config.receipt(),
            training_rows=len(frame), training_conditions=len(indices),
            training_sources=sorted(frame.group_id.astype(str).unique()) if 'group_id' in frame else [],
            objective=float(best.fun), n_iter=int(best.nit),
            gradient_inf=float(np.max(np.abs(best.jac))),
            stress_center_train=self.stress_center_, stress_sd_train=self.stress_sd_,
            ratio_median_train=self.ratio_median_, ratio_center_train=self.ratio_center_,
            ratio_missing_train=int(np.sum(~np.isfinite(ratio))),
            knots_standardized_log_stress_train=self.knots_.tolist(),
            unit_row_likelihood=True, condition_marginals_summed=True,
            source_balancing='validation score only; population likelihood is unit-row',
            population_parameter_uncertainty_integrated=False,
            target_intercept_uncertainty_integrated=True,
            natural_scatter_integrated=True, target_slope_or_scatter_updated=False,
            fixed_ridge='0.001*sum(physical_segment_slopes**2+cR**2)+0.5*(gamma1/0.25)**2',
            scale_is_student_t_standard_deviation=False,
            uncapped_arithmetic_mean_life='infinite for finite-nu Student log-life; no mean-life shortcut',
            max_quadrature_relative_error=max(p['quadrature_relative_error'] for p in certificates),
            max_tail_mass_bound=max(p['tail_mass_bound'] for p in certificates),
            max_quadrature_nodes=max(p['nodes'] for p in certificates),
            quadrature_tolerance=self.quadrature_tolerance,
            parameter_bounds=bounds,
            at_bound=[i for i,(v,(lo,hi)) in enumerate(zip(best.x,bounds))
                      if (lo is not None and np.isclose(v,lo)) or
                         (hi is not None and np.isclose(v,hi))],
            starts=[dict(success=bool(r.success), objective=float(r.fun), n_iter=int(r.nit),
                         message=str(r.message)) for r in results])
        return self

    def support_posterior(self, support=None, resolution_scale=None):
        if not hasattr(self, 'params_'):
            raise RuntimeError('fit the population model before prediction')
        if support is None or len(support) == 0:
            return self._integrate([], [], [], [],resolution_scale)
        if ('dataset_id' not in support or support.dataset_id.isna().any() or
                support.dataset_id.nunique(dropna=False) != 1):
            raise ValueError('selected support must belong to one statistical condition')
        mu, sigma, _, _ = self._evaluate(support)
        y, event = self._outcomes(support)
        key = hashlib.sha256(self.params_.tobytes()+mu.tobytes()+sigma.tobytes()+
            y.tobytes()+event.tobytes()+json.dumps(self.config.receipt(),sort_keys=True).encode()+
            str((self.quadrature_tolerance,self.quadrature_order,self.max_quadrature_nodes,resolution_scale)).encode()).hexdigest()
        if key not in self._posterior_cache:
            if len(self._posterior_cache) >= 32:
                self._posterior_cache.pop(next(iter(self._posterior_cache)))
            self._posterior_cache[key] = self._integrate(mu, sigma, y, event,resolution_scale)
        return self._posterior_cache[key]

    def _predict_setup(self, query, support):
        if not hasattr(self,'params_'):
            raise RuntimeError('fit the population model before prediction')
        mu, sigma, _, _ = self._evaluate(query)
        post = self.support_posterior(support,float(np.min(sigma)) if len(sigma) else None)
        if support is not None and len(support) and 'dataset_id' in query:
            if query.dataset_id.nunique(dropna=False) != 1 or str(query.dataset_id.iloc[0]) != str(support.dataset_id.iloc[0]):
                raise ValueError('query and selected support must be the same target condition')
        self.last_prediction_receipt_ = dict(selected_support_n=0 if support is None else len(support),
            selected_support_failures=0 if support is None else int(np.asarray(support.event).sum()),
            posterior_mean=post['mean'],posterior_variance=post['variance'],
            log_support_evidence=post['log_marginal'],quadrature_nodes=post['nodes'],
            quadrature_relative_error=post['quadrature_relative_error'],
            omitted_tail_relative_bound=post['tail_mass_bound'],
            population_parameter_uncertainty_integrated=False,
            natural_and_target_intercept_uncertainty_integrated=True,
            query_outcomes_read=False)
        return mu, sigma, post

    def predict_cdf(self, log_y, query, support=None):
        mu, sigma, post = self._predict_setup(query, support)
        y = np.broadcast_to(np.asarray(log_y,float), (len(query),))
        if np.any(np.isnan(y)):
            raise ValueError('CDF endpoints must not be NaN')
        z = (y[:,None]-mu[:,None]-post['u'][None,:])/sigma[:,None]
        cdf = ndtr(z) if np.isinf(self.config.nu) else stdtr(self.config.nu,z)
        result = np.clip(cdf@post['weight'],0,1)
        return np.where(y==np.inf,1.,np.where(y==-np.inf,0.,result))

    def predict_quantiles(self, query, support=None, alphas=(.1,)):
        alpha = np.asarray(alphas,float).reshape(-1)
        if not len(alpha) or np.any(~np.isfinite(alpha)) or np.any((alpha<=0)|(alpha>=1)):
            raise ValueError('quantile levels must lie strictly between0and1')
        mu, sigma, post = self._predict_setup(query, support)
        z_alpha = norm.ppf(alpha) if np.isinf(self.config.nu) else stdtrit(self.config.nu,alpha)
        u, w = post['u'], post['weight']
        output = np.empty((len(query),len(alpha)))
        for i,(m,s) in enumerate(zip(mu,sigma)):
            for j,(a,z) in enumerate(zip(alpha,z_alpha)):
                def root(value):
                    arg = (value-m-u)/s
                    cdf = ndtr(arg) if np.isinf(self.config.nu) else stdtr(self.config.nu,arg)
                    return float(cdf@w-a)
                lo,hi = m+u.min()+s*z-1e-10, m+u.max()+s*z+1e-10
                output[i,j] = brentq(root,lo,hi,xtol=2e-10)
        return output

    def predict_location(self, query, support=None):
        return self.predict_quantiles(query,support,(.5,))[:,0]

    def predict_log_score(self, query, support=None):
        mu,sigma,post = self._predict_setup(query,support)
        y,event = self._outcomes(query)
        self.last_prediction_receipt_['query_outcomes_read'] = True
        self.last_prediction_receipt_['query_outcomes_used_only_for_scoring'] = True
        self.last_prediction_receipt_['query_outcomes_used_for_model_or_support_update'] = False
        loglik = censored_t_parts(mu[:,None]+post['u'][None,:],sigma[:,None],
                                  y[:,None],event[:,None],self.config.nu)[0]
        with np.errstate(divide='ignore'):
            return logsumexp(loglik+np.log(post['weight'])[None,:],axis=1)
