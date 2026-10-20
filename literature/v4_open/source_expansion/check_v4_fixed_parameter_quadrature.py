"""96/192-node RFL diagnostic on cached fits. Never calls fit or changes frozen code."""
from pathlib import Path
import json,pickle,copy,hashlib,datetime
import numpy as np
import pandas as pd
from src.v3_rfl import NormalNormalRFL
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
main=json.loads((ROOT/'results/v4/controlled_cap1e7/run_receipt.json').read_text())
models={};cachehash={}
for name,r in main['fits'].items():
 p=ROOT/'work/v4/model_cache'/f'{r["signature"]}.pkl';cachehash[str(p.relative_to(ROOT))]=sha(p)
 with p.open('rb') as f:low=pickle.load(f)['rfl']
 low=copy.deepcopy(low);low._posterior_cache.clear();assert low.nodes==96 and low._fallback is None
 high=copy.deepcopy(low);rule=NormalNormalRFL(nodes=192,shift_prior_sd=low.shift_prior_sd)
 high.nodes=192;high._t=rule._t;high._w=rule._w;high._logw=rule._logw;high._posterior_cache.clear()
 assert np.array_equal(low.params_,high.params_) and low.shift_prior_sd==high.shift_prior_sd
 models[name]=(low,high)
Y=pd.read_csv(ROOT/'data/external_v4/yankin2025/table3_69.csv').set_index('row_id',drop=False)
E=pd.read_csv(ROOT/'data/external_v4/source_expansion/source_qualified_ca_expansion.csv').set_index('row_id',drop=False)
rows=[];maxcdf=0.;maxtail=0.;failures=[]
def evaluate(label,name,query,support=None,**info):
 global maxcdf,maxtail
 low,high=models[name]
 try:
  values=[m.predict_quantiles(query,support=support,alphas=(.1,))[:,0] for m in [low,high]]
  a,b=values;finite=np.isfinite(a)&np.isfinite(b);delta=np.abs(a[finite]-b[finite])
  assert not np.any(np.isnan(a)) and not np.any(np.isnan(b))
  tails=[];residuals=[]
  for model,q in zip([low,high],values):
   ff=np.isfinite(q)
   if np.any(ff):residuals.append(float(np.max(np.abs(model.predict_cdf(q[ff],query.loc[ff],support=support)-.1))))
   if support is not None and len(support):tails.append(model.support_posterior(support).get('tail_mass_bound',0.))
  cdf=max(residuals,default=0.);tail=max(tails,default=0.);maxcdf=max(maxcdf,cdf);maxtail=max(maxtail,tail)
  rows.append(dict(label=label,regime=name,n_quantiles=len(query),n_support=0 if support is None else len(support),n_support_censors=0 if support is None else int((support.event==0).sum()),infinite_status_identical=bool(np.array_equal(np.isposinf(a),np.isposinf(b))),n_infinite_96=int(np.isposinf(a).sum()),n_infinite_192=int(np.isposinf(b).sum()),max_abs_log10_q10_difference=float(delta.max()) if len(delta) else None,max_CDF_residual=cdf,max_posterior_tail_mass_bound=tail,**info))
 except Exception as exc:failures.append(dict(label=label,regime=name,error=repr(exc),**info))
for name in models:
 evaluate('all69_Yankin_zero_support',name,Y[['row_id','log_stress','load_ratio']])
 evaluate('all132_expansion_zero_support',name,E[['row_id','log_stress','load_ratio']])
# Choose representative source conditions by maximal censor fraction, then lexical ID.
# This is an integration diagnostic, not a performance/model selection rule.
source_datasets={}
for family,frame in E.groupby('group_id'):
 eligible=[(float((a.event==0).mean()),did) for did,a in frame.groupby('dataset_id') if len(a)>=8]
 source_datasets[family]=sorted(eligible,key=lambda z:(-z[0],z[1]))[0][1]
yankin_candidates=[(float((a.event==0).mean()),did) for did,a in Y.groupby('dataset_id') if len(a)>=6]
ydid=sorted(yankin_candidates,key=lambda z:(-z[0],z[1]))[0][1]
for capname in ['1e7','1e6']:
 for which,base,datasets in [('controlled',Y,{ydid}),('source_holdout',E,set(source_datasets.values()))]:
  path=ROOT/f'results/v4/{which}_cap{capname}';selections=pd.read_csv(path/'selections.csv');pred=pd.read_csv(path/'predictions.csv');pred=pred[(pred.model=='rfl')&(pred.k>0)]
  subset=pred[(pred.dataset_id.isin(datasets))&(pred.seed==0)]
  # Also include the first actual all-censored support case, if present.
  extra=pred[pred.n_support_failure==0].sort_values(['dataset_id','seed','policy','k','regime']).head(1)
  if len(extra):subset=pd.concat([subset,pred[(pred.dataset_id==extra.dataset_id.iloc[0])&(pred.seed==extra.seed.iloc[0])&(pred.policy==extra.policy.iloc[0])&(pred.k==extra.k.iloc[0])]],ignore_index=True).drop_duplicates(['regime','dataset_id','seed','policy','k','row_id'])
  for (regime,did,seed,policy,k),frame in subset.groupby(['regime','dataset_id','seed','policy','k'],sort=True):
   s=selections[(selections.dataset_id==did)&(selections.seed==seed)&(selections.policy==policy)&(selections.k<=k)].sort_values('k');support=base.loc[s.row_id].copy();support['log_life']=s.revealed_log_life.to_numpy();support['event']=s.revealed_event.to_numpy();query=base.loc[frame.row_id,['row_id','log_stress','load_ratio']]
   name=regime if regime!='expanded_family_excluded' else ('strict_plus_elanges347' if base.loc[frame.row_id.iloc[0],'group_id']=='v4_zhang_linked_original_experiments' else 'strict_plus_zhang403')
   evaluate(which+'_representative_support',name,query,support,dataset_id=did,seed=int(seed),policy=policy,k=int(k),cap=float(s.cap.iloc[0]))
maxdiff=max((z['max_abs_log10_q10_difference'] or 0 for z in rows),default=None)
unchanged={p:sha(ROOT/p)==h for p,h in cachehash.items()};assert all(unchanged.values())
r=dict(audited_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Fixed fitted population parameters, 96 versus192 Gamma integration nodes. No fits or parameter updates. Scalar-support posterior recomputed separately at each node count; caches cleared.',regimes=list(models),n_fitted_regimes=4,orders=[96,192],all_population_parameters_identical=True,cached_pickle_files_unchanged=unchanged,n_quantiles=sum(x['n_quantiles'] for x in rows),n_evaluation_cases=len(rows),n_support_cases=sum(x['n_support']>0 for x in rows),n_support_cases_with_censors=sum(x['n_support_censors']>0 for x in rows),representative_source_datasets=source_datasets,representative_yankin_dataset=ydid,infinite_status_identical=all(x['infinite_status_identical'] for x in rows),max_abs_log10_q10_difference=maxdiff,max_CDF_residual=maxcdf,max_posterior_tail_mass_bound=maxtail,numerical_exceptions=failures,verdict='PASS' if not failures and all(x['infinite_status_identical'] for x in rows) and maxdiff<1e-6 else 'REVIEW',interpretation='Numerical integration accuracy at fixed fitted parameters, not population parameter uncertainty, statistical reliability, or physical validation.',rows=rows)
(OUT/'v4_fixed_parameter_quadrature.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2))
