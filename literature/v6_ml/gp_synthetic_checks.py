"""Meaningful synthetic checks; no actual fatigue observations are fitted."""
from pathlib import Path
import hashlib
import json
import time
import platform
import numpy as np
import pandas as pd
from scipy.linalg import cho_factor,cho_solve
from scipy.optimize import brentq
from scipy.special import log_ndtr
from scipy.stats import norm
from src.v6_gp import CensoredLaplaceGP,GPKernelConfig,censored_normal_parts,proposed_gp_grid,training_reference

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'literature/v6_ml'

def frame(ids,x,ratio=.1,condition='c',y=None,event=1):
    n=len(ids)
    return pd.DataFrame(dict(row_id=ids,dataset_id=np.broadcast_to(condition,(n,)),
        log_stress=x,load_ratio=np.broadcast_to(ratio,(n,)),
        log_life=np.zeros(n) if y is None else y,event=np.broadcast_to(event,(n,))))

def exact_gaussian(model,observed,query):
    K=model.kernel(observed,observed)+np.eye(len(observed))*model.jitter_used_
    Ky=K+np.eye(len(observed))*model.noise_sd**2
    cross=model.kernel(observed,query)
    c=cho_factor(Ky,lower=True)
    residual=observed.log_life.to_numpy()-model._mean(observed)
    mean=model._mean(query)+cross.T@cho_solve(c,residual)
    prior=np.diag(model.kernel(query,query))
    variance=prior-np.sum(cross*cho_solve(c,cross),axis=0)+model.noise_sd**2
    lm=-.5*residual@cho_solve(c,residual)-np.log(np.diag(c[0])).sum()-.5*len(observed)*np.log(2*np.pi)
    return mean,variance,lm

