"""Frozen nested source-family tuning and common-support phase6 evaluation.

No command can fit an actual fatigue population without a verified freeze.json.
Existing outcomes were inspected historically; this remains exploratory reuse.
Inner tuning uses censored log score, never the outer utility/risk table.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import pickle
import time
import traceback

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/'protocols/v6/freeze.json'
DATA=ROOT/'data/processed/v4/controlled_expansion/expanded441.csv'
EPISODES=ROOT/'data/processed/v6/episode_design.json'
RESULT=ROOT/'results/v6'
CACHE=ROOT/'work/v6/cache'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_safe(x):
    if isinstance(x,dict):return {str(k):json_safe(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [json_safe(v) for v in x]
    if isinstance(x,np.ndarray):return json_safe(x.tolist())
    if isinstance(x,np.generic):return x.item()
    if isinstance(x,Path):return str(x)
    return x


def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(json_safe(value),indent=2)+'\n');temporary.replace(path)


def save_pickle(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+f'.{os.getpid()}.tmp')
    with temporary.open('wb') as f:pickle.dump(value,f)
    temporary.replace(path)


def write_gzip_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+f'.{os.getpid()}.tmp')
    payload=(json.dumps(json_safe(value),separators=(',',':'))+'\n').encode()
    temporary.write_bytes(gzip.compress(payload,mtime=0));temporary.replace(path)


def numerical_receipt(model,support):
    receipt=json_safe(getattr(model,'last_prediction_receipt_',{}))
    from src.v2_models import HierarchicalCensoredBasquin
    from src.v3_rfl import NormalNormalRFL
    posterior=None
    if isinstance(model,HierarchicalCensoredBasquin):posterior=model.target_posterior(support)
    elif isinstance(model,NormalNormalRFL):posterior=model.support_posterior(support)
    if posterior is not None:
        summary={k:v for k,v in posterior.items() if k not in ('u','weight')}
        summary.update(nodes=len(posterior['u']),weight_sum=float(np.sum(posterior['weight'])),
            k0_prediction_uses_exact_gaussian_convolution=support is None or len(support)==0)
        receipt['scalar_target_posterior']=json_safe(summary)
    return receipt


@contextmanager
def lock(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX)
        try:yield
        finally:fcntl.flock(f.fileno(),fcntl.LOCK_UN)


def load_frozen():
    freeze=json.loads(FREEZE.read_text())
    for relative,expected in freeze['sha256'].items():
        if digest(ROOT/relative)!=expected:raise RuntimeError('frozen input/code changed: '+relative)
    design=json.loads(EPISODES.read_text());cohort=pd.read_csv(DATA)
    if len(cohort)!=441 or not cohort.row_id.is_unique:raise RuntimeError('invalid corpus')
    if digest(DATA)!=design['source_sha256']:raise RuntimeError('episode source mismatch')
    return freeze,design,cohort


def candidate_grid():
    """Symbolic reference scales are1; bind them to each training fit only."""
    from src.v6_controls import control_grid
    from src.v6_gp import proposed_gp_grid
    from src.v6_student_aft import student_aft_grid
    grid=[]
    for c in control_grid():grid.append(dict(**c,category=c['kind'],implementation='control'))
    for c in proposed_gp_grid(1.,1.):
        grid.append(dict(candidate_id=c['candidate_id'],category='gp',implementation='gp',spec=c))
    for i,c in enumerate(student_aft_grid()):
        grid.append(dict(candidate_id=f'student_{i:02d}',category='student',implementation='student',config=c.receipt()))
    for i,m in enumerate((.25,.5,1.,2.,4.)):
        for j,v in enumerate((.05,.15)):
            grid.append(dict(candidate_id=f'joint_{2*i+j:02d}',category='joint_rfl',implementation='joint_rfl',
                life_prior_multiplier=m,fatigue_limit_prior_sd=v))
    assert len(grid)==146 and len({c['candidate_id'] for c in grid})==146
    return [dict(c,ordinal=i) for i,c in enumerate(grid)]


def select_winner(group):
    valid=group[group.eligible]
    if len(valid)==0:return None
    best=valid.mean_log_score.max()
    return valid[valid.mean_log_score>=best-1e-6].sort_values('ordinal').candidate_id.iloc[0]


def expected_model_aliases():
    tuned={'tuned_'+kind if kind in ('hierarchical','curved_hierarchical','rfl','local_slope') else kind
           for kind in {c['category'] for c in candidate_grid()}}
    frozen={'frozen_'+kind for kind in ('pooled','matched_intercept','hierarchical','curved_hierarchical','rfl','local_slope')}
    return sorted(tuned|frozen|{'selected_control','selected_predictor'})


class Experiment:
    def __init__(self):
        self.freeze,self.design,self.cohort=load_frozen()
        self.freeze_hash=digest(FREEZE)
        self.grid=json.loads((ROOT/'protocols/v6/grid.json').read_text())
        if self.grid!=candidate_grid():raise RuntimeError('grid creation differs from frozen manifest')
        self.by_id={c['candidate_id']:c for c in self.grid}
        self.index=self.cohort.set_index('row_id',drop=False)

    def fold(self,excluded):
        excluded=sorted(excluded)
        train=self.cohort[~self.cohort.group_id.isin(excluded)].copy()
        if set(excluded)&set(train.group_id):raise RuntimeError('family leakage')
        signature=hashlib.sha256((self.freeze_hash+'|'+json.dumps(excluded)+'|'+train.to_csv(index=False)).encode()).hexdigest()
        folder=CACHE/signature
        folder.mkdir(parents=True,exist_ok=True)
        receipt=dict(excluded_families=excluded,training_ids=train.row_id.tolist(),
            training_sources=sorted(train.group_id.unique()),training_rows=len(train),
            training_csv_sha256=hashlib.sha256(train.to_csv(index=False).encode()).hexdigest(),
            freeze_sha256=self.freeze_hash,signature=signature)
        write_json(folder/'fold.json',receipt)
        return train,folder,receipt

    def references(self,train,folder):
        path=folder/'references.pkl'
        with lock(folder/'references.lock'):
            if path.exists():
                with path.open('rb') as f:return pickle.load(f)
            from src.v2_models import CensoredBasquin,HierarchicalCensoredBasquin
            from src.v2_curved_models import HierarchicalCurvedBasquin
            from src.v3_rfl import NormalNormalRFL
            sizes=train.groupby(['group_id','dataset_id']).row_id.transform('size')
            counts=train[['group_id','dataset_id']].drop_duplicates().groupby('group_id').size()
            weights=(1/(sizes*train.group_id.map(counts))).to_numpy()
            models={};receipts={}
            for name in ('pooled','hierarchical','curved_hierarchical','rfl'):
                attempts=[];model=None
                for retry in (False,True):
                    start=time.monotonic()
                    try:
                        if name=='pooled':
                            fitted=CensoredBasquin(max_iter=6000 if retry else 1500).fit(train,sample_weight=weights)
                        elif name=='hierarchical':
                            fitted=HierarchicalCensoredBasquin(max_iter=6000 if retry else 1500).fit(train)
                        elif name=='curved_hierarchical':
                            fitted=HierarchicalCurvedBasquin(max_iter=6000 if retry else 1500).fit(train)
                        else:
                            if 'hierarchical' not in models:raise RuntimeError('training-only hierarchy unavailable')
                            fitted=NormalNormalRFL(max_iter=2000 if retry else 500,
                                shift_prior_sd=models['hierarchical'].tau_,fallback=False).fit(train)
                        success=bool(fitted.fit_receipt_.get('success',False))
                        attempts.append(dict(success=success,elapsed=time.monotonic()-start,receipt=fitted.fit_receipt_))
                        if success:model=fitted;break
                    except Exception as error:
                        attempts.append(dict(success=False,elapsed=time.monotonic()-start,error=repr(error),traceback=traceback.format_exc()))
                receipts[name]=dict(success=model is not None,attempts=attempts)
                if model is not None:models[name]=model
            result=(models,receipts)
            save_pickle(path,result);write_json(folder/'reference_fits.json',receipts)
            return result

    def predictor(self,candidate,train,folder,refs):
        from src.v6_controls import reference_candidate
        c=candidate;kind=c['implementation'];path=folder/(c['candidate_id']+'.pkl')
        if kind=='control':return reference_candidate(refs,c['kind'],c['multiplier'])
        if kind=='joint_rfl':
            from src.v6_rfl_adapter import JointRFLTargetAdapter
            return JointRFLTargetAdapter(refs['rfl'],c['life_prior_multiplier']*refs['hierarchical'].tau_,
                c['fatigue_limit_prior_sd'])
        with lock(folder/(c['candidate_id']+'.lock')):
            if path.exists():
                with path.open('rb') as f:return pickle.load(f)
            error_path=folder/(c['candidate_id']+'_failure.json')
            if error_path.exists():raise FloatingPointError('cached failed fit: '+str(error_path))
            attempts=[];model=None
            for retry in (False,True):
                start=time.monotonic()
                try:
                    if kind=='student':
                        from src.v6_student_aft import StudentAFTConfig,CensoredStudentAFT
                        fitted=CensoredStudentAFT(StudentAFTConfig(**c['config']),max_iter=2400 if retry else 600).fit(train)
                    elif kind=='gp':
                        from src.v6_gp import CensoredLaplaceGP,GPKernelConfig
                        base=refs['hierarchical'];spec=c['spec'];config=dict(spec['config'])
                        config['condition_intercept_sd']*=base.tau_
                        p=base.params_;center=base.center_
                        mean=[float(p[0]-p[1]*center[0]-p[2]*center[1]),float(p[1]),float(p[2])]
                        fitted=CensoredLaplaceGP(GPKernelConfig(**config),noise_sd=spec['noise_multiplier']*base.sigma_,
                            mean_parameters=mean,max_iter=400 if retry else 100).fit(train)
                    else:raise ValueError(kind)
                    if not fitted.fit_receipt_.get('success',False):raise FloatingPointError('nonconverged receipt')
                    attempts.append(dict(success=True,elapsed=time.monotonic()-start,fit_receipt=fitted.fit_receipt_))
                    model=fitted;break
                except Exception as error:
                    attempts.append(dict(success=False,elapsed=time.monotonic()-start,error=repr(error),traceback=traceback.format_exc()))
            receipt=dict(candidate=c,success=model is not None,attempts=attempts)
            if model is None:
                write_json(error_path,receipt);raise FloatingPointError('candidate fit failed: '+c['candidate_id'])
            save_pickle(path,model);write_json(folder/(c['candidate_id']+'_fit.json'),receipt)
            return model

    def plans(self,task,train,refs,excluded,cap,inner=False):
        from src.v6_selection import plan_episode
        from src.v3_design import POLICIES
        return plan_episode(self.cohort,task,refs['hierarchical'],train,cap,
            policies=('random',) if inner else POLICIES,
            budgets=(0,3) if inner else None,excluded_families=excluded)

    def inner_pair(self,index,categories=None):
        pair=self.design['excluded_family_pair_trainsets'][index]
        excluded=pair['excluded_families'];train,folder,fold=self.fold(excluded)
        assert train.row_id.tolist()==pair['training_row_ids']
        refs,receipts=self.references(train,folder)
        if 'hierarchical' not in refs:raise FloatingPointError('planner unavailable; inspect reference_fits.json')
        tasks=[t for t in self.design['inner_episode_templates'] if t['group_id'] in excluded]
        # Independent of evaluated predictor and configuration. Plans are made
        # from training-only planner; selectors never receive unrevealed outcomes.
        plans=[self.plans(t,train,refs,excluded,1e6,True) for t in tasks]
        candidates=[c for c in self.grid if categories is None or c['category'] in categories]
        for ci,c in enumerate(candidates):
            out=RESULT/'inner'/f'pair_{index:02d}'/(c['candidate_id']+'.csv')
            receipt_path=out.with_suffix('.json')
            if out.exists() and receipt_path.exists():
                previous=json.loads(receipt_path.read_text())
                if previous['freeze_sha256']!=self.freeze_hash:raise RuntimeError('stale inner results')
                if digest(out)!=previous['csv_sha256']:raise RuntimeError('inner result modified')
                continue
            start=time.monotonic();rows=[];numerics=[];failure=None
            try:predictor=self.predictor(c,train,folder,refs)
            except Exception as error:predictor=None;failure=repr(error)
            for task,plan in zip(tasks,plans):
                query=self.index.loc[task['query_ids']]
                for k in (0,3):
                    row=dict(candidate_id=c['candidate_id'],category=c['category'],ordinal=c['ordinal'],
                        pair_index=index,validation_family=task['group_id'],dataset_id=task['dataset_id'],
                        seed=task['seed'],k=k,n_query=len(query),fold_signature=fold['signature'])
                    support=plan['plans']['random']['supports'][k]
                    row.update(plan['plans']['random']['prefixes'][k])
                    try:
                        if predictor is None:raise FloatingPointError(failure)
                        score=np.asarray(predictor.predict_log_score(query,support),float)
                        if score.shape!=(len(query),) or not np.isfinite(score).all():
                            raise FloatingPointError('unavailable or nonfinite predictive log score')
                        row.update(mean_log_score=float(score.mean()),available=True,error='')
                    except Exception as error:row.update(mean_log_score=np.nan,available=False,error=repr(error))
                    try:
                        numeric=numerical_receipt(predictor,support) if predictor is not None else {}
                    except Exception as error:numeric=dict(receipt_error=repr(error))
                    numerics.append(dict(dataset_id=task['dataset_id'],validation_family=task['group_id'],
                        seed=task['seed'],k=k,available=row['available'],error=row['error'],receipt=numeric))
                    rows.append(row)
            out.parent.mkdir(parents=True,exist_ok=True)
            pd.DataFrame(rows).to_csv(out,index=False)
            numeric_path=out.with_suffix('.numerics.json.gz')
            write_gzip_json(numeric_path,numerics)
            write_json(receipt_path,dict(freeze_sha256=self.freeze_hash,candidate=c,pair_index=index,
                excluded_families=excluded,fold=fold,episodes=len(rows),available=sum(x['available'] for x in rows),
                elapsed=time.monotonic()-start,population_failure=failure,csv_sha256=digest(out),
                numerics_sha256=digest(numeric_path)))
            print(f'inner pair {index:02d} {ci+1}/{len(candidates)} {c["candidate_id"]} '+
                f'{sum(x["available"] for x in rows)}/{len(rows)} {time.monotonic()-start:.2f}s',flush=True)

    def select(self):
        parts=[]
        for i in range(66):
            for c in self.grid:
                path=RESULT/'inner'/f'pair_{i:02d}'/(c['candidate_id']+'.csv')
                receipt=json.loads(path.with_suffix('.json').read_text())
                if receipt['freeze_sha256']!=self.freeze_hash or digest(path)!=receipt['csv_sha256']:
                    raise RuntimeError('bad/stale inner result')
                if digest(path.with_suffix('.numerics.json.gz'))!=receipt['numerics_sha256']:
                    raise RuntimeError('inner numerical diagnostics changed')
                parts.append(pd.read_csv(path))
        data=pd.concat(parts,ignore_index=True);records=[];selected={}
        for family in self.design['outer_families']:
            pair_indices=[i for i,p in enumerate(self.design['excluded_family_pair_trainsets']) if family in p['excluded_families']]
            sub=data[data.pair_index.isin(pair_indices)&data.validation_family.ne(family)]
            expected=[t for t in self.design['inner_episode_templates'] if t['group_id']!=family]
            expected_keys={(t['group_id'],t['dataset_id'],t['seed'],k) for t in expected for k in (0,3)}
            fold_scores=[]
            for c in self.grid:
                a=sub[sub.candidate_id.eq(c['candidate_id'])]
                keys=set(zip(a.validation_family,a.dataset_id,a.seed,a.k))
                eligible=bool(len(a)==len(expected_keys) and keys==expected_keys and a.available.all() and np.isfinite(a.mean_log_score).all())
                value=np.nan
                if eligible:
                    # Equal query rows within episode, k0/k3, seeds, conditions,
                    # and validation families. Never weigh repeated seeds as labs.
                    by_condition=a.groupby(['validation_family','dataset_id','seed']).mean_log_score.mean()
                    by_condition=by_condition.groupby(['validation_family','dataset_id']).mean()
                    by_family=by_condition.groupby('validation_family').mean()
                    assert len(by_family)==11
                    value=float(by_family.mean())
                record=dict(outer_family=family,candidate_id=c['candidate_id'],category=c['category'],
                    ordinal=c['ordinal'],eligible=eligible,mean_log_score=value,
                    available_episodes=int(a.available.sum()),expected_episodes=len(expected_keys))
                fold_scores.append(record);records.append(record)
            frame=pd.DataFrame(fold_scores)
            chosen={}
            for category,g in frame.groupby('category'):
                chosen[category]=select_winner(g)
            chosen['selected_control']=select_winner(frame[frame.category.isin(
                ['pooled','matched_intercept','hierarchical','curved_hierarchical','rfl','local_slope'])])
            chosen['selected_predictor']=select_winner(frame)
            selected[family]=chosen
        RESULT.mkdir(parents=True,exist_ok=True)
        pd.DataFrame(records).to_csv(RESULT/'nested_selection_scores.csv',index=False)
        evidence={str(p.relative_to(ROOT)):digest(p) for p in sorted((RESULT/'inner').glob('pair_*/*.csv'))}
        write_json(RESULT/'selected.json',dict(freeze_sha256=self.freeze_hash,selected=selected,
            inner_csv_sha256=evidence,score_table_sha256=digest(RESULT/'nested_selection_scores.csv'),
            criterion='equal-family censored predictive logscore, equal k0/k3; tie1e-6 then grid ordinal',
            selected_before_outer_evaluation=True,created_utc=datetime.now(timezone.utc).isoformat()))
        print('All12 outer model selections frozen from inner scores',flush=True)

    def outer_family(self,family,cap):
        selection=json.loads((RESULT/'selected.json').read_text())
        selection_hash=digest(RESULT/'selected.json')
        if selection['freeze_sha256']!=self.freeze_hash:raise RuntimeError('selection freeze mismatch')
        if digest(RESULT/'nested_selection_scores.csv')!=selection['score_table_sha256']:
            raise RuntimeError('selection score table changed')
        # Recheck the full evidence, not just a boolean selected-before-outer flag.
        for relative,expected in selection['inner_csv_sha256'].items():
            if digest(ROOT/relative)!=expected:raise RuntimeError('inner evidence changed')
        train,folder,fold=self.fold([family]);refs,fit_receipts=self.references(train,folder)
        chosen=selection['selected'][family]
        table=pd.read_csv(RESULT/'nested_selection_scores.csv')
        table=table[table.outer_family.eq(family)]
        expected_chosen={category:select_winner(g) for category,g in table.groupby('category')}
        expected_chosen['selected_control']=select_winner(table[table.category.isin(
            ['pooled','matched_intercept','hierarchical','curved_hierarchical','rfl','local_slope'])])
        expected_chosen['selected_predictor']=select_winner(table)
        if chosen!=expected_chosen:raise RuntimeError('selected candidate differs from frozen inner rule')
        aliases={('tuned_'+k if k in ('hierarchical','curved_hierarchical','rfl','local_slope') else k):v
            for k,v in chosen.items()}
        for kind in ('hierarchical','curved_hierarchical','rfl','local_slope'):
            aliases['frozen_'+kind]=f'{kind}_m1'
        aliases['frozen_matched_intercept']='matched_intercept'
        aliases['frozen_pooled']='pooled'
        predictors={};failures={}
        for cid in {x for x in aliases.values() if x is not None}:
            try:predictors[cid]=self.predictor(self.by_id[cid],train,folder,refs)
            except Exception as error:failures[cid]=repr(error)
        tasks=[t for t in self.design['outer_tasks'] if t['group_id']==family]
        outfolder=RESULT/('outer_cap1e6' if cap==1e6 else 'outer_cap1e7')
        for ti,task in enumerate(tasks):
            token=hashlib.sha256(json.dumps(task,sort_keys=True).encode()).hexdigest()[:16]
            path=outfolder/('task_'+token+'.pkl')
            if path.exists():
                with path.open('rb') as f:previous=pickle.load(f)
                if previous['freeze_sha256']!=self.freeze_hash or previous['selection_sha256']!=selection_hash:
                    raise RuntimeError('stale outer shard')
                continue
            plan=self.plans(task,train,refs,[family],cap);query=self.index.loc[task['query_ids']]
            # Prediction APIs get a covariate-only query. True outcomes are
            # passed separately only to a predictive-scoring API after q is fixed.
            querycov=query[['row_id','dataset_id','log_stress','load_ratio']]
            rows=[];diagnostics=[]
            for policy,p in plan['plans'].items():
                for k,support in p['supports'].items():
                    prefix=p['prefixes'][k];computed={}
                    for cid in {x for x in aliases.values() if x is not None}:
                        q=np.full(len(query),np.nan);score=q.copy();error='';receipt={};score_receipt={};cdf_receipt={};cdf_error=np.nan
                        try:
                            if cid not in predictors:raise FloatingPointError(failures[cid])
                            model=predictors[cid]
                            q=np.asarray(model.predict_quantiles(querycov,support,(.1,)),float)[:,0]
                            receipt=numerical_receipt(model,support)
                            score=np.asarray(model.predict_log_score(query,support),float)
                            score_receipt=numerical_receipt(model,support)
                            if np.isnan(q).any() or not np.isfinite(score).all():
                                raise FloatingPointError('predictive law unavailable on held-out episode')
                            finite=np.isfinite(q)
                            if finite.any():
                                qc=querycov.loc[finite].copy()
                                if hasattr(model,'predict_cdf'):
                                    at=model.predict_cdf(q[finite],qc,support)
                                else:
                                    qc['log_life']=q[finite];qc['event']=0
                                    at=1-np.exp(model.predict_log_score(qc,support))
                                at=np.asarray(at,float)
                                if at.shape!=(int(finite.sum()),) or not np.isfinite(at).all() or np.any((at<0)|(at>1)):
                                    raise FloatingPointError('invalid finite-quantile CDF values')
                                cdf_error=float(np.max(np.abs(at-.1)))
                                cdf_receipt=numerical_receipt(model,support)
                            if q.shape!=(len(query),) or score.shape!=(len(query),):raise FloatingPointError('wrong prediction shape')
                            if np.isfinite(cdf_error) and cdf_error>1e-3:
                                raise FloatingPointError(f'CDF(q10) discrepancy {cdf_error:g}')
                        except Exception as problem:
                            error=repr(problem)
                            # No alternative predictor chosen after seeing this
                            # held-out episode. Preserve failure/availability.
                            receipt=dict(receipt,raw_quantile=q.tolist(),raw_log_score=score.tolist())
                            q=np.full(len(query),np.nan);score=q.copy()
                        computed[cid]=(q,score,error)
                        ordered=np.argsort(query.log_stress.to_numpy())
                        increments=np.diff(q[ordered]);good=np.isfinite(increments)
                        diagnostics.append(dict(candidate_id=cid,policy=policy,k=k,error=error,
                            cdf_q10_error=cdf_error,positive_query_stress_increments=int(np.sum(increments[good]>1e-8)),
                            max_positive_query_stress_increment=float(np.max(increments[good],initial=0)),
                            quantile_receipt=receipt,scoring_receipt=score_receipt,cdf_check_receipt=cdf_receipt))
                    for alias,cid in aliases.items():
                        q,score,error=computed[cid] if cid is not None else (
                            np.full(len(query),np.nan),np.full(len(query),np.nan),'no eligible inner candidate')
                        for i,(_,observation) in enumerate(query.iterrows()):
                            row={name:observation[name] for name in ['row_id','dataset_id','group_id','log_stress','load_ratio','log_life','event']}
                            row.update(prefix)
                            row.update(seed=task['seed'],policy=policy,k=k,model=alias,candidate_id=cid,
                                cap=cap,log_lower=float(q[i]),log_score=float(score[i]),error=error,
                                fold_signature=fold['signature'],
                                pool_logstress_span=task.get('pool_logstress_span',np.nan),
                                informative_policy_episode=k in task.get('informative_policy_ks',[]))
                            rows.append(row)
            save_pickle(path,dict(freeze_sha256=self.freeze_hash,selection_sha256=selection_hash,task=task,cap=cap,fold=fold,
                model_aliases=aliases,predictions=rows,diagnostics=diagnostics,
                selections={p:a['selections'] for p,a in plan['plans'].items()},plan_receipt=plan['receipt']))
            print(f'outer cap{cap:g} {family} {ti+1}/{len(tasks)} {task["dataset_id"]} seed{task["seed"]}',flush=True)

    def combine(self,cap):
        from src.v3_design import POLICIES
        folder=RESULT/('outer_cap1e6' if cap==1e6 else 'outer_cap1e7')
        rows=[];selections=[];diagnostics=[];tasks=[]
        for path in sorted(folder.glob('task_*.pkl')):
            with path.open('rb') as f:r=pickle.load(f)
            if r['freeze_sha256']!=self.freeze_hash or r['selection_sha256']!=digest(RESULT/'selected.json'):
                raise RuntimeError('mixed outer freezes/selections')
            rows.extend(r['predictions']);tasks.append(r['task'])
            if set(r['model_aliases'])!=set(expected_model_aliases()):raise RuntimeError('model alias coverage changed')
            key=dict(dataset_id=r['task']['dataset_id'],group_id=r['task']['group_id'],seed=r['task']['seed'],cap=cap)
            for policy,selected in r['selections'].items():
                selections.extend({**key,**x,'policy':policy} for x in selected)
            diagnostics.extend(dict(**key,**x) for x in r['diagnostics'])
        assert len(tasks)==370 and len({(t['dataset_id'],t['seed']) for t in tasks})==370
        pd.DataFrame(rows).to_csv(folder/'predictions.csv',index=False)
        pd.DataFrame(selections).to_csv(folder/'selections.csv',index=False)
        write_json(folder/'prediction_diagnostics.json',diagnostics)
        write_json(folder/'run_receipt.json',dict(freeze_sha256=self.freeze_hash,cap=cap,tasks=tasks,
            predictions=len(rows),selections=len(selections),source_families=12,
            expected_model_aliases=expected_model_aliases(),expected_policies=list(POLICIES),
            prediction_csv_sha256=digest(folder/'predictions.csv'),selection_csv_sha256=digest(folder/'selections.csv')))


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['inner','select','outer','combine'])
    p.add_argument('--pairs',type=int,nargs='*');p.add_argument('--categories',nargs='*')
    p.add_argument('--family');p.add_argument('--cap',type=float,choices=[1e6,1e7],default=1e6)
    a=p.parse_args();e=Experiment()
    if a.stage=='inner':
        for i in a.pairs if a.pairs is not None else range(66):e.inner_pair(i,a.categories)
    elif a.stage=='select':e.select()
    elif a.stage=='outer':
        for family in [a.family] if a.family else e.design['outer_families']:e.outer_family(family,a.cap)
    else:e.combine(a.cap)


if __name__=='__main__':main()
