"""Prespecified finite-curvature sensitivity, not a random fatigue-limit model.

A continuous two-slope log10 stress-life curve, with its knot fixed to the
TRAINING median log stress. Each slope is constrained negative. Random target
intercept updating and predictive uncertainty use the same audited scalar
censored-normal posterior as the straight Basquin benchmark.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm
from src.v2_models import (CensoredBasquin,HierarchicalCensoredBasquin,
                           _frame_arrays,_ll_parts,intercept_posterior)


def _marginal_objective(p,X,y,event,condition_indices,condition_weights,l2,nodes):
    """Generic p-dimensional fixed effects, then log sigma and log tau."""
    coefficients=p[:-2];sigma,tau=np.exp(p[-2:]);mu=X@coefficients
    total=0.;gradient=np.zeros_like(p)
    for idx,cw in zip(condition_indices,condition_weights):
        post=intercept_posterior(mu[idx],y[idx],event[idx],sigma,tau,nodes)
        _,dm,ds,_=_ll_parts(mu[idx,None]+post['u'][None,:],sigma,
                            y[idx,None],event[idx,None])
        w=post['weight'];total-=cw*post['log_marginal']
        gradient[:-2]-=cw*X[idx].T@(dm@w)
        gradient[-2]-=cw*(ds.sum(0)@w)
        gradient[-1]-=cw*(((post['u']/tau)**2-1)@w)
    total+=.5*l2*np.dot(coefficients[1:],coefficients[1:])
    gradient[1:-2]+=l2*coefficients[1:]
    return float(total),gradient


class CensoredCurvedBasquin(CensoredBasquin):
    """Continuous two-slope pooled censored fatigue law."""
    def _prepare_curved(self,frame):
        _,y,event,weights=super()._prepare(frame)
        self.knot_=float(np.median(np.asarray(frame.log_stress,float)))
        # center_[0] is the knot; center_[1] remains training mean load ratio.
        self.center_[0]=self.knot_
        return self.design(frame),y,event,weights

    def design(self,frame):
        x=_frame_arrays(frame,outcomes=False,load_ratio_fill=self.ratio_median_)
        t=x[:,0]-self.knot_
        return np.column_stack((np.ones(len(x)),np.minimum(t,0),
                                np.maximum(t,0),x[:,1]-self.center_[1]))

    def _curved_objective(self,p,X,y,event,weights):
        ll,dm,ds,_=_ll_parts(X@p[:-1],np.exp(p[-1]),y,event)
        val=-weights@ll+.5*self.l2*np.dot(p[1:-1],p[1:-1])
        grad=np.r_[-X.T@(weights*dm),-weights@ds]
        grad[1:-1]+=self.l2*p[1:-1]
        return float(val),grad

    def _bounds(self,hierarchical=False):
        bounds=[(None,None),(-50.,-1e-4),(-50.,-1e-4),(-20.,20.),
                (np.log(self.min_sigma),np.log(self.max_sigma))]
        if hierarchical:bounds.append((np.log(self.min_tau),np.log(self.max_tau)))
        return bounds

    def _receipt(self,result):
        return {'success':bool(result.success),'message':str(result.message),
                'n_iter':int(result.nit),'objective':float(result.fun),
                'gradient_inf':float(np.max(np.abs(result.jac))),
                'knot_training_median_log_stress':self.knot_,
                'stress_slopes_log10':self.params_[1:3].tolist(),
                'ratio_median_train':self.ratio_median_,
                'ratio_missing_train':self.ratio_missing_train_,
                'ratio_all_missing_train':self.ratio_all_missing_,
                'sigma_at_bound':bool(np.isclose(self.sigma_,self.min_sigma)
                                      or np.isclose(self.sigma_,self.max_sigma)),
                'model':'finite two-slope curve; not a fatigue-limit estimator'}

    def fit(self,frame,sample_weight=None):
        X,y,e,w=self._prepare_curved(frame)
        if sample_weight is not None:
            w=np.asarray(sample_weight,float)
            if len(w)!=len(y) or np.any(w<0) or w.sum()<=0:
                raise ValueError('invalid weights')
            w=w/w.sum()
        start=np.linalg.lstsq(X,y,rcond=None)[0]
        start[1:3]=np.minimum(start[1:3],-.01)
        sigma=np.clip(np.std(y-X@start),.10,1.5)
        result=minimize(self._curved_objective,np.r_[start,np.log(sigma)],
                        args=(X,y,e,w),jac=True,method='L-BFGS-B',bounds=self._bounds(),
                        options={'maxiter':self.max_iter,'ftol':1e-11,'gtol':1e-6,'maxls':40})
        if not np.isfinite(result.fun) or not np.all(np.isfinite(result.x)):
            raise FloatingPointError('nonfinite curved fit')
        self.params_=result.x;self.sigma_=float(np.exp(result.x[-1]))
        self.fit_receipt_=self._receipt(result)
        return self

    def predict_location(self,query):
        return self.design(query)@self.params_[:4]


class HierarchicalCurvedBasquin(HierarchicalCensoredBasquin,CensoredCurvedBasquin):
    """Two-slope population plus censored condition random-intercept updating.

Inheritance reuses scalar posterior and predictive mixture methods verbatim;
only the fixed-effects design and population fitting objective differ.
"""
    def fit(self,frame,sample_weight=None):
        if sample_weight is not None:
            raise ValueError('hierarchical weights fixed at equal source/condition')
        pooled=CensoredCurvedBasquin(self.max_iter,self.min_sigma,self.max_sigma,self.l2).fit(frame)
        X,y,e,_=self._prepare_curved(frame)
        conditions=np.asarray(frame.dataset_id.astype(str))
        groups=np.asarray(frame.group_id.astype(str))
        indices=[np.flatnonzero(conditions==c) for c in sorted(set(conditions))]
        if any(len(set(groups[idx]))!=1 for idx in indices):
            raise ValueError('each condition must belong to exactly one provenance block')
        sources=[groups[idx[0]] for idx in indices]
        counts={s:sources.count(s) for s in set(sources)}
        weights=np.asarray([1/counts[s] for s in sources],float);weights/=weights.sum()
        starts=[]
        for fraction in (.35,.75):
            sigma=max(self.min_sigma*2,pooled.sigma_*fraction)
            tau=np.sqrt(max(.05**2,pooled.sigma_**2-sigma**2))
            starts.append(np.r_[pooled.params_[:4],np.log(sigma),np.log(tau)])
        results=[minimize(_marginal_objective,p,
                          args=(X,y,e,indices,weights,self.l2,self.nodes),jac=True,
                          method='L-BFGS-B',bounds=self._bounds(hierarchical=True),
                          options={'maxiter':self.max_iter,'ftol':1e-10,'gtol':1e-6,'maxls':40})
                 for p in starts]
        result=min(results,key=lambda r:r.fun)
        if not np.isfinite(result.fun) or not np.all(np.isfinite(result.x)):
            raise FloatingPointError('nonfinite curved hierarchical fit')
        self.params_=result.x;self.sigma_=float(np.exp(result.x[-2]))
        self.tau_=float(np.exp(result.x[-1]))
        self.fit_receipt_=self._receipt(result)|{
            'nodes':self.nodes,'conditions':len(indices),'sources':len(set(sources)),
            'tau_at_bound':bool(np.isclose(self.tau_,self.min_tau)
                                or np.isclose(self.tau_,self.max_tau)),
            'training_start_receipts':[{'success':bool(r.success),'objective':float(r.fun),
                                        'n_iter':int(r.nit)} for r in results]}
        return self

