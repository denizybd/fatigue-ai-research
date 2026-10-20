"""A censored normal-normal random-fatigue-limit baseline.

Pascual and Meeker (1999), DOI 10.1080/00401706.1999.10485925,
sections 2 and 3.1 support this distributional variant. This is not a replica
of Trombley et al.'s Weibull RFL implementation. Logs in this module are base
10. Population parameters are plug-in estimates; the optional target update
integrates only a scalar life shift, with a separately supplied training prior.
"""
from __future__ import annotations

import hashlib
import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.optimize import brentq, minimize
from scipy.special import log_ndtr, logsumexp, ndtr, ndtri_exp
from scipy.stats import norm

from .v2_models import CensoredBasquin, _frame_arrays, intercept_posterior

LOG2PI = np.log(2*np.pi)
LN10 = np.log(10.)


def _legendre(order):
    x, w = leggauss(order)
    return (x+1)/2, w/2


class NormalNormalRFL:
    """Positive random fatigue limit and negative conditional stress slope.

    log10(Gamma) ~ N(mu_gamma, tau_gamma**2). If S > Gamma,
    log10(N) = a + b*log10((S-Gamma)/Sref) + c*(R-Rbar) + u + eps,
    where b < 0, eps ~ N(0, sigma**2). Otherwise N=infinity.

    ``shift_prior_sd`` must be fixed using training data alone (the benchmark
    uses its training-only hierarchical Basquin tau). At zero it disables the
    target adapter. The target life shift does not change the fatigue-limit
    distribution. ``fallback`` is a predetermined numerical fallback, never
    selected by query performance; its activation is explicit in the receipt.
    """
    parameter_names = ("a", "b", "c_R", "log_sigma", "mu_log10_gamma",
                       "log_tau_log10_gamma")

    def __init__(self, max_iter=500, nodes=96, shift_prior_sd=0.,
                 min_sigma=.025, max_sigma=3., l2=.001, fallback=True):
        self.max_iter = max_iter
        self.nodes = int(nodes)
        if self.nodes < 16:
            raise ValueError("at least 16 fatigue-limit quadrature nodes required")
        self.shift_prior_sd = float(shift_prior_sd)
        if not np.isfinite(self.shift_prior_sd) or self.shift_prior_sd < 0:
            raise ValueError("finite nonnegative training shift prior required")
        self.min_sigma, self.max_sigma = min_sigma, max_sigma
        self.l2, self.fallback = l2, fallback
        r, w = _legendre(self.nodes)
        # A sine-square probability map clusters resolution at both truncated
        # normal endpoints, where inverse-normal derivatives are singular.
        self._t = np.sin(.5*np.pi*r)**2
        self._w = w*.5*np.pi*np.sin(np.pi*r)
        self._w /= self._w.sum()
        self._logw = np.log(self._w)
        self._fallback = None
        self._posterior_cache = {}

    def _x(self, frame):
        return _frame_arrays(frame, outcomes=False,
                             load_ratio_fill=self.ratio_median_)

    def _kernel(self, x, params=None):
        """Smooth quadrature conditional on Gamma<S, with its exact mass."""
        p = self.params_ if params is None else np.asarray(params, float)
        a, b, c, logsigma, mugamma, logtau = p
        tau = np.exp(logtau)
        logstress = x[:, 0]
        zlimit = (logstress-mugamma)/tau
        logmass = log_ndtr(zlimit)
        # P(Gamma < S) * U transforms the entire lower normal tail. Unlike
        # masking a fixed Hermite grid, the likelihood is smooth in Gamma/S.
        z = ndtri_exp(logmass[:, None]+np.log(self._t)[None, :])
        logratio = LN10*(mugamma+tau*z-logstress[:, None])
        logratio = np.minimum(logratio, -np.finfo(float).eps)
        loggap = logstress[:, None]+np.log(-np.expm1(logratio))/LN10
        mu = a+b*(loggap-self.log_stress_ref_)+c*(x[:, 1, None]-self.ratio_center_)
        return {"mu": mu, "logmass": logmass,
                "log_infinite": log_ndtr(-zlimit), "sigma": np.exp(logsigma)}

    def _logparts(self, kernel, y, u):
        """Finite log density and survival at row endpoints, for each shift."""
        y, u = np.asarray(y, float), np.atleast_1d(u).astype(float)
        z = (y[:, None, None]-kernel['mu'][:, None, :]-u[None, :, None])/kernel['sigma']
        logpdf = (kernel['logmass'][:, None]
                  +logsumexp(self._logw[None, None, :]-.5*z*z
                            -.5*LOG2PI-np.log(kernel['sigma']), axis=2))
        logsfinite = (kernel['logmass'][:, None]
                      +logsumexp(self._logw[None, None, :]+log_ndtr(-z), axis=2))
        logsf = np.logaddexp(kernel['log_infinite'][:, None], logsfinite)
        return logpdf, logsf

    def _objective(self, params, x, y, event, weight):
        kernel = self._kernel(x, params)
        pdf, sf = self._logparts(kernel, y, np.array([0.]))
        ll = np.where(event == 1, pdf[:, 0], sf[:, 0])
        return float(-weight@ll+.5*self.l2*np.dot(params[1:3], params[1:3]))

    def fit(self, frame, sample_weight=None):
        self._posterior_cache.clear()
        ratio = np.asarray(frame.load_ratio, float)
        finite = ratio[np.isfinite(ratio)]
        self.ratio_median_ = float(np.median(finite)) if len(finite) else 0.
        x, y, event = _frame_arrays(frame, load_ratio_fill=self.ratio_median_)
        if not len(y) or not np.any(event == 1):
            raise ValueError("RFL fitting requires finite training data and a failure")
        self.log_stress_ref_, self.ratio_center_ = np.mean(x, axis=0)
        # Source-balanced working likelihood; this does not certify sources
        # independent and is not the unweighted original-paper likelihood.
        groups = np.asarray(frame.group_id.astype(str))
        _, inverse, counts = np.unique(groups, return_inverse=True, return_counts=True)
        w = 1/counts[inverse]
        if sample_weight is not None:
            w = np.asarray(sample_weight, float)
            if len(w) != len(y) or np.any(~np.isfinite(w)) or np.any(w < 0) or w.sum() <= 0:
                raise ValueError("invalid training weights")
        w = w/w.sum()
        base = CensoredBasquin(max_iter=self.max_iter, min_sigma=self.min_sigma,
                               max_sigma=self.max_sigma, l2=self.l2).fit(frame, sample_weight=w)
        # Starts and bounds depend only on training covariates/outcomes.
        lsmin, lsmax = np.min(x[:, 0]), np.max(x[:, 0])
        bounds = [(-30., 50.), (-40., -.02), (-20., 20.),
                  (np.log(self.min_sigma), np.log(self.max_sigma)),
                  (lsmin-2., lsmax+.5), (np.log(.02), np.log(.75))]
        starts = []
        for gap, tau in ((.7, .12), (.25, .25), (.08, .08)):
            mugamma = lsmin-gap
            gamma_ratio = 10**(mugamma-self.log_stress_ref_)
            a = base.params_[0]-base.params_[1]*np.log10(1-gamma_ratio)
            start = np.array([a, base.params_[1], base.params_[2],
                              np.log(base.sigma_), mugamma, np.log(tau)])
            start = np.clip(start, np.asarray(bounds)[:, 0]+1e-7,
                            np.asarray(bounds)[:, 1]-1e-7)
            r = minimize(self._objective, start, args=(x, y, event, w),
                         method='L-BFGS-B', bounds=bounds,
                         options={'maxiter': self.max_iter, 'ftol': 2e-10,
                                  'gtol': 2e-5, 'maxls': 40})
            starts.append(r)
        valid = [r for r in starts if r.success and np.isfinite(r.fun)
                 and np.all(np.isfinite(r.x))]
        chosen = min(valid, key=lambda r: r.fun) if valid else None
        if chosen is None and not self.fallback:
            raise FloatingPointError("no converged RFL training start; fallback disabled")
        self._fallback = base if chosen is None else None
        # Keep a finite diagnostic parameter vector even under explicit fallback.
        selected = chosen if chosen is not None else min(starts, key=lambda r: r.fun)
        self.params_ = selected.x.copy()
        self.sigma_ = float(np.exp(self.params_[3])) if chosen is not None else base.sigma_
        self.tau_gamma_ = float(np.exp(self.params_[5]))
        hits = [name for name, value, (lo, hi) in zip(self.parameter_names, self.params_, bounds)
                if min(abs(value-lo), abs(hi-value)) <= 1e-4*max(1., hi-lo)]
        self.fit_receipt_ = {
            'model': 'normal-normal RFL with load-ratio location extension',
            'success': chosen is not None, 'fallback_active': chosen is None,
            'fallback_model': 'censored Basquin' if chosen is None else None,
            'fallback_rule': 'all three fixed training starts fail numerical convergence',
            'n_train': len(y), 'n_failures': int(event.sum()),
            'n_distinct_stresses': int(len(np.unique(x[:, 0]))),
            'n_source_blocks': int(len(counts)),
            'source_balanced_working_likelihood': True,
            'regularization': self.l2, 'quadrature_nodes': self.nodes,
            'log_stress_ref_train': float(self.log_stress_ref_),
            'ratio_center_train': float(self.ratio_center_),
            'ratio_median_train': self.ratio_median_,
            'ratio_missing_train': int(np.sum(~np.isfinite(ratio))),
            'shift_prior_sd_training_supplied': self.shift_prior_sd,
            'population_uncertainty_integrated': False,
            'bounds': {n: [float(a), float(b)] for n, (a, b) in zip(self.parameter_names, bounds)},
            'bound_hits': hits,
            'identifiability_warning': bool(hits or len(np.unique(x[:, 0])) < 5 or event.sum() < 12),
            'starts': [{'success': bool(r.success), 'objective': float(r.fun),
                        'n_iter': int(r.nit), 'message': str(r.message),
                        'gradient_inf': float(np.max(np.abs(r.jac))),
                        'params': [float(v) for v in r.x]} for r in starts],
            'params': {n: float(v) for n, v in zip(self.parameter_names, self.params_)}}
        return self

    def _posterior(self, support=None):
        """Cache only revealed support outcomes, never acquisition/query rows."""
        if support is None or len(support) == 0 or self.shift_prior_sd == 0:
            return self._posterior_uncached(support)
        x, y, event = _frame_arrays(support, load_ratio_fill=self.ratio_median_)
        digest = hashlib.sha256(np.column_stack((x, y, event)).tobytes()).digest()
        key = (digest, self.shift_prior_sd, self.params_.tobytes(), self._fallback is not None)
        if key not in self._posterior_cache:
            if len(self._posterior_cache) >= 256:
                self._posterior_cache.pop(next(iter(self._posterior_cache)))
            self._posterior_cache[key] = self._posterior_uncached(support)
        return self._posterior_cache[key]

    def _posterior_uncached(self, support=None):
        tau = self.shift_prior_sd
        if tau == 0:
            return {'u': np.array([0.]), 'weight': np.array([1.]), 'mean': 0.,
                    'variance': 0., 'log_marginal': 0., 'tail_mass_bound': 0.}
        if support is None or len(support) == 0:
            # Normal convolution for no-support prediction is handled exactly
            # by _predict_components, so this discretization is not used there.
            t, w = _legendre(96)
            u = norm.ppf(t)*tau
            return {'u': u, 'weight': w, 'mean': 0., 'variance': tau*tau,
                    'log_marginal': 0., 'tail_mass_bound': 0.}
        x, y, event = _frame_arrays(support, load_ratio_fill=self.ratio_median_)
        if self._fallback is not None:
            return intercept_posterior(self._fallback.predict_location(support), y,
                                       event, self._fallback.sigma_, tau, nodes=61)
        kernel = self._kernel(x)
        def logposterior(u):
            u = np.atleast_1d(u)
            pdf, sf = self._logparts(kernel, y, u)
            return np.where(event[:, None] == 1, pdf, sf).sum(axis=0) + norm.logpdf(u, scale=tau)
        # Mixtures need not be log-concave. A partitioned global rule avoids
        # selecting a single posterior mode. No peak is sharper than the normal
        # error/prior curvature bound; order-8 intervals <=4 such sd resolve it.
        minscale = 1/np.sqrt(1/tau**2+len(y)/self.sigma_**2)
        residual = np.abs(y-np.median(kernel['mu'], axis=1))
        radius = max(10*tau, float(np.max(residual))+10*self.sigma_)
        loglike_upper = int(event.sum())*max(0., -np.log(self.sigma_)-.5*LOG2PI)
        for _ in range(7):
            intervals = max(16, int(np.ceil(2*radius/(4*minscale))))
            if intervals > 12000:
                raise FloatingPointError("target posterior requires excessive quadrature resolution")
            edges = np.linspace(-radius, radius, intervals+1)
            t, w = _legendre(8)
            width = np.diff(edges)
            u = (edges[:-1, None]+width[:, None]*t).ravel()
            logw = np.log((width[:, None]*w).ravel())
            # Chunking bounds memory for very small training scatter.
            lp = np.concatenate([logposterior(q) for q in np.array_split(u, max(1, int(np.ceil(len(u)/512))))])
            lm = float(logsumexp(lp+logw))
            tail_logbound = np.log(2.)+log_ndtr(-radius/tau)+loglike_upper-lm
            if tail_logbound < np.log(1e-10):
                break
            radius *= 1.7
        else:
            raise FloatingPointError("target posterior normal-prior tail bound failed")
        weight = np.exp(lp+logw-lm)
        # Remove negligible nodes, retaining at least 1-1e-12 posterior mass.
        keep = weight > 1e-14
        weight, u = weight[keep], u[keep]
        weight /= weight.sum()
        mean = float(weight@u)
        return {'u': u, 'weight': weight, 'mean': mean,
                'variance': float(weight@((u-mean)**2)), 'log_marginal': lm,
                'tail_mass_bound': float(np.exp(tail_logbound)),
                'quadrature_nodes_retained': len(u), 'radius': radius}

    def support_posterior(self, support=None):
        """Return scalar-shift posterior and integration receipts."""
        return self._posterior(support)

    def _predict_components(self, query, support=None):
        kernel = self._kernel(self._x(query))
        empty = support is None or len(support) == 0
        if empty:
            # u+eps is exactly normal. No-support k0 uses the SAME training
            # shift prior as positive k, rather than discarding target variance.
            kernel['sigma'] = np.hypot(kernel['sigma'], self.shift_prior_sd)
            return kernel, {'u': np.array([0.]), 'weight': np.array([1.])}
        return kernel, self._posterior(support)

    def failure_probability(self, query):
        """P(N<infinity); the complement is a literal atom at infinity."""
        if self._fallback is not None:
            return np.ones(len(query))
        return np.exp(self._kernel(self._x(query))['logmass'])

    def _fallback_predict(self, query, support=None):
        mu = self._fallback.predict_location(query)
        if support is None or len(support) == 0:
            return mu, np.hypot(self._fallback.sigma_, self.shift_prior_sd), None
        return mu, self._fallback.sigma_, self._posterior(support)

    def predict_cdf(self, log_y, query, support=None):
        """CDF at finite log10 lives; positive infinity includes its atom."""
        y = np.broadcast_to(np.asarray(log_y, float), (len(query),))
        if np.any(np.isnan(y)):
            raise ValueError("log life must not be NaN")
        if self._fallback is not None:
            mu, sigma, post = self._fallback_predict(query, support)
            if post is None:
                return ndtr((y-mu)/sigma)
            return ndtr((y[:, None]-mu[:, None]-post['u'][None, :])/sigma)@post['weight']
        kernel, post = self._predict_components(query, support)
        value = np.empty(len(query))
        for i in range(len(query)):
            z = (y[i]-kernel['mu'][i, None, :]-post['u'][:, None])/kernel['sigma']
            value[i] = np.exp(kernel['logmass'][i])*np.sum(post['weight'][:, None]*self._w*ndtr(z))
        return np.where(np.isposinf(y), 1., np.clip(value, 0., 1.))

    def predict_quantiles(self, query, support=None, alphas=(.1,)):
        """Unconditional log10-life quantiles, including infinity when needed."""
        alphas = np.asarray(alphas, float)
        if alphas.ndim != 1 or np.any((alphas <= 0) | (alphas >= 1)):
            raise ValueError("quantile levels must lie strictly between zero and one")
        if self._fallback is not None:
            mu, sigma, post = self._fallback_predict(query, support)
            if post is None:
                return mu[:, None]+sigma*norm.ppf(alphas)[None, :]
            mus = mu[:, None]+post['u'][None, :]
            mass = np.ones(len(query))
        else:
            kernel, post = self._predict_components(query, support)
            sigma = kernel['sigma']
            mus = kernel['mu'][:, :, None]+post['u'][None, None, :]
            mass = np.exp(kernel['logmass'])
        out = np.full((len(query), len(alphas)), np.inf)
        for i in range(len(query)):
            if self._fallback is None:
                weights = self._w[:, None]*post['weight'][None, :]
            else:
                weights = post['weight']
            loc = mus[i]
            def cdf(y):
                return mass[i]*np.sum(weights*ndtr((y-loc)/sigma))
            lo, hi = float(np.min(loc)-12*sigma), float(np.max(loc)+12*sigma)
            for j, alpha in enumerate(alphas):
                if alpha < mass[i]:
                    out[i, j] = brentq(lambda y: cdf(y)-alpha, lo, hi, xtol=2e-9)
        return out

    def predict_location(self, query, support=None):
        """Predictive median; may legitimately be positive infinity."""
        return self.predict_quantiles(query, support, (.5,))[:, 0]

    def predict_log_score(self, query, support=None):
        _, y, event = _frame_arrays(query, load_ratio_fill=self.ratio_median_)
        if self._fallback is not None:
            mu, sigma, post = self._fallback_predict(query, support)
            if post is None:
                post = {'u': np.array([0.]), 'weight': np.array([1.])}
            z = (y[:, None]-mu[:, None]-post['u'][None, :])/sigma
            ll = np.where(event[:, None] == 1, norm.logpdf(z)-np.log(sigma), log_ndtr(-z))
        else:
            kernel, post = self._predict_components(query, support)
            pdf, sf = self._logparts(kernel, y, post['u'])
            ll = np.where(event[:, None] == 1, pdf, sf)
        return logsumexp(ll+np.log(post['weight'])[None, :], axis=1)
