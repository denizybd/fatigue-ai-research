"""Independent synthetic audit of v6 GP; never loads real fatigue observations."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import dataclasses
import hashlib
import json
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from scipy.integrate import quad
from scipy.linalg import block_diag
from scipy.optimize import minimize
from scipy.stats import norm,multivariate_normal
from src.v6_gp import (GPKernelConfig,CensoredLaplaceGP,censored_normal_parts,
                       proposed_gp_grid,training_reference)
from src.v2_models import HierarchicalCensoredBasquin

CODE=ROOT/'src/v6_gp.py'
EXPECTED='14337ab27b986de8716b3ad2d510e19cfa468568aec13368f8a4fbb13f6a5c82'
assert hashlib.sha256(CODE.read_bytes()).hexdigest()==EXPECTED,'source changed during audit'
checks=[]
def record(name,**details):checks.append(dict(name=name,status='PASS',**details))
def df(stress,conditions,prefix,y=None,event=None,ratio=None):
    n=len(stress)
    d=pd.DataFrame(dict(row_id=[f'{prefix}{i}' for i in range(n)],dataset_id=conditions,
                        log_stress=np.log10(stress),load_ratio=np.repeat(-1.,n) if ratio is None else ratio,
                        group_id='synthetic_audit'))
    if y is not None:d['log_life']=y;d['event']=np.ones(n) if event is None else event
    return d
def kernel(a,b,c):
    # Independent formula, not a call through model.kernel.
    x=a.log_stress.to_numpy();z=b.log_stress.to_numpy();r=a.load_ratio.to_numpy();v=b.load_ratio.to_numpy()
    same=np.equal.outer(a.dataset_id.to_numpy(),b.dataset_id.to_numpy())
    return c.global_sd**2*np.exp(-.5*((x[:,None]-z[None,:])**2/c.stress_length**2+
        (r[:,None]-v[None,:])**2/c.ratio_length**2))+same*(c.condition_intercept_sd**2+
        c.condition_shape_sd**2*np.exp(-.5*(x[:,None]-z[None,:])**2/c.condition_shape_length**2))
def mean(d,p):return p[0]+p[1]*d.log_stress.to_numpy()+p[2]*d.load_ratio.to_numpy()

# The66count is checked at the actual covariance/noise level, not merely labels.
grid=proposed_gp_grid(.4,.7)
assert len(grid)==66 and len({x['candidate_id'] for x in grid})==66
probe=df([110,220,440]*3,['c1']*3+['c2']*3+['c3']*3,'probe',ratio=[-1,-1,-1,.1,.1,.1,.5,.5,.5])
fingerprints=set()
for row in grid:
    c=GPKernelConfig(**row['config']);K=kernel(probe,probe,c)+np.eye(len(probe))*row['noise_sd']**2
    assert np.linalg.eigvalsh(K).min()>0
    fingerprints.add(np.round(K,12).tobytes())
assert len(fingerprints)==66
structured=[x for x in grid if x['role']=='structured_GP_grid']
assert len(structured)==64
assert {r['noise_multiplier'] for r in structured}=={.5,.75,1.25,2.}
assert {r['config']['global_sd'] for r in structured}=={0.,.3,.6}
assert {r['config']['condition_shape_sd'] for r in structured}=={0.,.35}
zero=[r for r in structured if r['config']['global_sd']==r['config']['condition_shape_sd']==0]
assert len(zero)==4
record('exact66_unique_covariance_noise_candidates',candidates=66,structured=64,anchors=2,
       inert_length_duplicates_removed=True,all_probe_covariances_positive_definite=True)

# Independent Gaussian tail integrals avoid subtracting nearly equal large
# numbers to obtain curvature. No source hazard/curvature code is reused.
tail_errors=[]
for z in [8.1,20.,100.,1000.,10000.]:
    i0=quad(lambda w:np.exp(-w-w*w/(2*z*z)),0,np.inf,epsabs=1e-13,epsrel=1e-13)[0]
    i1=quad(lambda w:w*np.exp(-w-w*w/(2*z*z)),0,np.inf,epsabs=1e-13,epsrel=1e-13)[0]
    ll,g,w=censored_normal_parts(0.,1.,z,0)
    ref_ll=norm.logpdf(z)+np.log(i0/z)
    ref_g=z/i0;ref_w=i1/i0**2
    np.testing.assert_allclose([ll,g,w],[ref_ll,ref_g,ref_w],rtol=2e-12,atol=2e-12)
    tail_errors.append(float(abs(w-ref_w)))
record('censored_normal_tail_score_curvature_vs_independent_integrals',z_max=10000,
       max_absolute_curvature_error=max(tail_errors))

# All-failure GP conditionals and evidence have an exact analytic solution.
c=GPKernelConfig(global_sd=.4,stress_length=.22,ratio_length=.8,
                 condition_intercept_sd=.5,condition_shape_sd=.3,condition_shape_length=.13)
noise=.25;p=np.array([12.7,-3.,.15])
train=df([150,220,310,180,350],['train1']*3+['train2']*2,'train',
         y=[6.4,5.5,5.1,6.1,4.9],ratio=[-1,-1,-1,.1,.1])
support=df([175,285],['target']*2,'s',y=[6.6,5.6])
query=df([160,210,300,390],['target']*4,'q')
m=CensoredLaplaceGP(c,noise,mean_parameters=p).fit(train)
pred_mean,pred_var=m.predict_mean_variance(query,support)
joint=pd.concat([train,support],ignore_index=True)
K=kernel(joint,joint,c)+np.eye(len(joint))*m.jitter_used_
cross=kernel(joint,query,c);C=K+np.eye(len(joint))*noise**2
delta=joint.log_life.to_numpy()-mean(joint,p)
exact_mean=mean(query,p)+cross.T@np.linalg.solve(C,delta)
exact_cov=kernel(query,query,c)-cross.T@np.linalg.solve(C,cross)+np.eye(len(query))*noise**2
np.testing.assert_allclose(pred_mean,exact_mean,atol=2e-9)
np.testing.assert_allclose(pred_var,np.diag(exact_cov),atol=2e-10)
_,post=m._posterior(support)
exact_lm=multivariate_normal.logpdf(delta,cov=C)
np.testing.assert_allclose(post['receipt']['log_marginal_laplace'],exact_lm,atol=2e-9)
direct=CensoredLaplaceGP(c,noise,mean_parameters=p).fit(joint)
direct_mean,direct_var=direct.predict_mean_variance(query)
np.testing.assert_allclose(pred_mean,direct_mean,atol=2e-9)
np.testing.assert_allclose(pred_var,direct_var,atol=2e-10)
record('selected_support_joint_gaussian_matches_exact_conditioning_and_evidence',
       max_mean_error=float(np.max(np.abs(pred_mean-exact_mean))),
       max_variance_error=float(np.max(np.abs(pred_var-np.diag(exact_cov)))),
       log_evidence_error=float(abs(post['receipt']['log_marginal_laplace']-exact_lm)))

# A separate raw-latent BFGS optimizer verifies the censored Newton mode. A
# numerically differentiated likelihood curvature checks the Laplace variance.
small_train=df([180,300],['old']*2,'ct',y=[6.3,5.4],event=[1,0])
small_support=df([215],['new'],'cs',y=[6.4],event=[0])
small_query=df([190,260],['new']*2,'cq')
cm=CensoredLaplaceGP(c,noise,mean_parameters=p).fit(small_train)
observed,post=cm._posterior(small_support)
K=kernel(observed,observed,c)+np.eye(len(observed))*cm.jitter_used_
Kinv=np.linalg.inv(K);base=mean(observed,p);y=observed.log_life.to_numpy();e=observed.event.to_numpy()
def objective(f):
    z=(y-f)/noise;ll=np.where(e==1,norm.logpdf(z)-np.log(noise),norm.logsf(z))
    return .5*(f-base)@Kinv@(f-base)-ll.sum()
ind=minimize(objective,base,method='BFGS',options={'gtol':1e-8,'maxiter':500})
mode=base+K@post['alpha']
np.testing.assert_allclose(mode,ind.x,atol=2e-7)
h=1e-4;z=(y-mode)/noise
curvature=np.where(e==1,1/noise**2,-(norm.logsf(z+h/noise)-2*norm.logsf(z)+norm.logsf(z-h/noise))/h**2)
cov=np.linalg.inv(Kinv+np.diag(curvature));cross=kernel(observed,small_query,c)
ind_mean=mean(small_query,p)+cross.T@Kinv@(mode-base)
ind_var=np.diag(kernel(small_query,small_query,c)-cross.T@Kinv@cross+cross.T@Kinv@cov@Kinv@cross)+noise**2
actual_mean,actual_var=cm.predict_mean_variance(small_query,small_support)
np.testing.assert_allclose(actual_mean,ind_mean,atol=2e-10)
np.testing.assert_allclose(actual_var,ind_var,rtol=2e-7,atol=2e-9)
record('censored_joint_mode_and_laplace_variance_independently_verified',
       max_mode_error=float(np.max(np.abs(mode-ind.x))),
       max_variance_error=float(np.max(np.abs(actual_var-ind_var))),
       approximation_is_laplace_not_exact_censored_posterior=True)

# k0zero covariance anchor: the supplied mean and natural variance survive;
# training observations cannot induce a signal through numerical jitter.
anchor=CensoredLaplaceGP(GPKernelConfig(global_sd=0,condition_intercept_sd=0,condition_shape_sd=0),
                        .3,mean_parameters=p).fit(train)
am,av=anchor.predict_mean_variance(query,support)
np.testing.assert_array_equal(am,mean(query,p));np.testing.assert_array_equal(av,np.repeat(.09,len(query)))
record('zero_covariance_anchor_exact_mean_and_noise',numerical_jitter_does_not_create_cross_signal=True)

# Queries with nonsensical outcomes have byte-identical predictions. Their
# outcome columns are not even retained by validation(outcomes=False).
before=m.predict_quantiles(query,support,alphas=(.1,.5,.9))
changed=query.assign(log_life=np.nan,event=np.nan)
np.testing.assert_array_equal(m.predict_quantiles(changed,support,alphas=(.1,.5,.9)),before)
old_coef=m.mean_coef_.copy();old_config=dataclasses.asdict(m.config)
swapped=support.iloc[::-1].copy()
np.testing.assert_array_equal(m.predict_quantiles(query,swapped,alphas=(.1,.5,.9)),before)
modified=support.copy();modified.loc[0,'log_life']+=1
assert not np.allclose(m.predict_quantiles(query,modified,alphas=(.1,.5,.9)),before)
np.testing.assert_array_equal(m.mean_coef_,old_coef);assert dataclasses.asdict(m.config)==old_config
record('query_outcomes_isolated_selected_support_only_fixed_hyperparameters',
       support_order_invariant=True,changed_support_endpoint_changes_prediction=True,
       kernel_noise_and_mean_not_refitted_from_support=True)

checked=query.assign(log_life=before[:,0],event=[1,0,1,0])
pm,pv=m.predict_mean_variance(query,support);zs=(checked.log_life-pm)/np.sqrt(pv)
expected=np.where(checked.event==1,norm.logpdf(zs)-np.log(np.sqrt(pv)),norm.logsf(zs))
np.testing.assert_allclose(m.predict_log_score(checked,support),expected,atol=2e-14)
np.testing.assert_allclose(m.predict_cdf(before[:,0],query,support),.1,atol=4e-15)
record('common_quantile_CDF_logscore_APIs_use_observed_density_or_survival')

# An actual GENERATED-data reference fit demonstrates that within-condition
# sigma and between-condition tau are returned in separate named fields and
# that raw-unit location coefficients preserve the training reference function.
rng=np.random.default_rng(8871)
x=np.tile(np.linspace(160,380,10),4);cond=np.repeat(['a','b','c','d'],10)
rr=np.repeat([-1.,-1.,.1,.1],10);offset=np.repeat([-.5,.4,-.4,.5],10)
y=12.8-3*np.log10(x)+.1*rr+offset+rng.normal(0,.13,len(x))
refdata=df(x,cond,'ref',y=y,ratio=rr)
refdata['group_id']=np.repeat(['source1','source2'],20)
reference=training_reference(refdata)
base_model=HierarchicalCensoredBasquin().fit(refdata)
np.testing.assert_allclose(reference['reference_noise_sd'],base_model.sigma_,atol=0)
np.testing.assert_allclose(reference['reference_condition_sd'],base_model.tau_,atol=0)
np.testing.assert_allclose(mean(refdata,reference['mean_parameters']),base_model.predict_location(refdata),atol=4e-15)
assert reference['reference_noise_sd']<reference['reference_condition_sd']
record('generated_training_only_reference_mean_sigma_tau_exact_conversion',
       generated_rows=40,within_condition_sigma=reference['reference_noise_sd'],
       condition_tau=reference['reference_condition_sd'],
       raw_mean_conversion_error=float(np.max(np.abs(mean(refdata,reference['mean_parameters'])-base_model.predict_location(refdata)))))

invalid_checks=0
for f in [lambda:m.predict_quantiles(query,alphas=(np.nan,)),
          lambda:proposed_gp_grid(np.nan,.3),lambda:proposed_gp_grid(np.inf,.3),
          lambda:proposed_gp_grid(.3,np.nan),
          lambda:m.predict_quantiles(query.assign(row_id=[1,'1','x','y'])),
          lambda:m.predict_quantiles(query.assign(row_id=['s0','x','y','z']),support),
          lambda:m.predict_quantiles(query.assign(dataset_id='wrong'),support),
          lambda:m.predict_quantiles(query,support.assign(row_id=['train0','other']))]:
    try:f()
    except ValueError:invalid_checks+=1
assert invalid_checks==8
record('finite_configuration_quantile_and_identity_leakage_guards',invalid_cases_rejected=8)

assert hashlib.sha256(CODE.read_bytes()).hexdigest()==EXPECTED,'source changed during audit'
receipt=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS',
    independent_reader='v3_campaign_raw; GP authored by another agent',
    source='src/v6_gp.py',source_sha256=EXPECTED,checks=checks,check_groups=len(checks),
    real_fatigue_fits_performed=0,generated_data_reference_fits=2,
    source_files_modified=False,
    boundaries=['Laplace approximates censored latent posterior; no exact censored-GP posterior claim',
        'Kernel/mean/noise hyperparameter uncertainty not integrated; latent and natural variance included',
        'No monotonicity guarantee; diagnostic only',
        'API cannot certify outer-family exclusion or training-only external mean provenance; runner must enforce split',
        'Condition labels are statistical database labels, not physical build identities',
        'Training default mean can be estimated; kernel/noise fixed. Proposed training_reference mean/sigma/tau must be called inside each training fold',
        'Source-family balancing applies to inner validation; GP likelihood factors have unit weights'])
(ROOT/'literature/v6_methods/gp_independent_audit.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
