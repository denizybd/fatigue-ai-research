"""Runner-neutral, fixed-count support plans with outcome-blind selection.

No model fitting or predictor-specific acquisition occurs here. The supplied
planner is the training-only hierarchical Basquin Fisher reference. A ledger
contains only selected, horizon-capped observations; predictor supports should
be reconstructed with support_from_ledger, never looked up again in raw data.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from src.v3_design import POLICIES,choose_next,truncate_support

COLS=['row_id','dataset_id','group_id','log_stress','load_ratio','log_life','event']
COV=['row_id','log_stress','load_ratio']
QUERY_COV=['row_id','dataset_id','group_id','log_stress','load_ratio']


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def _data(frame):
    if set(COLS)-set(frame):raise ValueError('complete prepared cohort columns required')
    x=frame[COLS].copy().reset_index(drop=True)
    if x[['row_id','dataset_id','group_id']].isna().any().any():
        raise ValueError('row/condition/family labels must not be missing')
    for c in ['row_id','dataset_id','group_id']:x[c]=x[c].astype(str)
    if not x.row_id.is_unique:raise ValueError('unique row IDs required after string conversion')
    if not np.isfinite(x[['log_stress','load_ratio','log_life']].to_numpy(float)).all() or not x.event.isin([0,1]).all():
        raise ValueError('finite covariates/endpoints and binary event required')
    if (x.groupby('dataset_id').group_id.nunique()!=1).any():
        raise ValueError('each working condition must belong to one source family')
    return x


def _training_certificate(cohort,training_frame,task,planner,excluded_families):
    train=_data(training_frame)
    source=cohort.set_index('row_id',drop=False)
    if not set(train.row_id)<=set(source.index):raise ValueError('unknown planner-training row')
    expected=source.loc[train.row_id,COLS].reset_index(drop=True)
    pd.testing.assert_frame_equal(train,expected,check_dtype=False,check_exact=True)
    inferred=set(cohort.group_id)-set(train.group_id)
    excluded=inferred if excluded_families is None else set(map(str,excluded_families))
    if excluded!=inferred:raise ValueError('training exclusions do not match declared source families')
    expected_ids=set(cohort[~cohort.group_id.isin(excluded)].row_id)
    if set(train.row_id)!=expected_ids:raise ValueError('planner training must retain/drop whole source families')
    if str(task['group_id']) not in excluded:raise ValueError('target family leaked into planner training')
    phase=task.get('phase')
    if phase=='outer' and len(excluded)!=1:raise ValueError('outer planner must exclude exactly the target source family')
    if phase=='inner' and len(excluded)!=2:raise ValueError('inner planner must exclude outer and validation source families')
    certificate=dict(training_rows=len(train),training_families=sorted(train.group_id.unique()),
        excluded_families=sorted(excluded),training_data_sha256=hashlib.sha256(train.to_csv(index=False).encode()).hexdigest(),
        identity_scope='working source/condition labels; no physical build independence asserted',
        lineage_limit='caller binds fitted planner to this exact training frame; metadata validation does not introspect historical fit calls')
    if planner is not None:
        receipt=getattr(planner,'fit_receipt_',{})
        if not receipt.get('success',False):raise ValueError('successful fitted training-only planner receipt required')
        for name in ['sigma_','tau_','params_','center_']:
            if not hasattr(planner,name):raise ValueError('hierarchical Fisher planner interface missing '+name)
        if not np.isfinite([planner.sigma_,planner.tau_]).all() or min(planner.sigma_,planner.tau_)<=0:
            raise ValueError('positive finite planner scatters required')
        if not np.isfinite(planner.params_).all() or not np.isfinite(planner.center_).all():
            raise ValueError('finite planner population parameters required')
        if 'sources' in receipt and int(receipt['sources'])!=train.group_id.nunique():
            raise ValueError('planner source-count receipt disagrees with training frame')
        if 'conditions' in receipt and int(receipt['conditions'])!=train.dataset_id.nunique():
            raise ValueError('planner condition-count receipt disagrees with training frame')
        certificate['planner_class']=type(planner).__module__+'.'+type(planner).__qualname__
        certificate['planner_population_parameters_sha256']=_digest(dict(
            params=np.asarray(planner.params_,float).tolist(),center=np.asarray(planner.center_,float).tolist(),
            sigma=float(planner.sigma_),tau=float(planner.tau_)))
        certificate['planner_fit_success']=True
    else:certificate['planner_class']=None
    return certificate


def exposure_cost_bounds(log_life,event,cap):
    """Identified bounds for min(T,cap), preserving unknown censor stop times."""
    if not np.isfinite([log_life,cap]).all() or cap<=0 or event not in [0,1]:
        raise ValueError('finite endpoint, positive cap and binary event required')
    lower=float(cap) if log_life>=np.log10(cap) else float(10.**float(log_life))
    upper=float(cap) if event==0 else lower
    if lower>upper+1e-7:raise FloatingPointError('invalid exposure cost bounds')
    return lower,upper


def support_from_ledger(planrows,k):
    """Return ONLY the selected revealed observations, never raw endpoints."""
    if int(k)!=k or k<0:raise ValueError('nonnegative integer support count required')
    chosen=sorted([r for r in planrows if int(r['step'])<=k],key=lambda r:int(r['step']))
    if [int(r['step']) for r in chosen]!=list(range(1,int(k)+1)):
        raise ValueError('ledger does not contain requested complete support prefix')
    if len({r['row_id'] for r in chosen})!=len(chosen):raise ValueError('duplicate ledger support row')
    rows=[]
    for r in chosen:
        rows.append(dict(row_id=str(r['row_id']),dataset_id=str(r['dataset_id']),group_id=str(r['group_id']),
            log_stress=float(r['log_stress']),load_ratio=float(r['load_ratio']),
            log_life=float(r['revealed_log_life']),event=int(r['revealed_event'])))
    return pd.DataFrame(rows,columns=COLS)


def plan_episode(cohort,task,planner,training_frame,cap,policies=POLICIES,
                 budgets=None,excluded_families=None):
    """Plan a single frozen inner/outer task, shared across all predictors.

    Return {'receipt', 'query_covariates', 'plans'}, with each policy plan holding
    'selections' (JSON-safe rows), 'prefixes' (budget metadata) and 'supports'
    (DataFrames reconstructed only from revealed ledger observations).
    Budgets are fixed counts, not cost-based stopping rules. The full prepared
    cohort is required; training_frame is the exact whole-family-excluded subset.
    """
    if cap not in [1e6,1e7]:raise ValueError('v6 supports only frozen1M/10M horizons')
    data=_data(cohort);index=data.set_index('row_id',drop=False)
    policies=tuple(policies)
    if not policies or len(set(policies))!=len(policies) or not set(policies)<=set(POLICIES):
        raise ValueError('unique fixed v3 policy names required')
    raw_budgets=list(task['ks'] if budgets is None else budgets)
    if not raw_budgets or any(int(k)!=k or k<0 for k in raw_budgets):
        raise ValueError('nonnegative integer budgets required')
    ks=sorted(set(map(int,raw_budgets)))
    if not set(ks)<=set(task['ks']):raise ValueError('budget not feasible in frozen task')
    query_ids=list(map(str,task['query_ids']));pool_ids=list(map(str,task['pool_ids']))
    if len(set(query_ids))!=len(query_ids) or len(set(pool_ids))!=len(pool_ids):
        raise ValueError('duplicate frozen query/pool identity')
    if set(query_ids)&set(pool_ids):raise ValueError('query/pool identity overlap')
    condition=data[data.dataset_id.eq(str(task['dataset_id']))]
    if set(query_ids+pool_ids)!=set(condition.row_id):raise ValueError('frozen query/pool must partition the entire condition')
    if len(condition)==0 or set(condition.group_id)!={str(task['group_id'])}:
        raise ValueError('task working-condition/source-family mismatch')
    if len(query_ids)<3 or max(ks)>len(pool_ids):raise ValueError('insufficient query or support pool')
    if 'active_query_variance' in policies and max(ks)>0 and planner is None:
        raise ValueError('active policy requires the fitted training-only Fisher planner')
    certificate=_training_certificate(data,training_frame,task,planner,excluded_families)
    query_cov=index.loc[query_ids,QUERY_COV].copy().reset_index(drop=True)
    pool_cov=index.loc[pool_ids,COV].copy().reset_index(drop=True)
    # Explicit projection is the interface boundary: no query/candidate outcome
    # is passed to the frozen selector, even if the cohort contains it.
    selector_query=query_cov[COV].copy()
    plans={}
    for policy in policies:
        selected=[];rows=[];support=pd.DataFrame(columns=COLS)
        for step in range(1,max(ks)+1):
            rid,extra=choose_next(policy,pool_cov,selected,support,selector_query,
                planner,int(task['seed']),float(cap))
            if rid not in pool_ids or rid in selected:raise ValueError('selector returned an invalid support identity')
            selected.append(rid)
            # Selected support endpoints are revealed only AFTER row selection.
            raw=index.loc[selected,COLS].copy()
            support=truncate_support(raw,float(cap)).reset_index(drop=True)
            r=index.loc[rid]
            lower,upper=exposure_cost_bounds(float(r.log_life),int(r.event),float(cap))
            revealed=support.iloc[-1]
            rows.append(dict(step=step,k=step,policy=policy,row_id=rid,
                dataset_id=str(task['dataset_id']),group_id=str(task['group_id']),
                seed=int(task['seed']),cap=float(cap),log_stress=float(revealed.log_stress),
                load_ratio=float(revealed.load_ratio),stress_amplitude=float(10.**revealed.log_stress),
                revealed_log_life=float(revealed.log_life),revealed_event=int(revealed.event),
                cost_lower=lower,cost_upper=upper,**extra))
        prefixes={};supports={}
        for k in ks:
            supports[k]=support_from_ledger(rows,k)
            prefix=[r for r in rows if r['step']<=k]
            ids=[r['row_id'] for r in prefix]
            lower=float(sum(r['cost_lower'] for r in prefix));upper=float(sum(r['cost_upper'] for r in prefix))
            prefixes[k]=dict(k=k,support_ids=ids,n_support_failure=int(supports[k].event.sum()),
                support_cycles=lower,support_cycles_lower=lower,support_cycles_upper=upper,
                support_cost_exact=bool(np.isclose(lower,upper,rtol=0,atol=1e-6)),
                support_ids_sha256=hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
                support_set_sha256=hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest(),
                query_n=len(query_ids),pool_n=len(pool_ids),remaining_pool_n=len(pool_ids)-k,
                pool_exhausted=bool(k==len(pool_ids)))
        plans[policy]=dict(selections=rows,prefixes=prefixes,supports=supports)
    code=Path(__file__)
    selector=code.with_name('v3_design.py')
    receipt=dict(task_sha256=_digest(task),cap=float(cap),budgets=ks,policies=list(policies),
        dataset_id=str(task['dataset_id']),group_id=str(task['group_id']),phase=task.get('phase'),
        seed=int(task['seed']),query_ids=query_ids,pool_ids=pool_ids,
        training_certificate=certificate,query_and_pool_outcomes_absent_from_selector_inputs=True,
        outcomes_revealed_after_selection_only=True,model_neutral_shared_plan=True,
        budget_type='fixed support count; no cost-based stopping',
        cost_semantics='min(T,cap) identification bounds; inherited support_cycles is lower bound',
        source_code_sha256=hashlib.sha256(code.read_bytes()).hexdigest(),
        frozen_selector_code_sha256=hashlib.sha256(selector.read_bytes()).hexdigest())
    receipt['ledger_identity_sha256']=_digest(receipt)
    return dict(receipt=receipt,query_covariates=query_cov,plans=plans)
