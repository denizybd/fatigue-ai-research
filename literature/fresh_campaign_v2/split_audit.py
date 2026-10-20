"""Independent audit of phase2 frozen cohorts/splits; no src imports or mutation."""
from pathlib import Path
import json,csv,hashlib,math
from collections import defaultdict,Counter
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'literature/fresh_campaign_v2'
CONFIGS=['strict','strict_fulltraining','strict_nearcluster','external','external_fulltraining']
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashed_order(items,parts):
 # Independent direct construction of specified UTF8 salt|ID ordering.
 return sorted(items,key=lambda rid:hashlib.sha256(('|'.join(str(x) for x in parts)+'|'+str(rid)).encode('utf8')).hexdigest())
def check(cond,label,detail=''):
 if not cond:raise AssertionError(label+': '+str(detail))
checks=[];frames={};manifests={};summaries=[];warnings=[]
raw=ROOT/'data/processed/primary.csv';original={r['row_id']:r for r in read(raw)}
gate={r['source_id']:r for r in read(ROOT/'literature/provenance_v2/final_source_gate.csv')}
eligible={d for d,r in gate.items() if r['source_gate_status'].startswith('eligible')}
corrections=read(ROOT/'literature/provenance_v2/frozen_point_corrections.csv')
for name in CONFIGS:
 folder=ROOT/'data/processed/v2'/name;rows=read(folder/'cohort.csv');byid={r['row_id']:r for r in rows};j=json.loads((folder/'frozen_splits.json').read_text());frames[name]=byid;manifests[name]=j
 check(len(rows)==len(byid),name+' unique row IDs');check(sha(folder/'cohort.csv')==j['cohort_sha256'],name+' cohort SHA256')
 for path,digest in j.get('protocol_hashes',{}).items():check(sha(ROOT/path)==digest,name+' protocolSHA',path)
 for path,digest in j.get('gate_hashes',{}).items():check(sha(ROOT/path)==digest,name+' gateSHA',path)
 ext=name.startswith('external');histrows=[r for r in rows if not r['row_id'].startswith('mc2564')]
 check(set(r['doi'] for r in histrows)<=eligible,name+' whitelistonly')
 check(all(r['doi'] not in ['10.1016/j.ijfatigue.2021.106552','10.1016/j.engfracmech.2022.108883','10.1016/j.proeng.2018.02.002','10.1016/j.ijplas.2021.103172'] for r in histrows),name+' invalid/reusedquarantinedabsent')
 cui=[r for r in histrows if r['group_id']=='cui_linked_campaign'];check(len(cui)==13 and {r['doi'] for r in cui}=={'10.1016/j.jmst.2021.10.006'},name+' singleCuirepresentative')
 check(byid['a0554_d006_p004']['event']=='1' and byid['a0554_d006_p004']['runout']=='0',name+' correctedWood')
 ked=[r for r in histrows if r['dataset_id']=='a0577_d003'];check(len(ked)==9 and all(r['thermal']=='NHT' and r['heat_temperature']=='' and r['heat_time']=='' for r in ked),name+' KedzioraNHT')
 for c in corrections:
  if c['row_id'] not in byid:continue
  v=byid[c['row_id']][c['field']];e=c['corrected_value']
  equal=(v==e) or (v=='' and e=='')
  if not equal:
   try:equal=float(v)==float(e)
   except ValueError:pass
  check(equal,name+' correctionfield',(c['row_id'],c['field'],v,e))
 blocks={r['group_id'] for r in histrows};curves=defaultdict(set)
 for r in rows:curves[r['dataset_id']].add(r['row_id'])
 calcounts=[];targetepisodes=0;uniquequeries=defaultdict(set)
 for ti,t in enumerate(j['tasks']):
  fit=set(t['fit_blocks']);cal=set(t['cal_blocks']);outer=t['outer'];ks=t['ks'];targetepisodes+=len(t['targets'])
  check(not fit&cal,name+' fit/cal blockdisjoint',ti);check(outer not in fit|cal,name+' outerdisjoint',ti)
  check(fit|cal|({outer} if not ext else set())==blocks,name+' blockscomplete',ti)
  check(len(fit)>=4,name+' atleast4fitsources',ti)
  check(len(t['calibration'])==len(cal) and {c['block'] for c in t['calibration']}==cal,name+' onecalepisodeperblock',ti)
  if not j['calibration_enabled']:check(not cal and not t['calibration'],name+' fulltrainingnocal',ti)
  fitids={r['row_id'] for r in rows if r['group_id'] in fit};calids={r['row_id'] for r in rows if r['group_id'] in cal}
  check(not fitids&calids,name+' fitcalrowsdisjoint',ti)
  for role,episodes in [('target',t['targets']),('calibration',t['calibration'])]:
   for c in episodes:
    sup=c['support_pool'];query=c['query_ids'];sset=set(sup);qset=set(query);curve=c['curve']
    check(len(sup)==max(ks),name+' supportpoolmaxk',(ti,role,curve))
    check(len(sup)==len(sset) and len(query)==len(qset),name+' episodeuniquerows',(ti,role,curve))
    check(not sset&qset,name+' supportquerydisjoint',(ti,role,curve))
    check(sset|qset==curves[curve],name+' curvecomplete',(ti,role,curve))
    check(all(rid in byid and byid[rid]['dataset_id']==curve for rid in sup+query),name+' curveIDvalid',(ti,role,curve))
    check(not(sset|qset)&fitids,name+' episodefitdisjoint',(ti,role,curve))
    if role=='target':
     check(not(sset|qset)&calids,name+' targetcaldisjoint',(ti,curve))
     check({byid[rid]['group_id'] for rid in sup+query}=={outer},name+' targetsource',(ti,curve))
     uniquequeries[t['panel']].update(query)
    else:
     check({byid[rid]['group_id'] for rid in sup+query}=={c['block']},name+' calsource',(ti,curve))
     check(c['query_id'] in qset and c['query_id'] not in sset,name+' chosenquerydisjoint',(ti,curve))
    prev=set()
    for k in ks:
     selected=set(sup[:k]);check(prev<=selected,name+' nestedk',(ti,role,curve,k));check(len(selected)==k,name+' exactk',(ti,role,curve,k));check(not selected&qset,name+' allkfixedquery',(ti,role,curve,k));prev=selected
    if not ext:
     expected=hashed_order(curves[curve],['v2',t['panel'],t['seed'],'support-query'])
     check(sup+query==expected,name+' outcomeblindSHAorder',(ti,role,curve))
    elif role=='target' and t['panel']=='external_random':
     expected=hashed_order(curves[curve],['v2-external',t['seed'],'support-query']);check(sup+query==expected,name+' externalrandomSHA',(ti,curve))
    elif role=='target':
     tied=hashed_order(curves[curve],['v2-external','chronological-tie']);rank={r:i for i,r in enumerate(tied)}
     expected=sorted(curves[curve],key=lambda rid:(datetime.strptime(byid[rid]['test_date_author'],'%m/%d/%Y'),rank[rid]))
     check(sup+query==expected,name+' chronologicalUSdates',(ti,curve))
     sd=[datetime.strptime(byid[rid]['test_date_author'],'%m/%d/%Y') for rid in sup];qd=[datetime.strptime(byid[rid]['test_date_author'],'%m/%d/%Y') for rid in query]
     check(max(sd)<=min(qd),name+' chronologyNofuturelookahead',(ti,curve))
    elif role=='calibration':
     expected=hashed_order(curves[curve],['v2-external',t['seed'],'cal-support-query']);check(sup+query==expected,name+' externalcalSHA',(ti,curve))
  calcounts.append(len(cal))
 if ext:
  historical=next((n for n in ['strict','strict_fulltraining'] if sha(ROOT/'data/processed/v2'/n/'frozen_splits.json')==j['historical_split_sha256']),None)
  check(historical is not None,name+' historicalsplitSHAknown')
  check(sha(ROOT/'data/processed/v2'/historical/'cohort.csv')==j['historical_sha256'],name+' historicalSHA')
  check(sha(ROOT/'data/processed/v2'/historical/'frozen_splits.json')==j['historical_split_sha256'],name+' historicalsplitSHA')
  check(sha(ROOT/'data/external_v2/trombley2025/fatigue_asbuilt_available129.csv')==j['external_raw_sha256'],name+' externalrawSHA')
  erows=[r for r in rows if r['row_id'].startswith('mc2564')];check(len(erows)==129,name+'129external')
  check(j['external_independent_campaign_count']==1 and len({r['dataset_id'] for r in erows})==3,name+' onecampaign3conditions')
 else:
  check(j['n_rows']==len(rows) and j['n_blocks']==len(blocks) and j['n_curves']==len(curves),name+' metacounts')
  check(sha(raw)==j['source_sha256'],name+' originalsourceSHA')
  for p in j['panels']:
   eligiblecurves={c for c,ids in curves.items() if len(ids)>=p['min_rows']};eblocks={byid[next(iter(curves[c]))]['group_id'] for c in eligiblecurves}
   check(p['curves']==len(eligiblecurves) and p['blocks']==len(eblocks),name+' panelcounts',p['panel'])
   ts=[t for t in j['tasks'] if t['panel']==p['panel']];check(len(ts)==len(eblocks)*3,name+'3seedsallsourcefolds',p['panel'])
   for seed in [0,17,42]:check({t['outer'] for t in ts if t['seed']==seed}==eblocks,name+' eachouteronce',(p['panel'],seed))
 summaries.append({'configuration':name,'cohort_rows':len(rows),'historical_source_blocks':len(blocks),'historical_source_DOIs':len({r['doi'] for r in histrows}),'tasks':len(j['tasks']),'target_curve_episodes':targetepisodes,'calibration_counts':dict(Counter(calcounts)),'all_90pct_endpoint_calibration_fewer_than9':all(m<9 for m in calcounts),'independent_external_campaigns':1 if ext else 0,'unique_queried_rows_by_panel':{p:len(ids) for p,ids in uniquequeries.items()},'frozen_split_sha256':sha(folder/'frozen_splits.json'),'cohort_sha256':sha(folder/'cohort.csv'),'status':'PASS'})
