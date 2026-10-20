"""Same-query, same-support v4 training-evidence comparison; v3 models unchanged."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from src.v3_prepare import ROOT,digest
from src.v3_design import rank,POLICIES,choose_next,truncate_support
from src.v3_run import fit_models

BASE=ROOT/'data/processed/v4/controlled_expansion'
PROTOCOL=ROOT/'protocols/v4/frozen_training_expansion.txt'
COLS=['row_id','dataset_id','group_id','log_stress','load_ratio','log_life','event']

def prepare():
    BASE.mkdir(parents=True,exist_ok=True)
    paths={
        'strict':ROOT/'data/processed/v2/strict_fulltraining/cohort.csv',
        'increment':ROOT/'data/external_v4/source_expansion/source_qualified_ca_expansion.csv',
        'target':ROOT/'data/external_v4/yankin2025/table3_69.csv'}
    h,e,t=[pd.read_csv(paths[k]) for k in ['strict','increment','target']]
    assert not set(h.row_id)&set(e.row_id)
    assert not set(h.doi)&set(e.doi)
    assert not set(t.doi)&(set(h.doi)|set(e.doi))
    assert len(h)==309 and len(e)==132 and len(t)==69
    regimes={'strict309':h,
             'expanded441':pd.concat([h,e],ignore_index=True),
             'strict_plus_elanges347':pd.concat([h,e[e.group_id=='v4_elangeswaran_linked_experiments']],ignore_index=True),
             'strict_plus_zhang403':pd.concat([h,e[e.group_id=='v4_zhang_linked_original_experiments']],ignore_index=True)}
    counts={}
    for name,frame in regimes.items():
        x=frame[COLS].copy()
        for c in ['log_stress','load_ratio','log_life']:x[c]=x[c].astype(float)
        x['event']=x.event.astype(int)
        assert x.row_id.is_unique and np.isfinite(x[['log_stress','load_ratio','log_life']]).all().all()
        x.to_csv(BASE/f'{name}.csv',index=False)
        counts[name]={'rows':len(x),'conditions':x.dataset_id.nunique(),'source_blocks':x.group_id.nunique(),
                      'sha256':digest(BASE/f'{name}.csv')}
    t.to_csv(BASE/'target.csv',index=False)
    tasks=[]
    for did,d in t.groupby('dataset_id',sort=True):
        if len(d)<6:continue
        nq=max(3,int(np.floor(.4*len(d))))
        ks=[0]+[k for k in [3,5,10] if k<=len(d)-nq]
        for seed in range(10):
            ordered=rank(d.row_id,'v3-common-query',seed,did)
            tasks.append(dict(dataset_id=did,seed=seed,ks=ks,query_ids=ordered[:nq],pool_ids=ordered[nq:]))
    assert len(tasks)==40 and all(x['ks']==[0,3] for x in tasks)
    receipt=dict(protocol_sha256=digest(PROTOCOL),inputs={k:{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for k,p in paths.items()},
        regimes=counts,target_sha256=digest(BASE/'target.csv'),tasks=tasks,
        timing='Exploratory; all sources seen, freeze before v4 fitting.',
        planner='strict309 hierarchical; selections reused identically across regimes')
    (BASE/'frozen_splits.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='tasks'},indent=2))

def run(output,cap):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    s=json.loads((BASE/'frozen_splits.json').read_text())
    assert digest(PROTOCOL)==s['protocol_sha256']
    assert digest(BASE/'target.csv')==s['target_sha256']
    data=pd.read_csv(BASE/'target.csv').set_index('row_id',drop=False)
    models={};fits={};cache=ROOT/'work/v4/model_cache';cache.mkdir(parents=True,exist_ok=True)
    for regime,info in s['regimes'].items():
        assert digest(BASE/f'{regime}.csv')==info['sha256']
        train=pd.read_csv(BASE/f'{regime}.csv')
        assert set(train.row_id).isdisjoint(data.index) and 'yankin2025_program' not in set(train.group_id)
        models[regime],fits[regime]=fit_models(train,cache)
    planner=models['strict309']['hierarchical']
    pred=[];selections=[]
    for ti,task in enumerate(s['tasks']):
        query=data.loc[task['query_ids']];pool=data.loc[task['pool_ids']]
        for policy in POLICIES:
            selected=[];support=pool.iloc[:0].copy()
            for k in range(max(task['ks'])+1):
                if k in task['ks']:
                    for regime,mm in models.items():
                        for name,m in mm.items():
                            lower=(mm['hierarchical'] if name=='matched_intercept' and k==0 else m).predict_quantiles(query,support=support,alphas=(.1,))[:,0]
                            for i,(_,q) in enumerate(query.iterrows()):
                                row={f:q[f] for f in ['row_id','dataset_id','campaign_id','panel','identity_gate','group_id','log_life','event','log_stress','load_ratio']}
                                row.update(regime=regime,seed=task['seed'],policy=policy,k=k,model=name,cap=cap,
                                    log_lower=float(lower[i]),n_support_failure=int(support.event.sum()),
                                    support_cycles=float(np.power(10.,support.log_life).sum()),fit_signature=fits[regime]['signature'])
                                pred.append(row)
                if k==max(task['ks']):break
                cov=['row_id','log_stress','load_ratio']
                rid,extra=choose_next(policy,pool[cov],selected,support,query[cov],planner,task['seed'],cap)
                selected.append(rid);support=truncate_support(data.loc[selected],cap)
                selections.append(dict(dataset_id=task['dataset_id'],seed=task['seed'],policy=policy,k=k+1,
                    row_id=rid,stress_amplitude=float(10**data.loc[rid,'log_stress']),
                    revealed_event=int(support.iloc[-1].event),revealed_log_life=float(support.iloc[-1].log_life),
                    cap=cap,**extra))
        print(f'task{ti+1}/{len(s["tasks"])} {task["dataset_id"]} seed{task["seed"]}',flush=True)
    d=pd.DataFrame(pred);d.to_csv(out/'predictions.csv',index=False)
    pd.DataFrame(selections).to_csv(out/'selections.csv',index=False)
    receipt=dict(cap=cap,protocol_sha256=digest(PROTOCOL),splits_sha256=digest(BASE/'frozen_splits.json'),
        code_sha256={p:digest(ROOT/'src'/p) for p in ['v4_expansion.py','v3_run.py','v3_design.py','v2_models.py','v2_curved_models.py','v3_rfl.py']},
        prediction_rows=len(d),selection_rows=len(selections),fits=fits,n_tasks=len(s['tasks']),
        n_target_programs=1,independent_campaign_CI='not evaluable')
    (out/'run_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'prediction_rows':len(d),'selection_rows':len(selections)}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run'])
    p.add_argument('--output');p.add_argument('--cap',type=float,default=1e7)
    a=p.parse_args()
    if a.action=='prepare':prepare()
    else:run(a.output,a.cap)
