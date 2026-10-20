"""Family-held-out policy test with source-reviewed curves; no target-family fits."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from src.v3_prepare import ROOT,digest
from src.v3_design import rank,POLICIES,choose_next,truncate_support
from src.v3_run import fit_models
from src.v4_expansion import BASE

DEST=ROOT/'data/processed/v4/source_holdout'
PROTO=ROOT/'protocols/v4/source_holdout_policy_extension.txt'

def prepare():
    DEST.mkdir(parents=True,exist_ok=True)
    p=ROOT/'data/external_v4/source_expansion/source_qualified_ca_expansion.csv'
    t=pd.read_csv(p);t['campaign_id']=t.group_id
    t['panel']='source_qualified_expansion_holdout'
    t['identity_gate']='digitized_source_condition_no_specimen_build_ID'
    t.to_csv(DEST/'target.csv',index=False)
    tasks=[]
    for did,d in t.groupby('dataset_id',sort=True):
        if len(d)<6:continue
        nq=max(3,int(np.floor(.4*len(d))))
        ks=[0]+[k for k in [3,5,10] if k<=len(d)-nq]
        target_group=d.group_id.iloc[0]
        train='strict_plus_elanges347' if target_group=='v4_zhang_linked_original_experiments' else 'strict_plus_zhang403'
        for seed in range(10):
            order=rank(d.row_id,'v3-common-query',seed,did)
            tasks.append(dict(dataset_id=did,campaign_id=target_group,seed=seed,ks=ks,
                query_ids=order[:nq],pool_ids=order[nq:],expanded_training=train))
    assert len(tasks)==110
    eligible=t[t.dataset_id.isin({x['dataset_id'] for x in tasks})]
    assert len(eligible)==115 and eligible.dataset_id.nunique()==11
    s=dict(protocol_sha256=digest(PROTO),target_sha256=digest(DEST/'target.csv'),
        source_sha256=digest(p),main_split_sha256=digest(BASE/'frozen_splits.json'),
        tasks=tasks,target_rows=132,eligible_rows=115,eligible_conditions=11,source_families=2,
        design_note='Frozen after main fits but before parent inspected their numerical summaries; pool exhaustion identified from sample counts.')
    (DEST/'frozen_splits.json').write_text(json.dumps(s,indent=2)+'\n')
    print(json.dumps({k:v for k,v in s.items() if k!='tasks'},indent=2))

def run(output,cap):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    s=json.loads((DEST/'frozen_splits.json').read_text());assert digest(PROTO)==s['protocol_sha256']
    assert digest(DEST/'target.csv')==s['target_sha256']
    assert digest(BASE/'frozen_splits.json')==s['main_split_sha256']
    main=json.loads((BASE/'frozen_splits.json').read_text())
    models={};fits={};cache=ROOT/'work/v4/model_cache'
    for name in ['strict309','strict_plus_elanges347','strict_plus_zhang403']:
        p=BASE/f'{name}.csv';assert digest(p)==main['regimes'][name]['sha256']
        train=pd.read_csv(p);models[name],fits[name]=fit_models(train,cache)
    planner=models['strict309']['hierarchical'];t=pd.read_csv(DEST/'target.csv').set_index('row_id',drop=False)
    pred=[];sel=[];family_checks=[]
    for ti,task in enumerate(s['tasks']):
        names={'strict309':'strict309','expanded_family_excluded':task['expanded_training']}
        for label,name in names.items():
            blocks=fits[name]['training_sources']
            assert task['campaign_id'] not in blocks
            trainids=set(pd.read_csv(BASE/f'{name}.csv',usecols=['row_id']).row_id)
            targetids=set(t[t.group_id==task['campaign_id']].row_id)
            assert not targetids&trainids
            family_checks.append(dict(dataset_id=task['dataset_id'],seed=task['seed'],regime=label,
                excluded_family=task['campaign_id'],training_name=name,target_family_absent=True))
        query=t.loc[task['query_ids']];pool=t.loc[task['pool_ids']]
        for policy in POLICIES:
            chosen=[];support=pool.iloc[:0].copy()
            for k in range(max(task['ks'])+1):
                if k in task['ks']:
                    for regime,name in names.items():
                        for model,m in models[name].items():
                            mm=models[name]['hierarchical'] if model=='matched_intercept' and k==0 else m
                            bounds=mm.predict_quantiles(query,support=support,alphas=(.1,))[:,0]
                            for i,(_,q) in enumerate(query.iterrows()):
                                row={c:q[c] for c in ['row_id','dataset_id','campaign_id','panel','identity_gate',
                                    'group_id','log_life','event','log_stress','load_ratio']}
                                row.update(regime=regime,model=model,policy=policy,k=k,seed=task['seed'],cap=cap,
                                    log_lower=float(bounds[i]),n_support_failure=int(support.event.sum()),
                                    support_cycles=float(np.power(10.,support.log_life).sum()),fit_signature=fits[name]['signature'])
                                pred.append(row)
                if k==max(task['ks']):break
                cov=['row_id','log_stress','load_ratio']
                rid,extra=choose_next(policy,pool[cov],chosen,support,query[cov],planner,task['seed'],cap)
                chosen.append(rid);support=truncate_support(t.loc[chosen],cap)
                sel.append(dict(dataset_id=task['dataset_id'],campaign_id=task['campaign_id'],seed=task['seed'],policy=policy,
                    k=k+1,row_id=rid,stress_amplitude=float(10**t.loc[rid,'log_stress']),cap=cap,
                    revealed_event=int(support.iloc[-1].event),revealed_log_life=float(support.iloc[-1].log_life),**extra))
        print(f'task{ti+1}/{len(s["tasks"])} {task["dataset_id"]} seed{task["seed"]}',flush=True)
    pd.DataFrame(pred).to_csv(out/'predictions.csv',index=False)
    pd.DataFrame(sel).to_csv(out/'selections.csv',index=False)
    (out/'run_receipt.json').write_text(json.dumps(dict(cap=cap,n_tasks=len(s['tasks']),prediction_rows=len(pred),
        selection_rows=len(sel),source_families=2,protocol_sha256=digest(PROTO),
        splits_sha256=digest(DEST/'frozen_splits.json'),code_sha256=digest(Path(__file__)),
        family_checks=family_checks,fits=fits),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--output')
    p.add_argument('--cap',type=float,default=1e7);a=p.parse_args()
    if a.action=='prepare':prepare()
    else:run(a.output,a.cap)
