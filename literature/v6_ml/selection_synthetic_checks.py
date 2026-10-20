"""Synthetic-only causal, lineage and cost checks for model-neutral plans."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import src.v6_selection as selection

class SyntheticFixedPlanner:
    """Fixed artificial parameters; no real-data fitting is performed."""
    sigma_=.4;tau_=.5
    params_=np.array([6.,-4.,0.])
    center_=np.array([2.3,.1])
    def __init__(self,training):
        self.fit_receipt_=dict(success=True,sources=training.group_id.nunique(),
            conditions=training.dataset_id.nunique(),scope='synthetic fixed parameters')
    def predict_location(self,x):
        return self.params_[0]+self.params_[1]*(x.log_stress.to_numpy()-self.center_[0])


def fixture():
    rows=[]
    for family,n in [('A',8),('B',6),('T',9)]:
        for i in range(n):
            y=[5.2,6.3,7.2,6.0,6.7,5.8,4.5,7.3,6.2][i]
            event=[1,1,1,0,0,1,1,0,1][i]
            rows.append(dict(row_id=f'{family}{i}',dataset_id=f'{family}_condition',group_id=family,
                log_stress=2.6-.06*i,load_ratio=.1,log_life=y,event=event))
    d=pd.DataFrame(rows);train=d[d.group_id!='T'].copy()
    t=dict(dataset_id='T_condition',group_id='T',phase='outer',seed=17,
        query_ids=['T1','T4','T7'],pool_ids=['T0','T2','T3','T5','T6','T8'],ks=[0,3,5])
    return d,train,t


def must_reject(callback):
    try:callback()
    except (ValueError,AssertionError):return
    raise AssertionError('invalid input accepted')


def ids(plan,policy):return [r['row_id'] for r in plan['plans'][policy]['selections']]


def main():
    data,train,task=fixture();base=SyntheticFixedPlanner(train)
    receipts={};plans={}
    actual_selector=selection.choose_next;spy_calls=[]
    def spy(policy,pool,chosen,support,query,planner,seed,cap):
        assert list(pool.columns)==selection.COV and list(query.columns)==selection.COV
        assert set(support.row_id)==set(chosen)
        assert not set(support.row_id)&set(query.row_id)
        assert len(support)==len(chosen)
        if len(support):assert (support.log_life<=np.log10(cap)+1e-14).all()
        spy_calls.append((policy,len(chosen)))
        return actual_selector(policy,pool,chosen,support,query,planner,seed,cap)
    selection.choose_next=spy
    for cap in [1e6,1e7]:
        plans[cap]=selection.plan_episode(data,task,base,train,cap,excluded_families=['T'])
    selection.choose_next=actual_selector
    assert len(spy_calls)==40
    receipts['selector_boundary']=dict(calls_checked=40,only_covariates_passed=True,
        support_contains_previous_selected_reveals_only=True)
    checks=0
    for cap,plan in plans.items():
        assert list(plan['query_covariates'])==selection.QUERY_COV
        assert not {'log_life','event'}&set(plan['query_covariates'])
        for policy,p in plan['plans'].items():
            assert len(p['selections'])==5
            for k,support in p['supports'].items():
                assert list(support.columns)==selection.COLS and len(support)==k
                prefix=p['prefixes'][k]
                assert prefix['support_ids']==support.row_id.tolist()
                assert prefix['n_support_failure']==support.event.sum()
                assert prefix['remaining_pool_n']==6-k and not prefix['pool_exhausted']
                lo=hi=0.
                for row in p['selections'][:k]:
                    original=data.set_index('row_id').loc[row['row_id']]
                    expected_log=min(float(original.log_life),np.log10(cap))
                    expected_event=int(original.event) if original.log_life<=np.log10(cap) else 0
                    assert row['revealed_log_life']==expected_log and row['revealed_event']==expected_event
                    expected_lo=min(10.**original.log_life,cap)
                    expected_hi=cap if original.event==0 else expected_lo
                    assert abs(row['cost_lower']-expected_lo)<1e-6 and abs(row['cost_upper']-expected_hi)<1e-6
                    lo+=expected_lo;hi+=expected_hi
                assert abs(prefix['support_cycles_lower']-lo)<1e-6 and abs(prefix['support_cycles_upper']-hi)<1e-6
                if cap==1e6:assert prefix['support_cost_exact']
                checks+=1
    assert selection.exposure_cost_bounds(1000.,0,1e6)==(1e6,1e6)
    assert any(r['cost_upper']>r['cost_lower'] for p in plans[1e7]['plans'].values() for r in p['selections'])
    receipts['reveal_cost_prefixes']=dict(prefixes_checked=checks,primary_cap_exact=True,
        sensitivity_preserves_censor_cost_intervals=True,source_endpoints_beyond_horizon_absent_from_supports=True)

    changed=data.copy();query=changed.row_id.isin(task['query_ids'])
    changed.loc[query,'log_life']=10.;changed.loc[query,'event']=1-changed.loc[query,'event']
    for cap in plans:
        alternate=selection.plan_episode(changed,task,base,train,cap,excluded_families=['T'])
        for policy in selection.POLICIES:
            assert alternate['plans'][policy]['selections']==plans[cap]['plans'][policy]['selections']
    receipts['query_outcome_isolation']=dict(all_policies_both_caps_unchanged=True)

    # At step j all previously selected values are preserved, while every not
    # yet selected candidate outcome is changed. The next choice must stay fixed.
    next_choice_checks=0
    for cap,plan in plans.items():
        for policy in selection.POLICIES:
            sequence=ids(plan,policy)
            for j in range(5):
                altered=data.copy()
                future=set(task['pool_ids'])-set(sequence[:j])
                mask=altered.row_id.isin(future)
                altered.loc[mask,'log_life']=4.1+.1*j
                altered.loc[mask,'event']=j%2
                replay=selection.plan_episode(altered,task,base,train,cap,
                    policies=(policy,),excluded_families=['T'])
                assert ids(replay,policy)[:j+1]==sequence[:j+1]
                next_choice_checks+=1
    receipts['unselected_future_outcome_isolation']=dict(next_choice_checks=next_choice_checks,all_pass=True)

    inner_task=task|dict(phase='inner',seed=101)
    inner_train=data[data.group_id.eq('B')].copy()
    inner=selection.plan_episode(data,inner_task,None,inner_train,1e6,policies=('random',),
        budgets=(0,3),excluded_families=['A','T'])
    assert len(inner['plans']['random']['selections'])==3
    assert set(inner['plans']['random']['supports'])=={0,3}
    must_reject(lambda:selection.plan_episode(data,task,base,train.iloc[1:],1e6))
    must_reject(lambda:selection.plan_episode(data,task,base,pd.concat([train,data[data.row_id.eq('T0')]]),1e6))
    must_reject(lambda:selection.plan_episode(data,inner_task,None,inner_train,1e6,policies=('random',),excluded_families=['T']))
    must_reject(lambda:selection.plan_episode(data,task,None,train,1e6))
    must_reject(lambda:selection.plan_episode(data,task,base,train,5e6))
    must_reject(lambda:selection.support_from_ledger(inner['plans']['random']['selections'],5))
    receipts['whole_family_lineage_and_budgets']=dict(inner_pair_exclusion_accepted=True,
        partial_family_training_rejected=True,target_family_training_rejected=True,
        wrong_declared_exclusion_rejected=True,missing_active_planner_rejected=True,
        unsupported_cap_rejected=True,unrecorded_support_budget_rejected=True)

    small=data[(data.group_id!='T')|data.row_id.isin([f'T{i}' for i in range(6)])]
    st=task|dict(query_ids=['T0','T1','T2'],pool_ids=['T3','T4','T5'],ks=[0,3])
    exhausted=selection.plan_episode(small,st,base,train,1e6)
    hashes={p['prefixes'][3]['support_set_sha256'] for p in exhausted['plans'].values()}
    assert len(hashes)==1 and all(p['prefixes'][3]['pool_exhausted'] for p in exhausted['plans'].values())
    receipts['pool_exhaustion']=dict(all_policy_support_sets_equal_when_entire_pool_selected=True,
        explicitly_flagged=True,no_invented_selection_advantage=True)
    out=dict(status='PASS',checks=receipts,actual_fatigue_fits=0,actual_prepared_episode_plans=0,
        scope='generated observations and fixed synthetic Fisher-planner parameters only',
        source_sha256=hashlib.sha256((ROOT/'src/v6_selection.py').read_bytes()).hexdigest())
    (ROOT/'literature/v6_ml/selection_synthetic_receipt.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
