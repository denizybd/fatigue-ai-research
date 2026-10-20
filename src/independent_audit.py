"""Independent post-result audit, not another source of experimental evidence.

No imports from run_experiment, evaluation, features, or summarize. Risk counts
are reconstructed directly from saved rows using scalar interval reasoning.
Selected numerical replays import the frozen estimator only; that replay is
explicitly not an independent implementation of the statistical model.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import statistics
import sys
import time

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
NUMERIC = ['log_stress', 'load_ratio', 'direction', 'power', 'scan_speed',
           'hatch_space', 'layer_thickness', 'heat_temperature', 'heat_time']
CATEGORICAL = ['surface', 'thermal']
KEY = ['scheme', 'seed', 'group_id', 'model', 'bound', 'policy']


def avg(values):
    values = [float(x) for x in values if not math.isnan(float(x))]
    return sum(values) / len(values) if values else float('nan')


def quantile_linear(values, level):
    a = sorted(float(x) for x in values)
    index = (len(a) - 1) * level
    lo, hi = int(math.floor(index)), int(math.ceil(index))
    return a[lo] + (index-lo)*(a[hi]-a[lo])


def finite_order(values, alpha=.1):
    a = sorted(float(x) for x in values)
    order = int(math.ceil((len(a)+1)*(1-alpha)-1e-12))
    return a[order-1] if order <= len(a) else float('inf')


def reconstruct_encoder(train):
    raw = train[NUMERIC].to_numpy(float)
    medians = [float(np.median(col[np.isfinite(col)])) if np.isfinite(col).any()
               else 0. for col in raw.T]
    imputed = np.where(np.isfinite(raw), raw, medians)
    means = imputed.mean(0)
    scales = imputed.std(0)
    scales[scales < 1e-8] = 1.
    categories = {c: sorted(set(train[c].fillna('unknown').astype(str))) + ['__unseen__']
                  for c in CATEGORICAL}
    names = NUMERIC + [f'{x}_missing' for x in NUMERIC]
    names += [f'{c}={v}' for c in CATEGORICAL for v in categories[c]]
    return {'mode': 'rich', 'numeric': NUMERIC, 'median': medians,
            'mean': means.tolist(), 'sd': scales.tolist(),
            'categories': categories, 'names': names}


def encode(frame, enc):
    a = frame[enc['numeric']].to_numpy(float)
    missing = ~np.isfinite(a)
    z = (np.where(missing, enc['median'], a)-enc['mean'])/enc['sd']
    parts = [z, missing.astype(float)]
    for key, cats in enc['categories'].items():
        vals = frame[key].fillna('unknown').astype(str).tolist()
        vals = [v if v in cats else '__unseen__' for v in vals]
        parts.append(np.array([[v == c for c in cats] for v in vals], float))
    return np.concatenate(parts, axis=1)


def bool_value(x):
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if str(x).lower() in ['true', '1']:
        return True
    if str(x).lower() in ['false', '0']:
        return False
    raise ValueError(f'Unrecognized boolean {x}')


def scalar_metrics(rows, accepted, policy):
    first = rows.iloc[0]
    out = {k: first[k] for k in ['scheme', 'seed', 'group_id', 'model', 'bound']}
    out['policy'] = policy
    selected = rows.loc[np.asarray(accepted, bool)]
    n, m = len(rows), len(selected)
    for k in [1., 2.]:
        d = u = 0
        for rec in selected.itertuples(index=False):
            exceeds = float(rec.log_lower) > float(rec.log_life) + math.log10(k)
            d += int(exceeds and int(rec.event) == 1)
            u += int(exceeds and int(rec.event) == 0)
        prefix = '' if k == 1 else 'severe_'
        out.update({prefix+'n': n, prefix+'accepted': m,
                    prefix+'availability': m/n if n else float('nan'),
                    prefix+'known_danger': d, prefix+'unknown_runouts': u,
                    prefix+'risk_lower': d/m if m else float('nan'),
                    prefix+'risk_upper': (d+u)/m if m else float('nan')})
        out[prefix+'cohort_violation_lower'] = float(d>0) if m else float('nan')
        out[prefix+'cohort_violation_upper'] = float(d+u>0) if m else float('nan')
    med = lambda xs: float(statistics.median(xs)) if len(xs) else float('nan')
    out['runout_fraction'] = avg(selected.runout)
    out['median_log_stress'] = med(selected.log_stress.tolist())
    out['conservatism_decades'] = med((selected.mu-selected.log_lower).tolist())
    out['median_log_lower'] = med(selected.log_lower.tolist())
    out['zero_bound_fraction'] = avg([math.isinf(v) and v < 0 for v in selected.log_lower])
    out['increasing_life_with_stress_fraction'] = avg(selected.stress_slope > 0)
    failures = selected[selected.event == 1]
    errs = (failures.mu-failures.log_life).tolist()
    out['failure_mae'] = avg(abs(x) for x in errs)
    out['failure_rmse'] = math.sqrt(avg(x*x for x in errs)) if errs else float('nan')
    return out


def independent_cells(pred):
    all_cells = []
    for key, rows in pred.groupby(['scheme','seed','group_id','model','bound'], sort=True):
        all_cells.append(scalar_metrics(rows, [True]*len(rows), 'all'))
        if (key[3],key[4]) != ('linear','endpoint_pooled'):
            continue
        for score in ['distance','instability','combined']:
            for fraction in [.5,.8]:
                policy = f'operational_{score}_{fraction}'
                all_cells.append(scalar_metrics(rows,
                    [bool_value(v) for v in rows[f'accept_{score}_{fraction}']], policy))
                count = int(math.ceil(fraction*len(rows)))
                tie = [int(hashlib.sha256(f'{rid}|{key[1]}'.encode()).hexdigest()[:16],16)
                       for rid in rows.row_id]
                order = sorted(range(len(rows)), key=lambda i: (float(rows[score].iloc[i]),tie[i]))
                chosen = set(order[:count])
                all_cells.append(scalar_metrics(rows,
                    [i in chosen for i in range(len(rows))], f'matched_{score}_{fraction}'))
        for fraction in [.5,.8]:
            realizations=[]
            for j in range(20):
                permutation=np.random.default_rng(int(key[1])+10000+j).permutation(len(rows))
                chosen=set(permutation[:int(math.ceil(fraction*len(rows)))])
                realizations.append(scalar_metrics(rows,
                    [i in chosen for i in range(len(rows))],f'matched_random_{fraction}'))
            item=realizations[0].copy()
            for name in item:
                if name not in KEY:
                    item[name]=avg(v[name] for v in realizations)
            all_cells.append(item)
    return pd.DataFrame(all_cells)


def comparable(a,b, atol=2e-10):
    return bool(np.allclose(np.asarray(a,float),np.asarray(b,float),atol=atol,rtol=atol,equal_nan=True))


def run_audit(folder='results/primary', replay=True):
    start=time.time()
    out=ROOT/'results';out.mkdir(exist_ok=True)
    base=ROOT/folder
    required=['run_receipt.json','predictions.csv','source_seed_metrics.csv','summary.csv','paired_contrasts.csv']
    for name in required:
        if not (base/name).exists():
            raise FileNotFoundError(f'Await completed experiment and summary: {base/name}')
    report={'audit_date':'2026-10-20','experiment_folder':folder,'checks':[],
            'failures':[],'warnings':[], 'scope':{
                'all_folds':'split/source-family integrity, training-only encoder reconstruction, distance thresholds, acceptance flags, row identity/coverage',
                'all_saved_metrics':'scalar risk/utility recomputation; no import of root evaluation/summarize',
                'sampled_replay':'first heldout source seed0 and first multi-DOI family seed42; estimator imported only for numerical replay',
                'excluded_claims':'No new experimental data, independent external validation, or independent estimator implementation'}}
    def check(name, condition, detail=None):
        item={'name':name,'passed':bool(condition)}
        if detail is not None:item['detail']=detail
        report['checks'].append(item)
        if not condition:report['failures'].append(item)
    receipt=json.loads((base/'run_receipt.json').read_text())
    data=ROOT/receipt['arguments']['input'];d=pd.read_csv(data)
    check('data_hash_matches_completed_receipt',hashlib.sha256(data.read_bytes()).hexdigest()==receipt['data_sha256'])
    check('unique_database_row_ids',d.row_id.is_unique)
    check('source_to_family_mapping_single_valued',d.groupby('source_id').group_id.nunique().max()==1)
    check('censor_status_consistency',bool((d.event==1-d.runout).all()))
    family_report=json.loads((ROOT/'data/processed/grouping_report.json').read_text())
    for i,family in enumerate(family_report['families']):
        sub=d[d.source_id.isin(family)]
        check(f'prefit_family_{i+1}_is_one_block',sub.group_id.nunique()==1 and set(sub.source_id)==set(family))
    report['cohort']={'rows':len(d),'conditions':int(d.dataset_id.nunique()),
        'source_dois':int(d.source_id.nunique()),'blocks':int(d.group_id.nunique()),'runouts':int(d.runout.sum())}
    indexed=d.set_index('row_id',drop=False)
    p=pd.read_csv(base/'predictions.csv')
    seeds=receipt['seeds'];models=receipt['arguments']['models'].split(',')
    bounds=['model_q10','endpoint_pooled','cohort_max']
    check('prediction_count',len(p)==len(d)*len(seeds)*len(models)*len(bounds),{'actual':len(p),'expected':len(d)*len(seeds)*len(models)*len(bounds)})
    check('unique_prediction_keys',not p.duplicated(['row_id','seed','model','bound']).any())
    for key,z in p.groupby(['seed','model','bound']):
        check(f'each_eligible_row_once_{key}',len(z)==len(d) and set(z.row_id)==set(d.row_id))
    for name in ['event','runout','source_id','group_id','dataset_id','log_life','log_stress','stress_amplitude']:
        expected=p.row_id.map(indexed[name])
        ok=comparable(p[name],expected) if pd.api.types.is_numeric_dtype(p[name]) else bool((p[name]==expected).all())
        check('saved_row_identity_'+name,ok)
    check('finite_locations_sigmas_scores',bool(np.isfinite(p[['mu','sigma','distance','instability','combined']].to_numpy()).all()))
    check('positive_sigmas',bool((p.sigma>0).all()))
    check('lower_bound_formula',comparable(p.log_lower,p.mu+norm.ppf(.1)*p.sigma-p.calibration_shift))
    records=[];fit_status=[];sample_records=[]
    metadata_ok=encoder_ok=distance_ok=threshold_ok=accept_ok=True
    for file in sorted((base/'folds').glob('source_*.json')):
        r=json.loads(file.read_text());records.append(r)
        sets=[set(r[k+'_rows']) for k in ['train','cal','test']]
        metadata_ok &= all(not (sets[i]&sets[j]) for i in range(3) for j in range(i))
        metadata_ok &= set.union(*sets)==set(d.row_id)
        frames=[indexed.loc[r[k+'_rows']] for k in ['train','cal','test']]
        group_sets=[set(f.group_id) for f in frames]
        source_sets=[set(f.source_id) for f in frames]
        metadata_ok &= all(not(group_sets[i]&group_sets[j]) and not(source_sets[i]&source_sets[j])
                           for i in range(3) for j in range(i))
        metadata_ok &= all(group_sets[i]==set(r[k+'_groups']) for i,k in enumerate(['train','cal','test']))
        metadata_ok &= len(group_sets[0])>=4 and len(group_sets[1])>=9 and len(group_sets[2])==1
        enc=reconstruct_encoder(frames[0])
        encoder_ok &= enc['numeric']==r['encoder']['numeric'] and enc['categories']==r['encoder']['categories'] and enc['names']==r['encoder']['names']
        encoder_ok &= all(comparable(enc[k],r['encoder'][k]) for k in ['mean','median','sd'])
        x,xc,xt=[encode(f,enc) for f in frames]
        dc=np.sqrt(cdist(xc,x,'sqeuclidean').min(1)/x.shape[1])
        dt=np.sqrt(cdist(xt,x,'sqeuclidean').min(1)/x.shape[1])
        fold_p=p[(p.seed==r['seed'])&(p.fold.astype(int)==int(r['fold']))]
        distance_ok &= all(comparable(z.set_index('row_id').loc[frames[2].row_id].distance,dt)
                           for _,z in fold_p.groupby(['model','bound']))
        threshold_ok &= all(comparable([quantile_linear(dc,a)],[r['gate_thresholds']['distance'][str(a)]]) for a in [.5,.8])
        for score in ['distance','instability','combined']:
            for a in [.5,.8]:
                expected=(fold_p[score]<=r['gate_thresholds'][score][str(a)]).to_numpy()
                accept_ok &= bool(np.array_equal(expected,[bool_value(v) for v in fold_p[f'accept_{score}_{a}']]))
        for f in r['fits']:
            fit_status.append(dict(fold=r['fold'],seed=r['seed'],**f))
        if r['seed']==0 and int(r['fold'])==0:
            sample_records.append(r)
        if r['seed']==42 and frames[2].source_id.nunique()>1 and not any(s['seed']==42 for s in sample_records):
            sample_records.append(r)
    check('fold_count',len(records)==len(seeds)*d.group_id.nunique())
    check('all_fold_split_and_family_integrity',metadata_ok)
    check('all_training_only_encoders_reconstructed',encoder_ok)
    check('all_saved_support_distances_recomputed',distance_ok)
    check('all_distance_operational_thresholds_recomputed',threshold_ok)
    check('all_operational_acceptance_flags_match_saved_thresholds',accept_ok)
    status=pd.DataFrame(fit_status)
    check('all_optimizer_receipts_finite',bool(np.isfinite(status[['objective','sigma','gradient_inf_norm']]).all().all()))
    report['optimization']={'fits':len(status),'not_converged':int((~status.success).sum()),
        'sigma_at_bound':int(status.sigma_at_bound.sum()),'by_model':status.groupby('model').agg(
            fits=('success','size'),not_converged=('success',lambda x:int((~x).sum())),
            max_iterations=('n_iter','max'),max_gradient=('gradient_inf_norm','max')).to_dict('index')}
    if report['optimization']['not_converged']:
        report['warnings'].append('Numerical nonconvergence exists; inspect model/source-specific receipts before performance claims.')
    if replay:
        sys.path.insert(0,str(ROOT/'src'))
        from models import LinearCensoredAFT
        replays=[]
        for r in sample_records:
            tr,cal,te=[indexed.loc[r[k+'_rows']] for k in ['train','cal','test']]
            enc=reconstruct_encoder(tr);x,xc,xt=[encode(f,enc) for f in [tr,cal,te]]
            weight=np.array([1./sum(tr.group_id==g) for g in tr.group_id])
            mod=LinearCensoredAFT(max_iter=1000).fit(x,tr.log_life,tr.event,weight)
            bc=mod.predict_location(xc)+norm.ppf(.1)*mod.sigma_
            scores=bc-cal.log_life.to_numpy()
            qp=finite_order(scores)
            maxima=[max(scores[cal.group_id.to_numpy()==g]) for g in sorted(cal.group_id.unique())]
            qg=finite_order(maxima)
            fold_p=p[(p.seed==r['seed'])&(p.fold.astype(int)==int(r['fold']))&(p.model=='linear')]
            ok=comparable(fold_p.mu,fold_p.row_id.map(dict(zip(te.row_id,mod.predict_location(xt)))))
            ok &= comparable(fold_p[fold_p.bound=='endpoint_pooled'].calibration_shift,[qp]*len(te))
            ok &= comparable(fold_p[fold_p.bound=='cohort_max'].calibration_shift,[qg]*len(te))
            dc=np.sqrt(cdist(xc,x,'sqeuclidean').min(1)/x.shape[1]);dt=np.sqrt(cdist(xt,x,'sqeuclidean').min(1)/x.shape[1])
            bcal=[];btest=[];rng=np.random.default_rng(r['seed']+500);groups=sorted(tr.group_id.unique())
            for _ in range(8):
                sampled=rng.choice(groups,len(groups),replace=True)
                w=weight*np.array([sum(sampled==g) for g in tr.group_id])
                b=LinearCensoredAFT(max_iter=1000).fit(x,tr.log_life,tr.event,w)
                bcal.append(b.predict_location(xc));btest.append(b.predict_location(xt))
            uc=np.std(bcal,axis=0,ddof=1);ut=np.std(btest,axis=0,ddof=1)
            rank=lambda ref,v:sum(float(t)<=float(v) for t in ref)/len(ref)
            cc=np.array([(rank(dc,a)+rank(uc,b))/2 for a,b in zip(dc,uc)])
            ct=np.array([(rank(dc,a)+rank(uc,b))/2 for a,b in zip(dt,ut)])
            ok &= comparable(fold_p.instability,fold_p.row_id.map(dict(zip(te.row_id,ut))))
            ok &= comparable(fold_p.combined,fold_p.row_id.map(dict(zip(te.row_id,ct))))
            for score,values in [('instability',uc),('combined',cc)]:
                ok &= all(comparable([quantile_linear(values,a)],[r['gate_thresholds'][score][str(a)]]) for a in [.5,.8])
            check(f'sampled_calibration_and_bootstrap_replay_{r["fold"]}_{r["seed"]}',ok)
            replays.append({'fold':r['fold'],'seed':r['seed'],'test_sources':sorted(te.source_id.unique()),
                'pooled_shift':qp,'source_max_shift':qg,'calibration_sources':len(maxima),'passed':bool(ok)})
        report['sampled_numerical_replays']=replays
    fresh=independent_cells(p)
    supplied=pd.read_csv(base/'source_seed_metrics.csv')
    a=fresh.set_index(KEY).sort_index();b=supplied.set_index(KEY).sort_index()
    check('all_source_seed_policy_keys',a.index.equals(b.index))
    metric_checks={c:comparable(a[c],b[c]) for c in a.columns if c in b.columns}
    check('all_source_seed_scalar_metrics',all(metric_checks.values()),metric_checks)
    summary=pd.read_csv(base/'summary.csv');smkeys=['scheme','model','bound','policy']
    summary_ok=True;recomputed=[]
    for key,z in fresh.groupby(smkeys,sort=True):
        s=summary
        for name,value in zip(smkeys,key):s=s[s[name]==value]
        if len(s)!=1:summary_ok=False;continue
        item=dict(zip(smkeys,key));source_means=z.groupby('group_id').risk_lower.mean()
        item['risk_lower']=avg(source_means)
        item['risk_upper']=avg(z.groupby('group_id').risk_upper.mean())
        item['availability']=avg(z.groupby('group_id').availability.mean())
        item['pooled_risk_lower']=z.known_danger.sum()/z.accepted.sum() if z.accepted.sum() else float('nan')
        item['pooled_risk_upper']=(z.known_danger.sum()+z.unknown_runouts.sum())/z.accepted.sum() if z.accepted.sum() else float('nan')
        cohort_fields=['cohort_violation_lower','cohort_violation_upper','severe_cohort_violation_lower','severe_cohort_violation_upper']
        for field in cohort_fields:
            item[field]=avg(z.groupby('group_id')[field].mean())
        for metric in ['risk_lower','risk_upper','availability','pooled_risk_lower','pooled_risk_upper']+cohort_fields:
            summary_ok &= comparable([item[metric]],[s.iloc[0][metric]])
        recomputed.append(item)
    check('summary_macro_and_pooled_risk',summary_ok)
    report['independent_summary']=recomputed
    # Protocol clarification v1.4 (Git f028b6b, 15:55:18) precedes the completed
    # run receipt (15:56) and specifies the simultaneous-cohort target.
    cohort_diagnostic=[]
    all_cases=fresh[fresh.policy=='all']
    for (model,bound),z in all_cases.groupby(['model','bound']):
        failed=(z.known_danger>0).astype(float)
        ambiguous=((z.known_danger==0)&(z.unknown_runouts>0)).astype(float)
        cohort_diagnostic.append({'model':model,'bound':bound,
            'cohort_seed_instances':len(z),'known_failed_cohorts':int(failed.sum()),
            'ambiguous_cohorts':int(ambiguous.sum()),
            'cohort_failure_identification_lower':avg(failed),
            'cohort_failure_identification_upper':avg(failed+ambiguous)})
    report['cohort_target_diagnostic']=cohort_diagnostic
    contrast_checks=[];contrasts=pd.read_csv(base/'paired_contrasts.csv');rng=np.random.default_rng(3284)
    cells=fresh[(fresh.model=='linear')&(fresh.bound=='endpoint_pooled')]
    by=cells.groupby(['group_id','policy'])[['risk_lower','risk_upper']].mean()
    for fraction in [.5,.8]:
        combined=by.xs(f'matched_combined_{fraction}',level='policy')
        for score in ['distance','instability','random']:
            other=by.xs(f'matched_{score}_{fraction}',level='policy').loc[combined.index]
            dif=(combined.risk_lower-other.risk_lower).to_numpy()
            boot=dif[rng.integers(0,len(dif),(2000,len(dif)))].mean(1)
            ci=np.quantile(boot,[.025,.975])
            supplied=contrasts[(contrasts.fraction==fraction)&(contrasts.comparison==f'combined minus {score}')].iloc[0]
            ok=comparable([dif.mean(),ci[0],ci[1]],supplied[['known_violation_difference','ci_low','ci_high']])
            low=avg(combined.risk_lower-other.risk_upper);high=avg(combined.risk_upper-other.risk_lower)
            ok &= comparable([low,high],supplied[['risk_difference_identification_lower','risk_difference_identification_upper']])
            per_seed={}
            for seed in seeds:
                one=cells[cells.seed==seed].set_index(['group_id','policy'])
                ca=one.xs(f'matched_combined_{fraction}',level='policy').risk_lower
                cb=one.xs(f'matched_{score}_{fraction}',level='policy').risk_lower
                per_seed[str(seed)]=avg(ca-cb)
            contrast_checks.append({'fraction':fraction,'comparison':score,'known_difference':float(dif.mean()),
                'ci':ci.tolist(),'identification_interval':[low,high],'seed_differences':per_seed,
                'recomputed_matches':bool(ok),'passes_strict_primary_rule':bool(fraction==.8 and all(v<0 for v in per_seed.values()) and ci[1]<0),
                'true_risk_reduction_identified':bool(high<0)})
    check('paired_contrasts_and_descriptive_intervals',all(v['recomputed_matches'] for v in contrast_checks))
    report['contrasts']=contrast_checks
    primary=[v for v in contrast_checks if v['fraction']==.8]
    report['H2_strong_claim_passes']=all(v['passes_strict_primary_rule'] for v in primary)
    report['H2_true_risk_reduction_identified_for_all_comparators']=all(v['true_risk_reduction_identified'] for v in primary)
    report['warnings'] += [
        'All rows derive from the public literature database; source-block withholding is not independent newly collected external experimental validation.',
        'Near-coincident curves define conservative provenance blocks, not certified physical specimen identity.',
        'Risk intervals are empirical censoring-identification bounds; source bootstrap intervals are descriptive and do not repair distribution shift.',
        'Numerical replay uses the same estimator class; independently recomputed risk logic is a distinct calculation, not an independent scientific replication.',
        'Source-average headline rates are actually averages over 29 conservative source-family blocks, not 37 independent publications.',
        'All MLP fits failed the numerical convergence flag; neural-model performance remains a numerical-budget-limited diagnostic, not a validated architecture comparison.',
        'Results concern the frozen feature representation, homoscedastic AFTs and eight-bootstrap rank gate; they cannot establish that all BNNs/AM-ML models are unreliable or that all support-aware gates fail.',
        'Whole-cohort violation flags were specified by protocol clarification v1.4 before aggregate result inspection; the auditor independently recomputed those flags and their meaning.']
    report['passed_integrity_checks']=not report['failures']
    report['elapsed_seconds']=time.time()-start
    (out/'independent_audit.json').write_text(json.dumps(report,indent=2,default=lambda x:x.item() if hasattr(x,'item') else str(x)))
    lines=['# Independent critical audit','',f'Integrity checks passed: **{report["passed_integrity_checks"]}**.',
        f'Checked {len(records)} completed folds, {len(p)} saved predictions and {len(fresh)} source/seed/policy cells.',
        f'Strong preregistered combined-gate claim passes: **{report["H2_strong_claim_passes"]}**.','',
        'This audit recomputes split integrity, training-only encodings, all directional-risk counts, pooled/source averages and primary contrasts. It replays calibration and bootstrap gates on two named folds. It is code/analysis verification, not new external validation.','',
        '## Optimization receipts','',json.dumps(report['optimization'],indent=2),'',
        '## Primary matched-availability contrasts','',
        '| Combined minus | Known-risk difference | Descriptive 95% interval | Censoring identification interval | Seedwise differences | Passes rule |',
        '|---|---:|---|---|---|---|']
    for v in primary:
        lines.append(f'| {v["comparison"]} | {v["known_difference"]:.6f} | {v["ci"]} | {v["identification_interval"]} | {v["seed_differences"]} | {v["passes_strict_primary_rule"]} |')
    lines+=['','## Simultaneous-cohort target diagnostic','',
        'Protocol clarification v1.4 records this target before aggregate result inspection. A source cohort is known to fail simultaneous coverage if any member has an observed violation; otherwise ambiguous runouts leave its status unresolved. Three seeds do not make these independent cohorts.','',
        '| Model | Bound | Known failed cohort-seed instances | Ambiguous | Cohort-failure identification interval |',
        '|---|---|---:|---:|---|']
    for v in cohort_diagnostic:
        lines.append(f'| {v["model"]} | {v["bound"]} | {v["known_failed_cohorts"]}/{v["cohort_seed_instances"]} | {v["ambiguous_cohorts"]} | [{v["cohort_failure_identification_lower"]:.6f}, {v["cohort_failure_identification_upper"]:.6f}] |')
    lines+=['','## Failures','']+[json.dumps(v) for v in report['failures'] or ['None detected in checked scope.']]
    lines+=['','## Limits and critical interpretation','']+['- '+v for v in report['warnings']]
    lines+=['','Full machine-readable checks, sampled replay details and independent summary are in `independent_audit.json`.']
    (out/'independent_audit_report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'passed_integrity_checks':report['passed_integrity_checks'],'failure_count':len(report['failures']),
        'H2_strong_claim_passes':report['H2_strong_claim_passes'],'optimization':report['optimization'],'elapsed_seconds':report['elapsed_seconds']},indent=2))
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--folder',default='results/primary');ap.add_argument('--skip-replay',action='store_true')
    args=ap.parse_args();run_audit(args.folder,replay=not args.skip_replay)