# Same targetqueries/supports across calibrated/fulltraining tracks.
for a,b in [('strict','strict_fulltraining'),('external','external_fulltraining')]:
 ta={(t['panel'],t['seed'],t['outer']):t for t in manifests[a]['tasks']};tb={(t['panel'],t['seed'],t['outer']):t for t in manifests[b]['tasks']};check(ta.keys()==tb.keys(),'pairedtracktaskkeys',(a,b))
 for k in ta:check(ta[k]['targets']==tb[k]['targets'],'pairedtrackexacttargetepisodes',(a,b,k))
# Nearcluster removals: exact rowset and same-event nearcoordinate components.
base=frames['strict'];nc=frames['strict_nearcluster'];rem=read(ROOT/'data/processed/v2/strict_nearcluster/near_cluster_removals.csv')
check(set(base)-set(nc)=={r['removed'] for r in rem},'nearclusterremovedset')
for m in rem:
 a=base[m['removed']];b=base[m['retained']];check(a['dataset_id']==b['dataset_id']==m['dataset_id'] and a['event']==b['event'],'nearclustermatch');check(abs(float(a['log_life'])-float(b['log_life']))<=math.log10(1.02) and abs(float(a['log_stress'])-float(b['log_stress']))<=math.log10(1.01),'nearclustertolerance')
