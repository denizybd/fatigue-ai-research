"""Monotone, right-censored Basquin baselines for the v2 few-shot benchmark.

All lives and stresses use log10. A database condition is a working statistical
group, not a certified production batch. Hierarchical fitting is a source-
balanced composite marginal likelihood: conditions from the same source are
not asserted independent. The target-condition intercept is integrated out;
population parameter uncertainty is NOT integrated out. No coverage theorem,
Owen tolerance bound, or full Bayesian population fit is claimed here.
"""
from __future__ import annotations

import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.optimize import brentq, minimize
from scipy.special import log_ndtr, logsumexp, ndtr
from scipy.stats import norm

LOG2PI = np.log(2 * np.pi)


def _frame_arrays(frame, outcomes=True, load_ratio_fill=None):
    ratio=np.asarray(frame.load_ratio,float).copy()
    if load_ratio_fill is not None:
        ratio[~np.isfinite(ratio)]=load_ratio_fill
    x = np.column_stack((np.asarray(frame.log_stress, float),ratio))
    if not np.all(np.isfinite(x)):
        raise ValueError('log_stress/load_ratio must be finite')
    if not outcomes:
        return x
    y = np.asarray(frame.log_life, float)
    e = np.asarray(frame.event, float)
    if not np.all(np.isfinite(y)) or not np.all(np.isin(e, [0., 1.])):
        raise ValueError('finite log_life and binary event are required')
    return x, y, e


def _ll_parts(mu, sigma, y, event):
    """Per-row likelihood, location score, log-scatter score and curvature."""
    z = (y - mu) / sigma
    log_pdf = -.5*z*z - .5*LOG2PI
    log_sf = log_ndtr(-z)
    hazard = np.exp(log_pdf - log_sf)
    ll = event*(log_pdf - np.log(sigma)) + (1-event)*log_sf
    loc_score = (event*z + (1-event)*hazard) / sigma
    scale_score = event*(z*z-1) + (1-event)*z*hazard
    # h'(z)=h(z)*(h(z)-z), mathematically positive. Clip tiny rounding error.
    curv = (event + (1-event)*np.maximum(hazard*(hazard-z), 0)) / sigma**2
    return ll, loc_score, scale_score, curv


def intercept_posterior(mu, y, event, sigma, tau, nodes=41):
    """Adaptive Gauss-Hermite integration of a proper scalar-intercept posterior.

The log posterior is strictly concave. Node centering and scaling follow its
unique mode and observed curvature. All-failure data are conjugate and are
handled analytically; all-runout data retain a proper posterior via the prior.
The returned log marginal includes all density normalization constants.
"""
    mu, y, event = [np.asarray(a, float) for a in (mu, y, event)]
    if not (sigma > 0 and tau > 0) or len(mu) != len(y) or len(y) != len(event):
        raise ValueError('positive scatters and matching arrays required')
    if len(y) == 0:
        gx, gw = hermgauss(nodes)
        return {'u': np.sqrt(2)*tau*gx, 'weight': gw/np.sqrt(np.pi),
                'log_marginal': 0., 'mean': 0., 'variance': tau*tau,
                'mode': 0., 'curvature': 1/tau**2}
    if np.all(event == 1):
        variance = 1/(1/tau**2 + len(y)/sigma**2)
        mean = variance*np.sum(y-mu)/sigma**2
        residual = y-mu
        lm = (-len(y)*(.5*LOG2PI + np.log(sigma))
              -.5*np.dot(residual,residual)/sigma**2
              -.5*np.log(1+len(y)*tau**2/sigma**2)
              +.5*mean**2/variance)
        gx,gw = hermgauss(nodes)
        return {'u': mean+np.sqrt(2*variance)*gx, 'weight': gw/np.sqrt(np.pi),
                'log_marginal': float(lm), 'mean': float(mean),
                'variance': float(variance), 'mode': float(mean),
                'curvature': float(1/variance)}

    def derivative(u):
        return _ll_parts(mu+u,sigma,y,event)[1].sum()-u/tau**2
    radius = max(1., 8*tau, np.max(np.abs(y-mu))+8*sigma)
    lo,hi = -radius,radius
    for _ in range(20):
        if derivative(lo)>0 and derivative(hi)<0:
            break
        lo*=2; hi*=2
    else:
        raise FloatingPointError('failed to bracket posterior mode')
    mode = brentq(derivative,lo,hi,xtol=1e-11)
    curvature = 1/tau**2+_ll_parts(mu+mode,sigma,y,event)[3].sum()
    scale = 1/np.sqrt(curvature)
    gx,gw = hermgauss(nodes)
    u = mode+np.sqrt(2)*scale*gx
    ll = _ll_parts(mu[:,None]+u[None,:],sigma,y[:,None],event[:,None])[0].sum(0)
    lp = ll-.5*(u/tau)**2-np.log(tau)-.5*LOG2PI
    logw = np.log(gw)+lp+gx*gx+np.log(np.sqrt(2)*scale)
    lm = logsumexp(logw)
    w = np.exp(logw-lm)
    mean = float(w@u)
    var = float(w@((u-mean)**2))
    return {'u':u,'weight':w,'log_marginal':float(lm),'mean':mean,
            'variance':var,'mode':float(mode),'curvature':float(curvature)}


