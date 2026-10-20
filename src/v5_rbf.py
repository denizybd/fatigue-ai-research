"""Frozen exploratory RBF mode transfer; never modifies earlier experiments."""
from __future__ import annotations
import argparse
import hashlib
import json
import pickle
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from src.v3_prepare import ROOT, digest
from src.v3_design import rank, POLICIES, choose_next, truncate_support
from src.v3_run import fit_models
from src.v3_summarize import summarize as inherited_summary, campaign_summary

BASE = ROOT/'data/processed/v5/rbf'
PROTOCOL = ROOT/'protocols/v5/rbf_design.txt'
AUDIT = ROOT/'literature/v5_open/rbf'
COLS = ['row_id','dataset_id','group_id','log_stress','load_ratio','log_life','event']
FAMILY = 'Behvar_Aghayar_108491_109365'
FORBIDDEN_DOIS = {'10.1016/j.ijfatigue.2024.108491','10.1016/j.ijfatigue.2025.109365'}
CODE = ['v5_rbf.py','v3_run.py','v3_design.py','v3_summarize.py',
        'v2_models.py','v2_curved_models.py','v3_rfl.py']


def code_hashes():
    return {p:digest(ROOT/'src'/p) for p in CODE}


def prepare():
    BASE.mkdir(parents=True,exist_ok=True)
    AUDIT.mkdir(parents=True,exist_ok=True)
    inputs = {
        'table':ROOT/'data/external_v4/rbf2026/table1_rbf67.csv',
        'source_audit':ROOT/'literature/v4_open/rbf2026/source_audit.json',
        'independent_audit':ROOT/'literature/v4_open/rbf2026/independent_audit.json',
        'strict_raw':ROOT/'data/processed/v2/strict_fulltraining/cohort.csv',
        'increment_raw':ROOT/'data/external_v4/source_expansion/source_qualified_ca_expansion.csv',
        'strict309':ROOT/'data/processed/v4/controlled_expansion/strict309.csv',
        'expanded441':ROOT/'data/processed/v4/controlled_expansion/expanded441.csv',
    }
    audit=json.loads(inputs['independent_audit'].read_text())
    assert audit['status']=='PASS' and all(audit['checks'].values())
    source=pd.read_csv(inputs['table'])
    assert len(source)==67 and source.source_point_locator.is_unique
    assert source.event.sum()==63 and (source.event==0).sum()==4
    assert (source.R==-1).all() and set(source.source_family_block)=={FAMILY}
    assert set(source.test_mode)=={'rotating bending'}
    assert set(source.stress_definition)=={'nominal bending stress amplitude'}
    assert source[['author_specimen_id','physical_build_id','powder_lot_id']].isna().all().all()
    target=source.copy()
    target['row_id']='rbf2026_'+target.source_point_locator
    target['dataset_id']='rbf2026_'+target.condition
    target['group_id']=FAMILY
    target['campaign_id']=FAMILY
    target['panel']=np.where(target.temperature_c==25,'rbf_primary25C','rbf_sensitivity450C')
    target['identity_gate']='publication_point_locator_no_lab_build_or_verified_virgin_ID'
    target['log_stress']=np.log10(target.stress_amplitude_mpa)
    target['load_ratio']=target.R.astype(float)
    target['log_life']=np.log10(np.where(target.event==1,
        target.N_failure_cycles,target.censor_lower_bound_cycles))
    assert np.isfinite(target[['log_stress','load_ratio','log_life']]).all().all()
    assert target.groupby('panel').size().to_dict()=={'rbf_primary25C':44,'rbf_sensitivity450C':23}
    target.to_csv(BASE/'target.csv',index=False)
    raw=pd.concat([pd.read_csv(inputs['strict_raw']),pd.read_csv(inputs['increment_raw'])],ignore_index=True)
    assert set(raw.doi).isdisjoint(FORBIDDEN_DOIS)
    assert FAMILY not in set(raw.group_id)
    regimes={}
    for name,n in [('strict309',309),('expanded441',441)]:
        train=pd.read_csv(inputs[name])[COLS]
        assert len(train)==n and train.row_id.is_unique
        assert set(train.row_id).isdisjoint(target.row_id)
        assert FAMILY not in set(train.group_id)
        matching=raw.set_index('row_id',drop=False).loc[train.row_id,COLS].reset_index(drop=True)
        pd.testing.assert_frame_equal(train.reset_index(drop=True),matching,check_dtype=False)
        train.to_csv(BASE/f'{name}.csv',index=False)
        regimes[name]={'rows':n,'conditions':train.dataset_id.nunique(),
            'source_blocks':train.group_id.nunique(),'sha256':digest(BASE/f'{name}.csv')}
    tasks=[]
    for did,d in target.groupby('dataset_id',sort=True):
        nq=max(3,int(np.floor(.4*len(d))))
        ks=[0]+[k for k in [3,5,10] if k<=len(d)-nq]
        for seed in range(10):
            order=rank(d.row_id,'v3-common-query',seed,did)
            tasks.append(dict(dataset_id=did,panel=d.panel.iloc[0],seed=seed,
                ks=ks,query_ids=order[:nq],pool_ids=order[nq:]))
    assert len(tasks)==40
    assert all(t['ks']==([0,3,5,10] if t['panel']=='rbf_primary25C' else [0,3,5]) for t in tasks)
    receipt=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        protocol_sha256=digest(PROTOCOL),code_sha256=code_hashes(),
        inputs={k:{'path':str(v.relative_to(ROOT)),'sha256':digest(v)} for k,v in inputs.items()},
        regimes=regimes,target_sha256=digest(BASE/'target.csv'),tasks=tasks,
        target_source_families=1,independence_CI='not evaluable',
        target_family_excluded_from_training=True,
        planner='strict309 hierarchical; shared support sequence for every regime/model',
        caps={'primary':5e6,'planning_sensitivity':1e7},
        source_scope='As-reported RBF outcomes; virgin status and physical independence unverified',
        timing='Protocol and all splits/code saved before any v5RBF fitting/prediction; source outcomes already seen')
    (BASE/'frozen_splits.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (AUDIT/'design_receipt.json').write_text(json.dumps({k:v for k,v in receipt.items() if k!='tasks'},indent=2)+'\n')
    print(json.dumps({'tasks':len(tasks),'regimes':regimes,'protocol_sha256':receipt['protocol_sha256'],
        'target_by_panel':target.groupby('panel').size().to_dict()},indent=2))


def cost_bounds(source,cap):
    """Bounds for source-informed truncated exposure cost, not invented stop times."""
    lo=np.minimum(np.power(10.,source.log_life.to_numpy()),cap)
    hi=np.where(source.event.to_numpy()==0,cap,lo)
    assert np.all(lo<=hi+1e-7)
    return float(lo.sum()),float(hi.sum())


def run(output,cap):
    assert cap in [5e6,1e7]
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    s=json.loads((BASE/'frozen_splits.json').read_text())
    assert digest(PROTOCOL)==s['protocol_sha256']
    assert code_hashes()==s['code_sha256'],'code changed after split freeze'
    assert digest(BASE/'target.csv')==s['target_sha256']
    for item in s['inputs'].values():assert digest(ROOT/item['path'])==item['sha256']
    data=pd.read_csv(BASE/'target.csv').set_index('row_id',drop=False)
    cache=ROOT/'work/v4/model_cache';cache.mkdir(parents=True,exist_ok=True)
    models={};fits={}
    for regime,info in s['regimes'].items():
        assert digest(BASE/f'{regime}.csv')==info['sha256']
        train=pd.read_csv(BASE/f'{regime}.csv')
        assert FAMILY not in set(train.group_id) and set(train.row_id).isdisjoint(data.index)
        models[regime],fits[regime]=fit_models(train,cache)
    planner=models['strict309']['hierarchical']
    runtime_stamp=hashlib.sha256((digest(BASE/'frozen_splits.json')+str(cap)+json.dumps(code_hashes(),sort_keys=True)).encode()).hexdigest()
    predictions=[];selections=[];diagnostics=[]
    for ti,task in enumerate(s['tasks']):
        stamp=hashlib.sha256((json.dumps(task,sort_keys=True)+runtime_stamp).encode()).hexdigest()[:16]
        shard=out/f'task_{stamp}.pkl'
        if shard.exists():
            with shard.open('rb') as h:r=pickle.load(h)
        else:
            query=data.loc[task['query_ids']];pool=data.loc[task['pool_ids']]
            r={'predictions':[],'selections':[],'diagnostics':[]}
            for policy in POLICIES:
                selected=[];support=pool.iloc[:0].copy()
                for k in range(max(task['ks'])+1):
                    if k in task['ks']:
                        raw=data.loc[selected]
                        clo,chi=cost_bounds(raw,cap)
                        support_hash=hashlib.sha256(json.dumps(selected).encode()).hexdigest()
                        for regime,mm in models.items():
                            for name,model in mm.items():
                                predictor=mm['hierarchical'] if name=='matched_intercept' and k==0 else model
                                lower=predictor.predict_quantiles(query,support=support,alphas=(.1,))[:,0]
                                if np.isnan(lower).any():raise FloatingPointError('NaN predictive lower bound')
                                diag=dict(dataset_id=task['dataset_id'],seed=task['seed'],policy=policy,
                                    k=k,regime=regime,model=name,cap=cap)
                                if name=='rfl':
                                    posterior=model.support_posterior(support)
                                    diag.update({key:val for key,val in posterior.items() if key not in ['u','weight']})
                                elif hasattr(model,'last_prediction_receipt_'):
                                    diag.update(model.last_prediction_receipt_)
                                r['diagnostics'].append(diag)
                                for i,(_,q) in enumerate(query.iterrows()):
                                    row={f:q[f] for f in ['row_id','dataset_id','campaign_id','panel','identity_gate',
                                        'group_id','log_life','event','log_stress','load_ratio']}
                                    row.update(regime=regime,seed=task['seed'],policy=policy,k=k,model=name,
                                        cap=cap,budget_role='appendix_k10' if k==10 else 'primary_or_supporting',
                                        log_lower=float(lower[i]),n_support_failure=int(support.event.sum()),
                                        support_cycles=clo,support_cycles_lower=clo,support_cycles_upper=chi,
                                        support_cost_exact=bool(np.isclose(clo,chi,rtol=0,atol=1e-6)),
                                        support_ids_sha256=support_hash,fit_signature=fits[regime]['signature'])
                                    r['predictions'].append(row)
                    if k==max(task['ks']):break
                    cov=['row_id','log_stress','load_ratio']
                    rid,extra=choose_next(policy,pool[cov],selected,support,query[cov],planner,task['seed'],cap)
                    selected.append(rid)
                    # The source endpoint is accessed only AFTER the selector returns its rowID.
                    raw=data.loc[selected];support=truncate_support(raw,cap)
                    clo,chi=cost_bounds(data.loc[[rid]],cap)
                    r['selections'].append(dict(dataset_id=task['dataset_id'],panel=task['panel'],
                        campaign_id=FAMILY,seed=task['seed'],policy=policy,k=k+1,row_id=rid,
                        stress_amplitude=float(10**data.loc[rid,'log_stress']),
                        revealed_event=int(support.iloc[-1].event),revealed_log_life=float(support.iloc[-1].log_life),
                        cost_lower=clo,cost_upper=chi,cap=cap,**extra))
            with shard.open('wb') as h:pickle.dump(r,h)
        predictions.extend(r['predictions']);selections.extend(r['selections']);diagnostics.extend(r['diagnostics'])
        print(f'task{ti+1}/{len(s["tasks"])} {task["dataset_id"]} seed{task["seed"]}',flush=True)
    pd.DataFrame(predictions).to_csv(out/'predictions.csv',index=False)
    pd.DataFrame(selections).to_csv(out/'selections.csv',index=False)
    (out/'prediction_diagnostics.json').write_text(json.dumps(diagnostics,indent=2,default=float)+'\n')
    receipt=dict(created_utc=datetime.now(timezone.utc).isoformat(),cap=cap,
        protocol_sha256=digest(PROTOCOL),splits_sha256=digest(BASE/'frozen_splits.json'),
        code_sha256=code_hashes(),fits=fits,n_tasks=len(s['tasks']),
        prediction_rows=len(predictions),selection_rows=len(selections),target_source_families=1,
        population_CI='not evaluable:one family',support_cycles_semantics='lower cost bound; exact under5e6cap',
        query_endpoints='original source values, not support-capped',
        scope='Exploratory cross-mode/as-reported RBF transfer; no physical-build/virgin validation')
    (out/'run_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'prediction_rows':len(predictions),'selection_rows':len(selections)}),flush=True)


def summarize(output):
    folder=Path(output);d=pd.read_csv(folder/'predictions.csv')
    metrics=[];policies=[]
    for regime,a in d.groupby('regime',sort=True):
        sub=folder/regime;sub.mkdir(exist_ok=True)
        a.to_csv(sub/'predictions.csv',index=False);inherited_summary(sub)
        # A one-family pilot cannot evaluate campaign-CI gates. Preserve their
        # numerical inputs, but never encode missing evidence as a failed gate.
        gates=pd.read_csv(sub/'success_gates.csv')
        gates['gate_evaluable']=False
        gates['gate_status']='not_evaluable_one_family'
        for c in ['relative_success','absolute_reliability_supported','full_success']:
            gates[c]=pd.NA
        gates.to_csv(sub/'success_gates.csv',index=False)
        for filename,storage in [('summary.csv',metrics),('paired_comparisons.csv',policies)]:
            x=pd.read_csv(sub/filename);x.insert(0,'regime',regime);storage.append(x)
    pd.concat(metrics,ignore_index=True).to_csv(folder/'all_regime_summary.csv',index=False)
    pd.concat(policies,ignore_index=True).to_csv(folder/'all_policy_contrasts.csv',index=False)
    keys=['regime','panel','policy','model','k','cap'];idx=['campaign_id','dataset_id','seed','row_id']
    pieces=[];checks=[]
    for key,a in d.groupby(keys,sort=True):
        base=dict(zip(keys,key));a=a.set_index(idx).sort_index()
        b=d[(d.regime=='strict309')&(d.panel==base['panel'])&(d.policy==base['policy'])&
            (d.model==base['model'])&(d.k==base['k'])&(d.cap==base['cap'])].set_index(idx).sort_index()
        assert a.index.equals(b.index)
        for c in ['log_life','event','log_stress','support_cycles_lower','support_cycles_upper','support_ids_sha256']:
            assert np.array_equal(a[c],b[c]),f'common query/support mismatch:{c}'
        la,lb=a.log_lower.to_numpy(),b.log_lower.to_numpy();y=a.log_life.to_numpy();e=a.event.to_numpy()
        valid=~np.isnan(la)&~np.isnan(lb);finite=np.isfinite(la)&np.isfinite(lb)
        delta=(la>y).astype(float)-(lb>y).astype(float)
        c=a.reset_index()[['campaign_id','dataset_id','seed']].copy()
        for k,v in base.items():c[k]=v
        c['paired_availability']=valid.astype(float);c['paired_finite_availability']=finite.astype(float)
        c['log_life_gain']=np.where(finite,la-lb,np.nan)
        c['true_risk_change_lo']=np.where(valid,np.where(e==1,delta,-((lb>la)&(lb>y)).astype(float)),-1.)
        c['true_risk_change_hi']=np.where(valid,np.where(e==1,delta,((la>lb)&(la>y)).astype(float)),1.)
        pieces.append(c);checks.append(base|dict(pairs=len(a),queries_equal=True,supports_equal=True))
    contrasts=pd.concat(pieces,ignore_index=True)
    campaign_summary(contrasts,['paired_availability','paired_finite_availability','log_life_gain',
        'true_risk_change_lo','true_risk_change_hi'],keys).to_csv(folder/'training_contrasts.csv',index=False)
    contrasts.groupby(keys+['campaign_id','dataset_id','seed']).mean(numeric_only=True).to_csv(folder/'training_by_condition.csv')
    (folder/'training_pair_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    cost=campaign_summary(d,['support_cycles_lower','support_cycles_upper'],keys)
    cost.to_csv(folder/'support_cost_bounds.csv',index=False)
    costs=cost.pivot(index=keys,columns='metric',values='mean').reset_index();rows=[]
    for _,a in costs.iterrows():
        b=costs[(costs.regime==a.regime)&(costs.panel==a.panel)&(costs.policy=='random')&
            (costs.model==a.model)&(costs.k==a.k)&(costs.cap==a.cap)].iloc[0]
        lower,upper=float(a.support_cycles_lower),float(a.support_cycles_upper)
        rlo,rhi=float(b.support_cycles_lower),float(b.support_cycles_upper)
        rows.append({k:a[k] for k in keys}|dict(cost_lower=lower,cost_upper=upper,
            savings_percent_lower=100*(1-upper/rlo) if rlo else np.nan,
            savings_percent_upper=100*(1-lower/rhi) if rhi else np.nan,
            interpretation='identification bounds from unknown runout stop, not confidence intervals'))
    pd.DataFrame(rows).to_csv(folder/'policy_cost_savings_bounds.csv',index=False)
    assert cost.n_campaigns.eq(1).all() and cost[['lo95','hi95']].isna().all().all()
    print(json.dumps({'regimes':d.regime.nunique(),'panels':d.panel.nunique(),'training_pair_checks':len(checks)}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','summarize'])
    p.add_argument('--output');p.add_argument('--cap',type=float,default=5e6);a=p.parse_args()
    if a.action=='prepare':prepare()
    elif a.action=='run':run(a.output,a.cap)
    else:summarize(a.output)
