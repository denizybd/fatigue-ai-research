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
def family_values(cells):
    conditions={k:{m:av(v[m] for v in vals) for m in vals[0]} for k,vals in cells.items()}
    groups=collections.defaultdict(list)
    for k,v in conditions.items(): groups[k[:-2]+(k[-1],)].append(v)
    byseed={k:{m:av(v[m] for v in vals) for m in vals[0]} for k,vals in groups.items()}
    groups=collections.defaultdict(list)
    for k,v in byseed.items(): groups[k[:-1]].append(v)
    byfamily={k:{m:av(v[m] for v in vals) for m in vals[0]} for k,vals in groups.items()}
    groups=collections.defaultdict(list)
    for k,v in byfamily.items(): groups[k[:-1]].append(v)
    out={}
    for key,vals in groups.items():
        for metric in vals[0]:
            values=[v[metric] for v in vals if math.isfinite(v[metric])]
            # For two families, 2,000 bootstrap draws have >2.5% mass on both extrema.
            out[(key,metric)]={'mean':av(values),'lo95':min(values) if len(values)==2 else math.nan,'hi95':max(values) if len(values)==2 else math.nan,'n_campaigns':len(vals),'n_finite_campaigns':len(values)}
    return out

def compare(path,expected,keys):
    errors=[];maxerr=0.;maxci=0.;n=0
    for row in read(path):
        key=(sk(row,keys),row['metric']);want=expected[key];n+=1
        for metric in ['mean','lo95','hi95']:
            got=float(row[metric]) if row[metric] else math.nan
            if math.isnan(want[metric]): assert math.isnan(got),(path,key,metric,want,got)
            else:
                err=abs(want[metric]-got)
                if metric=='mean':maxerr=max(maxerr,err)
                else:maxci=max(maxci,err)
                if err>1e-7:errors.append({'key':str(key),'metric':metric,'actual':got,'expected':want[metric],'error':err})
        assert int(row['n_campaigns'])==want['n_campaigns']==2
        assert int(row['n_finite_campaigns'])==want['n_finite_campaigns']
    assert n==len(expected),(path,n,len(expected))
    return dict(rows=n,max_abs_mean_error=maxerr,max_abs_CI_endpoint_error=maxci,errors=errors,source_families=2,CI_interpretation='Descriptive two-family bootstrap; not certified independent physical campaigns.')

frozen=ROOT/'data/processed/v4/source_holdout/frozen_splits.json';s=json.loads(frozen.read_text());mainpath=ROOT/'data/processed/v4/controlled_expansion/frozen_splits.json';main=json.loads(mainpath.read_text());protocol=ROOT/'protocols/v4/source_holdout_policy_extension.txt';targetpath=ROOT/'data/processed/v4/source_holdout/target.csv';increment=ROOT/'data/external_v4/source_expansion/source_qualified_ca_expansion.csv'
assert s['protocol_sha256']==sha(protocol) and s['main_split_sha256']==sha(mainpath) and s['target_sha256']==sha(targetpath) and s['source_sha256']==sha(increment)
target=read(targetpath);T={x['row_id']:x for x in target};tasks={(x['dataset_id'],x['seed']):x for x in s['tasks']};families={x['group_id'] for x in target};assert len(T)==132 and len(tasks)==110 and len(families)==2
expectedmap={'v4_zhang_linked_original_experiments':'strict_plus_elanges347','v4_elangeswaran_linked_experiments':'strict_plus_zhang403'}
trains={}
for name in ['strict309','strict_plus_elanges347','strict_plus_zhang403']:
 p=ROOT/f'data/processed/v4/controlled_expansion/{name}.csv';assert sha(p)==main['regimes'][name]['sha256'];trains[name]=read(p)
checks=[]
for task in tasks.values():
 assert task['expanded_training']==expectedmap[task['campaign_id']]
 familyids={x['row_id'] for x in target if x['group_id']==task['campaign_id']}
 for name in ['strict309',task['expanded_training']]:
  assert not familyids & {x['row_id'] for x in trains[name]};assert task['campaign_id'] not in {x['group_id'] for x in trains[name]}
 checks.append(dict(condition=task['dataset_id'],seed=task['seed'],target_family=task['campaign_id'],B_training=task['expanded_training'],whole_family_absent_from_both_training_regimes=True))
