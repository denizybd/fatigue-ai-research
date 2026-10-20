"""Prepare nested source-family episodes before phase6 predictor evaluation.

This does not fit a model or select hyperparameters. The numerical outcomes
were seen in historical analyses; the new method evaluation is exploratory.
"""
from pathlib import Path
import hashlib
import json
import math
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/processed/v6'
INPUT=ROOT/'data/processed/v4/controlled_expansion/expanded441.csv'
INNER_SEEDS=[101,202,303]
OUTER_SEEDS=list(range(10))


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def order(ids,seed,did):
    return sorted(map(str,ids),key=lambda rid:hashlib.sha256(
        f'v3-common-query|{seed}|{did}|{rid}'.encode()).hexdigest())


def prepare():
    BASE.mkdir(parents=True,exist_ok=True)
    d=pd.read_csv(INPUT)
    assert len(d)==441 and d.row_id.is_unique and d.group_id.nunique()==13 and d.dataset_id.nunique()==48
    assert d.event.sum()==380 and d[d.event==0].log_life.min()>=6
    assert d[['log_stress','load_ratio','log_life','event']].notna().all().all()
    conditions=[];outer=[];inner=[]
    for did,c in d.groupby('dataset_id',sort=True):
        assert c.group_id.nunique()==1
        n=len(c);nq=max(3,math.floor(.4*n));ks=[0]+[k for k in [3,5,10] if k<=n-nq]
        ok=3 in ks
        conditions.append(dict(dataset_id=did,group_id=c.group_id.iloc[0],rows=n,
            stress_levels=c.log_stress.nunique(),query_n=nq,pool_n=n-nq,ks=ks,eligible_k3=ok))
        if not ok:continue
        for seeds,storage,phase in [(OUTER_SEEDS,outer,'outer'),(INNER_SEEDS,inner,'inner')]:
            for seed in seeds:
                ranked=order(c.row_id,seed,did)
                pool=c.set_index('row_id').loc[ranked[nq:]]
                span=float(pool.log_stress.max()-pool.log_stress.min())
                storage.append(dict(dataset_id=did,group_id=c.group_id.iloc[0],phase=phase,
                    seed=seed,query_ids=ranked[:nq],pool_ids=ranked[nq:],ks=ks,
                    pool_logstress_span=span,
                    informative_policy_ks=[k for k in ks if k>0 and k<len(pool) and span>=.05]))
    eligible=sorted({x['group_id'] for x in outer})
    assert len(eligible)==12 and len(outer)==370 and len(inner)==111
    assert sum(x['rows'] for x in conditions if x['eligible_k3'])==396
    pairs=[]
    for i,f in enumerate(eligible):
        for g in eligible[i+1:]:
            train=d[~d.group_id.isin([f,g])]
            pairs.append(dict(excluded_families=[f,g],training_row_ids=train.row_id.tolist(),
                training_rows=len(train),training_families=train.group_id.nunique()))
    assert len(pairs)==66
    for t in outer+inner:
        assert not set(t['query_ids'])&set(t['pool_ids'])
        assert set(t['query_ids']+t['pool_ids'])==set(d[d.dataset_id.eq(t['dataset_id'])].row_id)
    config=dict(source_sha256=digest(INPUT),preparation_code_sha256=digest(__file__),
        source_rows=441,source_conditions=48,source_families=13,
        primary_eligible_rows=396,primary_eligible_conditions=37,outer_families=eligible,
        train_only_family='cui_linked_campaign',train_only_rows=13,
        noneligible_rows=45,noneligible_conditions=11,
        outer_tasks=outer,inner_episode_templates=inner,excluded_family_pair_trainsets=pairs,
        primary_support_cap=1e6,sensitivity_support_cap=1e7,
        all_recorded_censor_endpoints_ge_primary_cap=True,
        model_or_grid_fit_performed=False,
        status='Prepared data episodes only; final method/grid/protocol hashes required before first fit',
        independence='Conservative source families, not verified physical specimen/build independence.',
        timing='Existing numerical outcomes previously seen; exploratory method comparison with source-separated tuning/evaluation.')
    (BASE/'episode_design.json').write_text(json.dumps(config,indent=2)+'\n')
    pd.DataFrame(conditions).assign(ks=lambda x:x.ks.apply(json.dumps)).to_csv(BASE/'condition_eligibility.csv',index=False)
    counts=d.groupby('group_id').agg(rows=('row_id','size'),conditions=('dataset_id','nunique')).reset_index()
    counts['eligible_for_primary_outer']=counts.group_id.isin(eligible)
    counts.to_csv(BASE/'family_counts.csv',index=False)
    print(json.dumps({k:v for k,v in config.items() if k not in ['outer_tasks','inner_episode_templates','excluded_family_pair_trainsets','outer_families']},indent=2))


if __name__=='__main__':prepare()
