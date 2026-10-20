"""Generated predictions only: independent full-analysis gate counterexamples."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import src.v6_analyze as analysis
from src.v6_run import digest

MODELS=['selected_control','tuned_hierarchical','tuned_curved_hierarchical',
        'tuned_local_slope','tuned_rfl','joint_rfl','student','gp']
POLICIES=['random','high_stress','stress_span','active_query_variance']


def fixture(folder,case):
    tasks=[];rows=[];ledgers=[]
    for family in ['generated_A','generated_B','generated_C']:
        did=family+'_condition'
        tasks.append(dict(group_id=family,dataset_id=did,seed=0,ks=[0,3],
            query_ids=[f'{family}_query{i}' for i in range(3)]))
        for policy in POLICIES:
            cost=50. if policy=='high_stress' else 100.
            for step in range(1,4):
                ledgers.append(dict(group_id=family,dataset_id=did,seed=0,policy=policy,
                    cap=1e7,step=step,row_id=f'{family}_{policy}_support{step}',
                    cost_lower=cost,cost_upper=cost))
            for model in MODELS:
                advantage=.1
                if case=='friendly_members_only' and model not in ('selected_control','tuned_hierarchical','tuned_rfl','gp'):
                    advantage=0.
                if case=='curve_reversal' and model=='tuned_curved_hierarchical':advantage=-.1
                for k in [0,3]:
                    for query in range(3):
                        bound=5. if k==0 else 5.2+(advantage if policy=='high_stress' else 0.)
                        missing=case=='missing_GP_family' and family=='generated_C' and model=='gp'
                        rows.append(dict(group_id=family,dataset_id=did,seed=0,row_id=f'{family}_query{query}',
                            model=model,policy=policy,k=k,cap=1e7,log_life=7.,event=int(query!=1),
                            log_lower=np.nan if missing else bound,log_score=np.nan if missing else -1.,
                            n_support_failure=k,informative_policy_episode=k>0,
                            support_cycles_lower=cost*k,support_cycles_upper=cost*k))
    pd.DataFrame(rows).to_csv(folder/'predictions.csv',index=False)
    pd.DataFrame(ledgers).to_csv(folder/'selections.csv',index=False)
    freeze=folder/'generated_freeze.json';freeze.write_text('{"generated":true}\n')
    receipt=dict(tasks=tasks,expected_model_aliases=MODELS,expected_policies=POLICIES,
        cap=1e7,freeze_sha256=digest(freeze),prediction_csv_sha256=digest(folder/'predictions.csv'),
        selection_csv_sha256=digest(folder/'selections.csv'))
    (folder/'run_receipt.json').write_text(json.dumps(receipt))
    return tasks,freeze


def main():
    checks={}
    with tempfile.TemporaryDirectory(prefix='v6_analysis_mock_') as directory:
        for case in ['all_classes','friendly_members_only','curve_reversal','missing_GP_family']:
            folder=Path(directory)/case;folder.mkdir()
            tasks,freeze=fixture(folder,case)
            with patch.object(analysis,'FREEZE',freeze),patch.object(analysis,'load_frozen',lambda:({},dict(outer_tasks=tasks),None)),patch.object(analysis,'expected_model_aliases',lambda:MODELS),redirect_stdout(io.StringIO()):
                analysis.analyze(folder)
            robust=json.loads((folder/'model_robust_policy_gates.json').read_text())
            r=next(x for x in robust if x['policy']=='high_stress' and x['k']==3 and x['subset']=='full')
            if case=='all_classes':
                assert len(r['passing_classes'])==5 and r['model_robust_policy_criterion']
            if case=='friendly_members_only':
                assert r['passing_classes']==['gp'] and not r['model_robust_policy_criterion']
                assert not r['class_status']['hierarchical_curved']['passed']
                assert not r['class_status']['rfl']['passed']
            if case=='curve_reversal':
                assert len(r['passing_classes'])==4 and r['reversed_classes']==['hierarchical_curved']
                assert not r['model_robust_policy_criterion']
            if case=='missing_GP_family':
                gates=pd.read_csv(folder/'success_gates.csv')
                g=gates[gates.model.eq('gp')&gates.policy.eq('high_stress')&gates.k.eq(3)&gates.subset.eq('full')].iloc[0]
                assert g.status=='indeterminate' and not g.evaluable and g.n_sources==3
            checks[case]=dict(passing_classes=r['passing_classes'],reversed_classes=r['reversed_classes'],
                criterion=r['model_robust_policy_criterion'])
        # Both same-k pairing and frozen-universe validation must reject the
        # earlier whole-family deletion counterexample rather than average it.
        d=pd.read_csv(folder/'predictions.csv')
        removed=d[~(d.group_id.eq('generated_C')&d.policy.eq('high_stress'))]
        try:analysis.validate_evaluation_universe(removed,tasks,MODELS,POLICIES)
        except RuntimeError:pass
        else:raise AssertionError('missing family accepted')
        source=removed[removed.model.eq('gp')&removed.policy.eq('high_stress')&removed.k.eq(3)]
        try:analysis.comparison(removed,source,'versus_random','gp','random',3)
        except RuntimeError:pass
        else:raise AssertionError('same-budget subset accepted')
        checks['structural_missing_family_rejected']=True
        checks['same_budget_subset_pair_rejected']=True
    receipt=dict(status='PASS',generated_end_to_end_cases=4,checks=checks,actual_fatigue_fits=0,
        scope='Fabricated predictions/ledgers and patched synthetic freeze/design only; no model fits or fatigue outcomes',
        analysis_source_sha256=digest(ROOT/'src/v6_analyze.py'),test_source_sha256=digest(__file__))
    (ROOT/'literature/v6_ml/analysis_independent_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