class CensoredBasquin:
    """Pooled lognormal Basquin, with a negative stress slope and proper runouts."""
    def __init__(self, max_iter=1500, min_sigma=.02, max_sigma=3., l2=.001):
        self.max_iter=max_iter;self.min_sigma=min_sigma;self.max_sigma=max_sigma
        self.l2=l2

    def _prepare(self,frame):
        ratio=np.asarray(frame.load_ratio,float)
        finite_ratio=ratio[np.isfinite(ratio)]
        self.ratio_median_=float(np.median(finite_ratio)) if len(finite_ratio) else 0.
        self.ratio_all_missing_=len(finite_ratio)==0
        self.ratio_missing_train_=int(np.sum(~np.isfinite(ratio)))
        x,y,e=_frame_arrays(frame,load_ratio_fill=self.ratio_median_)
        if len(x)==0 or e.sum()==0:
            raise ValueError('population fitting requires at least one failure')
        self.center_=x.mean(0)
        X=np.column_stack((np.ones(len(x)),x-self.center_))
        groups=np.asarray(frame.group_id.astype(str))
        unique,cnt=np.unique(groups,return_counts=True)
        count=dict(zip(unique,cnt))
        w=np.asarray([1/count[z] for z in groups]);w/=w.sum()
        return X,y,e,w

    def _objective(self,p,X,y,e,w):
        ll,dm,ds,_=_ll_parts(X@p[:3],np.exp(p[3]),y,e)
        value=-w@ll+.5*self.l2*np.dot(p[1:3],p[1:3])
        grad=np.r_[-X.T@(w*dm),-w@ds]
        grad[1:3]+=self.l2*p[1:3]
        return float(value),grad

    def fit(self,frame,sample_weight=None):
        X,y,e,w=self._prepare(frame)
        if sample_weight is not None:
            w=np.asarray(sample_weight,float)
            if len(w)!=len(y) or np.any(w<0) or w.sum()<=0:
                raise ValueError('invalid weights')
            w=w/w.sum()
        init=np.linalg.lstsq(X,y,rcond=None)[0]
        init[1]=min(init[1],-.01)
        scatter=np.clip(np.std(y-X@init),.10,1.5)
        p0=np.r_[init,np.log(scatter)]
        bounds=[(None,None),(-50.,-1e-4),(-20.,20.),
                (np.log(self.min_sigma),np.log(self.max_sigma))]
        r=minimize(self._objective,p0,args=(X,y,e,w),jac=True,
                   method='L-BFGS-B',bounds=bounds,
                   options={'maxiter':self.max_iter,'ftol':1e-11,'gtol':1e-6,'maxls':40})
        self.params_=r.x;self.sigma_=float(np.exp(r.x[3]))
        self.fit_receipt_={'success':bool(r.success),'message':str(r.message),
                           'n_iter':int(r.nit),'objective':float(r.fun),
                           'gradient_inf':float(np.max(np.abs(r.jac))),
                           'ratio_median_train':self.ratio_median_,
                           'ratio_all_missing_train':self.ratio_all_missing_,
                           'ratio_missing_train':self.ratio_missing_train_,
                           'sigma_at_bound':bool(np.isclose(self.sigma_,self.min_sigma)
                                                 or np.isclose(self.sigma_,self.max_sigma))}
        return self

    def predict_location(self,query):
        x=_frame_arrays(query,outcomes=False,load_ratio_fill=self.ratio_median_)-self.center_
        return self.params_[0]+x@self.params_[1:3]

    def predict_quantiles(self,query,support=None,alphas=(.1,)):
        # Pooled baseline deliberately does not update from target support.
        return self.predict_location(query)[:,None]+self.sigma_*norm.ppf(alphas)[None,:]

    def predict_log_score(self,query,support=None):
        _,y,e=_frame_arrays(query,load_ratio_fill=self.ratio_median_)
        return _ll_parts(self.predict_location(query),self.sigma_,y,e)[0]


