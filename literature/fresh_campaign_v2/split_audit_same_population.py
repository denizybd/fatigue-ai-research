"""Independent non-creator audit of the explicit post-result matched control.
No imports of src models, summary or evaluation modules. No population fitting.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,csv,math,hashlib
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
R=Path(__file__).resolve().parents[2];O=R/'literature/fresh_campaign_v2'
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def num(s):return float(s) if s else math.nan
def avg(v):
 v=[x for x in v if not math.isnan(x)];return sum(v)/len(v) if v else math.nan
def eq(a,b,tol=2e-11):return (math.isnan(a) and math.isnan(b)) or a==b or abs(a-b)<tol
configs=[('same_population_internal','fulltraining','strict_fulltraining'),('same_population_external','external_fulltraining','external_fulltraining')]
receipts=[];selected=[]
for current,original,dataset in configs:
 folder=R/'results/v2'/current;old=R/'results/v2'/original;data=R/'data/processed/v2'/dataset
 pred=read(folder/'predictions.csv');oldpred=read(old/'predictions.csv');cohort={r['row_id']:r for r in read(data/'cohort.csv')};sign=json.load(open(folder/'signature.json'));recon=json.load(open(folder/'reconstruction_receipt.json'));fits=json.load(open(old/'run_receipt.json'))['fits'];oldsign=json.load(open(old/'signature.json'))
 assert sign['population_refitted'] is False and sign['population_parameter_uncertainty_included'] is False
 assert 'POST-RESULT' in sign['timing'];assert sha(old/'predictions.csv')==sign['original_predictions_sha256'];assert sha(old/'run_receipt.json')==sign['original_population_receipt_sha256'];assert sha(data/'cohort.csv')==sign['cohort_sha256'];assert sha(data/'frozen_splits.json')==sign['splits_sha256']
 assert sha(R/'src/v2_same_population_control.py')==sign['code_sha256'];assert sha(R/'src/v2_models.py')==sign['model_sha256'];assert sha(R/'protocols/v2/postresult_matched_population_control.md')==sign['protocol_sha256']
 def key(r):return (r['panel'],int(r['seed']),r['group_id'],r['dataset_id'],r['row_id'],int(r['k']))
 index={(key(r),r['model']):r for r in pred};assert len(index)==len(pred)
 originalhier={key(r):r for r in oldpred if r['model']=='hierarchical' and r['bound']=='raw'}
 newhier={key(r):r for r in pred if r['model']=='hierarchical_reference'};control={key(r):r for r in pred if r['model']=='same_population_unpooled'}
 assert newhier.keys()==originalhier.keys()==control.keys();maxhier=0.;maxcontrol=0.;maxcenter=0.;numericcontrols=0;populationchecks=0;episodechecks=0;unavailable=0;unavailreasons=Counter()
 recindex={(r['panel'],int(r['seed']),r['outer']):r for r in recon}
 for key_,row in newhier.items():
  delta=abs(num(row['log_lower'])-num(originalhier[key_]['log_lower']));maxhier=max(maxhier,delta);assert delta<1e-9
  assert row['log_life']==originalhier[key_]['log_life'] or abs(num(row['log_life'])-num(originalhier[key_]['log_life']))<1e-12
  assert row['event']==originalhier[key_]['event']
  assert row['bound']=='raw' and row['diagnostic_timing']=='post-result exploratory'
 for receipt in fits:
  task=receipt['task'];rr=receipt['hierarchical'];p=np.array(rr['params_']);sigma=float(rr['sigma_']);tau=float(rr['tau_']);fit=rr['fit_receipt_'];assert fit['success']
  assert abs(math.exp(p[3])-sigma)<1e-12 and abs(math.exp(p[4])-tau)<1e-12
  train=[r for r in cohort.values() if r['group_id'] in task['fit_blocks']];finiteR=[num(r['load_ratio']) for r in train if math.isfinite(num(r['load_ratio']))];fill=float(np.median(finiteR)) if finiteR else 0.;assert fill==fit['ratio_median_train']
  xstress=np.array([num(r['log_stress']) for r in train]);ratio=np.array([num(r['load_ratio']) if math.isfinite(num(r['load_ratio'])) else fill for r in train]);center=np.array([xstress.mean(),ratio.mean()]);saved=recindex[(task['panel'],int(task['seed']),task['outer'])]
  assert np.array_equal(p,np.array(saved['saved_population_params']));maxcenter=max(maxcenter,float(np.max(np.abs(center-saved['training_center_reconstructed']))));assert maxcenter<1e-12;populationchecks+=1
  def location(row):
   ratio=num(row['load_ratio']);ratio=ratio if math.isfinite(ratio) else fill
   return p[0]+p[1]*(num(row['log_stress'])-center[0])+p[2]*(ratio-center[1])
  for target in task['targets']:
   ids=target['query_ids'];supportpool=target['support_pool'];assert set(ids).isdisjoint(supportpool)
   for k in task['ks']:
    sup=[cohort[r] for r in supportpool[:k]];sumevent=sum(int(r['event']) for r in sup);episodechecks+=1
    querykeys=[(task['panel'],int(task['seed']),task['outer'],target['curve'],rid,k) for rid in ids]
    assert set(querykeys)<=newhier.keys() and set(querykeys)<=control.keys()
    if k==0:
     for key_ in querykeys:assert num(control[key_]['log_lower'])==num(newhier[key_]['log_lower'])
     continue
    if sumevent==0:
     unavailable+=1;unavailreasons[(task['panel'],k)]+=1
     for key_ in querykeys:assert math.isnan(num(control[key_]['log_lower']))
     continue
    mu=np.array([location(r) for r in sup]);y=np.array([num(r['log_life']) for r in sup]);event=np.array([int(r['event']) for r in sup]);res=y-mu
    if event.sum()==k:shift=res.mean();variance=sigma*sigma/k
    else:
     def derivatives(shift):
      z=(res-shift)/sigma;h=np.exp(norm.logpdf(z)-norm.logsf(z));score=np.sum(np.where(event==1,z,h))/sigma;information=np.sum(np.where(event==1,1.,h*(h-z)))/(sigma*sigma);return score,information
     lo=float(min(res)-20*sigma-1);hi=float(max(res)+20*sigma+1)
     while derivatives(lo)[0]<=0:lo=2*lo-1
     while derivatives(hi)[0]>=0:hi=2*hi+1
     shift=brentq(lambda u:derivatives(u)[0],lo,hi,xtol=1e-12);variance=1/derivatives(shift)[1]
    for key_ in querykeys:
     row=control[key_];assert int(row['n_support_failures'])==sumevent and int(row['n_support_runouts'])==k-sumevent
     expected=location(cohort[key_[4]])+shift+norm.ppf(.1)*math.sqrt(sigma*sigma+variance);got=num(row['log_lower']);error=abs(expected-got);maxcontrol=max(maxcontrol,error);assert error<1e-9,(current,key_,expected,got,error);numericcontrols+=1
 # Matched SAME-k means/identified risk changes on common finite query pairs.
 episodes=defaultdict(list)
 for key_,a in newhier.items():
  b=control[key_];panel,seed,group,curve,rid,k=key_;ha=num(a['log_lower']);hb=num(b['log_lower']);y=num(a['log_life']);e=int(a['event']);valid=math.isfinite(ha) and math.isfinite(hb);d=float(ha>y)-float(hb>y)
  values={'availability_pair':float(valid),'log_life_gain_hier_minus_control':ha-hb if valid else math.nan,'hier_risk_lower':float(ha>y and e==1) if valid else math.nan,'hier_risk_upper':float(ha>y) if valid else math.nan,'control_risk_lower':float(hb>y and e==1) if valid else math.nan,'control_risk_upper':float(hb>y) if valid else math.nan,'true_risk_change_lo':(d if e else -float(hb>ha and hb>y)) if valid else math.nan,'true_risk_change_hi':(d if e else float(ha>hb and ha>y)) if valid else math.nan}
  episodes[(panel,k,group,seed,curve)].append(values)
 fields=list(next(iter(episodes.values()))[0]);curvem={k:{f:avg([r[f] for r in rs]) for f in fields} for k,rs in episodes.items()}
 def aggregate(src,drop):
  g=defaultdict(list)
  for k,v in src.items():g[k[:-drop]].append(v)
  return {k:{f:avg([x[f] for x in vs]) for f in fields} for k,vs in g.items()}
 sm=aggregate(curvem,1);sa=aggregate(sm,1);metricchecks=0
 for r in read(folder/'matched_population_comparison.csv'):
  panel=r['panel'];k=int(r['k']);metric=r['metric'];values=np.array([v[metric] for key_,v in sorted(sa.items()) if key_[:2]==(panel,k)]);expected=float(np.mean(values));assert eq(expected,num(r['mean'])),(current,panel,k,metric,expected,r)
  if len(values)>1 and np.isfinite(values).all():
   rng=np.random.default_rng(231);boot=values[rng.integers(0,len(values),size=(2000,len(values)))].mean(1);lo,hi=np.quantile(boot,[.025,.975])
  else:lo,hi=math.nan,math.nan
  assert eq(lo,num(r['lo95'])) and eq(hi,num(r['hi95']));assert int(r['n_sources'])==len(values);metricchecks+=3
  if k==3 and panel in ['A','external_random','external_chronological']:selected.append({'run':current,**r})
 receipts.append({'run':current,'original_run':original,'population_receipts_checked':populationchecks,'target_episodes_all_k_checked':episodechecks,'reference_prediction_rows':len(newhier),'control_finite_k_positive_rows_independently_recomputed':numericcontrols,'all_runout_unavailable_episodes':unavailable,'all_runout_unavailable_by_panel_k':{str(k):v for k,v in unavailreasons.items()},'hierarchy_reference_max_difference':maxhier,'control_scalar_MLE_quantile_max_difference':maxcontrol,'training_center_max_difference':maxcenter,'matched_metric_cells_checked':metricchecks,'status':'PASS'})
result={'status':'PASS','scope':'Non-creator arithmetic, reference identity, populationparameter/transformation and exact same-k common-query-mask audit. No root model or metric implementation imported, no population refit.','receipts':receipts,'selected_k3':selected,'interpretation':['Explicit post-result exploratory ablation, cannot rescue frozen primary failure.','At k0 both names are the same hierarchical new-condition reference, not a zero-observation unpooled estimator.','At k>0 only target-intercept prior borrowing changes: same fitted hierarchical slope/R/sigma; censored flat-prior predictive variance is an observed-curvature approximation.','Unavailable all-runout support episodes are retained as missing, not silently fitted or converted to failures. Paired risk/utility is conditional on common finite predictions; availability is reported separately.','External three diameter conditions are one campaign; source-bootstrap CI is intentionally unavailable.']}
(O/'split_audit_same_population.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'receipts':receipts},indent=2))
