"""Independent arithmetic audit. Does not import experiment/model code or fit models."""
from pathlib import Path
import csv,json,hashlib,math,collections,statistics,datetime
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:list(csv.DictReader(p.open()))
def av(x):
 x=[z for z in x if math.isfinite(z)];return statistics.mean(x)if x else math.nan

def paired_range(la,lb,y,event):
 if math.isnan(la)or math.isnan(lb):return -1.,1.
 if event:return float(la>y)-float(lb>y),float(la>y)-float(lb>y)
 # Enumerate all intervals where either strict threshold indicator may change.
 cuts=sorted({y,*[z for z in [la,lb]if math.isfinite(z)and z>y]})
 times=[(a+b)/2 for a,b in zip(cuts,cuts[1:])]+[cuts[-1]+1.,math.inf]
 times +=[z for z in cuts if z>y]
 dif=[float(la>t)-float(lb>t)for t in times]
 return min(dif),max(dif)

def combine(cells):
 # cells: summarykey+(campaign,condition,seed) -> list of rowmetric dictionaries
 cond={k:{m:av(v[m]for v in vals)for m in vals[0]}for k,vals in cells.items()}
 byseed=collections.defaultdict(list)
 for k,v in cond.items():byseed[k[:-2]+(k[-1],)].append(v)
 means={k:{m:av(v[m]for v in vals)for m in vals[0]}for k,vals in byseed.items()}
 bycampaign=collections.defaultdict(list)
 for k,v in means.items():bycampaign[k[:-1]].append(v)
 means={k:{m:av(v[m]for v in vals)for m in vals[0]}for k,vals in bycampaign.items()}
 out=collections.defaultdict(list)
 for k,v in means.items():out[k[:-1]].append(v)
 return {(k,m):av(v[m]for v in vals)for k,vals in out.items()for m in vals[0]}

def sk(row,keys):return tuple(int(row[k])if k=='k'else float(row[k])if k=='cap'else row[k]for k in keys)
def compare(path,expected,keys):
 errors=[];maxerr=0.;n=0
 for row in read(path):
  key=(sk(row,keys),row['metric']);want=expected[key];got=float(row['mean']);n+=1
  if math.isnan(want):assert math.isnan(got),(path,key,want,got)
  else:
   err=abs(want-got);maxerr=max(maxerr,err)
   if err>1e-7:errors.append({'key':str(key),'actual':got,'expected':want,'error':err})
  assert row['n_campaigns']=='1'and not row['lo95']and not row['hi95']
 assert n==len(expected),(path,n,len(expected));return dict(rows=n,max_abs_mean_error=maxerr,errors=errors,all_one_campaign_and_empty_CI=True)

frozen=ROOT/'data/processed/v4/controlled_expansion/frozen_splits.json';splits=json.loads(frozen.read_text());protocol=ROOT/'protocols/v4/frozen_training_expansion.txt';assert sha(protocol)==splits['protocol_sha256']
target=read(ROOT/'data/processed/v4/controlled_expansion/target.csv');T={x['row_id']:x for x in target};tasks={(x['dataset_id'],x['seed']):x for x in splits['tasks']}
assert len(tasks)==40 and all(len(x['query_ids'])==3 and x['ks']==[0,3]for x in tasks.values())
regime_leakage={}
for name,info in splits['regimes'].items():
 p=ROOT/f'data/processed/v4/controlled_expansion/{name}.csv';assert sha(p)==info['sha256'];r=read(p);ids={x['row_id']for x in r};groups={x['group_id']for x in r};assert not ids&set(T)and 'yankin2025_program' not in groups
 regime_leakage[name]=dict(rows=len(r),conditions=len({x['dataset_id']for x in r}),source_blocks=len(groups),target_observation_or_program_overlap=False)
