"""Nonlinear Gaussian-process AFT baseline with proper right-censor likelihood.

No target-driven hyperparameter optimization occurs in this module. A fixed
kernel/noise configuration is supplied by an external source-family CV protocol.
The log10-life GP posterior is approximated by Laplace's method. Selected target
supports are appended to the training likelihood with fixed mean/kernel/noise;
the JOINT latent mode is recomputed, rather than treating censored stops as
failures or stacking two Gaussian posterior approximations.

The condition kernel uses database condition labels, not asserted build IDs.
All predictive distributions here have finite Gaussian log-life tails. Neither
population hyperparameter uncertainty nor a literal infinite-life atom is used.
GP survival/AFT models are established prior art, not a novelty claim.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
import hashlib
import json
import time
import numpy as np
import pandas as pd
from scipy.linalg import cholesky, cho_solve, solve_triangular
from scipy.special import log_ndtr, ndtr
from scipy.stats import norm

LOG2PI = float(np.log(2*np.pi))
FEATURES = ['row_id','dataset_id','log_stress','load_ratio']
OBSERVATIONS = FEATURES+['log_life','event']


@dataclass(frozen=True)
class GPKernelConfig:
    global_sd: float = 0.5
    stress_length: float = 0.2  # log10(MPa), not standardized or fitted on target
    ratio_length: float = 1.0
    condition_intercept_sd: float = 0.5
    condition_shape_sd: float = 0.35
    condition_shape_length: float = 0.2

    def __post_init__(self):
        values=np.array(list(asdict(self).values()),float)
        if not np.isfinite(values).all():raise ValueError('kernel parameters must be finite')
        if min(self.stress_length,self.ratio_length,self.condition_shape_length)<=0:
            raise ValueError('positive kernel length scales required')
        if min(self.global_sd,self.condition_intercept_sd,self.condition_shape_sd)<0:
            raise ValueError('kernel standard deviations must be nonnegative')
        # All-zero covariance is an intentional nested pooled-normal anchor.


def censored_normal_parts(location, noise_sd, log_life, event):
    """Log likelihood, derivative and negative second derivative wrt location.

    Failures contribute Normal(log_life; location,noise_sd). Right-censored
    observations contribute P(Y>log_life|location)=Phi((location-log_life)/sd).
    A continued fraction avoids cancellation in extreme positive upper tails.
    """
    f,y,e=np.broadcast_arrays(np.asarray(location,float),np.asarray(log_life,float),np.asarray(event,float))
    if not np.isfinite(noise_sd) or noise_sd<=0:raise ValueError('positive noise required')
    if not np.isfinite(f).all() or not np.isfinite(y).all() or not np.isin(e,[0,1]).all():
        raise ValueError('finite location/life and binary event required')
    z=(y-f)/noise_sd
    logpdf=-.5*z*z-.5*LOG2PI
    logsf=log_ndtr(-z)
    hazard=np.asarray(np.exp(logpdf-logsf)).copy()
    difference=np.asarray(hazard-z).copy()
    tail=z>8
    if np.any(tail):
        q=z[tail];fraction=np.zeros_like(q)
        for numerator in range(80,1,-1):fraction=numerator/(q+fraction)
        difference[tail]=1/(q+fraction)
        hazard[tail]=q+difference[tail]
    ll=np.where(e==1,logpdf-np.log(noise_sd),logsf)
    score=np.where(e==1,z,hazard)/noise_sd
    curvature=np.where(e==1,1.,np.maximum(hazard*difference,0.))/noise_sd**2
    return ll,score,curvature


def _validate(frame, outcomes):
    columns=OBSERVATIONS if outcomes else FEATURES
    missing=set(columns)-set(frame.columns)
    if missing:raise ValueError('missing GP columns: '+str(sorted(missing)))
    x=frame[columns].copy().reset_index(drop=True)
    if not x.row_id.is_unique or x.row_id.isna().any() or x.dataset_id.isna().any():
        raise ValueError('unique row IDs and nonmissing working condition labels required')
    x['row_id']=x.row_id.astype(str);x['dataset_id']=x.dataset_id.astype(str)
    if not x.row_id.is_unique:raise ValueError('row IDs collide after string conversion')
    if not np.isfinite(x[['log_stress','load_ratio']].to_numpy(float)).all():
        raise ValueError('finite stress/load ratio required; no implicit imputation')
    if outcomes and (not np.isfinite(x.log_life.to_numpy(float)).all() or not x.event.isin([0,1]).all()):
        raise ValueError('finite observed log-life and binary event required')
    return x


def _laplace(prior_cov, prior_chol, mean, y, event, noise_sd, start=None,
             max_iter=100, gradient_tolerance=1e-7):
    """Damped Newton in whitened coordinates; posterior objective is convex."""
    n=len(y)
    if n==0:
        return dict(alpha=np.zeros(0),sqrt_w=np.zeros(0),B_chol=np.zeros((0,0)),
            v_mode=np.zeros(0),receipt=dict(success=True,n=0,iterations=0,
            gradient_inf=0.,log_marginal_laplace=0.,objective=0.))
    v=np.zeros(n) if start is None else np.array(start,float).copy()
    if v.shape!=(n,):raise ValueError('invalid latent warm start')
    def parts(v):
        f=mean+prior_chol@v
        ll,g,w=censored_normal_parts(f,noise_sd,y,event)
        objective=.5*np.dot(v,v)-ll.sum()
        gradient=v-prior_chol.T@g
        return float(objective),gradient,ll,g,w
    backtracks=0
    for iteration in range(max_iter+1):
        objective,gradient,ll,g,w=parts(v)
        gradient_inf=float(np.max(np.abs(gradient)))
        if gradient_inf<=gradient_tolerance:break
        if iteration==max_iter:raise FloatingPointError('GP Laplace mode did not converge')
        hessian=np.eye(n)+prior_chol.T@(w[:,None]*prior_chol)
        hc=cholesky(hessian,lower=True,check_finite=False)
        direction=cho_solve((hc,True),gradient,check_finite=False)
        decrement=float(np.dot(gradient,direction))
        step=1.
        for _ in range(40):
            candidate=v-step*direction
            new_objective=parts(candidate)[0]
            if new_objective<=objective-1e-4*step*decrement+1e-13:
                v=candidate;break
            step*=.5;backtracks+=1
        else:raise FloatingPointError('GP Laplace Newton line search failed')
    sqrt_w=np.sqrt(w)
    B=np.eye(n)+(sqrt_w[:,None]*prior_cov)*sqrt_w[None,:]
    B_chol=cholesky(B,lower=True,check_finite=False)
    # At the mode alpha=grad(log likelihood). This avoids an unstable inversion
    # of an almost rank-deficient kernel at repeated stress/condition inputs.
    alpha=g.copy()
    log_marginal=float(ll.sum()-.5*np.dot(v,v)-np.log(np.diag(B_chol)).sum())
    return dict(alpha=alpha,sqrt_w=sqrt_w,B_chol=B_chol,v_mode=v,
        receipt=dict(success=True,n=n,iterations=iteration,backtracks=backtracks,
            gradient_inf=gradient_inf,objective=objective,
            log_marginal_laplace=log_marginal,all_uncensored_exact_gaussian=bool(np.all(event==1))))


class CensoredLaplaceGP:
    """Fixed-hyperparameter nonlinear GP with selected-support conditioning.

    mean_parameters optionally gives (intercept,log_stress coefficient,R
    coefficient) in raw units for tests or a predeclared external training mean.
    Otherwise a censored Basquin mean is estimated from the supplied TRAINING
    rows only. All GP likelihood factors have unit weight; family balancing is
    an external validation-score operation, not an unreported power likelihood.
    """
    def __init__(self,config=None,noise_sd=0.35,mean_parameters=None,
                 jitter=1e-9,max_support_cache=16,max_iter=100,gradient_tolerance=1e-7):
        self.config=config or GPKernelConfig()
        if not isinstance(self.config,GPKernelConfig):raise TypeError('GPKernelConfig required')
        if not np.isfinite(noise_sd) or noise_sd<=0:raise ValueError('positive fixed noise_sd required')
        if not np.isfinite(jitter) or jitter<=0:raise ValueError('positive numerical jitter required')
        self.noise_sd=float(noise_sd);self.mean_parameters=mean_parameters
        self.jitter=float(jitter);self.max_support_cache=int(max_support_cache)
        self.max_iter=int(max_iter);self.gradient_tolerance=float(gradient_tolerance)

    def kernel(self,a,b):
        c=self.config
        ds=a.log_stress.to_numpy(float)[:,None]-b.log_stress.to_numpy(float)[None,:]
        dr=a.load_ratio.to_numpy(float)[:,None]-b.load_ratio.to_numpy(float)[None,:]
        same=a.dataset_id.to_numpy()[:,None]==b.dataset_id.to_numpy()[None,:]
        return (c.global_sd**2*np.exp(-.5*((ds/c.stress_length)**2+(dr/c.ratio_length)**2))+
            same*(c.condition_intercept_sd**2+c.condition_shape_sd**2*np.exp(-.5*(ds/c.condition_shape_length)**2)))

    def _mean(self,frame):
        return self.mean_coef_[0]+self.mean_coef_[1]*frame.log_stress.to_numpy(float)+self.mean_coef_[2]*frame.load_ratio.to_numpy(float)

    def fit(self,train):
        start=time.monotonic();self.train_=_validate(train,True)
        if self.mean_parameters is None:
            if len(train)<3:raise ValueError('fixed mean_parameters required for fewer than3training rows')
            from src.v2_models import CensoredBasquin
            mean_model=CensoredBasquin().fit(train)
            if not mean_model.fit_receipt_['success']:raise FloatingPointError('GP training mean failed')
            p=mean_model.params_;center=mean_model.center_
            self.mean_coef_=np.array([p[0]-p[1]*center[0]-p[2]*center[1],p[1],p[2]])
            mean_receipt=mean_model.fit_receipt_
        else:
            self.mean_coef_=np.asarray(self.mean_parameters,float)
            if self.mean_coef_.shape!=(3,) or not np.isfinite(self.mean_coef_).all():
                raise ValueError('three finite mean coefficients required')
            mean_receipt={'success':True,'source':'externally fixed coefficients'}
        self.prior_cov_=self.kernel(self.train_,self.train_)
        scale=max(1.,self.config.global_sd**2+self.config.condition_intercept_sd**2+self.config.condition_shape_sd**2)
        self.jitter_used_=self.jitter*scale
        self.prior_cov_+=np.eye(len(self.train_))*self.jitter_used_
        self.prior_chol_=cholesky(self.prior_cov_,lower=True,check_finite=False) if len(train) else np.zeros((0,0))
        self.population_=_laplace(self.prior_cov_,self.prior_chol_,self._mean(self.train_),
            self.train_.log_life.to_numpy(),self.train_.event.to_numpy(),self.noise_sd,
            max_iter=self.max_iter,gradient_tolerance=self.gradient_tolerance)
        self._support_cache=OrderedDict()
        self.fit_receipt_=dict(model='censored Laplace GP AFT',success=True,n_train=len(train),
            n_conditions=self.train_.dataset_id.nunique(),n_source_families=(train.group_id.nunique() if 'group_id' in train else None),
            kernel=asdict(self.config),noise_sd=self.noise_sd,mean_coefficients=self.mean_coef_.tolist(),
            mean_receipt=mean_receipt,latent_mode=self.population_['receipt'],jitter=self.jitter_used_,
            likelihood='proper unit-weight Gaussian failure density/right survival factors',
            hyperparameters_optimized_in_fit=False,hyperparameter_uncertainty_integrated=False,
            covariance_function_uncertainty='Laplace approximation',mean_parameter_uncertainty_integrated=False,
            condition_labels_are_physical_build_IDs=False,elapsed_seconds=time.monotonic()-start)
        return self

    def _posterior(self,support):
        if support is None or len(support)==0:return self.train_,self.population_
        s=_validate(support,True).sort_values('row_id').reset_index(drop=True)
        if s.dataset_id.nunique()!=1:raise ValueError('few-shot supports must belong to one working condition')
        if set(s.row_id).intersection(self.train_.row_id):raise ValueError('support duplicates a training observation')
        # No unselected candidate or query outcomes enter this cache key or fit.
        token=hashlib.sha256(s.to_csv(index=False).encode()).hexdigest()
        if token in self._support_cache:
            self._support_cache.move_to_end(token);return self._support_cache[token]
        joint=pd.concat([self.train_,s],ignore_index=True)
        n=len(self.train_);k=len(s)
        cross=self.kernel(self.train_,s)
        V=solve_triangular(self.prior_chol_,cross,lower=True,check_finite=False) if n else np.zeros((0,k))
        ss=self.kernel(s,s)+np.eye(k)*self.jitter_used_
        schur=ss-V.T@V
        schur=.5*(schur+schur.T)
        lower=cholesky(schur,lower=True,check_finite=False)
        prior_chol=np.block([[self.prior_chol_,np.zeros((n,k))],[V.T,lower]])
        prior_cov=np.block([[self.prior_cov_,cross],[cross.T,ss]])
        initial=np.r_[self.population_['v_mode'],np.zeros(k)]
        post=_laplace(prior_cov,prior_chol,self._mean(joint),joint.log_life.to_numpy(),
            joint.event.to_numpy(),self.noise_sd,start=initial,max_iter=self.max_iter,
            gradient_tolerance=self.gradient_tolerance)
        post['receipt']['n_selected_support']=k
        result=(joint,post)
        if self.max_support_cache>0:
            self._support_cache[token]=result
            while len(self._support_cache)>self.max_support_cache:self._support_cache.popitem(last=False)
        return result

    def predict_mean_variance(self,query,support=None):
        if not hasattr(self,'population_'):raise RuntimeError('fit training data first')
        q=_validate(query,False)
        observed,post=self._posterior(support)
        if set(q.row_id).intersection(observed.row_id):raise ValueError('query outcome identity overlaps training/support')
        if support is not None and len(support) and set(q.dataset_id)!=set(support.dataset_id.astype(str)):
            raise ValueError('query/support must address the same target working condition')
        cross=self.kernel(observed,q)
        mean=self._mean(q)+cross.T@post['alpha']
        prior_diagonal=np.full(len(q),self.config.global_sd**2+self.config.condition_intercept_sd**2+self.config.condition_shape_sd**2)
        V=solve_triangular(post['B_chol'],post['sqrt_w'][:,None]*cross,lower=True,check_finite=False) if len(observed) else np.zeros((0,len(q)))
        latent_variance=prior_diagonal-np.sum(V*V,axis=0)
        if np.any(latent_variance < -1e-8*max(1.,prior_diagonal.max(initial=0.))):
            raise FloatingPointError('GP negative predictive latent variance')
        latent_variance=np.maximum(latent_variance,0.)
        variance=latent_variance+self.noise_sd**2
        self.last_prediction_receipt_=post['receipt']|dict(n_query=len(q),
            n_train=len(self.train_),n_selected_support=0 if support is None else len(support),
            min_latent_variance=float(latent_variance.min(initial=np.inf)),
            max_latent_variance=float(latent_variance.max(initial=0.)),
            fixed_hyperparameters=True,population_and_selected_support_joint_Laplace=True,
            quantile_is_R90C90=False)
        return mean,variance

    def predict_quantiles(self,query,support=None,alphas=(.1,)):
        alpha=np.asarray(alphas,float)
        if alpha.ndim!=1 or not np.isfinite(alpha).all() or np.any((alpha<=0)|(alpha>=1)):
            raise ValueError('finite quantiles must be in(0,1)')
        mean,var=self.predict_mean_variance(query,support)
        return mean[:,None]+np.sqrt(var)[:,None]*norm.ppf(alpha)[None,:]

    def predict_log_score(self,query,support=None):
        checked=_validate(query,True)
        mean,var=self.predict_mean_variance(query,support)
        sd=np.sqrt(var);z=(checked.log_life.to_numpy()-mean)/sd
        return np.where(checked.event.to_numpy()==1,-.5*z*z-.5*LOG2PI-np.log(sd),log_ndtr(-z))

    def predict_cdf(self,log_y,query,support=None):
        mean,var=self.predict_mean_variance(query,support)
        y=np.broadcast_to(np.asarray(log_y,float),(len(query),))
        if np.isnan(y).any():raise ValueError('log-life CDF argument must not be NaN')
        return ndtr((y-mean)/np.sqrt(var))

    def predict_location(self,query,support=None):
        # The log-normal predictive distribution has log-median equal to mean.
        return self.predict_mean_variance(query,support)[0]

    def monotonicity_receipt(self,grid,support=None,alpha=.1,tolerance=1e-8):
        """Diagnostic only; no projection, target tuning or monotonicity theorem."""
        q=_validate(grid,False);value=self.predict_quantiles(q,support,(alpha,))[:,0]
        q=q.assign(log_quantile=value);increases=[];edges=0
        for _,g in q.groupby(['dataset_id','load_ratio']):
            g=g.sort_values('log_stress');difference=np.diff(g.log_quantile)
            increases.extend(difference[difference>tolerance].tolist());edges+=len(difference)
        return dict(alpha=alpha,stress_grid_edges=edges,positive_quantile_increments=len(increases),
            max_positive_log10life_increment=max(increases,default=0.),monotonicity_guaranteed=False,
            interpretation='diagnostic evaluated at fixed hyperparameters; never a post-hoc tuning objective')


def training_reference(frame):
    """Training-only hierarchical location/within-condition noise reference.

    The unchanged hierarchical Basquin reference estimates within-condition
    sigma and condition-intercept tau using its declared source-balanced
    composite marginal likelihood. These empirical-Bayes reference values are
    held fixed within the candidate GP fits. No target statistics are used.
    """
    from src.v2_models import HierarchicalCensoredBasquin
    _validate(frame,True)
    if 'group_id' not in frame or frame.group_id.isna().any():
        raise ValueError('nonmissing source-family labels required for training reference')
    base=HierarchicalCensoredBasquin().fit(frame)
    if not base.fit_receipt_['success']:raise FloatingPointError('GP hierarchical training reference failed')
    p=base.params_;center=base.center_
    mean=[float(p[0]-p[1]*center[0]-p[2]*center[1]),float(p[1]),float(p[2])]
    return dict(mean_parameters=mean,reference_noise_sd=float(base.sigma_),
        reference_condition_sd=float(base.tau_),fit_receipt=base.fit_receipt_,
        n_rows=len(frame),source_families=int(frame.group_id.nunique()),
        training_data_sha256=hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest(),
        recipe='inner-training-only unchanged hierarchical Basquin; within-condition sigma, condition tau, fixed linear mean')


def proposed_gp_grid(reference_noise_sd,reference_condition_sd):
    """66-candidate proposal; parent protocol must freeze it before real tuning."""
    if not np.isfinite([reference_noise_sd,reference_condition_sd]).all() or min(reference_noise_sd,reference_condition_sd)<0 or reference_noise_sd==0:
        raise ValueError('positive reference noise/nonnegative condition scale required')
    choices=[];seen=set()
    for amplitude in [0.,.30,.60]:
        for shape in [0.,.35]:
            lengths=[.20] if amplitude==shape==0 else [.10,.35,1.0]
            for length in lengths:
                for noise_multiplier in [.5,.75,1.25,2.]:
                    cfg=GPKernelConfig(global_sd=amplitude,stress_length=length,
                        ratio_length=1.,condition_intercept_sd=float(reference_condition_sd),
                        condition_shape_sd=shape,condition_shape_length=length)
                    record=dict(config=asdict(cfg),noise_sd=float(reference_noise_sd)*noise_multiplier,
                        noise_multiplier=noise_multiplier,role='structured_GP_grid')
                    token=json.dumps(record,sort_keys=True)
                    assert token not in seen;seen.add(token);choices.append(record)
    choices.extend([
        dict(config=asdict(GPKernelConfig(global_sd=0.,condition_intercept_sd=0.,condition_shape_sd=0.)),
            noise_sd=float(reference_noise_sd),noise_multiplier=1.,role='zero_covariance_pooled_normal_anchor'),
        dict(config=asdict(GPKernelConfig(global_sd=.5,stress_length=.2,ratio_length=1.,
            condition_intercept_sd=float(reference_condition_sd),condition_shape_sd=.35,condition_shape_length=.2)),
            noise_sd=float(reference_noise_sd),noise_multiplier=1.,role='sensible_GP_default_anchor')])
    assert len(choices)==66
    for i,record in enumerate(choices):
        record['candidate_id']=f'gp{i:02d}'
        record['note']='shape0removescondition-specificshapeonly;globalGPcanstillupdateshape'
    return choices
