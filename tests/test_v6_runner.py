"""Synthetic interface/aggregation checks; actual fatigue data are not loaded."""
import json
import pickle
import numpy as np
import pandas as pd
from scipy.stats import norm
from src.v2_models import HierarchicalCensoredBasquin
import src.v6_run as runner


class GaussianStub:
    def predict_quantiles(self,query,support=None,alphas=(.1,)):
        assert 'log_life' not in query and 'event' not in query
        return np.full((len(query),len(alphas)),6.)+.3*norm.ppf(alphas)[None,:]
    def predict_log_score(self,query,support=None):
        y=np.asarray(query.log_life);e=np.asarray(query.event)
        return np.where(e==1,norm.logpdf((y-6)/.3)-np.log(.3),norm.logsf((y-6)/.3))
    def predict_cdf(self,log_y,query,support=None):
        assert 'log_life' not in query and 'event' not in query
        return norm.cdf((np.asarray(log_y)-6)/.3)


def test_grid_is_complete_and_symbolic_reference_values_are_not_target_fitted():
    g=runner.candidate_grid()
    assert len(g)==146
    assert pd.Series([c['category'] for c in g]).value_counts().to_dict()=={
        'gp':66,'student':48,'joint_rfl':10,'hierarchical':5,'curved_hierarchical':5,
        'rfl':5,'local_slope':5,'pooled':1,'matched_intercept':1}
    assert all(c['ordinal']==i for i,c in enumerate(g))


def test_full_outer_shard_uses_covariate_prediction_common_supports_and_retains_fixed_controls(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'RESULT',tmp_path)
    cohort=pd.DataFrame(dict(row_id=[f's{i}' for i in range(12)],
        dataset_id=['target']*6+['train']*6,group_id=['held']*6+['kept']*6,
        log_stress=np.tile(np.linspace(2.1,2.5,6),2),load_ratio=-1.,
        log_life=np.tile([6.5,6.2,6.,5.8,5.6,5.4],2),event=[1]*12))
    base=HierarchicalCensoredBasquin();base.params_=np.array([6.,-4.,0.,np.log(.3),np.log(.5)])
    base.center_=np.array([2.3,-1.]);base.sigma_=.3;base.tau_=.5;base.ratio_median_=-1.
    base.fit_receipt_=dict(success=True,sources=1,conditions=1)
    task=dict(dataset_id='target',group_id='held',seed=0,phase='outer',
        query_ids=['s0','s1','s2'],pool_ids=['s3','s4','s5'],ks=[0,3])
    e=runner.Experiment.__new__(runner.Experiment)
    e.freeze_hash='synthetic-freeze';e.cohort=cohort;e.index=cohort.set_index('row_id',drop=False)
    e.grid=runner.candidate_grid();e.by_id={c['candidate_id']:c for c in e.grid}
    e.design={'outer_tasks':[task]}
    train=cohort[cohort.group_id.eq('kept')]
    e.fold=lambda excluded:(train,tmp_path,{'signature':'synthetic-fold'})
    e.references=lambda train,folder:({'hierarchical':base},{})
    e.predictor=lambda candidate,train,folder,refs:GaussianStub()
    selection=dict(freeze_sha256=e.freeze_hash,inner_csv_sha256={},selected={'held':{
        'gp':'gp00','hierarchical':'hierarchical_m1','matched_intercept':None,
        'selected_predictor':'gp00','selected_control':'hierarchical_m1'}})
    scores=pd.DataFrame([dict(outer_family='held',candidate_id=cid,category=cat,
        mean_log_score=score,eligible=eligible,ordinal=i) for i,(cid,cat,score,eligible) in enumerate([
            ('gp00','gp',.3,True),('hierarchical_m1','hierarchical',.1,True),
            ('matched_intercept','matched_intercept',.9,False)])])
    scores.to_csv(tmp_path/'nested_selection_scores.csv',index=False)
    selection['score_table_sha256']=runner.digest(tmp_path/'nested_selection_scores.csv')
    (tmp_path/'selected.json').write_text(json.dumps(selection))
    e.outer_family('held',1e6)
    files=list((tmp_path/'outer_cap1e6').glob('task_*.pkl'));assert len(files)==1
    with files[0].open('rb') as f:r=pickle.load(f)
    d=pd.DataFrame(r['predictions'])
    assert len(d)==11*4*2*3  #5selectionaliases +6fixedcontrols, includingNaNwinner
    assert set(d['model'])>=set(['frozen_matched_intercept','frozen_pooled'])
    assert d[d['model'].eq('matched_intercept')].log_lower.isna().all()
    assert d[d['model'].eq('frozen_matched_intercept')].log_lower.notna().all()
    assert d.groupby(['policy','k']).support_ids_sha256.nunique().eq(1).all()
    assert not d[d['model'].ne('matched_intercept')].error.ne('').any()
    assert all(x['cdf_q10_error']<1e-12 for x in r['diagnostics'])
    assert all(row['revealed_log_life']<=6 for plan in r['selections'].values() for row in plan)
    before=files[0].read_bytes();e.outer_family('held',1e6)
    assert files[0].read_bytes()==before


def test_freeze_is_required_and_actual_files_are_never_read_by_synthetic_mock(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'FREEZE',tmp_path/'absent.json')
    try:runner.load_frozen()
    except FileNotFoundError:pass
    else:raise AssertionError('fitting must require real freeze')
