"""Full summary pipeline on manufactured predictions/ledgers, no fitted data."""
import json
import numpy as np
import pandas as pd
from scipy.stats import norm
import src.v6_analyze as analysis
from src.v6_run import digest


def test_full_analysis_preserves_common_queries_coupled_costs_and_score_gain(tmp_path,monkeypatch):
    freeze=tmp_path/'synthetic_freeze.json';freeze.write_text('{"synthetic":true}\n')
    monkeypatch.setattr(analysis,'FREEZE',freeze)
    rows=[];selected=[];tasks=[]
    policies=['random','high_stress','stress_span','active_query_variance']
    for family in ('A','B'):
        did=family+'_condition'
        for seed in (0,1):
            tasks.append(dict(group_id=family,dataset_id=did,seed=seed,
                query_ids=[f'{family}_q{i}' for i in range(3)],ks=[0,3]))
            for policy in policies:
                for step in range(1,4):
                    selected.append(dict(group_id=family,dataset_id=did,seed=seed,policy=policy,
                        cap=1e7,step=step,row_id=f'{family}_support{step}',cost_lower=10.*step,cost_upper=20.*step))
                for model in ('selected_control','gp'):
                    for k in (0,3):
                        for i,(y,event) in enumerate(zip([5.,6.,7.],[1,0,1])):
                            bound=5.4+.1*(model=='gp')+.2*(k==3)
                            score=norm.logpdf((y-6)/.5)-np.log(.5) if event else norm.logsf((y-6)/.5)
                            score+=.1*(model=='gp')
                            rows.append(dict(group_id=family,dataset_id=did,seed=seed,row_id=f'{family}_q{i}',
                                log_life=y,event=event,log_lower=bound,log_score=score,model=model,
                                policy=policy,k=k,cap=1e7,n_support_failure=0,
                                informative_policy_episode=k>0,support_cycles_lower=60. if k else 0.,
                                support_cycles_upper=120. if k else 0.))
    pd.DataFrame(rows).to_csv(tmp_path/'predictions.csv',index=False)
    pd.DataFrame(selected).to_csv(tmp_path/'selections.csv',index=False)
    monkeypatch.setattr(analysis,'load_frozen',lambda:({},dict(outer_tasks=tasks),None))
    monkeypatch.setattr(analysis,'expected_model_aliases',lambda:['selected_control','gp'])
    (tmp_path/'run_receipt.json').write_text(json.dumps(dict(freeze_sha256=digest(freeze),cap=1e7,tasks=tasks,
        expected_model_aliases=['selected_control','gp'],expected_policies=policies,
        prediction_csv_sha256=digest(tmp_path/'predictions.csv'),
        selection_csv_sha256=digest(tmp_path/'selections.csv'))))
    analysis.analyze(tmp_path)
    p=pd.read_csv(tmp_path/'paired_comparisons.csv')
    a=p[p.comparison.eq('versus_random')&p.metric.eq('support_cost_ratio_upper')]
    np.testing.assert_allclose(a['mean'],1.)
    a=p[p.comparison.eq('versus_selected_control')&p.model.eq('gp')&p.metric.eq('log_score_gain')]
    np.testing.assert_allclose(a[['mean','lo95','hi95']],.1,atol=1e-14)
    a=p[p.comparison.eq('versus_k0')&p.k.eq(3)&p.metric.eq('log_life_gain')]
    np.testing.assert_allclose(a[['mean','lo95','hi95']],.2,atol=1e-14)
    gates=pd.read_csv(tmp_path/'success_gates.csv')
    assert not gates.relative_success.any()  #Same support sets: no policy benefit.
    robust=json.loads((tmp_path/'model_robust_policy_gates.json').read_text())
    assert not any(r['model_robust_policy_criterion'] for r in robust)
    values=pd.read_csv(tmp_path/'paired_query_values.csv')
    a=values[values.comparison.eq('versus_random')]
    np.testing.assert_allclose(a.support_cost_change_lower,0.)
    np.testing.assert_allclose(a.support_cost_change_upper,0.)


def test_dropped_whole_family_and_source_code_change_fail_closed(tmp_path,monkeypatch):
    d=pd.DataFrame([dict(model=m,policy=p,group_id=f,dataset_id=f,seed=0,k=3,row_id=f'{f}{i}')
        for m in ['a','b'] for p in ['random','high_stress'] for f in ['A','B','C'] for i in range(3)])
    tasks=[dict(group_id=f,dataset_id=f,seed=0,ks=[3],query_ids=[f'{f}{i}' for i in range(3)]) for f in ['A','B','C']]
    analysis.validate_evaluation_universe(d,tasks,['a','b'],['random','high_stress'])
    bad=d[~(d.group_id.eq('C')&d.policy.eq('high_stress'))]
    try:analysis.validate_evaluation_universe(bad,tasks,['a','b'],['random','high_stress'])
    except RuntimeError:pass
    else:raise AssertionError('a whole missing source must never disappear in aggregation')
    def changed():raise RuntimeError('frozen source changed')
    monkeypatch.setattr(analysis,'load_frozen',changed)
    try:analysis.analyze(tmp_path)
    except RuntimeError as error:assert 'frozen source changed' in str(error)
    else:raise AssertionError('analysis must verify runtime source seal first')