results={};static={};staticseq={};familydetails={}
for capname,cap in [('1e7',1e7),('1e6',1e6)]:
 folder=ROOT/f'results/v4/source_holdout_cap{capname}';d=read(folder/'predictions.csv');selections=read(folder/'selections.csv');run=json.loads((folder/'run_receipt.json').read_text());assert len(d)==59040 and len(selections)==2120 and run['n_tasks']==110
 assert run['protocol_sha256']==sha(protocol) and run['splits_sha256']==sha(frozen) and run['code_sha256']==sha(ROOT/'src/v4_policy_extension.py')
 mr=json.loads((ROOT/f'results/v4/controlled_cap{capname}/run_receipt.json').read_text())
 fitcheck=[]
 for name,v in run['fits'].items():
  assert v['signature']==mr['fits'][name]['signature'];assert v['n_rows']==len(trains[name])
  for m,a in v['fits'].items():
   assert a['success'] and not any(a.get(z,False) for z in ['fallback_active','sigma_at_bound','tau_at_bound']) and not a.get('bound_hits',[])
  fitcheck.append(dict(training_name=name,rows=v['n_rows'],identical_fit_to_predeclared_main_regime=True,all_four_population_models_converged_without_fallback_or_bound_hits=True))
 prefixes=collections.defaultdict(list)
 for row in selections:prefixes[(row['dataset_id'],int(row['seed']),row['policy'])].append(row)
 for key,a in prefixes.items():
  a.sort(key=lambda z:int(z['k']));task=tasks[key[:2]];assert [int(z['k']) for z in a]==list(range(1,max(task['ks'])+1));assert len({z['row_id'] for z in a})==len(a);assert all(z['row_id'] in task['pool_ids'] for z in a)
  for z in a:
   t=T[z['row_id']];y=min(float(t['log_life']),math.log10(cap));event=int(t['event']) if float(t['log_life'])<=math.log10(cap) else 0
   assert float(z['revealed_log_life'])==y and int(z['revealed_event'])==event
 F={};absolute=collections.defaultdict(list);maxcost=0.
 for row in d:
  key=(row['regime'],row['policy'],row['model'],int(row['k']),row['dataset_id'],int(row['seed']),row['row_id']);assert key not in F;F[key]=row
  task=tasks[(row['dataset_id'],int(row['seed']))];assert row['row_id'] in task['query_ids'] and int(row['k']) in task['ks']
  trainname='strict309' if row['regime']=='strict309' else task['expanded_training'];assert row['fit_signature']==run['fits'][trainname]['signature']
  for c in ['log_life','event','log_stress','load_ratio']:assert float(row[c])==float(T[row['row_id']][c])
  a=prefixes[(row['dataset_id'],int(row['seed']),row['policy'])][:int(row['k'])];cost=sum(10**float(x['revealed_log_life']) for x in a);maxcost=max(maxcost,abs(cost-float(row['support_cycles'])));assert abs(cost-float(row['support_cycles']))<1e-7;assert sum(int(x['revealed_event']) for x in a)==int(row['n_support_failure'])
  y,L,e=float(row['log_life']),float(row['log_lower']),int(row['event']);available=not math.isnan(L);finite=math.isfinite(L)
  metrics=dict(availability=float(available),finite_availability=float(finite),positive_infinite=float(L==math.inf),known_risk=float(available and e==1 and L>y),upper_risk=float(L>y) if available else 1.,finite_log_lower=L if finite else math.nan,failure_shortfall=max(y-L,0.) if e and finite else math.nan,support_cycles=float(row['support_cycles']),all_support_runout=float(int(row['k'])>0 and int(row['n_support_failure'])==0))
  cell=sk(row,['regime','panel','policy','model','k','cap'])+(row['campaign_id'],row['dataset_id'],int(row['seed']));absolute[cell].append(metrics)
 for key,row in F.items():
  baseline=F[('strict309',)+key[1:]];assert all(row[c]==baseline[c] for c in ['row_id','dataset_id','campaign_id','log_life','event','log_stress','load_ratio','support_cycles','n_support_failure'])
  if key[2]=='matched_intercept' and key[3]==0:assert row['log_lower']==F[(key[0],key[1],'hierarchical')+key[3:]]['log_lower']
  if key[2]=='pooled':assert row['log_lower']==F[(key[0],'random','pooled',0)+key[4:]]['log_lower']
 policycells=collections.defaultdict(list);traincells=collections.defaultdict(list)
 for key,row in F.items():
  la,y,event=float(row['log_lower']),float(row['log_life']),int(row['event'])
  for how in ['training','versus_random','versus_k0']:
   other=F[('strict309',)+key[1:]] if how=='training' else F[(key[0],'random')+key[2:]] if how=='versus_random' else F[key[:3]+(0,)+key[4:]]
   lb=float(other['log_lower']);valid=not(math.isnan(la) or math.isnan(lb));finite=math.isfinite(la) and math.isfinite(lb);lo,hi=paired_range(la,lb,y,event)
   metrics=dict(paired_availability=float(valid),paired_finite_availability=float(finite),log_life_gain=la-lb if finite else math.nan,true_risk_change_lo=lo,true_risk_change_hi=hi)
   if how=='training':cell=sk(row,['regime','policy','model','k','cap'])+(row['campaign_id'],row['dataset_id'],int(row['seed']));traincells[cell].append(metrics)
   else:
    metrics['support_cycle_change']=float(row['support_cycles'])-float(other['support_cycles']);cell=sk(row,['regime','panel','policy','model','k','cap'])+(how,row['campaign_id'],row['dataset_id'],int(row['seed']));policycells[cell].append(metrics)
 a=compare(folder/'all_regime_summary.csv',family_values(absolute),['regime','panel','policy','model','k','cap']);p=compare(folder/'all_policy_contrasts.csv',family_values(policycells),['regime','panel','policy','model','k','cap','comparison']);t=compare(folder/'training_contrasts.csv',family_values(traincells),['regime','policy','model','k','cap']);assert not(a['errors'] or p['errors'] or t['errors'])
 static[capname]={key:{c:row[c] for c in ['log_lower','support_cycles','n_support_failure']} for key,row in F.items() if key[1]!='active_query_variance'}
 staticseq[capname]={key:[z['row_id'] for z in a] for key,a in prefixes.items() if key[2]!='active_query_variance'}
 results[capname]=dict(tasks=110,prediction_rows=len(d),selection_rows=len(selections),absolute_summary=a,policy_contrasts=p,training_contrasts=t,all_queries_and_supports_identical_between_training_regimes=True,whole_family_exclusion_verified_for_every_task=True,support_events_stops_costs_reconstructed=True,max_support_cost_error=maxcost,query_censoring_unchanged_across_caps=True,population_fit_checks=fitcheck)