def main():
    receipts={};sigma=.7
    z=np.array([-30.,-10.,-1.,0.,1.,10.,30.])
    y=z*sigma;mu=np.zeros(len(y));h=1e-4
    max_gradient=max_curvature=0.
    for event in [0,1]:
        e=np.full(len(y),event)
        ll,g,w=censored_normal_parts(mu,sigma,y,e)
        plus=censored_normal_parts(mu+h,sigma,y,e)
        minus=censored_normal_parts(mu-h,sigma,y,e)
        max_gradient=max(max_gradient,float(np.max(np.abs((plus[0]-minus[0])/(2*h)-g))))
        max_curvature=max(max_curvature,float(np.max(np.abs(-(plus[1]-minus[1])/(2*h)-w))))
        assert np.isfinite(ll).all() and (w>=0).all()
    assert max_gradient<2e-7 and max_curvature<2e-7
    extreme=censored_normal_parts(np.array([0.,0.]),1.,np.array([1000.,-1000.]),np.array([0,0]))
    assert all(np.isfinite(x).all() for x in extreme)
    assert 0.999<extreme[2][0]<1.001
    receipts['likelihood_derivatives']=dict(max_gradient_error=max_gradient,max_curvature_error=max_curvature,extreme_z1000_finite=True)

    x=np.linspace(1.9,2.6,8)
    y=11.-2*x-.3*.1+.4*np.sin(12*x)
    train=frame([f'synthetic_train{i}' for i in range(8)],x,condition=['a']*4+['b']*4,y=y)
    query=frame([f'synthetic_query{i}' for i in range(6)],np.linspace(1.95,2.55,6),condition='new')
    config=GPKernelConfig(global_sd=.6,stress_length=.18,ratio_length=.7,
        condition_intercept_sd=.4,condition_shape_sd=.3,condition_shape_length=.2)
    gp=CensoredLaplaceGP(config,noise_sd=.25,mean_parameters=(11.,-2.,-.3)).fit(train)
    actual=gp.predict_mean_variance(query);expected=exact_gaussian(gp,train,query)
    me=float(np.max(np.abs(actual[0]-expected[0])));ve=float(np.max(np.abs(actual[1]-expected[1])))
    lme=abs(gp.population_['receipt']['log_marginal_laplace']-expected[2])
    assert max(me,ve,lme)<1e-8
    q10=gp.predict_quantiles(query)[:,0]
    assert np.max(np.abs(gp.predict_cdf(q10,query)-.1))<1e-12
    assert np.array_equal(gp.predict_cdf(-np.inf,query),np.zeros(len(query)))
    assert np.array_equal(gp.predict_cdf(np.inf,query),np.ones(len(query)))
    receipts['uncensored_exact_GP']=dict(mean_error=me,variance_error=ve,log_marginal_error=lme,q10_CDF_matches=True)
    curvature=float(np.max(np.abs(np.diff(actual[0],n=2))))
    assert curvature>1e-3
    receipts['nonlinear_function_behavior']=dict(max_absolute_second_difference=curvature,nonlinear_posterior_curve_confirmed=True)

    support=frame(['synthetic_support1','synthetic_support2'],[2.05,2.45],condition='new',y=[6.6,5.8])
    before=gp.mean_coef_.copy();original_config=gp.fit_receipt_['kernel'].copy()
    am,av=gp.predict_mean_variance(query,support)
    em,ev,_=exact_gaussian(gp,pd.concat([train,support],ignore_index=True),query)
    assert np.max(np.abs(am-em))<1e-8 and np.max(np.abs(av-ev))<1e-8
    assert np.array_equal(before,gp.mean_coef_) and original_config==gp.fit_receipt_['kernel']
    assert np.array_equal(gp.predict_quantiles(query,support),gp.predict_quantiles(query,support.iloc[::-1]))
    changed=query.copy();changed['log_life']=100.;changed['event']=0
    assert np.array_equal(gp.predict_quantiles(query,support),gp.predict_quantiles(changed,support))
    try:gp.predict_quantiles(support,support)
    except ValueError:pass
    else:raise AssertionError('query/support identity leakage guard missing')
    receipts['selected_support_joint_update']=dict(exact_Gaussian_joint_mean_error=float(np.max(np.abs(am-em))),exact_Gaussian_joint_variance_error=float(np.max(np.abs(av-ev))),fixed_population_mean_and_kernel=True,query_outcomes_ignored=True,support_order_invariant=True,identity_overlap_rejected=True)

    empty=frame([],np.array([]))
    scalar_cfg=GPKernelConfig(global_sd=.7,stress_length=.2,condition_intercept_sd=0.,condition_shape_sd=0.)
    scalar=CensoredLaplaceGP(scalar_cfg,noise_sd=.3,mean_parameters=(5.,0.,0.)).fit(empty)
    runout=frame(['synthetic_runout'],[2.2],condition='new',y=[6.],event=0)
    sq=frame(['synthetic_unobserved'],[2.2],condition='new')
    sm,sv=scalar.predict_mean_variance(sq,runout)
    prior_var=.7**2;obs_var=.3**2
    derivative=lambda f:float(np.exp(norm.logpdf((6-f)/.3)-log_ndtr((f-6)/.3))/.3-(f-5)/prior_var)
    mode=brentq(derivative,5.,8.)
    w=censored_normal_parts(np.array([mode]),.3,np.array([6.]),np.array([0]))[2][0]
    reference_var=1/(1/prior_var+w)+obs_var
    assert abs(sm[0]-mode)<2e-8 and abs(sv[0]-reference_var)<2e-8
    failure=runout.copy();failure.event=1
    fm,_=scalar.predict_mean_variance(sq,failure)
    assert sm[0]>fm[0]>5. and np.isfinite(scalar.predict_quantiles(sq,runout)).all()
    receipts['right_censor_all_runout']=dict(scalar_mode_error=float(abs(sm[0]-mode)),scalar_Laplace_variance_error=float(abs(sv[0]-reference_var)),censor_updates_above_failure_at_stop=True,proper_prior_keeps_finite_quantile=True)
    zero_cfg=GPKernelConfig(global_sd=0.,condition_intercept_sd=0.,condition_shape_sd=0.)
    zero=CensoredLaplaceGP(zero_cfg,noise_sd=.3,mean_parameters=(5.,0.,0.)).fit(train)
    zm,zv=zero.predict_mean_variance(sq,runout)
    assert np.array_equal(zm,np.array([5.])) and np.array_equal(zv,np.array([.3**2]))
    receipts['zero_covariance_anchor']=dict(exact_fixed_mean_and_observation_noise=True,selected_support_has_no_effect=True)
    for invalid in [(np.nan,),(-.1,),(1.1,)]:
        try:zero.predict_quantiles(sq,alphas=invalid)
        except ValueError:pass
        else:raise AssertionError('invalid quantile accepted')
    for invalid in [(np.nan,.5),(.3,np.inf)]:
        try:proposed_gp_grid(*invalid)
        except ValueError:pass
        else:raise AssertionError('nonfinite reference scale accepted')
    colliding=frame([1,'1'],[2.,2.1])
    try:zero.predict_quantiles(colliding)
    except ValueError:pass
    else:raise AssertionError('string-converted row identity collision accepted')
    rising=CensoredLaplaceGP(zero_cfg,noise_sd=.3,mean_parameters=(0.,1.,0.)).fit(empty)
    rise_grid=frame(['rise1','rise2','rise3'],[2.,2.1,2.2])
    assert rising.monotonicity_receipt(rise_grid)['positive_quantile_increments']==2
    receipts['API_edge_validation']=dict(nonfinite_quantiles_rejected=True,nonfinite_reference_scales_rejected=True,converted_identity_collisions_rejected=True,monotonicity_diagnostic_detects_positive_increments=True)
    grid=proposed_gp_grid(.3,.5)
    assert len(grid)==66 and len({json.dumps((r['config'],r['noise_sd']),sort_keys=True) for r in grid})==66
    receipts['proposed_grid']=dict(n_candidates=66,distinct_effective_configs=True,zero_covariance_and_default_anchors=True,frozen_for_real_tuning=False)

    # Generated observations with similar matrix dimensions, never real rows.
    rng=np.random.default_rng(6021);n=441
    stress=rng.uniform(1.9,2.65,n);ratio=rng.choice([.7,.1,-1.],n)
    condition=np.array([f'synthetic_condition{i%48}' for i in range(n)])
    offsets=rng.normal(0,.35,48)
    latent=11.-2*stress-.25*ratio+.2*np.sin(10*stress)+offsets[np.arange(n)%48]
    actual_life=latent+rng.normal(0,.3,n);stop=6.3
    observed=np.minimum(actual_life,stop);event=(actual_life<=stop).astype(int)
    synthetic=frame([f'generated_population{i}' for i in range(n)],stress,ratio,condition,observed,event)
    synthetic['group_id']=[f'synthetic_family{(i%48)%13}' for i in range(n)]
    start=time.monotonic();large=CensoredLaplaceGP(config,noise_sd=.35).fit(synthetic)
    fit_seconds=time.monotonic()-start
    manyq=frame([f'generated_query{i}' for i in range(10)],np.linspace(1.95,2.6,10),condition='new_synthetic')
    manys=frame([f'generated_support{i}' for i in range(5)],np.linspace(2.,2.55,5),condition='new_synthetic',y=[6.3,6.3,6.1,5.8,5.7],event=[0,0,1,1,1])
    start=time.monotonic();prediction=large.predict_quantiles(manyq,manys)
    support_seconds=time.monotonic()-start
    assert np.isfinite(prediction).all()
    receipts['synthetic_441_runtime']=dict(training_rows=n,generated_families=13,generated_conditions=48,censored_rows=int((event==0).sum()),fit_seconds=fit_seconds,support5_and_query10_seconds=support_seconds,fit_gradient_inf=large.population_['receipt']['gradient_inf'],support_gradient_inf=large.last_prediction_receipt_['gradient_inf'],real_fatigue_rows_fitted=0,scientific_validation=False)
    start=time.monotonic();reference=training_reference(synthetic)
    assert reference['reference_noise_sd']>0 and reference['reference_condition_sd']>0
    assert reference['n_rows']==441 and reference['source_families']==13
    receipts['training_reference_recipe']=dict(synthetic_only=True,success=reference['fit_receipt']['success'],n_rows=441,within_condition_noise=reference['reference_noise_sd'],condition_intercept_sd=reference['reference_condition_sd'],elapsed_seconds=time.monotonic()-start)
    start=time.monotonic();worst_fit_gradient=worst_support_gradient=0.
    for candidate in proposed_gp_grid(reference['reference_noise_sd'],reference['reference_condition_sd']):
        model=CensoredLaplaceGP(GPKernelConfig(**candidate['config']),
            noise_sd=candidate['noise_sd'],mean_parameters=reference['mean_parameters']).fit(synthetic)
        proposal=model.predict_quantiles(manyq,manys)
        assert np.isfinite(proposal).all()
        worst_fit_gradient=max(worst_fit_gradient,model.population_['receipt']['gradient_inf'])
        worst_support_gradient=max(worst_support_gradient,model.last_prediction_receipt_['gradient_inf'])
    receipts['all66_proposed_configs_synthetic_numerics']=dict(configurations=66,
        all_modes_converged=True,all_quantiles_finite=True,max_population_gradient_inf=worst_fit_gradient,
        max_selected_support_gradient_inf=worst_support_gradient,total_seconds=time.monotonic()-start,
        actual_fatigue_rows_used=0,no_candidate_accuracy_comparison_or_selection=True)
    receipts['monotonicity_diagnostic']=large.monotonicity_receipt(manyq,manys)
    result=dict(status='PASS',checks=receipts,python=platform.python_version(),platform=platform.platform(),source_code_sha256=hashlib.sha256((ROOT/'src/v6_gp.py').read_bytes()).hexdigest(),scope='Synthetic likelihood/GP algebra and numerical feasibility only; no target or actual fatigue data fits/tuning')
    (OUT/'gp_synthetic_receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