class HierarchicalCensoredBasquin(CensoredBasquin):
    """Condition random intercept with source-balanced composite MML fitting.

One marginal condition likelihood per condition. The training objective averages
condition log likelihood within each provenance block, then averages blocks.
This limits a publication's influence but is not an independence correction.
"""
    def __init__(self,max_iter=1500,min_sigma=.02,max_sigma=3.,
                 min_tau=.02,max_tau=3.,l2=.001,nodes=41):
        super().__init__(max_iter,min_sigma,max_sigma,l2)
        self.min_tau=min_tau;self.max_tau=max_tau;self.nodes=nodes

    def _hier_objective(self,p,X,y,e,condition_indices,condition_weights):
        sigma,tau=np.exp(p[3:5]);mu=X@p[:3]
        total=0.;grad=np.zeros(5)
        for idx,cw in zip(condition_indices,condition_weights):
            post=intercept_posterior(mu[idx],y[idx],e[idx],sigma,tau,self.nodes)
            ll,dm,ds,_=_ll_parts(mu[idx,None]+post['u'][None,:],sigma,
                                y[idx,None],e[idx,None])
            w=post['weight']
            total-=cw*post['log_marginal']
            grad[:3]-=cw*X[idx].T@(dm@w)
            grad[3]-=cw*(ds.sum(0)@w)
            grad[4]-=cw*((post['u']/tau)**2-1)@w
        total+=.5*self.l2*np.dot(p[1:3],p[1:3])
        grad[1:3]+=self.l2*p[1:3]
        return float(total),grad

    def fit(self,frame,sample_weight=None):
        if sample_weight is not None:
            raise ValueError('hierarchical weights fixed at equal source/condition')
        pooled=CensoredBasquin(self.max_iter,self.min_sigma,self.max_sigma,self.l2).fit(frame)
        X,y,e,_=self._prepare(frame)
        conditions=np.asarray(frame.dataset_id.astype(str))
        groups=np.asarray(frame.group_id.astype(str))
        condition_indices=[np.flatnonzero(conditions==c) for c in sorted(set(conditions))]
        sources=[groups[idx[0]] for idx in condition_indices]
        if any(len(set(groups[idx]))!=1 for idx in condition_indices):
            raise ValueError('each condition must belong to exactly one provenance block')
        source_counts={s:sources.count(s) for s in set(sources)}
        condition_weights=np.array([1/source_counts[s] for s in sources],float)
        condition_weights/=condition_weights.sum()
        # Fixed deterministic two-start fit, selected by TRAINING objective only.
        starts=[]
        for frac in (.35,.75):
            sigma=max(self.min_sigma*2,pooled.sigma_*frac)
            tau=np.sqrt(max(.05**2,pooled.sigma_**2-sigma**2))
            starts.append(np.r_[pooled.params_[:3],np.log(sigma),np.log(tau)])
        bounds=[(None,None),(-50.,-1e-4),(-20.,20.),
                (np.log(self.min_sigma),np.log(self.max_sigma)),
                (np.log(self.min_tau),np.log(self.max_tau))]
        results=[minimize(self._hier_objective,start,
                          args=(X,y,e,condition_indices,condition_weights),jac=True,
                          method='L-BFGS-B',bounds=bounds,
                          options={'maxiter':self.max_iter,'ftol':1e-10,'gtol':1e-6,'maxls':40})
                 for start in starts]
        r=min(results,key=lambda z:z.fun)
        self.params_=r.x;self.sigma_=float(np.exp(r.x[3]));self.tau_=float(np.exp(r.x[4]))
        self.fit_receipt_={'success':bool(r.success),'message':str(r.message),
                           'n_iter':int(r.nit),'objective':float(r.fun),
                           'gradient_inf':float(np.max(np.abs(r.jac))),
                           'ratio_median_train':self.ratio_median_,
                           'ratio_all_missing_train':self.ratio_all_missing_,
                           'ratio_missing_train':self.ratio_missing_train_,
                           'nodes':self.nodes,'conditions':len(condition_indices),
                           'sources':len(set(sources)),
                           'sigma_at_bound':bool(np.isclose(self.sigma_,self.min_sigma)
                                                 or np.isclose(self.sigma_,self.max_sigma)),
                           'tau_at_bound':bool(np.isclose(self.tau_,self.min_tau)
                                               or np.isclose(self.tau_,self.max_tau)),
                           'training_start_receipts':[{'success':bool(q.success),
                              'objective':float(q.fun),'n_iter':int(q.nit)} for q in results]}
        return self

    def target_posterior(self,support=None):
        if support is None or len(support)==0:
            return intercept_posterior([],[],[],self.sigma_,self.tau_,self.nodes)
        _,y,e=_frame_arrays(support,load_ratio_fill=self.ratio_median_)
        if support.dataset_id.nunique()!=1:
            raise ValueError('target support must belong to one condition')
        return intercept_posterior(self.predict_location(support),y,e,
                                   self.sigma_,self.tau_,self.nodes)

    def predict_quantiles(self,query,support=None,alphas=(.1,)):
        alpha=np.asarray(alphas,float)
        if np.any((alpha<=0)|(alpha>=1)):
            raise ValueError('quantile probabilities must be in (0,1)')
        mu=self.predict_location(query)
        if support is None or len(support)==0:
            return mu[:,None]+np.sqrt(self.sigma_**2+self.tau_**2)*norm.ppf(alpha)[None,:]
        post=self.target_posterior(support)
        if np.all(np.asarray(support.event)==1):
            return (mu[:,None]+post['mean']
                    +np.sqrt(self.sigma_**2+post['variance'])*norm.ppf(alpha)[None,:])
        u,w=post['u'],post['weight']
        lower=float(u.min()-12*self.sigma_);upper=float(u.max()+12*self.sigma_)
        offset=np.array([brentq(lambda z:ndtr((z-u)/self.sigma_)@w-a,
                                lower,upper,xtol=1e-10) for a in alpha])
        return mu[:,None]+offset[None,:]

    def predict_log_score(self,query,support=None):
        _,y,e=_frame_arrays(query,load_ratio_fill=self.ratio_median_);mu=self.predict_location(query)
        if support is None or len(support)==0:
            return _ll_parts(mu,np.hypot(self.sigma_,self.tau_),y,e)[0]
        post=self.target_posterior(support)
        ll=_ll_parts(mu[:,None]+post['u'][None,:],self.sigma_,y[:,None],e[:,None])[0]
        return logsumexp(ll+np.log(post['weight'])[None,:],axis=1)