assert staticseq['1e7']==staticseq['1e6'];dif=sum(static['1e7'][k]!=static['1e6'][k] for k in static['1e7'])
receipt=dict(audited_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),verdict='PASS. Whole-family exclusion, shared supports, fit reuse and numerical summaries verified.',scope='Independent post-run read-only code/numerical audit. No model fitting or experiment changes.',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'src/v4_policy_extension.py',ROOT/'src/v4_summarize.py',protocol,frozen,targetpath,increment,mainpath]},source_counts=dict(collected_rows=132,eligible_rows=115,eligible_conditions=11,small_condition_rows_outside_replay=17,conservative_source_family_blocks=2),exclusion_checks=checks,results=results,static_cap_check=dict(selection_sequences_identical=True,prediction_rows_compared=len(static['1e7']),rows_with_changed_cost_or_prediction=dif,interpretation='Elanges author runouts are2e6; C1e6 truncates support censor stops. Static IDs agree but static predictions/costs can change. Query censors remain2e6.'),scientific_limits=['Exploratory extension added after main fits but before parent read main performance summaries, based on pool-size evidence.','Two source families are not two certified independent physical campaigns.','Bootstrap endpoints are descriptive; cannot establish safe-design generality.','Finite-pair utility excludes unavailable/infinite pairs; availability must accompany ratios.','No fresh numerical model replay performed by auditor.'])
(OUT/'v4b_code_audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'verdict':receipt['verdict'],'results':{k:{z:v[z] for z in ['tasks','prediction_rows','selection_rows','absolute_summary','policy_contrasts','training_contrasts']} for k,v in results.items()},'static_cap':receipt['static_cap_check']},indent=2))
