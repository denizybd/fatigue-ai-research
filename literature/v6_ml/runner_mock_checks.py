"""Independent runner audit: generated source families and mocked predictors only.

Does not instantiate Experiment normally, load fatigue observations, fit any
population model or execute prepared fatigue episodes. Tests actual orchestration
and inner aggregation against a separately written arithmetic oracle.
"""
from __future__ import annotations
import hashlib
import itertools
import json
from pathlib import Path
import pickle
import sys
import tempfile
import types

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import src.v6_run as run


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def synthetic_design():
    families=[f'generated_{j:02d}' for j in range(12)]
    rows=[];inner=[];outer=[]
    for j,family in enumerate(families):
        for c in range(1+j%3):
            did=family+f'_condition_{c}'
            ids=[]
            for i in range(6):
                rid=did+f'_sample_{i}';ids.append(rid)
                rows.append(dict(row_id=rid,dataset_id=did,group_id=family,
                    log_stress=2.+i*.08,load_ratio=.1,
                    log_life=5.1+.1*i,event=1))
            for phase,seeds,storage in [('inner',[101,202,303],inner),('outer',[0],outer)]:
                for seed in seeds:
                    storage.append(dict(dataset_id=did,group_id=family,phase=phase,seed=seed,
                        query_ids=ids[:3],pool_ids=ids[3:],ks=[0,3]))
    rows.append(dict(row_id='generated_training_only_small',dataset_id='generated_small',
        group_id='generated_training_only',log_stress=2.2,load_ratio=.1,log_life=5.3,event=1))
    cohort=pd.DataFrame(rows)
    pairs=[]
    for excluded in itertools.combinations(families,2):
        train=cohort[~cohort.group_id.isin(excluded)]
        pairs.append(dict(excluded_families=list(excluded),training_row_ids=train.row_id.tolist()))
    design=dict(outer_families=families,inner_episode_templates=inner,outer_tasks=outer,
        excluded_family_pair_trainsets=pairs)
    return design,cohort


def experiment(design,cohort,grid):
    e=run.Experiment.__new__(run.Experiment)
    e.freeze={};e.freeze_hash='synthetic_not_a_real_freeze';e.design=design;e.cohort=cohort
    e.index=cohort.set_index('row_id',drop=False);e.grid=grid
    e.by_id={c['candidate_id']:c for c in grid}
    return e