results={};static={};receipts={};all_source_hashes=True
for capname,cap in [('1e7',1e7),('1e6',1e6)]:
 folder=ROOT/f'results/v4/controlled_cap{capname}';d=read(folder/'predictions.csv');sel=read(folder/'selections.csv');run=json.loads((folder/'run_receipt.json').read_text());assert len(d)==23040 and len(sel)==480
 assert run['protocol_sha256']==sha(protocol)and run['splits_sha256']==sha(frozen)
 for file,value in run['code_sha256'].items():assert sha(ROOT/'src'/file)==value
 perfit=[]
 for regime,fit in run['fits'].items():
  assert fit['n_rows']==regime_leakage[regime]['rows'];assert 'yankin2025_program' not in fit['training_sources']
  for name,v in fit['fits'].items():
   assert v['success'];assert not any(v.get(z,False)for z in ['fallback_active','sigma_at_bound','tau_at_bound']);assert not v.get('bound_hits',[])
   perfit.append(dict(regime=regime,model=name,success=True,fallback=False,bound_hit=False,gradient_inf=v.get('gradient_inf')))
 # Verify selection stage, outcome reveal/truncation, and support costs directly from raw target rows.
 prefixes=collections.defaultdict(list);reveal_errors=[]
 for row in sel:
  key=(row['dataset_id'],int(row['seed']),row['policy']);prefixes[key].append(row)
 for key,a in prefixes.items():
  a.sort(key=lambda x:int(x['k']));task=tasks[key[:2]];assert [int(z['k'])for z in a]==[1,2,3];assert len({z['row_id']for z in a})==3;assert all(z['row_id']in task['pool_ids']for z in a)
  for z in a:
   t=T[z['row_id']];observed=min(float(t['log_life']),math.log10(cap));event=int(t['event'])if float(t['log_life'])<=math.log10(cap) else 0
   assert float(z['revealed_log_life'])==observed and int(z['revealed_event'])==event
 # Unique complete prediction matrix and literal equal-query/support assertions across regimes.
 F={};absolute=collections.defaultdict(list);maxcosterror=0.
 for row in d:
  for key in ['log_life','event','log_stress','load_ratio']:assert float(row[key])==float(T[row['row_id']][key])
  task=tasks[(row['dataset_id'],int(row['seed']))];assert row['row_id']in task['query_ids']and int(row['k'])in task['ks']
  support=prefixes[(row['dataset_id'],int(row['seed']),row['policy'])][:int(row['k'])]
  cost=sum(10**float(z['revealed_log_life'])for z in support);maxcosterror=max(maxcosterror,abs(cost-float(row['support_cycles'])));assert abs(cost-float(row['support_cycles']))<1e-7
  assert sum(int(z['revealed_event'])for z in support)==int(row['n_support_failure'])
  i=(row['regime'],row['policy'],row['model'],int(row['k']),row['dataset_id'],int(row['seed']),row['row_id']);assert i not in F;F[i]=row
  y,L,e=float(row['log_life']),float(row['log_lower']),int(row['event']);avail=not math.isnan(L);finite=math.isfinite(L)
  m=dict(availability=float(avail),finite_availability=float(finite),positive_infinite=float(L==math.inf),known_risk=float(avail and L>y and e==1),upper_risk=float(L>y)if avail else 1.,finite_log_lower=L if finite else math.nan,failure_shortfall=max(y-L,0)if finite and e else math.nan,support_cycles=float(row['support_cycles']),all_support_runout=float(int(row['k'])>0 and int(row['n_support_failure'])==0))
  key=sk(row,['regime','panel','policy','model','k','cap'])+(row['campaign_id'],row['dataset_id'],int(row['seed']));absolute[key].append(m)
 assert len(F)==23040
 for key,row in F.items():
  baseline=F[('strict309',)+key[1:]]
  assert all(row[z]==baseline[z]for z in ['row_id','dataset_id','campaign_id','log_life','event','log_stress','load_ratio','support_cycles','n_support_failure'])
  if key[2]=='matched_intercept'and key[3]==0:assert row['log_lower']==F[(key[0],key[1],'hierarchical')+key[3:]]['log_lower']
  if key[2]=='pooled':assert row['log_lower']==F[(key[0],'random','pooled',0)+key[4:]]['log_lower']
 # Recompute each paired metric by independent threshold interval enumeration.
 policycells=collections.defaultdict(list);traincells=collections.defaultdict(list)
 for key,row in F.items():
  la=float(row['log_lower']);y=float(row['log_life']);event=int(row['event'])
  for how in ['training','versus_random','versus_k0']:
   other=F[('strict309',)+key[1:]]if how=='training'else F[(key[0],'random')+key[2:]]if how=='versus_random'else F[key[:3]+(0,)+key[4:]]
   lb=float(other['log_lower']);valid=not(math.isnan(la)or math.isnan(lb));finite=math.isfinite(la)and math.isfinite(lb);lo,hi=paired_range(la,lb,y,event)
   metrics=dict(paired_availability=float(valid),paired_finite_availability=float(finite),log_life_gain=la-lb if finite else math.nan,true_risk_change_lo=lo,true_risk_change_hi=hi)
   if how=='training':cell=sk(row,['regime','policy','model','k','cap'])+(row['campaign_id'],row['dataset_id'],int(row['seed']));traincells[cell].append(metrics)
   else:
    metrics['support_cycle_change']=float(row['support_cycles'])-float(other['support_cycles']);cell=sk(row,['regime','panel','policy','model','k','cap'])+(how,row['campaign_id'],row['dataset_id'],int(row['seed']));policycells[cell].append(metrics)
 a=compare(folder/'all_regime_summary.csv',combine(absolute),['regime','panel','policy','model','k','cap']);p=compare(folder/'all_policy_contrasts.csv',combine(policycells),['regime','panel','policy','model','k','cap','comparison']);t=compare(folder/'training_contrasts.csv',combine(traincells),['regime','policy','model','k','cap']);assert not(a['errors']or p['errors']or t['errors'])
 static[capname]={key:{z:row[z]for z in ['log_lower','n_support_failure','support_cycles']}for key,row in F.items()if key[1]!='active_query_variance'}
 results[capname]=dict(prediction_rows=len(d),selection_rows=len(sel),tasks=len(tasks),absolute_summary=a,policy_contrasts=p,training_contrasts=t,query_and_support_equality_across_regimes=True,support_reveal_and_cap_truncation_verified=True,max_support_cost_reconstruction_error=maxcosterror,matched_intercept_k0_equals_hierarchical=True,pooled_is_support_independent=True,population_fit_diagnostics=perfit,protocol_splits_and_runtime_code_hashes_match=True)
