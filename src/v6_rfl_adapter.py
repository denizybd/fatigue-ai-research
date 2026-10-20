"""Two-dimensional target adaptation of the frozen Normal-Normal RFL population.

This module does not refit the population or edit the v3 implementation.  Target
u shifts finite log10 life and target v shifts the Normal mean of log10 Gamma.
The proper independent Gaussian priors are supplied/selected using training
sources only. They are not a physical-build covariance or a population posterior.

Positive nested quadrature integrates v and a globally integrated
conditional-u posterior; it never substitutes one posterior mode. Explicit
prior-tail bounds and deterministic resolution checks accompany the result.
At k0 both Gaussian convolutions are analytic, including infinite-life mass.
"""
from __future__ import annotations

from collections import OrderedDict
import copy
from functools import lru_cache
import hashlib
import time

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import log_ndtr, logsumexp, ndtr
from scipy.stats import norm

from .v2_models import _frame_arrays
from .v3_rfl import NormalNormalRFL, _legendre, LOG2PI


@lru_cache(maxsize=16)
def _rule(order):
    # Nodes and weights are read-only by convention; never recompute the
    # Legendre eigenproblem separately at every nested integration node.
    return _legendre(order)


class JointRFLTargetAdapter:
    """Wrap one fitted RFL with proper target life and fatigue-limit shifts.

    ``life_prior_sd`` is in log10 cycles, ``fatigue_limit_prior_sd`` in log10
    stress. Population parameters are fixed. All selected support likelihood
    factors have unit weight, as in the original scalar target adapter.
    ``fatigue_limit_prior_sd=0`` delegates exactly to that scalar adapter.
    A population Basquin fallback is rejected rather than called a 2D RFL.
    """
    def __init__(self, population, life_prior_sd, fatigue_limit_prior_sd,
                 tail_tolerance=1e-10, evidence_tolerance=2e-6,
                 cdf_tolerance=2e-6, quantile_tolerance=2e-4,
                 max_refinements=5, max_v_nodes=8192, max_support_cache=16):
        if not isinstance(population, NormalNormalRFL) or not hasattr(population, 'params_'):
            raise TypeError('a fitted NormalNormalRFL population is required')
        if population._fallback is not None:
            raise ValueError('population fallback is not a two-dimensional RFL control')
        self.life_prior_sd = float(life_prior_sd)
        self.fatigue_limit_prior_sd = float(fatigue_limit_prior_sd)
        if not np.isfinite([self.life_prior_sd, self.fatigue_limit_prior_sd]).all() or min(self.life_prior_sd, self.fatigue_limit_prior_sd) < 0:
            raise ValueError('finite nonnegative prior standard deviations required')
        self.population = self._clone(population)
        self.population.shift_prior_sd = self.life_prior_sd
        self.tail_tolerance = float(tail_tolerance)
        self.evidence_tolerance = float(evidence_tolerance)
        self.cdf_tolerance = float(cdf_tolerance)
        self.quantile_tolerance = float(quantile_tolerance)
        tolerances=[self.tail_tolerance,self.evidence_tolerance,self.cdf_tolerance,self.quantile_tolerance]
        if not np.isfinite(tolerances).all() or min(tolerances)<=0 or max(self.tail_tolerance,self.cdf_tolerance)>=1:
            raise ValueError('finite positive numerical tolerances and probability tolerances<1 required')
        self.max_refinements = int(max_refinements)
        self.max_v_nodes = int(max_v_nodes)
        self.max_support_cache = int(max_support_cache)
        if self.max_refinements < 1 or self.max_v_nodes < 32:
            raise ValueError('at least one refinement and 32 v nodes required')
        self._support_cache = OrderedDict()
        self._cold = self._clone(population)
        self._cold.params_[3] = np.log(np.hypot(np.exp(population.params_[3]), self.life_prior_sd))
        self._cold.params_[5] = np.log(np.hypot(np.exp(population.params_[5]), self.fatigue_limit_prior_sd))
        self._cold.shift_prior_sd = 0.
        self.fit_receipt_ = dict(
            model='Normal-Normal RFL with joint target life/fatigue-limit shifts',
            success=True,population_refitted=False,population_parameters=population.params_.tolist(),
            life_prior_sd=self.life_prior_sd,fatigue_limit_prior_sd=self.fatigue_limit_prior_sd,
            prior_correlation=0.,prior_selected_from_training_only_required=True,
            prior_is_physical_build_covariance=False,population_uncertainty_integrated=False,
            target_posterior_integration='positive nested quadrature, not Laplace',
            population_quadrature_nodes=population.nodes,
            k0_convolutions='sigma_eff=hypot(sigma,sd_u), tauGamma_eff=hypot(tauGamma,sd_v)',
            tail_tolerance=self.tail_tolerance,evidence_tolerance=self.evidence_tolerance,
            cdf_tolerance=self.cdf_tolerance,quantile_log10_tolerance=self.quantile_tolerance,
            max_refinements=self.max_refinements,max_v_nodes=self.max_v_nodes,
            quantile_is_R90C90=False)

    @staticmethod
    def _clone(population):
        result = copy.copy(population)
        result.params_ = population.params_.copy()
        result._posterior_cache = {}
        return result

    @staticmethod
    def _empty(support):
        return support is None or len(support) == 0

    @staticmethod
    def _token(frame, outcomes):
        cols = ['log_stress','load_ratio'] + (['log_life','event'] if outcomes else [])
        # Only pretest identity/covariates enter query keys. No query endpoint.
        cols = [c for c in ['row_id','dataset_id'] if c in frame] + cols
        return hashlib.sha256(frame[cols].to_csv(index=False).encode()).hexdigest()

    def _checked_support(self, support):
        if self._empty(support):
            return None
        s = support.copy()
        if 'row_id' in s:
            if s.row_id.isna().any() or not s.row_id.astype(str).is_unique:
                raise ValueError('selected support identity must be unique')
            s = s.sort_values('row_id').reset_index(drop=True)
        if 'dataset_id' in s and s.dataset_id.nunique() != 1:
            raise ValueError('one target working condition required')
        _, y, event = _frame_arrays(s,load_ratio_fill=self.population.ratio_median_)
        if not np.isfinite(y).all() or not np.isin(event,[0,1]).all():
            raise ValueError('finite support endpoints and binary event flags required')
        return s

    def _check_query(self, query, support):
        self.population._x(query)
        if support is not None:
            if 'row_id' in query and 'row_id' in support and set(query.row_id.astype(str)) & set(support.row_id.astype(str)):
                raise ValueError('query/support identity overlap')
            if 'dataset_id' in query and 'dataset_id' in support and set(query.dataset_id.astype(str)) != set(support.dataset_id.astype(str)):
                raise ValueError('query and supports must address same working condition')

    def _at_v(self, value):
        p = self._clone(self.population)
        p.params_[4] += float(value)
        return p

    def _observation_loglikelihood(self,kernel,y,event,u):
        """Evaluate only the event-required branch of the SAME RFL likelihood."""
        u=np.atleast_1d(np.asarray(u,float));y=np.asarray(y,float);event=np.asarray(event)
        result=np.empty((len(y),len(u)));sigma=kernel['sigma']
        for observed_failure in (True,False):
            index=np.flatnonzero((event==1)==observed_failure)
            if not len(index):continue
            z=(y[index,None,None]-kernel['mu'][index,None,:]-u[None,:,None])/sigma
            if observed_failure:
                result[index]=kernel['logmass'][index,None]+logsumexp(
                    self.population._logw[None,None,:]-.5*z*z-.5*LOG2PI-np.log(sigma),axis=2)
            else:
                finite=kernel['logmass'][index,None]+logsumexp(
                    self.population._logw[None,None,:]+log_ndtr(-z),axis=2)
                result[index]=np.logaddexp(kernel['log_infinite'][index,None],finite)
        return result

    def _conditional_u(self, shifted, support, arrays=None, precomputed_kernel=None):
        """Global positive quadrature with certified interval-mass pruning.

        Every prior-domain interval is bounded before pruning; all potentially
        important modes are retained. A failure density's interval supremum is
        bounded by the sum of its Gaussian component suprema, and survival is
        monotone in u. This avoids evaluating thousands of irrelevant fine
        intervals under a broad prior without assuming posterior unimodality.
        Bounds are for the population's fixed fatigue-limit quadrature model.
        """
        su=self.life_prior_sd
        x,y,event=(_frame_arrays(support,load_ratio_fill=shifted.ratio_median_)
                   if arrays is None else arrays)
        kernel=shifted._kernel(x) if precomputed_kernel is None else precomputed_kernel
        sigma=kernel['sigma']
        if su==0:
            lm=float(self._observation_loglikelihood(kernel,y,event,np.array([0.])).sum())
            return dict(u=np.array([0.]),weight=np.array([1.]),mean=0.,variance=0.,
                log_marginal=lm,tail_mass_bound=0.,u_intervals_total=0,
                u_intervals_evaluated=0,u_resolution_log_evidence_difference=0.,
                coarse_u=np.array([0.]),coarse_weight=np.array([1.]),coarse_log_marginal=lm)
        minscale=1/np.sqrt(1/su**2+(len(y)+1)/sigma**2)
        residual=np.abs(y-np.median(kernel['mu'],axis=1))
        radius=max(8*su,float(np.max(residual))+8*sigma)
        # At FIXED v every failure density is bounded by its finite-life mass
        # times the Gaussian peak. Retain those masses: discarding them makes a
        # rare-Gamma likelihood appear to need an enormous u prior domain even
        # when the tiny common factor cancels from its conditional posterior.
        loglike_upper=float(kernel['logmass'][event==1].sum())+int(event.sum())*(-np.log(sigma)-.5*LOG2PI)
        for _domain in range(8):
            intervals=max(8,int(np.ceil(2*radius/(4*minscale))))
            if intervals>16000:raise FloatingPointError('joint RFL conditional-u interval limit exceeded')
            edges=np.linspace(-radius,radius,intervals+1);left,right=edges[:-1],edges[1:]
            # Stable exact Normal prior mass in each interval. Use the upper
            # tail on the positive side to avoid subtracting two rounded ones.
            log_big=np.where(left>=0,log_ndtr(-left/su),log_ndtr(right/su))
            log_small=np.where(left>=0,log_ndtr(-right/su),log_ndtr(left/su))
            log_prior_mass=log_big+np.log(-np.expm1(log_small-log_big))
            log_supremum=np.zeros(intervals)
            for i,e in enumerate(event):
                if e==1:
                    target=y[i]-kernel['mu'][i]
                    distance=np.maximum(np.maximum(left[:,None]-target[None,:],target[None,:]-right[:,None]),0.)/sigma
                    log_supremum+=kernel['logmass'][i]+logsumexp(
                        shifted._logw[None,:]-.5*distance**2-.5*LOG2PI-np.log(sigma),axis=1)
                else:
                    # Survival monotone in location u; evaluate exact endpoint.
                    one=dict(mu=kernel['mu'][[i]],logmass=kernel['logmass'][[i]],
                        log_infinite=kernel['log_infinite'][[i]],sigma=sigma)
                    log_supremum+=self._observation_loglikelihood(one,np.array([y[i]]),np.array([0]),right)[0]
            interval_bound=log_prior_mass+log_supremum
            ranked=np.argsort(interval_bound)[::-1]
            remaining_bound=np.r_[np.logaddexp.accumulate(interval_bound[ranked][::-1])[::-1],-np.inf]
            count=min(8,intervals)
            while True:
                chosen=ranked[:count]
                def rule(order):
                    t,w=_rule(order)
                    widths=right[chosen]-left[chosen]
                    u=(left[chosen,None]+widths[:,None]*t).ravel()
                    logw=np.log((widths[:,None]*w).ravel())
                    ll=self._observation_loglikelihood(kernel,y,event,u).sum(axis=0)
                    log_joint=ll+norm.logpdf(u,scale=su)+logw
                    lm=float(logsumexp(log_joint))
                    return u,np.exp(log_joint-lm),lm
                u,weight,lm=rule(8)
                omitted=float(logsumexp(interval_bound[ranked[count:]])) if count<intervals else -np.inf
                prior_tail=np.log(2.)+log_ndtr(-radius/su)+loglike_upper
                log_error_bound=float(np.logaddexp(omitted,prior_tail)-lm)
                if log_error_bound<=np.log(.5*self.tail_tolerance):
                    break
                if prior_tail-lm>np.log(.25*self.tail_tolerance):
                    # Adding INSIDE-domain intervals cannot repair an OUTSIDE-
                    # domain tail bound. Expand the global domain immediately;
                    # otherwise count+1 iterations repeatedly recompute all
                    # inside nodes and can make broad-prior tail cases quadratic.
                    break
                if count<intervals:
                    admissible=np.flatnonzero(remaining_bound<=lm+np.log(.5*self.tail_tolerance))
                    count=max(count+1,int(admissible[0]) if len(admissible) else intervals)
                    count=min(count,intervals)
                    continue
                # All intervals were evaluated, so the remaining error is the
                # prior outside this domain. Expand globally, not around a mode.
                break
            if log_error_bound>np.log(self.tail_tolerance):
                radius*=1.7
                continue
            uc,wc,lmc=u,weight,lm
            uf,wf,lmf=rule(16)
            difference=abs(lmf-lm)
            if difference>self.evidence_tolerance:
                # Same global intervals, higher positive order. There is no
                # opportunity to choose an attractive target prediction.
                previous=lmf
                for order in (32,64,128):
                    uc,wc,lmc=uf,wf,lmf
                    uf,wf,lmf=rule(order);difference=abs(lmf-previous)
                    if difference<=self.evidence_tolerance:break
                    previous=lmf
                else:raise FloatingPointError('joint RFL conditional-u rule did not converge')
            final_log_bound=float(np.logaddexp(omitted,prior_tail)-lmf)
            if final_log_bound>np.log(self.tail_tolerance):
                radius*=1.7
                continue
            keep=wf>1e-15
            discarded=float(wf[~keep].sum())
            uf,wf=uf[keep],wf[keep];wf/=wf.sum()
            mean=float(wf@uf)
            return dict(u=uf,weight=wf,mean=mean,variance=float(wf@(uf-mean)**2),
                log_marginal=lmf,tail_mass_bound=float(np.exp(final_log_bound))+discarded,
                u_intervals_total=intervals,u_intervals_evaluated=count,
                u_resolution_log_evidence_difference=difference,radius=radius,
                coarse_u=uc,coarse_weight=wc,
                coarse_log_marginal=lmc,
                omitted_interval_upper_mass_ratio=float(np.exp(omitted-lmf)),
                discarded_numerical_node_mass=discarded)
        raise FloatingPointError('joint RFL conditional-u global tail bound failed')

    def _level(self, support, radius, refinement, edges_override=None,
               quadrature_order=8, conditional_cache=None):
        """One positive finite-domain v rule and conditional global-u rules."""
        start = time.monotonic()
        sv = self.fatigue_limit_prior_sd
        tau_gamma = np.exp(self.population.params_[5])
        # Each specimen's latent logGamma Gaussian convolution limits negative
        # log-likelihood curvature to k/tauGamma^2. One extra factor reserves
        # resolution for a predictive likelihood, independent of query outcomes.
        minimum_scale = 1/np.sqrt(1/sv**2+(len(support)+1)/tau_gamma**2)
        if edges_override is None:
            intervals = max(4,int(np.ceil(2*radius/(4*minimum_scale)))) * 2**refinement
            edges = np.linspace(-radius,radius,intervals+1)
        else:
            edges=np.asarray(edges_override,float);intervals=len(edges)-1
        if quadrature_order*intervals > self.max_v_nodes:
            raise FloatingPointError('joint RFL v quadrature exceeded predetermined node limit')
        t,w = _rule(quadrature_order)
        width = np.diff(edges)
        v = (edges[:-1,None]+width[:,None]*t).ravel()
        interval_index=np.repeat(np.arange(intervals),quadrature_order)
        log_weight = np.log((width[:,None]*w).ravel())
        log_prior = norm.logpdf(v,scale=sv)
        xs,ys,event=_frame_arrays(support,load_ratio_fill=self.population.ratio_median_)
        sigma=np.exp(self.population.params_[3])
        factor_sup=np.where(event==1,-np.log(sigma)-.5*LOG2PI,0.)
        # Bound each positive v quadrature node BEFORE expensive u integration.
        # E_u[prod L_j] <= E_u[L_i] prod_{j!=i}sup L_j for every i.
        # Each E_u[L_i] is an analytic Gaussian convolution, evaluated with the
        # same Gamma quadrature. Pruned node mass is bounded relative to Z;
        # continuous-domain v error remains checked by refinement and tails.
        node_bound=[];kernels=[]
        for value in v:
            shifted=self._at_v(value);kernel=shifted._kernel(xs)
            kernels.append(kernel)
            convolved=dict(kernel,sigma=np.hypot(sigma,self.life_prior_sd))
            single=self._observation_loglikelihood(convolved,ys,event,np.array([0.]))[:,0]
            bound=float(np.min(single+factor_sup.sum()-factor_sup))
            failed=np.flatnonzero(event==1)
            # A much sharper bound when >=2 failures identify relative shape:
            # integrate their shared u EXACTLY, conditional on the two Gamma
            # quadrature components, then sum the positive 2D Gaussian mixture.
            # Other factors remain uniformly bounded. No target mode is used.
            common_variance=sigma**2+2*self.life_prior_sd**2
            for ia,i in enumerate(failed):
                for j in failed[ia+1:]:
                    r1=ys[i]-kernel['mu'][i,:,None]
                    r2=ys[j]-kernel['mu'][j,None,:]
                    quadratic=(r1-r2)**2/(2*sigma**2)+(r1+r2)**2/(2*common_variance)
                    lp=(-LOG2PI-.5*np.log(sigma**2*common_variance)-.5*quadratic+
                        kernel['logmass'][i]+kernel['logmass'][j]+
                        shifted._logw[:,None]+shifted._logw[None,:])
                    pair=float(logsumexp(lp))
                    bound=min(bound,pair+factor_sup.sum()-factor_sup[i]-factor_sup[j])
            node_bound.append(bound)
        log_upper=np.asarray(node_bound)+log_prior+log_weight
        ranked=np.argsort(log_upper)[::-1]
        remaining_bound=np.r_[np.logaddexp.accumulate(log_upper[ranked][::-1])[::-1],-np.inf]
        components=[];log_joint_values=[];used=[];count=0
        while True:
            if count==0:next_count=min(8,len(v))
            else:
                admissible=np.flatnonzero(remaining_bound<=evidence+np.log(.5*self.tail_tolerance))
                next_count=max(count+1,int(admissible[0]) if len(admissible) else len(v))
                next_count=min(next_count,len(v))
            for index in ranked[count:next_count]:
                value=v[index]
                if conditional_cache is not None and float(value) in conditional_cache:
                    post=conditional_cache[float(value)]
                else:
                    post=self._conditional_u(self._at_v(value),support,(xs,ys,event),kernels[index])
                    if conditional_cache is not None:conditional_cache[float(value)]=post
                components.append((float(value),post));used.append(index)
                log_joint_values.append(float(post['log_marginal'])+log_prior[index]+log_weight[index])
            count=next_count
            evidence=float(logsumexp(log_joint_values))
            omitted_node_bound=float(logsumexp(log_upper[ranked[count:]])) if count<len(v) else -np.inf
            if omitted_node_bound-evidence<=np.log(.5*self.tail_tolerance) or count==len(v):break
        log_joint=np.asarray(log_joint_values)
        evidence=float(logsumexp(log_joint))
        weights=np.exp(log_joint-evidence)
        # A finite-life mixture density cannot exceed the Gaussian peak; each
        # survival factor <=1. This bounds unintegrated prior v tails uniformly.
        log_likelihood_upper=int(event.sum())*max(0.,-np.log(sigma)-.5*LOG2PI)
        log_tail_bound=np.log(2.)+log_ndtr(-radius/sv)+log_likelihood_upper-evidence
        selected_v=v[used]
        v_mean=float(weights@selected_v)
        u_mean=float(sum(p['mean']*weight for (_,p),weight in zip(components,weights)))
        tail_u=float(sum(p.get('tail_mass_bound',0.)*weight for (_,p),weight in zip(components,weights)))
        resolution_u=float(sum(np.expm1(p.get('u_resolution_log_evidence_difference',0.))*weight
            for (_,p),weight in zip(components,weights)))
        used_intervals=interval_index[used]
        interval_log_marginal=np.array([float(logsumexp(log_joint[used_intervals==i]))
            if np.any(used_intervals==i) else -np.inf for i in range(intervals)])
        return dict(components=components,weight=weights,log_marginal=evidence,
            v_mean=v_mean,u_mean=u_mean,v_variance=float(weights@(selected_v-v_mean)**2),
            radius=radius,refinement=refinement,v_nodes=len(used),v_nodes_full_rule=len(v),
            tail_mass_bound_v=float(np.exp(min(0.,log_tail_bound)))+float(np.exp(omitted_node_bound-evidence)),
            omitted_positive_v_rule_mass_bound=float(np.exp(omitted_node_bound-evidence)),
            interval_log_marginal=interval_log_marginal,edges=edges,
            quadrature_order=quadrature_order,
            conditional_u_tail_bound_weighted=tail_u,minimum_scale_v=float(minimum_scale),
            conditional_u_resolution_estimate_weighted=resolution_u,
            elapsed_seconds=time.monotonic()-start)

    def _posterior(self, support):
        token=self._token(support,True)
        if token in self._support_cache:
            self._support_cache.move_to_end(token)
            return self._support_cache[token]
        result=self._integrated_evidence(support)
        result.update(query_checks={},support=support)
        if self.max_support_cache>0:
            self._support_cache[token]=result
            while len(self._support_cache)>self.max_support_cache:
                self._support_cache.popitem(last=False)
        return result

    def _integrated_evidence(self, observations):
        """Marginal-likelihood evaluator, with NO model or prediction cache.

        For predictive scoring it may evaluate support+one scoring observation;
        this computes a numerator integral only, and never installs that query
        as selected support, changes a parameter, or enters a prediction cache.
        """
        support=observations;sv=self.fatigue_limit_prior_sd
        radius=8*sv;conditional_cache={}
        scale=1/np.sqrt(1/sv**2+(len(support)+1)/np.exp(self.population.params_[5])**2)
        for _domain in range(8):
            # Start globally, covering every possible mode. Only intervals whose
            # positive 8/16-point contributions disagree are bisected. The scale
            # of any component in the latent-Gaussian v mixture is >= this scale;
            # 12*scale is a starting interval, not an accepted final resolution.
            intervals=max(4,int(np.ceil(2*radius/(12*scale))))
            edges=np.linspace(-radius,radius,intervals+1)
            for refinement in range(self.max_refinements+1):
                coarse=self._level(support,radius,refinement,edges,8,conditional_cache)
                fine=self._level(support,radius,refinement,edges,16,conditional_cache)
                if fine['tail_mass_bound_v']>self.tail_tolerance:
                    break
                relative_errors=np.abs(np.exp(coarse['interval_log_marginal']-fine['log_marginal'])-
                    np.exp(fine['interval_log_marginal']-fine['log_marginal']))
                error=float(relative_errors.sum())
                fine['interval_evidence_resolution_L1']=error
                if error<=self.evidence_tolerance:
                    return dict(levels=[coarse,fine],conditional_cache=conditional_cache)
                if refinement==self.max_refinements:
                    raise FloatingPointError('joint RFL adaptive evidence resolution did not converge')
                ranked=np.argsort(relative_errors)[::-1]
                remaining=error;split=[]
                for i in ranked:
                    split.append((edges[i]+edges[i+1])/2)
                    remaining-=relative_errors[i]
                    if remaining<=.25*self.evidence_tolerance:break
                edges=np.sort(np.r_[edges,split])
            radius*=1.7
        raise FloatingPointError('joint RFL adaptive v prior-tail bound failed')

    def _components_for_query(self, query, level):
        x=self.population._x(query)
        values=[]
        for (v,post),wv in zip(level['components'],level['weight']):
            # Omitted tiny v components carry <= round-off-scale total mass;
            # do not truncate unnormalized posterior components by point count.
            kernel=self._at_v(v)._kernel(x)
            values.append((kernel,post,float(wv)))
        return values

    def _cdf_from_components(self, log_y, query, components):
        y=np.broadcast_to(np.asarray(log_y,float),(len(query),))
        if np.isnan(y).any():raise ValueError('CDF log-life argument must not be NaN')
        result=np.zeros(len(query))
        for kernel,post,wv in components:
            for i in range(len(query)):
                z=(y[i]-kernel['mu'][i,None,:]-post['u'][:,None])/kernel['sigma']
                result[i]+=wv*np.exp(kernel['logmass'][i])*np.sum(post['weight'][:,None]*self.population._w*ndtr(z))
        return np.where(np.isposinf(y),1.,np.clip(result,0.,1.))

    def _finite_mass(self, query, components):
        value=np.zeros(len(query))
        for kernel,_,wv in components:value+=wv*np.exp(kernel['logmass'])
        return np.clip(value,0.,1.)

    def _quantiles_from_components(self,query,components,alphas):
        mass=self._finite_mass(query,components)
        out=np.full((len(query),len(alphas)),np.inf)
        # Brackets in log10 life expand deterministically; this is numerical
        # root finding, never an outcome-dependent model or configuration choice.
        for i in range(len(query)):
            qi=query.iloc[[i]]
            ci=[(dict(mu=k['mu'][[i]],logmass=k['logmass'][[i]],sigma=k['sigma']),p,w) for k,p,w in components]
            for j,alpha in enumerate(alphas):
                if alpha>=mass[i]:continue
                lo,hi=-20.,30.
                for _ in range(12):
                    if self._cdf_from_components(lo,qi,ci)[0]<alpha<self._cdf_from_components(hi,qi,ci)[0]:break
                    lo-=max(10.,hi-lo);hi+=max(10.,hi-lo)
                else:raise FloatingPointError('joint RFL quantile could not be bracketed')
                out[i,j]=brentq(lambda y:self._cdf_from_components(y,qi,ci)[0]-alpha,lo,hi,xtol=2e-8)
        return out

    def _resolved(self, query, support, alphas=(.1,.5)):
        """Refine using query covariates and quantiles, NEVER query outcomes."""
        posterior=self._posterior(support)
        token=(self._token(query,False),tuple(float(a) for a in alphas))
        if token in posterior['query_checks']:
            index,receipt=posterior['query_checks'][token]
            self.last_prediction_receipt_=receipt
            return self._components_for_query(query,posterior['levels'][index])
        while True:
            coarse,fine=posterior['levels'][-2:]
            cc=self._components_for_query(query,coarse)
            cf=self._components_for_query(query,fine)
            qc=self._quantiles_from_components(query,cc,alphas)
            qf=self._quantiles_from_components(query,cf,alphas)
            same_class=bool(np.array_equal(np.isfinite(qc),np.isfinite(qf)))
            finite=np.isfinite(qc)&np.isfinite(qf)
            qdiff=float(np.max(np.abs(qc[finite]-qf[finite]),initial=0.))
            massdiff=float(np.max(np.abs(self._finite_mass(query,cc)-self._finite_mass(query,cf)),initial=0.))
            massfine=self._finite_mass(query,cf)
            classification_margin=float(np.min(np.abs(massfine[:,None]-np.asarray(alphas)[None,:]),initial=np.inf))
            classification_error=max(4*massdiff,4*fine['tail_mass_bound_v'],
                4*fine['conditional_u_tail_bound_weighted'],
                4*fine['conditional_u_resolution_estimate_weighted'],
                4*fine.get('interval_evidence_resolution_L1',0.),1e-14)
            classification_separated=classification_margin>classification_error
            cdfdiff=0.
            for j in range(len(alphas)):
                at=np.where(np.isfinite(qf[:,j]),qf[:,j],6.)
                cdfdiff=max(cdfdiff,float(np.max(np.abs(self._cdf_from_components(at,query,cc)-self._cdf_from_components(at,query,cf)),initial=0.)))
            evdiff=abs(fine['log_marginal']-coarse['log_marginal'])
            if same_class and classification_separated and qdiff<=self.quantile_tolerance and max(cdfdiff,massdiff)<=self.cdf_tolerance and evdiff<=self.evidence_tolerance:
                receipt=dict(success=True,n_selected_support=len(support),n_query=len(query),
                    k0_analytic_convolution=False,scalar_reduction=False,
                    support_log_marginal=fine['log_marginal'],v_nodes=fine['v_nodes'],
                    v_nodes_full_rule=fine['v_nodes_full_rule'],
                    refinement=fine['refinement'],v_radius=fine['radius'],
                    tail_mass_bound_v=fine['tail_mass_bound_v'],
                    conditional_u_tail_bound_weighted=fine['conditional_u_tail_bound_weighted'],
                    conditional_u_resolution_estimate_weighted=fine['conditional_u_resolution_estimate_weighted'],
                    max_quantile_log10_resolution_difference=qdiff,max_cdf_resolution_difference=cdfdiff,
                    max_finite_mass_resolution_difference=massdiff,evidence_resolution_difference=evdiff,
                    finite_infinite_classification_consistent=same_class,
                    finite_infinite_classification_margin=classification_margin,
                    finite_infinite_classification_resolution_error=classification_error,
                    posterior_u_mean=fine['u_mean'],posterior_v_mean=fine['v_mean'],
                    query_outcomes_used_for_resolution=False,target_posterior_is_Laplace=False,
                    rule_difference_is_analytic_error_bound=False,
                    population_parameters_uncertainty_integrated=False,quantile_is_R90C90=False)
                posterior['query_checks'][token]=(len(posterior['levels'])-1,receipt)
                self.last_prediction_receipt_=receipt
                return cf
            next_refinement=fine['refinement']+1
            if next_refinement>self.max_refinements:
                raise FloatingPointError('joint RFL predictive quantile/CDF resolution did not converge')
            edges=fine['edges'];edges=np.sort(np.r_[edges,(edges[:-1]+edges[1:])/2])
            cache=posterior.get('conditional_cache')
            posterior['levels'].extend([
                self._level(support,fine['radius'],next_refinement,edges,8,cache),
                self._level(support,fine['radius'],next_refinement,edges,16,cache)])

    def _direct(self, support, query):
        if self._empty(support):
            self.last_prediction_receipt_=dict(success=True,n_selected_support=0,n_query=len(query),
                k0_analytic_convolution=True,scalar_reduction=False,quantile_is_R90C90=False)
            return self._cold
        if self.fatigue_limit_prior_sd==0:
            self.last_prediction_receipt_=dict(success=True,n_selected_support=len(support),n_query=len(query),
                k0_analytic_convolution=False,scalar_reduction=True,quantile_is_R90C90=False)
            return self.population
        return None

    def predict_quantiles(self,query,support=None,alphas=(.1,)):
        alphas=np.asarray(alphas,float)
        if alphas.ndim!=1 or np.any(~np.isfinite(alphas)) or np.any((alphas<=0)|(alphas>=1)):
            raise ValueError('quantile levels must be finite and strictly between0and1')
        support=self._checked_support(support);self._check_query(query,support)
        direct=self._direct(support,query)
        if direct is not None:return direct.predict_quantiles(query,support,alphas)
        components=self._resolved(query,support,tuple(alphas))
        return self._quantiles_from_components(query,components,alphas)

    def predict_cdf(self,log_y,query,support=None):
        support=self._checked_support(support);self._check_query(query,support)
        direct=self._direct(support,query)
        if direct is not None:return direct.predict_cdf(log_y,query,support)
        return self._cdf_from_components(log_y,query,self._resolved(query,support))

    def failure_probability(self,query,support=None):
        support=self._checked_support(support);self._check_query(query,support)
        direct=self._direct(support,query)
        if direct is not None:return direct.failure_probability(query)
        return self._finite_mass(query,self._resolved(query,support))

    def predict_location(self,query,support=None):
        return self.predict_quantiles(query,support,(.5,))[:,0]

    def _predict_log_score_evidence_ratio(self,query,support=None):
        """Proper predictive log score via separately certified evidence ratios.

        log p(query_i|selected support)=log Z(support,query_i)-log Z(support).
        Every numerator uses the SAME fixed population and target prior. Query
        outcomes affect only evaluation of their own predictive likelihood;
        neither numerical posterior objects nor query outcomes enter the fitted
        model or selected-support/prediction caches. This avoids requiring tail
        accuracy relative to an extremely small density from a support-only
        quadrature domain.
        """
        support=self._checked_support(support);self._check_query(query,support)
        direct=self._direct(support,query)
        if direct is not None:return direct.predict_log_score(query,support)
        _,y,event=_frame_arrays(query,load_ratio_fill=self.population.ratio_median_)
        if not np.isfinite(y).all() or not np.isin(event,[0,1]).all():
            raise ValueError('scoring requires finite query endpoints and binary events')
        start=time.monotonic()
        denominator=self._posterior(support)['levels'][-1]
        scores=[];numerator_receipts=[]
        for i in range(len(query)):
            # Local integration input, not a call to fit/adapt and not cached.
            observations=pd.concat([support,query.iloc[[i]]],ignore_index=True)
            result=self._integrated_evidence(observations)
            numerator=result['levels'][-1]
            scores.append(numerator['log_marginal']-denominator['log_marginal'])
            numerator_receipts.append(dict(v_nodes=numerator['v_nodes'],
                tail_mass_bound_v=numerator['tail_mass_bound_v'],
                conditional_u_tail_bound_weighted=numerator['conditional_u_tail_bound_weighted'],
                evidence_resolution_difference=abs(numerator['log_marginal']-result['levels'][-2]['log_marginal'])))
        self.last_prediction_receipt_=dict(success=True,n_selected_support=len(support),n_query=len(query),
            score_method='separately certified log marginal likelihood ratio',
            support_log_marginal=denominator['log_marginal'],
            support_tail_mass_bound_v=denominator['tail_mass_bound_v'],
            query_outcomes_used_only_for_numeric_likelihood_evaluation=True,
            query_outcomes_used_for_fit_or_support_cache=False,
            numerator_integrals_cached=False,numerator_receipts=numerator_receipts,
            population_parameters_uncertainty_integrated=False,target_posterior_is_Laplace=False,
            elapsed_seconds=time.monotonic()-start,quantile_is_R90C90=False)
        return np.asarray(scores)

    def _score_components(self,query,components,coarse_u=False):
        _,y,event=_frame_arrays(query,load_ratio_fill=self.population.ratio_median_)
        log_v_weights=np.array([np.log(wv) if wv>0 else -np.inf for _,_,wv in components])
        if coarse_u:
            # Switching u rules also changes each conditional evidence and
            # therefore v posterior weights. Comparing only normalized u
            # expectations at fixed v weights would miss that error source.
            log_v_weights+=np.array([p.get('coarse_log_marginal',p['log_marginal'])-p['log_marginal']
                                    for _,p,_ in components])
        log_v_weights-=logsumexp(log_v_weights)
        terms=[]
        for (kernel,post,wv),logwv in zip(components,log_v_weights):
            if wv==0:continue
            u=post.get('coarse_u',post['u']) if coarse_u else post['u']
            weight=post.get('coarse_weight',post['weight']) if coarse_u else post['weight']
            logw=np.full(len(weight),-np.inf)
            np.log(weight,out=logw,where=weight>0)
            ll=self._observation_loglikelihood(kernel,y,event,u)
            terms.append(logwv+logsumexp(ll+logw[None,:],axis=1))
        return logsumexp(np.asarray(terms),axis=0)

    def predict_log_score(self,query,support=None):
        """Positive posterior-mixture score, with checked relative accuracy.

        Separate u-rule and v-rule comparisons are numerical resolution
        diagnostics. Uniform omitted posterior mass times a row's likelihood
        supremum bounds the truncation/pruning effect relative to that row's
        retained predictive likelihood. Only rows that fail these checks use
        separately certified evidence ratios. Query outcomes influence only
        this scoring arithmetic, never the support posterior/model caches.
        """
        support=self._checked_support(support);self._check_query(query,support)
        direct=self._direct(support,query)
        if direct is not None:return direct.predict_log_score(query,support)
        _,y,event=_frame_arrays(query,load_ratio_fill=self.population.ratio_median_)
        if not np.isfinite(y).all() or not np.isin(event,[0,1]).all():
            raise ValueError('scoring requires finite query endpoints and binary events')
        start=time.monotonic();posterior=self._posterior(support)
        coarse,fine=posterior['levels'][-2:]
        cf=self._components_for_query(query,fine)
        cc=self._components_for_query(query,coarse)
        value=self._score_components(query,cf)
        u_coarse=self._score_components(query,cf,True)
        v_coarse=self._score_components(query,cc)
        u_error=np.abs(value-u_coarse);v_error=np.abs(value-v_coarse)
        omitted=fine['tail_mass_bound_v']+fine['conditional_u_tail_bound_weighted']
        likelihood_peak=np.where(event==1,-np.log(np.exp(self.population.params_[3]))-.5*LOG2PI,0.)
        log_relative_bound=np.log(max(omitted,np.finfo(float).tiny))+np.logaddexp(0.,likelihood_peak-value)
        relative_bound=np.exp(np.minimum(log_relative_bound,700))
        log_error_bound=np.full(len(query),np.inf)
        bounded=relative_bound<1
        log_error_bound[bounded]=-np.log1p(-relative_bound[bounded])
        eligible=(np.isfinite(value)&(u_error<=self.evidence_tolerance)&(v_error<=self.evidence_tolerance)&
                  (log_error_bound<=self.evidence_tolerance))
        failed=np.flatnonzero(~eligible);fallback_receipt=None
        if len(failed):
            value[failed]=self._predict_log_score_evidence_ratio(query.iloc[failed],support)
            fallback_receipt=self.last_prediction_receipt_.copy()
        self.last_prediction_receipt_=dict(success=True,n_selected_support=len(support),n_query=len(query),
            score_method='positive posterior mixture with per-row u/v resolution and relative-tail checks; evidence-ratio fallback',
            support_log_marginal=fine['log_marginal'],
            posterior_omitted_mass_bound=omitted,
            u_log_score_resolution_difference=u_error.tolist(),v_log_score_resolution_difference=v_error.tolist(),
            relative_predictive_likelihood_tail_bound=relative_bound.tolist(),
            predictive_log_score_tail_error_bound=log_error_bound.tolist(),
            posterior_mixture_rows=int(eligible.sum()),evidence_ratio_fallback_rows=failed.tolist(),
            evidence_ratio_fallback_receipt=fallback_receipt,
            query_outcomes_used_only_for_numeric_likelihood_evaluation=True,
            query_outcomes_used_for_fit_or_support_cache=False,numerator_integrals_cached=False,
            resolution_difference_is_analytic_error_bound=False,
            omitted_mass_bound_conditional_on_fixed_Gamma_rule=True,
            population_parameters_uncertainty_integrated=False,target_posterior_is_Laplace=False,
            elapsed_seconds=time.monotonic()-start,quantile_is_R90C90=False)
        return value

    def _predict_log_score_posterior_quadrature(self,query,support):
        """Diagnostic benchmark only; production score uses certified ratios.

        Its covariance-only q10/median resolution receipt does not certify
        relative accuracy for a far-tail predictive density. Never silently
        substitute this faster path for the production evidence-ratio method.
        """
        components=self._resolved(query,support)  # depends on pretest columns only
        _,y,event=_frame_arrays(query,load_ratio_fill=self.population.ratio_median_)
        log_terms=[]
        for kernel,post,wv in components:
            if wv==0:continue
            pdf,sf=self.population._logparts(kernel,y,post['u'])
            ll=np.where(event[:,None]==1,pdf,sf)
            log_terms.append(np.log(wv)+logsumexp(ll+np.log(post['weight'])[None,:],axis=1))
        return logsumexp(np.asarray(log_terms),axis=0)


def proposed_joint_rfl_prior_grid(training_hier_tau):
    """Ten prefit candidates; final nested protocol chooses among them."""
    tau=float(training_hier_tau)
    if not np.isfinite(tau) or tau<0:raise ValueError('nonnegative training-only tau required')
    return [dict(life_prior_sd=m*tau,fatigue_limit_prior_sd=v,
                 life_prior_multiplier=m,training_hier_tau=tau)
            for m in [.25,.5,1.,2.,4.] for v in [.05,.15]]