def main():
    checks={}
    # Inspect actual grid construction without fitting anything.
    actual_grid=run.candidate_grid()
    counts=pd.Series([c['implementation'] for c in actual_grid]).value_counts().to_dict()
    assert counts==dict(gp=66,student=48,control=22,joint_rfl=10)
    assert len({c['candidate_id'] for c in actual_grid})==146
    checks['manifest_grid']=dict(candidates=146,counts=counts,fit_calls=0)
    design,cohort=synthetic_design()
    grid=[dict(candidate_id=cid,category=category,ordinal=i,implementation='mock')
        for i,(cid,category) in enumerate([
            ('pooled','pooled'),('gp_tie','gp'),('gp_family_sensitive','gp'),
            ('gp_missing','gp'),('student_generated','student')])]
    with tempfile.TemporaryDirectory(prefix='v6_mock_') as directory:
        mockroot=Path(directory);run.ROOT=mockroot;run.RESULT=mockroot/'results'
        run.CACHE=mockroot/'cache'
        e=experiment(design,cohort,grid)
        # The fold cache must bind full exclusions, data values, order and freeze.
        train,folder,receipt=e.fold(['generated_00','generated_01'])
        assert not set(train.group_id)&{'generated_00','generated_01'}
        assert set(train.row_id)==set(cohort[~cohort.group_id.isin(['generated_00','generated_01'])].row_id)
        assert 'generated_training_only' in set(train.group_id)
        assert e.fold(['generated_01','generated_00'])[1]==folder
        changed=cohort.copy();changed.loc[changed.group_id.eq('generated_02'),'log_life']+=.2
        altered=experiment(design,changed,grid)
        assert altered.fold(['generated_00','generated_01'])[1]!=folder
        altered.freeze_hash='another_synthetic_freeze'
        assert altered.fold(['generated_00','generated_01'])[1]!=folder
        checks['whole_family_and_cache_binding']=dict(pair_excluded=True,
            train_only_family_retained=True,unordered_pair_reused=True,
            training_values_and_freeze_change_cache=True)
        # Create every pair CSV from generated values; unequal conditions/family
        # and unequal query counts deliberately prevent row-weighted arithmetic.
        source_records=[]
        for pair_index,pair in enumerate(design['excluded_family_pair_trainsets']):
            tasks=[t for t in design['inner_episode_templates'] if t['group_id'] in pair['excluded_families']]
            for c in grid:
                records=[]
                for t in tasks:
                    family_index=design['outer_families'].index(t['group_id'])
                    condition_index=int(t['dataset_id'].rsplit('_',1)[1])
                    for k in [0,3]:
                        base=.09*family_index+.7*condition_index+.001*t['seed']+.02*k
                        cid=c['candidate_id'];bonus=0.
                        if cid=='gp_tie':bonus=5e-7
                        if cid=='gp_family_sensitive':bonus=1.2 if family_index%3==0 else -.7
                        if cid=='gp_missing':bonus=50.
                        if cid=='student_generated':bonus=.13 if condition_index==0 else -.3
                        available=not(cid=='gp_missing' and pair_index==0 and family_index==1 and t['seed']==101 and k==3)
                        record=dict(candidate_id=cid,category=c['category'],ordinal=c['ordinal'],
                            pair_index=pair_index,validation_family=t['group_id'],dataset_id=t['dataset_id'],
                            seed=t['seed'],k=k,n_query=3+condition_index*100,
                            mean_log_score=base+bonus if available else np.nan,available=available)
                        records.append(record);source_records.append(record)
                path=run.RESULT/'inner'/f'pair_{pair_index:02d}'/(c['candidate_id']+'.csv')
                path.parent.mkdir(parents=True,exist_ok=True);pd.DataFrame(records).to_csv(path,index=False)
                numeric_path=path.with_suffix('.numerics.json.gz')
                run.write_gzip_json(numeric_path,[])
                run.write_json(path.with_suffix('.json'),dict(freeze_sha256=e.freeze_hash,csv_sha256=sha(path),
                    numerics_sha256=sha(numeric_path)))
        e.select()
        actual=pd.read_csv(run.RESULT/'nested_selection_scores.csv')
        differences=[];not_evaluable=0
        # Independent nested loops, no summary/groupby functions from runner.
        for family in design['outer_families']:
            allowed_pairs={i for i,p in enumerate(design['excluded_family_pair_trainsets']) if family in p['excluded_families']}
            for c in grid:
                r=[x for x in source_records if x['candidate_id']==c['candidate_id'] and
                    x['pair_index'] in allowed_pairs and x['validation_family']!=family]
                got=actual[actual.outer_family.eq(family)&actual.candidate_id.eq(c['candidate_id'])].iloc[0]
                eligible=all(x['available'] and np.isfinite(x['mean_log_score']) for x in r)
                assert bool(got.eligible)==eligible
                if not eligible:
                    not_evaluable+=1;assert pd.isna(got.mean_log_score);continue
                family_scores=[]
                for validation_family in [f for f in design['outer_families'] if f!=family]:
                    condition_scores=[]
                    dids=sorted({x['dataset_id'] for x in r if x['validation_family']==validation_family})
                    for did in dids:
                        seed_scores=[]
                        for seed in [101,202,303]:
                            k_scores=[next(x['mean_log_score'] for x in r if
                                x['validation_family']==validation_family and x['dataset_id']==did and
                                x['seed']==seed and x['k']==k) for k in [0,3]]
                            seed_scores.append(sum(k_scores)/2)
                        condition_scores.append(sum(seed_scores)/3)
                    family_scores.append(sum(condition_scores)/len(condition_scores))
                expected=sum(family_scores)/11
                differences.append(abs(float(got.mean_log_score)-expected))
        assert max(differences)<1e-12
        selected=json.loads((run.RESULT/'selected.json').read_text())
        assert selected['selected']['generated_00']['gp']=='gp_tie'
        assert selected['selected']['generated_00']['selected_predictor']=='pooled'
        assert not bool(actual[actual.outer_family.eq('generated_00')&actual.candidate_id.eq('gp_missing')].eligible.iloc[0])
        assert bool(actual[actual.outer_family.eq('generated_01')&actual.candidate_id.eq('gp_missing')].eligible.iloc[0])
        checks['independent_inner_arithmetic']=dict(pair_files=66*len(grid),outer_families=12,
            candidates=len(grid),max_equal_family_score_error=max(differences),
            unavailable_candidate_outer_combinations=not_evaluable,
            k_seed_condition_family_weighting_verified=True,query_count_does_not_weight_families=True,
            unavailable_episode_disqualifies=True,tie_tolerance_ordinal_verified=True,
            outer_family_validation_scores_excluded=True)
        # Exercise the actual outer orchestration using fixed fake laws. No
        # fitting, actual cohort, actual task or model implementation is used.
        seen=[]
        class MockPredictor:
            def __init__(self,cid):self.cid=cid
            def predict_quantiles(self,query,support,alphas):
                assert not {'log_life','event'}&set(query)
                seen.append((self.cid,'quantile',query.row_id.tolist(),support.row_id.tolist()))
                self.last_prediction_receipt_=dict(stage='quantile',generated=True)
                return np.full((len(query),len(alphas)),5.)
            def predict_log_score(self,query,support):
                assert {'log_life','event'}<=set(query)
                self.last_prediction_receipt_=dict(stage='score',generated=True)
                return np.full(len(query),-.3)
            def predict_cdf(self,y,query,support):
                assert not {'log_life','event'}&set(query)
                self.last_prediction_receipt_=dict(stage='cdf',generated=True)
                return np.full(len(query),np.nan if self.cid=='gp_tie' else .1)
        def fake_plans(task,train,refs,excluded,cap):
            query=cohort.set_index('row_id',drop=False).loc[task['query_ids']]
            pool=cohort.set_index('row_id',drop=False).loc[task['pool_ids']]
            plans={}
            for policy in ['random','high_stress']:
                supports={0:pool.iloc[:0].copy(),3:pool.copy()}
                prefixes={k:dict(k=k,support_ids=s.row_id.tolist(),support_cycles=float(k)*100.,
                    support_cycles_lower=float(k)*100.,support_cycles_upper=float(k)*100.) for k,s in supports.items()}
                plans[policy]=dict(supports=supports,prefixes=prefixes,selections=[dict(
                    step=i+1,policy=policy,row_id=rid) for i,rid in enumerate(pool.row_id)])
            return dict(plans=plans,receipt=dict(generated=True))
        e.references=lambda train,folder:({'hierarchical':object()},dict(generated=True))
        e.predictor=lambda c,train,folder,refs:MockPredictor(c['candidate_id'])
        e.plans=fake_plans
        e.outer_family('generated_00',1e6)
        shard_path=next((run.RESULT/'outer_cap1e6').glob('task_*.pkl'))
        with shard_path.open('rb') as handle:shard=pickle.load(handle)
        predictions=pd.DataFrame(shard['predictions'])
        bad=predictions[predictions.model.eq('gp')]
        assert bad.log_lower.isna().all() and bad.error.str.contains('invalid finite-quantile CDF values').all()
        good=predictions[predictions.model.eq('pooled')]
        assert np.isfinite(good.log_lower).all() and good.error.eq('').all()
        assert all(d['scoring_receipt'].get('stage')=='score' and d['quantile_receipt'].get('stage')=='quantile'
            and d['cdf_check_receipt'].get('stage')=='cdf' for d in shard['diagnostics'] if d['candidate_id']=='pooled')
        for (policy,k),part in predictions.groupby(['policy','k']):
            assert part.groupby('model').row_id.apply(list).apply(tuple).nunique()==1
            assert part.support_ids.apply(tuple).nunique()==1
        assert shard['selection_sha256']==sha(run.RESULT/'selected.json')
        checks['outer_mock_orchestration']=dict(quantile_calls=len(seen),
            query_outcomes_absent_from_quantile_api=True,score_uses_separate_truth_api=True,
            all_aliases_share_queries_supports=True,NaN_CDF_rejected=True,
            separate_quantile_scoring_CDF_receipts_retained=True,
            selection_bytes_bound_in_shard=True,no_actual_population_fit=True)
        # Changing any CSV invalidates the post-selection evidence guard BEFORE
        # an outer population fit/planner call can execute.
        one=next((run.RESULT/'inner').glob('pair_*/*.csv'))
        one.write_bytes(one.read_bytes()+b'\n')
        def must_not_fit(*args,**kwargs):raise AssertionError('fit reached before evidence guard')
        e.fold=must_not_fit
        try:e.outer_family('generated_00',1e6)
        except RuntimeError as error:assert str(error)=='inner evidence changed'
        else:raise AssertionError('modified inner evidence accepted')
        checks['outer_evidence_guard']=dict(modified_inner_csv_rejected_before_any_fit=True)
    receipt=dict(status='PASS',checks=checks,actual_fatigue_fits=0,actual_fatigue_episode_plans=0,
        scope='generated families, manufactured mock log scores, real orchestration/aggregation only',
        runner_source_sha256=sha(ROOT/'src/v6_run.py'),test_source_sha256=sha(__file__))
    target=ROOT/'literature/v6_ml/runner_mock_receipt.json'
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
