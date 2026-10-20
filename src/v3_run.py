"""Run frozen identical-query stress-selection replays with censored baselines."""
from __future__ import annotations
import argparse,hashlib,json,pickle,time
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from src.v2_models import CensoredBasquin,HierarchicalCensoredBasquin,FixedSlopeShiftPredictor
from src.v2_curved_models import HierarchicalCurvedBasquin
from src.v3_design import POLICIES,LocalSlopeControl,choose_next,truncate_support
from src.v3_prepare import ROOT,digest

def fit_models(train,cache):
    from src.v3_rfl import NormalNormalRFL
    code={str(p.name):digest(p) for p in [ROOT/'src/v3_run.py',ROOT/'src/v2_models.py',ROOT/'src/v2_curved_models.py',
                                        ROOT/'src/v3_rfl.py']}
    signature=hashlib.sha256((train.to_csv(index=False)+json.dumps(code,sort_keys=True)).encode()).hexdigest()
    path=cache/(signature+'.pkl');receipt_path=cache/(signature+'.json')
    if path.exists():
        with path.open('rb') as f:models=pickle.load(f)
        return models,json.loads(receipt_path.read_text())
    sizes=train.groupby(['group_id','dataset_id']).row_id.transform('size')
    nc=train[['group_id','dataset_id']].drop_duplicates().groupby('group_id').size()
    w=1/(sizes*train.group_id.map(nc))
    receipt={'training_sources':sorted(train.group_id.unique()),'n_rows':len(train),
             'signature':signature,'code':code,'fits':{}}
    start=time.monotonic();print('Fitting '+str(len(train))+' training rows',flush=True)
    pooled=CensoredBasquin().fit(train,sample_weight=w.to_numpy())
    hier=HierarchicalCensoredBasquin().fit(train)
    curved=HierarchicalCurvedBasquin().fit(train)
    rfl=NormalNormalRFL(shift_prior_sd=hier.tau_).fit(train)
    models={'pooled':pooled,'hierarchical':hier,'curved_hierarchical':curved,
            'rfl':rfl,'local_slope':LocalSlopeControl(hier),
            'matched_intercept':FixedSlopeShiftPredictor(hier)}
    for name,m in models.items():
        if hasattr(m,'fit_receipt_'):
            receipt['fits'][name]=m.fit_receipt_
            if not m.fit_receipt_.get('success',False):
                raise FloatingPointError('Population fit failed: '+name+': '+str(m.fit_receipt_))
    receipt['elapsed_seconds']=time.monotonic()-start
    with path.open('wb') as f:pickle.dump(models,f)
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    print('Fits done '+str(round(receipt['elapsed_seconds'],2))+'s',flush=True)
    return models,receipt

