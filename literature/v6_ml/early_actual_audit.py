"""Read-only lineage/numerics audit; never reads predictive score/utility columns.

No fit/predict/selection method is called. Pickles are own locally generated
training checkpoints, loaded only to inspect immutable attributes and identities.
"""
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import pickle
import sys
from collections import Counter,defaultdict
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    sealpath=ROOT/'protocols/v6/freeze.json'
    seal=json.loads(sealpath.read_text());sealhash=sha(sealpath)
    assert sealhash=='25d1641a62c49cb8f969f907ac5a4dae7838393d3553fe711b13aced4049dc3e'
    assert all(sha(ROOT/p)==v for p,v in seal['sha256'].items())
    cohort=pd.read_csv(ROOT/'data/processed/v4/controlled_expansion/expanded441.csv')
    design=json.loads((ROOT/'data/processed/v6/episode_design.json').read_text())
    grid={c['candidate_id']:c for c in json.loads((ROOT/'protocols/v6/grid.json').read_text())}
    fold_reports=[];folder_by_signature={}
    for path in sorted((ROOT/'work/v6/cache').glob('*/fold.json')):
        f=json.loads(path.read_text());excluded=sorted(f['excluded_families'])
        if len(excluded)!=2:continue  # The early audit targets inner pair fits.
        train=cohort[~cohort.group_id.isin(excluded)].copy()
        assert train.row_id.tolist()==f['training_ids'] and len(train)==f['training_rows']
        assert set(train.group_id)==set(f['training_sources']) and len(set(train.group_id))==11
        assert not set(excluded)&set(train.group_id)
        assert 'cui_linked_campaign' in set(train.group_id)
        csv=train.to_csv(index=False)
        assert hashlib.sha256(csv.encode()).hexdigest()==f['training_csv_sha256']
        signature=hashlib.sha256((sealhash+'|'+json.dumps(excluded)+'|'+csv).encode()).hexdigest()
        assert signature==path.parent.name==f['signature'] and f['freeze_sha256']==sealhash
        folder_by_signature[signature]=f
        expected_pair=next(p for p in design['excluded_family_pair_trainsets'] if sorted(p['excluded_families'])==excluded)
        assert train.row_id.tolist()==expected_pair['training_row_ids']
        refpath=path.parent/'references.pkl'
        if not refpath.exists():continue
        with refpath.open('rb') as handle:refs,reference_receipts=pickle.load(handle)
        hierarchy=refs['hierarchical'];p=hierarchy.params_;center=hierarchy.center_
        mean=np.asarray([p[0]-p[1]*center[0]-p[2]*center[1],p[1],p[2]])
        gpcount=0;maxcoef=0.;maxnoise=0.;maxcondition=0.;gpgrad=[]
        for fitpath in sorted(path.parent.glob('gp*_fit.json')):
            record=json.loads(fitpath.read_text());c=record['candidate'];assert c==grid[c['candidate_id']]
            attempt=next(a for a in reversed(record['attempts']) if a['success'])
            receipt=attempt['fit_receipt'];spec=c['spec']
            assert receipt['success'] and receipt['n_train']==len(train)
            assert receipt['n_source_families']==11 and receipt['n_conditions']==train.dataset_id.nunique()
            coeferror=float(np.max(np.abs(np.asarray(receipt['mean_coefficients'])-mean)))
            noiseerror=abs(receipt['noise_sd']-spec['noise_multiplier']*hierarchy.sigma_)
            conditionerror=abs(receipt['kernel']['condition_intercept_sd']-spec['config']['condition_intercept_sd']*hierarchy.tau_)
            assert max(coeferror,noiseerror,conditionerror)<1e-12
            assert not receipt['hyperparameters_optimized_in_fit']
            gpgrad.append(receipt['latent_mode']['gradient_inf'])
            maxcoef=max(maxcoef,coeferror);maxnoise=max(maxnoise,noiseerror);maxcondition=max(maxcondition,conditionerror);gpcount+=1
        representative=[]
        for cid in ['gp00','gp64','gp65']:
            modelpath=path.parent/(cid+'.pkl')
            if not modelpath.exists():continue
            with modelpath.open('rb') as handle:model=pickle.load(handle)
            assert model.train_.row_id.tolist()==train.row_id.tolist()
            assert not set(model.train_.row_id)&set(cohort[cohort.group_id.isin(excluded)].row_id)
            assert len(model._support_cache)==0
            np.testing.assert_array_equal(model.mean_coef_,mean)
            representative.append(cid)
        fold_reports.append(dict(signature=signature,excluded_families=excluded,training_rows=len(train),
            training_sources=11,training_conditions=train.dataset_id.nunique(),training_only_Cui_retained=True,
            references={name:bool(r['success']) for name,r in reference_receipts.items()},
            gp_fit_receipts_checked=gpcount,max_GP_mean_conversion_error=maxcoef,
            max_GP_noise_reference_error=maxnoise,max_GP_condition_reference_error=maxcondition,
            max_GP_population_gradient_inf=max(gpgrad,default=None),
            representative_GP_pickles_training_IDs_and_empty_support_cache_checked=representative))
    pair_reports=[];allnumeric=defaultdict(list);allerrors=Counter()
    # Do not read mean_log_score, log_lower, utilities or any outer result.
    cols=['candidate_id','category','pair_index','validation_family','dataset_id','seed','k','n_query',
          'fold_signature','support_ids_sha256','support_set_sha256','n_support_failure','available','error']
    numeric_keys={'gradient_inf','quadrature_relative_error','tail_mass_bound','tail_mass_bound_v',
        'conditional_u_tail_bound_weighted','evidence_resolution_difference',
        'u_resolution_log_evidence_difference','max_quantile_log10_resolution_difference',
        'max_cdf_resolution_difference'}
    def numerics(node):
        if isinstance(node,dict):
            for k,v in node.items():
                if k in numeric_keys and isinstance(v,(int,float)) and np.isfinite(v):allnumeric[k].append(float(v))
                elif k=='receipt_error':allerrors['numeric_receipt:'+str(v)]+=1
                elif isinstance(v,(dict,list)):numerics(v)
        elif isinstance(node,list):
            for v in node:numerics(v)
    for directory in sorted((ROOT/'results/v6/inner').glob('pair_*')):
        pairindex=int(directory.name.split('_')[1]);pair=design['excluded_family_pair_trainsets'][pairindex]
        tasks=[t for t in design['inner_episode_templates'] if t['group_id'] in pair['excluded_families']]
        expected={(t['group_id'],t['dataset_id'],t['seed'],k):t for t in tasks for k in [0,3]}
        hashes={};categories=defaultdict(lambda:Counter());filehashes={};unavailable=[];times=[]
        for path in sorted(directory.glob('*.csv')):
            rp=path.with_suffix('.json');npth=path.with_suffix('.numerics.json.gz')
            if not rp.exists() or not npth.exists():continue
            receipt=json.loads(rp.read_text())
            assert receipt['freeze_sha256']==sealhash and sha(path)==receipt['csv_sha256'] and sha(npth)==receipt['numerics_sha256']
            assert sorted(receipt['excluded_families'])==sorted(pair['excluded_families'])
            frame=pd.read_csv(path,usecols=cols).fillna({'error':''})
            keys=set(zip(frame.validation_family,frame.dataset_id,frame.seed,frame.k))
            assert keys==set(expected) and len(frame)==len(expected)
            for row in frame.itertuples():
                key=(row.validation_family,row.dataset_id,row.seed,row.k);task=expected[key]
                ordered=sorted(task['pool_ids'],key=lambda rid:hashlib.sha256(f'v3|{int(row.seed)}|random|{rid}'.encode()).hexdigest())[:row.k]
                orderhash=hashlib.sha256(json.dumps(ordered).encode()).hexdigest()
                sethash=hashlib.sha256(json.dumps(sorted(ordered)).encode()).hexdigest()
                assert row.support_ids_sha256==orderhash and row.support_set_sha256==sethash
                assert row.n_query==len(task['query_ids']) and row.fold_signature in folder_by_signature
                selected=cohort.set_index('row_id').loc[ordered]
                failures=int(((selected.event==1)&(selected.log_life<=6.)).sum())
                assert row.n_support_failure==failures
                if key in hashes:assert hashes[key]==(orderhash,sethash)
                hashes[key]=(orderhash,sethash)
                categories[row.category]['available' if row.available else 'unavailable']+=1
                if not row.available:
                    unavailable.append(dict(candidate=row.candidate_id,category=row.category,k=row.k,
                        selected_failures=failures,error=row.error))
                    allerrors[row.error]+=1
            with gzip.open(npth,'rt') as handle:sidecar=json.load(handle)
            assert len(sidecar)==len(frame)
            numerics(sidecar)
            filehashes[path.name]=dict(csv=sha(path),numerics=sha(npth),receipt=sha(rp))
            times.append(float(receipt['elapsed']))
        pair_reports.append(dict(pair_index=pairindex,excluded_families=pair['excluded_families'],
            completed_candidate_files=len(filehashes),checked_episode_keys=len(hashes),
            available_counts_by_category={k:dict(v) for k,v in categories.items()},
            unavailable_episodes=unavailable,common_support_hashes_match_across_all_candidates=True,
            independently_reconstructed_random_supports_and_capped_failure_counts=True,
            candidate_total_elapsed_seconds_min=min(times,default=None),
            candidate_total_elapsed_seconds_max=max(times,default=None),evidence_file_sha256=filehashes))
    assert all(sha(ROOT/p)==v for p,v in seal['sha256'].items())
    report=dict(status='PASS_EARLY_READ_ONLY_SNAPSHOT',checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        seal_sha256=sealhash,all21_frozen_files_unchanged=True,
        pipeline=json.loads((ROOT/'logs/v6/pipeline_status.json').read_text()),
        dispatcher=json.loads((ROOT/'logs/v6/inner/dispatch_status.json').read_text()),
        folds=fold_reports,inner_pairs=pair_reports,
        numerical_diagnostic_maxima={k:dict(max=max(v),observations=len(v)) for k,v in allnumeric.items()},
        unavailable_error_counts=dict(allerrors),
        audit_boundaries=dict(no_model_fits_or_predict_calls=True,no_launch_or_process_control=True,
            no_frozen_edits=True,no_predictive_mean_log_scores_read=True,no_outer_result_or_utility_read=True,
            no_config_or_model_choice=True,cache_pickles='Local own-code training checkpoints inspected for attributes/IDs only'),
        limitation='An early snapshot, not full-run convergence/coverage proof or scientific result validation.')
    (ROOT/'literature/v6_ml/early_actual_run_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],folds_checked=len(fold_reports),
        GP_fit_receipts_checked=sum(f['gp_fit_receipts_checked'] for f in fold_reports),
        completed_candidate_files_checked=sum(p['completed_candidate_files'] for p in pair_reports),
        unavailable_errors=dict(allerrors),numeric_maxima=report['numerical_diagnostic_maxima']),indent=2))


if __name__=='__main__':main()