class FixedSlopeShiftPredictor:
    """Target-only intercept MLE with shared training slope/scatter.

Uses observed-curvature intercept uncertainty in a normal predictive
approximation. It is exact for uncensored normal data with known sigma and a
flat intercept prior, approximate for censoring, and unavailable if all target
supports are runouts. Population parameter uncertainty remains omitted.
"""
    def __init__(self,pooled):
        self.pooled=pooled

    def _shift(self,support):
        if support is None or len(support)==0:
            return 0.,0.,'zero_shot_pooled'
        _,y,e=_frame_arrays(support,load_ratio_fill=self.pooled.ratio_median_)
        if e.sum()==0:
            return np.nan,np.nan,'unidentified_all_runout'
        mu=self.pooled.predict_location(support);sigma=self.pooled.sigma_
        derivative=lambda u:_ll_parts(mu+u,sigma,y,e)[1].sum()
        radius=max(1.,np.max(np.abs(y-mu))+8*sigma)
        lo,hi=-radius,radius
        for _ in range(20):
            if derivative(lo)>0 and derivative(hi)<0:break
            lo*=2;hi*=2
        else:raise FloatingPointError('failed to bracket target MLE')
        mode=brentq(derivative,lo,hi,xtol=1e-11)
        var=1/_ll_parts(mu+mode,sigma,y,e)[3].sum()
        return float(mode),float(var),'estimated'

    def predict_location(self,query):
        return self.pooled.predict_location(query)

    def predict_quantiles(self,query,support=None,alphas=(.1,)):
        shift,var,status=self._shift(support)
        self.last_prediction_receipt_={'status':status,'shift':shift,'variance':var}
        return (self.pooled.predict_location(query)[:,None]+shift
                +np.sqrt(self.pooled.sigma_**2+var)*norm.ppf(alphas)[None,:])