def run(dataset,output,cap,seeds=None,panels=None):
    dataset=Path(dataset);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    cache=ROOT/'work/v3/model_cache';cache.mkdir(parents=True,exist_ok=True)
    splits=json.loads((dataset/'frozen_splits.json').read_text())
    assert digest(dataset/'cohort.csv')==splits['cohort_sha256']
    assert digest(ROOT/'protocols/v3/frozen_design.txt')==splits['protocol_sha256']
    for rel,expected in splits.get('extension_protocols',{}).items():
        assert digest(ROOT/rel)==expected,'extension protocol changed'
    cohort=pd.read_csv(dataset/'cohort.csv').set_index('row_id',drop=False)
    historical=cohort[cohort.panel=='historical_reused']
    tasks=[t for t in splits['tasks'] if (seeds is None or t['seed'] in seeds)
            and (panels is None or t['panel'] in panels)]
    predictions=[];selections=[];receipts={};completed=[]
    runtime_hash=hashlib.sha256(''.join(digest(ROOT/'src'/p) for p in
        ['v3_run.py','v3_design.py','v3_rfl.py','v2_models.py','v2_curved_models.py']).encode()).hexdigest()
    for ti,task in enumerate(tasks):
        stamp=hashlib.sha256((json.dumps(task,sort_keys=True)+runtime_hash+str(cap)
            +splits['cohort_sha256']+digest(dataset/'frozen_splits.json')).encode()).hexdigest()[:16]
        shard=output/('task_'+stamp+'.pkl')
        if shard.exists():
            with shard.open('rb') as f:r=pickle.load(f)
            predictions.extend(r['predictions']);selections.extend(r['selections']);completed.append(task)
            receipts[r['fit_key']]=r['fit_receipt'];continue
        train=historical[historical.group_id.isin(task['fit_blocks'])]
        models,fit_receipt=fit_models(train,cache);key=fit_receipt['signature'];receipts[key]=fit_receipt
        query=cohort.loc[task['query_ids']];pool=cohort.loc[task['pool_ids']]
        covcols=['row_id','log_stress','load_ratio']
        querycov=query[covcols];poolcov=pool[covcols]
        taskpred=[];tasksel=[]
        for policy in POLICIES:
            selected=[];support=pool.iloc[:0].copy()
            for k in range(max(task['ks'])+1):
                if k in task['ks']:
                    for name,m in models.items():
                        if name=='matched_intercept' and k==0:
                            bound=models['hierarchical'].predict_quantiles(query,support,alphas=(.1,))[:,0]
                        else:bound=m.predict_quantiles(query,support=support,alphas=(.1,))[:,0]
                        for i,(_,q) in enumerate(query.iterrows()):
                            row={f:q[f] for f in ['row_id','dataset_id','campaign_id','panel','identity_gate',
                                  'group_id','log_life','event','log_stress','load_ratio']}
                            row.update(seed=task['seed'],policy=policy,k=k,model=name,cap=cap,
                                log_lower=float(bound[i]),n_support_failure=int(support.event.sum()),
                                support_cycles=float(np.power(10.,support.log_life).sum()),
                                fit_signature=key)
                            taskpred.append(row)
                if k==max(task['ks']):break
                rid,selection_receipt=choose_next(policy,poolcov,selected,support,querycov,
                                                  models['hierarchical'],task['seed'],cap)
                # Endpoint revealed only after selection; no candidate outcome passed above.
                selected.append(rid);support=truncate_support(cohort.loc[selected],cap)
                tasksel.append({'dataset_id':task['dataset_id'],'campaign_id':task['campaign_id'],
                    'seed':task['seed'],'policy':policy,'k':k+1,'row_id':rid,
                    'stress_amplitude':float(10**cohort.loc[rid,'log_stress']),
                    'revealed_event':int(support.iloc[-1].event),
                    'revealed_log_life':float(support.iloc[-1].log_life),
                    'cap':cap,**selection_receipt})
        result={'predictions':taskpred,'selections':tasksel,'fit_key':key,'fit_receipt':fit_receipt}
        with shard.open('wb') as f:pickle.dump(result,f)
        predictions.extend(taskpred);selections.extend(tasksel);completed.append(task)
        print(f"task {ti+1}/{len(tasks)} {task['dataset_id']} seed{task['seed']} done",flush=True)
    pd.DataFrame(predictions).to_csv(output/'predictions.csv',index=False)
    pd.DataFrame(selections).to_csv(output/'selections.csv',index=False)
    receipt={'created_utc':datetime.now(timezone.utc).isoformat(),'cap':cap,'tasks':completed,
        'fits':receipts,'splits_sha256':digest(dataset/'frozen_splits.json'),
        'protocol_sha256':splits['protocol_sha256'],
        'code_sha256':{p.name:digest(p) for p in (ROOT/'src').glob('v3*.py')},
        'prediction_rows':len(predictions),'selection_rows':len(selections)}
    (output/'run_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'prediction_rows':len(predictions),'selection_rows':len(selections)}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',default=str(ROOT/'data/processed/v3/common'))
    p.add_argument('--output',required=True);p.add_argument('--cap',type=float,default=1e7)
    p.add_argument('--seeds',type=int,nargs='*');p.add_argument('--panels',nargs='*')
    a=p.parse_args();run(a.dataset,a.output,a.cap,a.seeds,a.panels)
