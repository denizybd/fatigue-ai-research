"""Independent generated-data limiting case, no .fit calls or real-data reads."""
import sys,json,hashlib,time
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import norm,multivariate_normal
from src.v3_rfl import NormalNormalRFL
from src.v6_rfl_adapter import JointRFLTargetAdapter

Path('work/v6_rfl_independent').mkdir(parents=True,exist_ok=True)
expected=sys.argv[1]
p=Path('src/v6_rfl_adapter.py');start_hash=hashlib.sha256(p.read_bytes()).hexdigest()
assert start_hash==expected,(start_hash,expected)
pop=NormalNormalRFL(nodes=16)
pop.params_=np.array([5.,-3.,-.2,np.log(.4),-12.,np.log(.03)])
pop.log_stress_ref_=2.2;pop.ratio_center_=.1;pop.ratio_median_=.1
pop.sigma_=.4;pop.tau_gamma_=.03;pop._fallback=None
su=.3;sv=.05
ss=np.array([150.,200.,240.]);qs=np.array([140.,180.,260.])
mu=lambda s:5.-3.*(np.log10(s)-2.2)
sy=mu(ss)+np.array([.25,-.2,.45])
qy=mu(qs)+np.array([-4.,0.,4.])
def frame(stress,y,ids):
 return pd.DataFrame(dict(row_id=ids,dataset_id='synthetic_conjugate',log_stress=np.log10(stress),load_ratio=.1,log_life=y,event=np.ones(len(stress),int)))
s=frame(ss,sy,['s0','s1','s2']);q=frame(qs,qy,['q0','q1','q2'])
variance=1/(1/su**2+len(s)/.4**2);umean=variance*np.sum(sy-mu(ss))/.4**2
expected_scores=norm.logpdf(qy,loc=mu(qs)+umean,scale=np.sqrt(.4**2+variance))
expected_ev=multivariate_normal.logpdf(sy,mean=mu(ss),cov=.4**2*np.eye(len(s))+su**2*np.ones((len(s),len(s))))
a=JointRFLTargetAdapter(pop,su,sv)
t=time.monotonic();scores=a.predict_log_score(q,s);score_receipt=a.last_prediction_receipt_.copy();duration=time.monotonic()-t
vals=a.predict_quantiles(q,s,(.1,.5));qreceipt=a.last_prediction_receipt_.copy()
reference_q=mu(qs)[:,None]+umean+np.sqrt(.4**2+variance)*norm.ppf([.1,.5])[None,:]
changed=q.copy();changed.log_life=[-100,0,100];changed.event=[0,1,0]
assert np.array_equal(vals,a.predict_quantiles(changed,s,(.1,.5)))
assert len(a._support_cache)==1
err=float(np.max(np.abs(scores-expected_scores)));qerr=float(np.max(np.abs(vals-reference_q)))
ev_err=abs(a._posterior(s)['levels'][-1]['log_marginal']-expected_ev)
assert err<2e-5,(scores,expected_scores,err)
assert qerr<2e-5,(vals,reference_q,qerr)
assert ev_err<2e-5,ev_err
end_hash=hashlib.sha256(p.read_bytes()).hexdigest();assert end_hash==start_hash
r=dict(status='PASS',source_sha256_at_start=start_hash,source_sha256_at_end=end_hash,
 scope='Gamma-negligible limiting case equals exact conjugate shared-u Normal; generated numbers only',
 gamma_mean_logstress=-12.,Gamma_nodes=16,life_prior_sd=su,v_prior_sd=sv,
 computed_scores=scores.tolist(),exact_conjugate_scores=expected_scores.tolist(),
 max_score_absolute_error=err,max_quantile_absolute_error=qerr,support_log_evidence_error=ev_err,
 query_outcome_prediction_isolation=True,support_cache_entries=1,population_refitted=False,
 actual_fatigue_rows_read_or_fitted=0,score_elapsed_seconds=duration,
 score_receipt=score_receipt,prediction_receipt=qreceipt)
Path('work/v6_rfl_independent/conjugate_receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2),flush=True)
