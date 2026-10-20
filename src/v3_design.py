"""Frozen outcome-blind stress acquisition and local MAP/Laplace control."""
from __future__ import annotations
import hashlib
import numpy as np
from scipy.optimize import minimize
from scipy.special import ndtr, log_ndtr
from scipy.stats import norm
from src.v2_models import _ll_parts

POLICIES=('random','stress_span','high_stress','active_query_variance')

def rank(ids,*salt):
    return sorted(map(str,ids),key=lambda i:hashlib.sha256(
        ('|'.join(map(str,(*salt,i)))).encode()).hexdigest())

def truncate_support(frame,cap):
    x=frame.copy()
    after=x.log_life.to_numpy()>np.log10(cap)
    x.loc[after,'event']=0
    x.loc[after,'log_life']=np.log10(cap)
    return x

def design(frame,base):
    return np.column_stack((np.ones(len(frame)),
                            np.asarray(frame.log_stress)-base.center_[0]))

def target_fit(base,support):
    """Proper fixed prior; curvature approximation, not an exact posterior."""
    prior_var=np.array([base.tau_**2,max(1.,abs(base.params_[1])/2)**2])
    precision=np.diag(1/prior_var)
    if support is None or not len(support):
        return np.zeros(2),np.diag(prior_var),{'success':True,'n':0}
    X=design(support,base);mu=base.predict_location(support)
    y=support.log_life.to_numpy();e=support.event.to_numpy()
    def obj(u):
        ll,score,_,_= _ll_parts(mu+X@u,base.sigma_,y,e)
        return float(-ll.sum()+.5*u@precision@u),-X.T@score+precision@u
    result=minimize(obj,np.zeros(2),jac=True,method='L-BFGS-B',
        bounds=[(None,None),(-50-base.params_[1],-1e-4-base.params_[1])],
        options={'maxiter':500,'ftol':1e-12,'gtol':1e-7,'maxls':40})
    first_status=str(result.message)
    recovered=False
    if not result.success:
        # Deterministic second numerical solver for the same convex objective;
        # no alternative model or query outcomes enter this recovery.
        result=minimize(obj,result.x,jac=True,method='SLSQP',
            bounds=[(None,None),(-50-base.params_[1],-1e-4-base.params_[1])],
            options={'maxiter':500,'ftol':1e-11})
        recovered=True
    if not result.success or not np.isfinite(result.fun):
        raise FloatingPointError('local MAP fit failed: '+str(result.message))
    curv=_ll_parts(mu+X@result.x,base.sigma_,y,e)[3]
    covariance=np.linalg.inv(precision+X.T@(curv[:,None]*X))
    return result.x,covariance,{'success':True,'n':len(y),
        'second_solver_used':recovered,'initial_solver_message':first_status,
        'slope_at_bound':bool(np.isclose(result.x[1]+base.params_[1],-1e-4)),
        'gradient_inf':float(np.max(np.abs(result.jac)))}

class LocalSlopeControl:
    def __init__(self,base):self.base=base
    def predict_quantiles(self,query,support=None,alphas=(.1,)):
        u,V,self.last_prediction_receipt_=target_fit(self.base,support)
        X=design(query,self.base)
        mu=self.base.predict_location(query)+X@u
        sd=np.sqrt(self.base.sigma_**2+np.einsum('ij,jk,ik->i',X,V,X))
        return mu[:,None]+sd[:,None]*norm.ppf(alphas)[None,:]

def expected_information(z,sigma):
    z=np.asarray(z,float)
    phi=np.exp(-.5*z*z)/np.sqrt(2*np.pi)
    term=np.exp(-z*z-np.log(2*np.pi)-log_ndtr(-z))
    g=ndtr(z)-z*phi+term
    return np.clip(g,0,1)/sigma**2

def choose_next(policy,pool_covariates,selected_ids,support,query_covariates,base,seed,cap):
    """Candidate/query outcomes must be absent, not merely ignored."""
    forbidden={'log_life','cycles_observed','event','runout'}
    if forbidden.intersection(pool_covariates.columns) or forbidden.intersection(query_covariates.columns):
        raise ValueError('acquisition accepts candidate/query covariates only')
    pool=pool_covariates.set_index('row_id',drop=False)
    remaining=pool.loc[~pool.index.isin(selected_ids)]
    if len(remaining)==0:raise ValueError('empty acquisition pool')
    order=rank(remaining.row_id,'v3',seed,policy)
    remaining=remaining.loc[order]
    x=remaining.log_stress.to_numpy()
    if policy=='random':return str(remaining.row_id.iloc[0]),{}
    if policy=='high_stress':score=x
    elif policy=='stress_span':
        if not selected_ids:score=x
        else:
            chosen=pool.loc[selected_ids].log_stress.to_numpy()
            score=np.min(np.abs(x[:,None]-chosen[None,:]),axis=1)
    elif policy=='active_query_variance':
        u,V,receipt=target_fit(base,support)
        X=design(remaining,base);Xq=design(query_covariates,base)
        Q=Xq.T@Xq/len(Xq)
        mu=base.predict_location(remaining)+X@u
        info=expected_information((np.log10(cap)-mu)/base.sigma_,base.sigma_)
        VX=X@V
        numerator=np.einsum('ij,jk,ik->i',VX,Q,VX)
        denominator=1+info*np.einsum('ij,ij->i',VX,X)
        score=info*numerator/denominator
    else:raise ValueError(policy)
    i=int(np.argmax(score))
    return str(remaining.row_id.iloc[i]),{'selection_score':float(score[i])}
