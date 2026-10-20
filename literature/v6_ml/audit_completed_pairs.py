"""Read-only phase6 inner-pair audit, excluding predictive scores and utilities.

Run from the repository with its venv Python. No fit, predict, selection, or
process-control function is called. Own local training pickles are inspected
only for identities, fixed parameters, and empty population support caches.
The set of complete pairs is captured before reading any candidate files.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import gzip
import hashlib
import json
import pickle
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SEAL = '25d1641a62c49cb8f969f907ac5a4dae7838393d3553fe711b13aced4049dc3e'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text())


def finite(value, name, lower=None, upper=None):
    value = float(value)
    assert np.isfinite(value), (name, value)
    assert lower is None or value >= lower, (name, value)
    assert upper is None or value <= upper, (name, value)
    return value


def main():
    started = datetime.now(timezone.utc).isoformat()
    frozen = load_json(ROOT/'protocols/v6/freeze.json')
    assert sha(ROOT/'protocols/v6/freeze.json') == SEAL
    for rel, value in frozen['sha256'].items():
        assert sha(ROOT/rel) == value, rel
    cohort = pd.read_csv(ROOT/'data/processed/v4/controlled_expansion/expanded441.csv')
    indexed = cohort.set_index('row_id')
    design = load_json(ROOT/'data/processed/v6/episode_design.json')
    grid = load_json(ROOT/'protocols/v6/grid.json')
    by_id = {c['candidate_id']: c for c in grid}
    dispatch_path = ROOT/'logs/v6/inner/dispatch_status.json'
    dispatch = load_json(dispatch_path)
    pair_status = []
    for path in sorted((ROOT/'logs/v6/inner').glob('pair_*.json')):
        state = load_json(path)
        pair_status.append(dict(pair_index=int(path.stem.split('_')[1]),
                                state=state, status_file_sha256=sha(path)))
    complete = [p for p in pair_status if p['state']['status'] == 'complete'
                and p['state'].get('returncode') == 0]
    assert complete, 'No complete pairs at snapshot'
    # All statistics below are numerical/identity diagnostics, never accuracy.
    maxima = defaultdict(list)
    errors = Counter()
    pair_reports = []
    folds = []
    start_messages = Counter()
    source_categories = Counter(c['category'] for c in grid)

    for entry in complete:
        ix = entry['pair_index']
        pair = design['excluded_family_pair_trainsets'][ix]
        excluded = sorted(pair['excluded_families'])
        train = cohort[~cohort.group_id.isin(excluded)].copy()
        train_csv = train.to_csv(index=False)
        signature = hashlib.sha256((SEAL+'|'+json.dumps(excluded)+'|'+train_csv).encode()).hexdigest()
        cache = ROOT/'work/v6/cache'/signature
        fold = load_json(cache/'fold.json')
        assert fold['signature'] == signature and fold['freeze_sha256'] == SEAL
        assert fold['training_ids'] == train.row_id.tolist() == pair['training_row_ids']
        assert fold['training_rows'] == len(train)
        assert sorted(fold['training_sources']) == sorted(train.group_id.unique())
        assert set(excluded).isdisjoint(train.group_id) and train.group_id.nunique() == 11
        assert 'cui_linked_campaign' in set(train.group_id)
        assert hashlib.sha256(train_csv.encode()).hexdigest() == fold['training_csv_sha256']
        with (cache/'references.pkl').open('rb') as f:
            refs, ref_receipts = pickle.load(f)
        assert set(refs) == {'pooled', 'hierarchical', 'curved_hierarchical', 'rfl'}
        assert all(r['success'] for r in ref_receipts.values())
        assert refs['rfl']._fallback is None
        assert len(refs['rfl']._posterior_cache) == 0
        h = refs['hierarchical']
        mean = np.array([h.params_[0]-h.params_[1]*h.center_[0]-h.params_[2]*h.center_[1],
                         h.params_[1], h.params_[2]])
        fit_hashes, student_gradients, gp_gradients = {}, [], []
        retry_count = 0
        for c in grid:
            cid = c['candidate_id']
            if c['implementation'] not in ('gp', 'student'):
                continue
            fp = cache/(cid+'_fit.json')
            assert fp.exists() and not (cache/(cid+'_failure.json')).exists(), cid
            fit = load_json(fp)
            assert fit['candidate'] == c and fit['success']
            successful = [a for a in fit['attempts'] if a['success']]
            assert successful
            r = successful[-1]['fit_receipt']
            assert r['success']
            retry_count += len(fit['attempts']) > 1
            if c['implementation'] == 'gp':
                assert r['n_train'] == len(train) and r['n_source_families'] == 11
                assert r['n_conditions'] == train.dataset_id.nunique()
                np.testing.assert_array_equal(r['mean_coefficients'], mean)
                assert r['noise_sd'] == c['spec']['noise_multiplier']*h.sigma_
                assert r['kernel']['condition_intercept_sd'] == c['spec']['config']['condition_intercept_sd']*h.tau_
                assert r['hyperparameters_optimized_in_fit'] is False
                g = finite(r['latent_mode']['gradient_inf'], 'GP population gradient', 0, 1e-7)
                gp_gradients.append(g)
            else:
                assert r['training_rows'] == len(train)
                assert r['training_conditions'] == train.dataset_id.nunique()
                assert r['training_sources'] == sorted(train.group_id.unique())
                stress = train.log_stress.to_numpy(float)
                assert r['stress_center_train'] == float(stress.mean())
                assert r['stress_sd_train'] == float(stress.std())
                ratio = train.load_ratio.to_numpy(float)
                median = float(np.median(ratio[np.isfinite(ratio)]))
                assert r['ratio_median_train'] == median
                assert r['ratio_center_train'] == float(np.where(np.isfinite(ratio), ratio, median).mean())
                knots = np.quantile((stress-stress.mean())/stress.std(), [1/3, 2/3]) if c['config']['mean'] == 'two_knots' else np.array([])
                np.testing.assert_array_equal(r['knots_standardized_log_stress_train'], knots)
                assert r['unit_row_likelihood'] and r['condition_marginals_summed']
                assert not r['population_parameter_uncertainty_integrated']
                assert r['target_intercept_uncertainty_integrated'] and r['natural_scatter_integrated']
                assert not r['target_slope_or_scatter_updated']
                g = finite(r['gradient_inf'], 'Student population raw gradient', 0)
                student_gradients.append(dict(candidate=cid, gradient_inf=g,
                                              at_bound=r['at_bound']))
                finite(r['max_quadrature_relative_error'], 'Student population quadrature', 0, r['quadrature_tolerance'])
                finite(r['max_tail_mass_bound'], 'Student population tail', 0, r['quadrature_tolerance'])
                assert 0 < r['max_quadrature_nodes'] <= 65536
                for start in r['starts']:
                    start_messages[start['message']] += 1
                with (cache/(cid+'.pkl')).open('rb') as f:
                    model = pickle.load(f)
                assert len(model._posterior_cache) == 0
                # JSON stores tuple bounds as lists; compare canonical values.
                assert json.loads(json.dumps(model.fit_receipt_)) == r
            fit_hashes[fp.name] = sha(fp)
        for cid in ('gp00', 'gp64', 'gp65'):
            with (cache/(cid+'.pkl')).open('rb') as f:
                model = pickle.load(f)
            assert model.train_.row_id.tolist() == train.row_id.tolist()
            assert len(model._support_cache) == 0
            np.testing.assert_array_equal(model.mean_coef_, mean)
        folds.append(dict(pair_index=ix, signature=signature, excluded_families=excluded,
            training_rows=len(train), training_families=11, training_conditions=train.dataset_id.nunique(),
            training_only_Cui_retained=True, reference_population_fits_success=True, RFL_population_has_no_fallback=True,
            GP_receipts_checked=len(gp_gradients), GP_max_population_gradient_inf=max(gp_gradients),
            Student_receipts_checked=len(student_gradients), Student_population_gradients=student_gradients,
            population_retries=retry_count, population_support_caches_empty=True,
            training_only_standardization_and_hierarchical_GP_mean_scatter_checked=True,
            fit_receipt_sha256=fit_hashes))

        tasks = [t for t in design['inner_episode_templates'] if t['group_id'] in excluded]
        expected = {(t['group_id'], t['dataset_id'], t['seed'], k): t for t in tasks for k in (0,3)}
        directory = ROOT/'results/v6/inner'/f'pair_{ix:02d}'
        assert {p.stem for p in directory.glob('*.csv')} == set(by_id)
        files, availability = {}, defaultdict(Counter)
        joint_rows = joint_fallbacks = scalar_norms = 0
        common_supports = {}
        for c in grid:
            cid = c['candidate_id']; path = directory/(cid+'.csv')
            receipt_path = path.with_suffix('.json'); numeric_path = path.with_suffix('.numerics.json.gz')
            assert receipt_path.exists() and numeric_path.exists()
            rec = load_json(receipt_path)
            assert rec['freeze_sha256'] == SEAL and rec['candidate'] == c and rec['pair_index'] == ix
            assert sorted(rec['excluded_families']) == excluded and rec['fold'] == fold
            assert sha(path) == rec['csv_sha256'] and sha(numeric_path) == rec['numerics_sha256']
            # Explicit allow-list: no predictive mean_log_score or outer quantities.
            columns = ['candidate_id','category','ordinal','pair_index','validation_family','dataset_id','seed','k',
                       'n_query','fold_signature','support_ids_sha256','support_set_sha256','n_support_failure','available','error']
            frame = pd.read_csv(path, usecols=columns).fillna({'error':''})
            assert len(frame) == len(expected) == rec['episodes']
            assert int(frame.available.sum()) == rec['available']
            assert set(zip(frame.validation_family,frame.dataset_id,frame.seed,frame.k)) == set(expected)
            with gzip.open(numeric_path,'rt') as f:
                sidecar = json.load(f)
            assert len(sidecar) == len(frame)
            for row, numeric in zip(frame.itertuples(), sidecar):
                key = (row.validation_family,row.dataset_id,row.seed,row.k); task = expected[key]
                assert row.candidate_id == cid and row.category == c['category'] and row.ordinal == c['ordinal']
                assert row.pair_index == ix and row.fold_signature == signature and row.n_query == len(task['query_ids'])
                assert all(numeric[k] == getattr(row,k) for k in ('validation_family','dataset_id','seed','k','available','error'))
                order = sorted(task['pool_ids'],key=lambda rid:hashlib.sha256(f'v3|{row.seed}|random|{rid}'.encode()).hexdigest())[:row.k]
                order_hash = hashlib.sha256(json.dumps(order).encode()).hexdigest()
                set_hash = hashlib.sha256(json.dumps(sorted(order)).encode()).hexdigest()
                assert (row.support_ids_sha256,row.support_set_sha256) == (order_hash,set_hash)
                assert not set(order)&set(task['query_ids'])
                supports = indexed.loc[order]
                failures = int(((supports.event==1)&(supports.log_life<=6.)).sum())
                assert row.n_support_failure == failures
                if key in common_supports: assert common_supports[key] == (order_hash,set_hash)
                common_supports[key] = (order_hash,set_hash)
                availability[c['category']]['available' if row.available else 'unavailable'] += 1
                if not row.available:
                    errors[row.error] += 1
                    assert c['category'] == 'matched_intercept' and row.k == 3 and failures == 0
                    continue
                r = numeric['receipt']; assert 'receipt_error' not in r
                if c['category'] == 'gp':
                    assert r['success'] and r['n_selected_support'] == row.k and r['n_train'] == len(train)
                    assert r['n_query'] == row.n_query and r['fixed_hyperparameters']
                    assert r['population_and_selected_support_joint_Laplace'] and not r['quantile_is_R90C90']
                    maxima['GP_target_gradient_inf'].append(finite(r['gradient_inf'],'GP target gradient',0,1e-7))
                    finite(r['min_latent_variance'],'GP minimum latent variance',0)
                elif c['category'] == 'student':
                    assert r['selected_support_n'] == row.k and r['selected_support_failures'] == failures
                    assert r['query_outcomes_used_only_for_scoring'] and not r['query_outcomes_used_for_model_or_support_update']
                    assert not r['population_parameter_uncertainty_integrated']
                    maxima['Student_target_quadrature_relative_error'].append(finite(r['quadrature_relative_error'],'Student target quadrature',0,2e-8))
                    maxima['Student_target_omitted_tail_relative_bound'].append(finite(r['omitted_tail_relative_bound'],'Student target tail',0,2e-8))
                elif c['category'] == 'joint_rfl':
                    assert r['success'] and r['n_selected_support'] == row.k and r['n_query'] == row.n_query
                    assert not r['quantile_is_R90C90']
                    if row.k == 0:
                        assert r['k0_analytic_convolution'] and not r['scalar_reduction']
                    else:
                        assert not r['query_outcomes_used_for_fit_or_support_cache'] and not r['numerator_integrals_cached']
                        assert r['omitted_mass_bound_conditional_on_fixed_Gamma_rule']
                        assert not r['target_posterior_is_Laplace'] and not r['population_parameters_uncertainty_integrated']
                        assert not r['resolution_difference_is_analytic_error_bound']
                        omitted = finite(r['posterior_omitted_mass_bound'],'joint omitted posterior mass',0,2e-10)
                        maxima['joint_posterior_omitted_mass_bound'].append(omitted)
                        fallback = r['evidence_ratio_fallback_rows']
                        assert len(set(fallback)) == len(fallback) and set(fallback) <= set(range(row.n_query))
                        assert r['posterior_mixture_rows'] + len(fallback) == row.n_query
                        for field in ('u_log_score_resolution_difference','v_log_score_resolution_difference',
                                      'relative_predictive_likelihood_tail_bound','predictive_log_score_tail_error_bound'):
                            a = r[field]; assert len(a) == row.n_query
                            for j,val in enumerate(a):
                                if j not in fallback:
                                    maxima['joint_'+field].append(finite(val,field,0,2e-6))
                        if fallback:
                            fr = r['evidence_ratio_fallback_receipt']; assert fr['success']
                            assert len(fr['numerator_receipts']) == len(fallback)
                            for nr in fr['numerator_receipts']:
                                finite(nr['tail_mass_bound_v'],'fallback v tail',0,1e-10)
                                finite(nr['conditional_u_tail_bound_weighted'],'fallback u tail',0,1e-10)
                                finite(nr['evidence_resolution_difference'],'fallback resolution',0,2e-6)
                        joint_rows += row.n_query; joint_fallbacks += len(fallback)
                elif 'scalar_target_posterior' in r:
                    p = r['scalar_target_posterior']
                    assert abs(finite(p['weight_sum'],'scalar posterior normalization',0)-1) <= 1e-12
                    assert p['nodes'] > 0
                    scalar_norms += 1
            files[path.name] = dict(csv=sha(path),receipt=sha(receipt_path),numerics=sha(numeric_path))
        assert Counter({cat:sum(values.values())//len(expected) for cat,values in availability.items()}) == source_categories
        pair_reports.append(dict(pair_index=ix, excluded_families=excluded, candidates_checked=len(files),
            expected_episodes_per_candidate=len(expected), distinct_shared_episode_keys=len(common_supports),
            total_candidate_episodes=len(files)*len(expected), availability_by_category={k:dict(v) for k,v in availability.items()},
            reconstructed_common_random_supports_and_capped_failures=True, joint_query_numeric_rows=joint_rows,
            joint_evidence_ratio_fallback_rows=joint_fallbacks, scalar_weight_sums_checked=scalar_norms,
            evidence_file_sha256=files))

    transient = []
    complete_ids = {r['pair_index'] for r in complete}
    for directory in sorted((ROOT/'results/v6/inner').glob('pair_*')):
        ix = int(directory.name.split('_')[1])
        if ix in complete_ids: continue
        csvs = list(directory.glob('*.csv'))
        transient.append(dict(pair_index=ix, snapshot='not audited as complete at start',csv_files=len(csvs),
            committed_triples=sum(p.with_suffix('.json').exists() and p.with_suffix('.numerics.json.gz').exists() for p in csvs),
            temporary_files=[p.name for p in directory.glob('*.tmp')]))
    for rel,value in frozen['sha256'].items(): assert sha(ROOT/rel) == value,rel
    report = dict(status='PASS_COMPLETED_INNER_PAIR_IDENTITY_AND_RECORDED_NUMERICS_WITH_LIMITS',
        started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(), freeze_sha256=SEAL,
        all21_frozen_files_unchanged=True, script_sha256=sha(__file__),
        completed_pairs_at_start=sorted(complete_ids), pair_status_snapshot=pair_status,
        dispatch_snapshot=dispatch, dispatch_sha256_at_start=sha(dispatch_path),
        completed_folds=folds, completed_pairs=pair_reports, transient_partial_pairs=transient,
        unavailable_error_counts=dict(errors), Student_start_termination_messages=dict(start_messages),
        numerical_diagnostic_maxima={k:dict(max=max(v),observations=len(v)) for k,v in maxima.items()},
        explicit_limits=[
            'A complete-pair snapshot of inner tuning arithmetic, not the complete phase6 benchmark or a scientific benefit result.',
            'Student population success follows the frozen L-BFGS-B criterion: relative objective reduction may terminate before raw gradient <=1e-5. Raw gradients and bound flags remain visible; no refit or candidate choice was made.',
            'Joint scoring sidecars retain resolution/tail diagnostics, not full posterior weight arrays or normalization sums. Their actual joint-array normalization cannot be independently recomputed from these persisted receipts. Scalar posterior normalization sums are directly checked.',
            'Joint omitted-mass bounds are conditional on the fixed 96-node fatigue-limit rule. Coarse/fine rule differences are numerical diagnostics, not rigorous continuous-quadrature error bounds.',
            'No joint quantile/CDF receipts exist in this inner-score stage. Those outer prediction checks are still pending.',
            'Working source-family exclusion is verified computationally. It does not establish independent physical specimens/builds or validate provenance of all original numeric fatigue coordinates.',
            'Historically inspected outcomes remain reused exploratory data. No untouched prospective validation or R90C90 confidence statement follows.'
        ],
        boundaries=dict(no_fits=True,no_predict_calls=True,no_model_selection=True,no_outer_result_or_utility_read=True,
            no_predictive_score_columns_read=True,no_frozen_edits=True,no_process_control=True,
            cache_pickles='Own locally generated checkpoints inspected for metadata, IDs and cached state only'))
    output = ROOT/'literature/v6_ml/actual_completed_pairs_audit.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], complete_pairs=sorted(complete_ids),
        candidates_checked=sum(r['candidates_checked'] for r in pair_reports),
        candidate_episodes_checked=sum(r['total_candidate_episodes'] for r in pair_reports),
        numerical_maxima=report['numerical_diagnostic_maxima'], unavailable_errors=dict(errors)),indent=2))


if __name__ == '__main__':
    main()