# Protocol tie semantics: stable databaseaddress versus author specimen name.
warnings.append('ChronologicaltiesuseSHA256ofrow_id (stableauthorrecordaddress), while amendmentcallsit specimenID; deterministic/outcomeblindbutprose should clarify beforeclaimingliteralprotocol identity.')
receipt={'status':'PASS','scope':'Independent frozen split/cohort/sourcegate arithmetic; no model imports or performance outcomes; no frozenfile changed.','configurations':summaries,'source_corrections_verified':len(corrections),'near_cluster_rows_removed':len(rem),'warnings':warnings,'inference_limits':['HistoricalconditionsareS-Ncurves,notcertifiedbatches;11sourceblocksnot11independentlaboratories.','PanelA9sourceblocks,PanelB6,PanelC5;bootstrappairedwithinpanelandseedaveragewithinsource;donottreatseeds/curves/rowsasindependentcampaigns.','External3conditionsareonecampaign;4episodes(random3seeds+chronological1)aredependentsubsamples,not4independentsources.','Allcalibratedtrackscurrentlyhavefewerthan9independentcalibrationblocks;thefinite90%endpointorderstatisticmustyieldzero-lifebounds,notaconvenientfiniterank.','Cuihasone13rowJMSTrepresentativeinonefamilyblock;theIJPpaperisabsent.','CorrectedWoodrunoutisfailure;KedzioraRenishawNHTwithblankheattemperature/time;MerotandlinkedsteppedcontinuationandMolaeirepublishedcurvesareabsent.']}
(OUT/'split_audit_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
with (OUT/'split_audit_configurations.csv').open('w',newline='') as f:
 fields=['configuration','cohort_rows','historical_source_blocks','historical_source_DOIs','tasks','target_curve_episodes','calibration_counts','frozen_split_sha256','cohort_sha256','status'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in summaries)
print(json.dumps(receipt,indent=2))
