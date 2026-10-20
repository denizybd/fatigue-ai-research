"""New tuning wrappers around frozen phase3 controls; no population fitting here.

Target prior multipliers never change the training fit. Local slope updating
uses a constrained MAP and untruncated Gaussian curvature approximation, not
an exact posterior. Matched intercept is unregularized and unavailable for
all-runout supports. Those limitations are retained and exposed.
"""
from __future__ import annotations
from copy import copy
import numpy as np
from scipy.optimize import minimize
from scipy.special import ndtr
from scipy.stats import norm
from src.v2_models import _ll_parts, FixedSlopeShiftPredictor
from src.v3_design import design

PRIOR_MULTIPLIERS=(.25,.5,1.,2.,4.)


class LocalSlopeAdapter:
    def __init__(self,base,multiplier=1.):
        if multiplier not in PRIOR_MULTIPLIERS:raise ValueError('unfrozen multiplier')
        self.base=base;self.multiplier=float(multiplier);self._cache={}

    def posterior(self,support):
        variance=(self.multiplier*np.array([self.base.tau_,max(1.,abs(self.base.params_[1])/2)]))**2
        precision=np.diag(1/variance)
        if support is None or not len(support):
            return np.zeros(2),np.diag(variance),dict(success=True,n=0)
        key=support[['row_id','log_stress','load_ratio','log_life','event']].to_csv(index=False)
        if key in self._cache:return self._cache[key]
        X=design(support,self.base);mu=self.base.predict_location(support)
        y=support.log_life.to_numpy();e=support.event.to_numpy()
        def objective(u):
            ll,score,_,_=_ll_parts(mu+X@u,self.base.sigma_,y,e)
            return float(-ll.sum()+.5*u@precision@u),-X.T@score+precision@u
        bounds=[(None,None),(-50-self.base.params_[1],-1e-4-self.base.params_[1])]
        fit=minimize(objective,np.zeros(2),jac=True,method='L-BFGS-B',bounds=bounds,
            options=dict(maxiter=500,ftol=1e-12,gtol=1e-7,maxls=40))
        initial_status=str(fit.message);recovered=False
        if not fit.success:
            fit=minimize(objective,fit.x,jac=True,method='SLSQP',bounds=bounds,
                options=dict(maxiter=500,ftol=1e-11));recovered=True
        if not fit.success or not np.isfinite(fit.fun):
            raise FloatingPointError('local MAP fit failed: '+str(fit.message))
        curvature=_ll_parts(mu+X@fit.x,self.base.sigma_,y,e)[3]
        covariance=np.linalg.inv(precision+X.T@(curvature[:,None]*X))
        receipt=dict(success=True,n=len(support),second_solver_used=recovered,
            initial_solver_message=initial_status,
            slope_at_bound=bool(np.isclose(fit.x[1]+self.base.params_[1],-1e-4)),
            slope_at_lower_bound=bool(np.isclose(fit.x[1]+self.base.params_[1],-50.)),
            gradient_inf=float(np.max(np.abs(fit.jac))),
            multiplier=self.multiplier,prior_variances=variance.tolist(),
            approximation='constrained MAP plus untruncated Gaussian curvature')
        result=(fit.x,covariance,receipt)
        if len(self._cache)>=64:self._cache.pop(next(iter(self._cache)))
        self._cache[key]=result
        return result

    def moments(self,query,support=None):
        u,V,receipt=self.posterior(support);X=design(query,self.base)
        self.last_prediction_receipt_=receipt
        mu=self.base.predict_location(query)+X@u
        sd=np.sqrt(self.base.sigma_**2+np.einsum('ij,jk,ik->i',X,V,X))
        return mu,sd

    def predict_quantiles(self,query,support=None,alphas=(.1,)):
        mu,sd=self.moments(query,support)
        return mu[:,None]+sd[:,None]*norm.ppf(alphas)[None,:]

    def predict_log_score(self,query,support=None):
        mu,sd=self.moments(query,support)
        return _ll_parts(mu,sd,query.log_life.to_numpy(),query.event.to_numpy())[0]

    def predict_cdf(self,log_y,query,support=None):
        mu,sd=self.moments(query,support)
        return ndtr((np.asarray(log_y)-mu)/sd)


class MatchedInterceptAdapter:
    """Frozen matched-intercept control with explicit k0 reference and scoring."""
    def __init__(self,hier):
        self.base=hier;self.adapter=FixedSlopeShiftPredictor(hier)

    def moments(self,query,support=None):
        if support is None or not len(support):
            self.last_prediction_receipt_=dict(status='hierarchical_zero_support_reference')
            return self.base.predict_location(query),np.full(len(query),np.hypot(self.base.sigma_,self.base.tau_))
        shift,var,status=self.adapter._shift(support)
        self.last_prediction_receipt_=dict(status=status,shift=shift,variance=var)
        return self.base.predict_location(query)+shift,np.full(len(query),np.sqrt(self.base.sigma_**2+var))

    def predict_quantiles(self,query,support=None,alphas=(.1,)):
        mu,sd=self.moments(query,support)
        return mu[:,None]+sd[:,None]*norm.ppf(alphas)[None,:]

    def predict_log_score(self,query,support=None):
        mu,sd=self.moments(query,support)
        return _ll_parts(mu,sd,query.log_life.to_numpy(),query.event.to_numpy())[0]

    def predict_cdf(self,log_y,query,support=None):
        mu,sd=self.moments(query,support)
        return ndtr((np.asarray(log_y)-mu)/sd)


def reference_candidate(models,kind,multiplier=1.):
    """Clone adapter-level state only; frozen fit/parameters remain unchanged."""
    if kind=='pooled':return models['pooled']
    if kind=='matched_intercept':return MatchedInterceptAdapter(models['hierarchical'])
    if kind=='local_slope':return LocalSlopeAdapter(models['hierarchical'],multiplier)
    if multiplier not in PRIOR_MULTIPLIERS:raise ValueError('unfrozen multiplier')
    result=copy(models[kind])
    if kind=='rfl':
        result.shift_prior_sd=multiplier*models['hierarchical'].tau_
        result._posterior_cache={}
    elif kind in ('hierarchical','curved_hierarchical'):
        result.tau_=multiplier*models[kind].tau_
    else:raise ValueError(kind)
    return result


def control_grid():
    return [dict(candidate_id=kind,kind=kind,multiplier=1.) for kind in ('pooled','matched_intercept')]+[
        dict(candidate_id=f'{kind}_m{m:g}',kind=kind,multiplier=m)
        for kind in ('hierarchical','curved_hierarchical','rfl','local_slope') for m in PRIOR_MULTIPLIERS]
