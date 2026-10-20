"""Source-weighted phase6 summaries; model selection is already frozen upstream."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.v6_metrics import (risk_bounds,paired_risk_change_bounds,paired_ledger_cost_bounds,
    source_means,source_bootstrap)
from src.v6_run import ROOT,RESULT,FREEZE,digest,write_json,load_frozen,expected_model_aliases
from src.v3_design import POLICIES

KEYS=['model','policy','k','cap']
INDEX=['group_id','dataset_id','seed','row_id']


def validate_evaluation_universe(data,tasks,models,policies):
    """A structurally dropped query/family is an error, never a favorable mean."""
    if set(data.model)!=set(models) or set(data.policy)!=set(policies):
        raise RuntimeError('missing/extra model or policy in outer evaluation')
    expected={(str(t['group_id']),str(t['dataset_id']),int(t['seed']),int(k),str(rid))
        for t in tasks for k in t['ks'] for rid in t['query_ids']}
    for (model,policy),g in data.groupby(['model','policy'],sort=False):
        observed=set(zip(g.group_id.astype(str),g.dataset_id.astype(str),g.seed.astype(int),
            g.k.astype(int),g.row_id.astype(str)))
        if observed!=expected or len(g)!=len(expected):
            raise RuntimeError(f'incomplete frozen query universe: {model}/{policy}')


def summarize_metrics(data,metrics,keys,strict_metrics=()):
    rows=[]
    for key,g in data.groupby(keys,dropna=False,sort=True):
        if not isinstance(key,tuple):key=(key,)
        base=dict(zip(keys,key))
        for metric in metrics:
            values=source_means(g,metric,strict=metric in strict_metrics)
            rows.append(dict(**base,metric=metric,**source_bootstrap(values,strict=True)))
    return pd.DataFrame(rows)


def comparison(data,source,prefix,model,policy,k):
    a=source.set_index(INDEX).sort_index()
    b=data[data.model.eq(model)&data.policy.eq(policy)&data.k.eq(k)].set_index(INDEX)
    if not set(a.index)<=set(b.index):raise RuntimeError('paired query identity mismatch')
    if prefix!='versus_k0' and set(a.index)!=set(b.index):
        raise RuntimeError('same-budget paired query universe differs')
    b=b.loc[a.index]
    if not np.array_equal(a.log_life,b.log_life) or not np.array_equal(a.event,b.event):
        raise RuntimeError('paired query outcomes differ')
    low,high=paired_risk_change_bounds(a.log_lower,b.log_lower,a.log_life,a.event)
    finite=np.isfinite(a.log_lower)&np.isfinite(b.log_lower)
    c=a.reset_index()[INDEX+KEYS+['informative_policy_episode']].copy()
    c['comparison']=prefix
    c['reference_model']=model;c['reference_policy']=policy;c['reference_k']=k
    c['paired_availability']=(~a.log_lower.isna()&~b.log_lower.isna()).to_numpy(float)
    c['paired_finite_availability']=finite.to_numpy(float)
    c['log_life_gain']=np.where(finite,a.log_lower.to_numpy()-b.log_lower.to_numpy(),np.nan)
    c['log_score_gain']=a.log_score.to_numpy()-b.log_score.to_numpy()
    c['true_risk_change_lo']=low;c['true_risk_change_hi']=high
    return c


def analyze(folder):
    _,design,_=load_frozen()  # Also verify every frozen source/input byte.
    folder=Path(folder);receipt=json.loads((folder/'run_receipt.json').read_text())
    if receipt['freeze_sha256']!=digest(FREEZE):raise RuntimeError('outer seal mismatch')
    if digest(folder/'predictions.csv')!=receipt['prediction_csv_sha256']:raise RuntimeError('predictions modified')
    if digest(folder/'selections.csv')!=receipt['selection_csv_sha256']:raise RuntimeError('selection ledger modified')
    d=pd.read_csv(folder/'predictions.csv');sel=pd.read_csv(folder/'selections.csv')
    if set(d.cap)!={receipt['cap']} or set(sel.cap)!={receipt['cap']}:
        raise RuntimeError('mixed horizons in outer result')
    if d.duplicated(KEYS+INDEX).any():raise RuntimeError('duplicate evaluated query identity')
    task_key=lambda t:json.dumps(t,sort_keys=True)
    if (len(receipt['tasks'])!=len(design['outer_tasks']) or
            set(map(task_key,receipt['tasks']))!=set(map(task_key,design['outer_tasks']))):
        raise RuntimeError('run task universe differs from frozen episodes')
    if (set(receipt['expected_model_aliases'])!=set(expected_model_aliases()) or
            set(receipt['expected_policies'])!=set(POLICIES)):
        raise RuntimeError('unexpected model/policy declaration')
    validate_evaluation_universe(d,design['outer_tasks'],expected_model_aliases(),POLICIES)
    d['availability']=(~d.log_lower.isna()).astype(float)
    d['finite_availability']=np.isfinite(d.log_lower).astype(float)
    d['positive_infinite']=np.isposinf(d.log_lower).astype(float)
    d['score_availability']=np.isfinite(d.log_score).astype(float)
    d['known_risk'],d['upper_risk']=risk_bounds(d.log_lower,d.log_life,d.event)
    d['finite_log_lower']=np.where(np.isfinite(d.log_lower),d.log_lower,np.nan)
    d['all_support_runout']=((d.k>0)&d.n_support_failure.eq(0)).astype(float)
    summary_metrics=['availability','finite_availability','positive_infinite','score_availability',
        'known_risk','upper_risk','finite_log_lower','log_score','support_cycles_lower','support_cycles_upper',
        'all_support_runout']
    overall=summarize_metrics(d,summary_metrics,KEYS,strict_metrics=('log_score',))
    overall['subset']='full'
    informative=d[d.informative_policy_episode]
    secondary=summarize_metrics(informative,summary_metrics,KEYS,strict_metrics=('log_score',))
    secondary['subset']='informative_policy'
    absolute=pd.concat([overall,secondary],ignore_index=True)
    absolute.to_csv(folder/'summary.csv',index=False)

    # Reconstruct each cost from the shared original selected-row ledger.
    ledgers={}
    for key,g in sel.groupby(['group_id','dataset_id','seed','policy'],sort=False):
        ledgers[key]=g.sort_values('step')
    def cost(task,k):
        if k==0:return {}
        g=ledgers[task];g=g[g.step<=k]
        if len(g)!=k or g.row_id.duplicated().any():raise RuntimeError('incomplete cost ledger')
        return {str(r.row_id):(float(r.cost_lower),float(r.cost_upper)) for r in g.itertuples()}
    cost_cache={}
    contrasts=[]
    for key,g in d.groupby(KEYS,sort=True):
        alias,policy,k,cap=key
        for name,reference_model,reference_policy,reference_k in [
            ('versus_random',alias,'random',k),('versus_k0',alias,policy,0),
            ('versus_selected_control','selected_control',policy,k)]:
            c=comparison(d,g,name,reference_model,reference_policy,reference_k)
            cost_values=[]
            for row in c.itertuples():
                task=(row.group_id,row.dataset_id,int(row.seed))
                ck=(task,policy,int(k),reference_policy,int(reference_k))
                if ck not in cost_cache:
                    cost_cache[ck]=paired_ledger_cost_bounds(cost(task+(policy,),int(k)),
                        cost(task+(reference_policy,),int(reference_k)))
                cost_values.append(cost_cache[ck])
            values=pd.DataFrame(cost_values,index=c.index)
            for metric in ('change_lower','change_upper','ratio_lower','ratio_upper','savings_lower','savings_upper'):
                c['support_cost_'+metric]=values[metric]
            c['shared_selected_rows']=values['shared_selected_rows']
            contrasts.append(c)
    paired=pd.concat(contrasts,ignore_index=True)
    metrics=['paired_availability','paired_finite_availability','log_life_gain','log_score_gain',
        'true_risk_change_lo','true_risk_change_hi','support_cost_change_lower','support_cost_change_upper',
        'support_cost_ratio_lower','support_cost_ratio_upper','support_cost_savings_lower','support_cost_savings_upper']
    keys=KEYS+['comparison']
    full=summarize_metrics(paired,metrics,keys,strict_metrics=('log_score_gain',));full['subset']='full'
    part=summarize_metrics(paired[paired.informative_policy_episode],metrics,keys,
        strict_metrics=('log_score_gain',));part['subset']='informative_policy'
    paired_summary=pd.concat([full,part],ignore_index=True)
    paired_summary.to_csv(folder/'paired_comparisons.csv',index=False)
    paired.to_csv(folder/'paired_query_values.csv',index=False)

    gates=[]
    for key,g in paired_summary[paired_summary.comparison.eq('versus_random')].groupby(KEYS+['subset']):
        base=dict(zip(KEYS+['subset'],key));m=g.set_index('metric')
        a=absolute
        for col,value in base.items():a=a[a[col].eq(value)]
        a=a.set_index('metric')
        values=dict(utility_lo95=float(m.loc['log_life_gain','lo95']),
            utility_hi95=float(m.loc['log_life_gain','hi95']),
            paired_risk_hi95=float(m.loc['true_risk_change_hi','hi95']),
            finite_pair_fraction=float(m.loc['paired_finite_availability','mean']),
            cost_ratio_hi95=float(m.loc['support_cost_ratio_upper','hi95']),
            absolute_risk_hi95=float(a.loc['upper_risk','hi95']))
        evaluable=bool(all(np.isfinite(x) for x in values.values()) and int(g.n_sources.min())>=2)
        relative=bool(evaluable and values['utility_lo95']>=np.log10(1.05) and values['paired_risk_hi95']<=.02
            and values['finite_pair_fraction']>=.95 and values['cost_ratio_hi95']<=.9)
        gates.append(dict(**base,**values,evaluable=evaluable,relative_success=relative,
            empirical_absolute_risk_supported=bool(evaluable and values['absolute_risk_hi95']<=.1),
            status='pass' if relative else ('not_supported' if evaluable else 'indeterminate'),
            n_sources=int(g.n_sources.min())))
    gates=pd.DataFrame(gates);gates.to_csv(folder/'success_gates.csv',index=False)
    # No post-hoc choice of the friendliest member of a model class.
    classes={'hierarchical_curved':['tuned_hierarchical','tuned_curved_hierarchical'],
        'local_slope':['tuned_local_slope'],'rfl':['tuned_rfl','joint_rfl'],
        'student':['student'],'gp':['gp']}
    robust=[]
    for key,g in gates.groupby(['policy','k','cap','subset']):
        base=dict(zip(['policy','k','cap','subset'],key));passes=[];reversals=[];class_status={}
        for name,models in classes.items():
            a=g[g.model.isin(models)]
            passed=bool(set(a.model)==set(models) and a.evaluable.all() and a.relative_success.all())
            reversed_=bool(((a.finite_pair_fraction>=.95)&(a.utility_hi95<0)).any())
            class_status[name]=dict(passed=passed,utility_reversal=reversed_)
            if passed:passes.append(name)
            if reversed_:reversals.append(name)
        robust.append(dict(**base,passing_classes=passes,reversed_classes=reversals,
            model_robust_policy_criterion=bool(len(passes)>=3 and not reversals),class_status=class_status))
    write_json(folder/'model_robust_policy_gates.json',robust)
    write_json(folder/'analysis_receipt.json',dict(predictions=len(d),source_families=d.group_id.nunique(),
        source_of_uncertainty='descriptive conservative-source bootstrap, not verified physical builds',
        query_pairs=len(paired),cost_pairs=len(cost_cache),summary_rows=len(absolute),
        paired_summary_rows=len(paired_summary),model_robust_criteria_passed=sum(x['model_robust_policy_criterion'] for x in robust),
        metric_code_sha256=digest(ROOT/'src/v6_metrics.py'),analysis_code_sha256=digest(__file__),
        freeze_sha256=digest(FREEZE),R90C90_claim=False))
    print(json.dumps({'predictions':len(d),'query_pairs':len(paired),'cost_pairs':len(cost_cache)},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');a=p.parse_args();analyze(a.folder)