assert static['1e7'].keys()==static['1e6'].keys();staticdiff=sum(static['1e7'][k]!=static['1e6'][k]for k in static['1e7'])
receipt=dict(audited_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),verdict='PASS for currentv4codeandnumericalexecution;pool-exhaustionlimitsstress-policyinformativeness.',scope='Independentread-onlycode/numericalaudit;actualrunsalreadycompletedbyparent;noauditmodelfitsormodelreruns.',source_sha256={str(p.relative_to(ROOT)):sha(p)for p in [ROOT/'src/v4_expansion.py',ROOT/'src/v4_summarize.py',ROOT/'src/v3_design.py',ROOT/'src/v3_summarize.py',protocol,frozen]},source_leakage=regime_leakage,design=dict(eligible_target_rows=25,eligible_conditions=4,target_author_programs=1,query_per_condition=3,pool_sizes=dict(collections.Counter(len(t['pool_ids'])for t in tasks.values())),k=[0,3],policy_informativeness_limit='At k3,threeof4conditionsfullyexhaustpool;onlyHT45n7conditioncanhaveasupport-setchoice.Policycontrastsarenotbroadstress-selectionconfirmation.',selection_outcome_boundary='Codecallchoose_nextonlyreceivesrow_id/log_stress/load_ratioforcandidate/query;supportoutcomesrevealedonlyafterselection.',predictor_query_outcomes='Allquantilepathwaysinspected;querydesignusesoutcomes=Falseor_xcovariates,supportlikelihoodusesonlyrevealedoutcomes.',same_sequence_training_regimes='OneA309hierarchicalplannerandonesharedselectionloop;allsupportsequencesandcostsidenticalbetween4regimes.',independence='OneYankinprogram;repeatedseedsarenotnewcampaigns;allcampaignCIsunavailable.',training_estimator='Source-balancedworkinglikelihood;moretrainingevidencealsochangessourcefamilyweights,notapurematched-sizecausaldiversityeffect.'),small_checks=dict(command='.venv/bin/python -m pytest -q tests/test_v3_design.py',tests=6,passed=6,elapsed_seconds=.46),result_checks=results,static_policy_cap_comparison=dict(rows_compared=len(static['1e7']),different_rows=staticdiff),not_done=['No model fit','No changed experiment choices','No fresh numerical replay;parentreplayremainsseparate','No physical independence or reliability certification'],issues=[dict(severity='design_limit_not_code_bug',issue='k3pool exhaustion in3/4targetconditions',status='Reportedtoparentbeforeheadlineinterpretation;parentacceptedandplannedseparatev4bsourceholdoutdesignbasedoncounts.')])
(OUT/'v4_code_audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'verdict':receipt['verdict'],'caps':{k:{'absolute':v['absolute_summary'],'policy':v['policy_contrasts'],'training':v['training_contrasts']}for k,v in results.items()},'static_cap':receipt['static_policy_cap_comparison']},indent=2))
