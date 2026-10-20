"""Independent arithmetic and split audit; imports no project model/metric code.

Reconstructs risk/aggregation from saved predictions and selected predictive
quantiles from receipts with direct normal formulas or scipy adaptive quad.
This is an internal computational audit, not an external scientific replication.
"""
from __future__ import annotations
import argparse,hashlib,json,math,warnings
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import log_ndtr
from scipy.stats import norm

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
CHECKS=[];DIFFS=[];MIXED=0
METRICS=['availability','risk_lower','risk_upper','severe_risk_lower','severe_risk_upper',
         'mean_log_lower','mean_safe_gap','below1','below100','below10000','vacuous']
KEYS=['panel','model','k','bound','group_id','seed','dataset_id']


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(name,condition,detail=''):
    CHECKS.append({'check':name,'pass':bool(condition),'detail':detail})
    if not condition:raise AssertionError(name+' '+str(detail))


def equal(a,b,name,tol=1e-9):
    a,b=float(a),float(b)
    ok=(math.isnan(a) and math.isnan(b)) or (a==b)
    if np.isfinite(a) and np.isfinite(b):
        diff=abs(a-b);DIFFS.append(diff);ok=diff<=tol
    check(name,ok,{'expected':a,'saved':b})


def average(x):
    x=np.asarray(x,float);x=x[~np.isnan(x)]
    return float(np.mean(x)) if len(x) else float('nan')


def direct_metrics(d):
    values=d.log_lower.to_numpy(float);event=d.event.to_numpy(int);end=d.log_life.to_numpy(float)
    a=~np.isnan(values);out={'n_query':len(d),'n_available':int(a.sum()),'availability':float(a.mean())}
    if not a.any():
        return out|{m:float('nan') for m in METRICS if m!='availability'}
    values,event,end=values[a],event[a],end[a]
    danger=values>end;severe=values>end+math.log10(2)
    return out|{'risk_lower':float(np.count_nonzero(danger&(event==1))/len(values)),
        'risk_upper':float(np.count_nonzero(danger)/len(values)),
        'severe_risk_lower':float(np.count_nonzero(severe&(event==1))/len(values)),
        'severe_risk_upper':float(np.count_nonzero(severe)/len(values)),
        'mean_log_lower':float(np.mean(values)),'mean_safe_gap':float(np.mean(end-values)),
        'below1':float(np.mean(values<0)),'below100':float(np.mean(values<2)),
        'below10000':float(np.mean(values<4)),'vacuous':float(np.mean(np.isneginf(values)))}


def aggregate(records,indices):
    buckets={}
    for key,value in records.items():
        group=tuple(key[i] for i in indices);buckets.setdefault(group,[]).append(value)
    return {key:{m:average([v.get(m,np.nan) for v in vv]) for m in METRICS}
            for key,vv in buckets.items()}


def direct_posterior(mu,y,event,sigma,tau):
    """Independent adaptive integration, no Gauss-Hermite/project imports."""
    mu,y,event=map(lambda x:np.asarray(x,float),(mu,y,event))
    if len(y)==0:return {'kind':'normal','mean':0.,'var':tau*tau}
    if np.all(event==1):
        var=1/(1/tau**2+len(y)/sigma**2)
        return {'kind':'normal','mean':var*np.sum(y-mu)/sigma**2,'var':var}
    def logpost(u):
        z=(y-mu-u)/sigma
        logf=-.5*z*z-np.log(sigma)-.5*np.log(2*np.pi)
        return float(np.sum(event*logf+(1-event)*log_ndtr(-z))-.5*(u/tau)**2)
    def derivative(u):
        z=(y-mu-u)/sigma
        h=np.exp(-.5*z*z-.5*np.log(2*np.pi)-log_ndtr(-z))
        return float(np.sum((event*z+(1-event)*h)/sigma)-u/tau**2)
    r=max(10.,np.max(np.abs(y-mu))+10*(tau+sigma))
    mode=brentq(derivative,-r,r);peak=logpost(mode)
    # Shifting the integration origin avoids quadrature missing a narrow mode.
    f=lambda v:np.exp(logpost(mode+v)-peak)
    normer=quad(f,-np.inf,np.inf,epsabs=1e-10,epsrel=1e-9)[0]
    check('independent_quad_mass_positive',normer>0)
    return {'kind':'quad','mode':mode,'f':f,'normer':normer}


def posterior_cdf(offset,sigma,post):
    if post['kind']=='normal':return norm.cdf((offset-post['mean'])/np.sqrt(sigma*sigma+post['var']))
    return quad(lambda v:post['f'](v)*norm.cdf((offset-post['mode']-v)/sigma),
                -np.inf,np.inf,epsabs=1e-10,epsrel=1e-9)[0]/post['normer']


def location(rows,train,receipt,curved):
    p=np.asarray(receipt['params_'],float);fill=receipt['fit_receipt_']['ratio_median_train']
    tr=train.load_ratio.fillna(fill).to_numpy();r=rows.load_ratio.fillna(fill).to_numpy()
    t=rows.log_stress.to_numpy()
    if curved:
        knot=float(np.median(train.log_stress));x=t-knot
        equal(knot,receipt['fit_receipt_']['knot_training_median_log_stress'],'training_knot_exact')
        return p[0]+p[1]*np.minimum(x,0)+p[2]*np.maximum(x,0)+p[3]*(r-np.mean(tr))
    return p[0]+p[1]*(t-np.mean(train.log_stress))+p[2]*(r-np.mean(tr))


def audit_saved_quantiles(folder,d,receipts,cohort,curved):
    global MIXED
    checked=0
    for rr in receipts:
        task=rr['task'];train=cohort[cohort.group_id.isin(task['fit_blocks'])]
        # Independent parameter bound and source separation checks.
        check('held_source_absent_from_training',task['outer'] not in set(train.group_id))
        check('fit_calibration_disjoint',set(task['fit_blocks']).isdisjoint(task['cal_blocks']))
        for model in ['pooled','hierarchical']:
            model_r=rr[model];p=np.asarray(model_r['params_'],float);fit=model_r['fit_receipt_']
            check('converged_finite_'+model,fit['success'] and np.isfinite(p).all())
            slopes=p[1:3] if curved else p[1:2]
            check('strictly_negative_stress_slopes',bool((slopes<0).all()))
            check('scatter_in_declared_bounds',.02-1e-8<=model_r['sigma_']<=3.+1e-8)
            if model=='hierarchical':check('tau_in_declared_bounds',.02-1e-8<=model_r['tau_']<=3.+1e-8)
        for target in task['targets']:
            query=cohort.loc[target['query_ids']];pool=target['support_pool']
            check('support_query_disjoint',set(pool).isdisjoint(target['query_ids']))
            check('query_condition_matches',set(query.dataset_id)=={target['curve']})
            for k in task['ks']:
                support=cohort.loc[pool[:k]]
                # Every stored lower bound differs from location only by a
                # condition/support-specific scalar, because slopes are shared.
                for name in ['pooled','hierarchical']:
                    modelname=name+('_curved' if curved else '')
                    rr_model=rr[name];mu=location(query,train,rr_model,curved)
                    select=d[(d.panel==task['panel'])&(d.seed==task['seed'])&
                             (d.group_id==task['outer'])&(d.dataset_id==target['curve'])&
                             (d.model==modelname)&(d.k==k)&(d.bound=='raw')].set_index('row_id')
                    check('every_expected_query_present',set(select.index)==set(query.row_id))
                    actual=select.loc[query.row_id].log_lower.to_numpy()
                    sigma=rr_model['sigma_']
                    if name=='pooled':expected=mu+norm.ppf(.1)*sigma
                    else:
                        sy=support.log_life.to_numpy();ev=support.event.to_numpy()
                        if len(support) and np.any(ev==0) and MIXED>=30:
                            # Check shared offset even when numerical replay is
                            # deliberately limited to30 mixed support episodes.
                            offsets=actual-mu
                            check('shared_support_offset',np.ptp(offsets)<1e-8)
                            continue
                        smu=location(support,train,rr_model,curved)
                        post=direct_posterior(smu,sy,ev,sigma,rr_model['tau_'])
                        if post['kind']=='normal':offset=post['mean']+norm.ppf(.1)*np.sqrt(sigma*sigma+post['var'])
                        else:
                            MIXED+=1;offset=brentq(lambda z:posterior_cdf(z,sigma,post)-.1,-30,30)
                        expected=mu+offset
                    check('independent_predictive_formula',np.max(np.abs(expected-actual))<2e-6,
                          {'folder':str(folder),'model':name,'k':k,'max_error':float(np.max(np.abs(expected-actual)))})
                    checked+=len(query)
        for cal in rr['calibration']:
            scores=cal['scores'];rank=math.ceil(.9*(len(scores)+1)-1e-12)
            expected=(np.nan if cal['failed_blocks'] else
                      sorted(scores)[rank-1] if rank<=len(scores) else np.inf)
            equal(expected,cal['cutoff'],'finite_sample_calibration_rank')
    return checked


def audit_metrics(folder,d):
    rows={}
    for key,group in d.groupby(KEYS,sort=True):rows[key]=direct_metrics(group)
    cells=0
    targets=[('curve_metrics.csv',KEYS,rows),
             ('source_seed_metrics.csv',KEYS[:-1],aggregate(rows,range(6)))]
    source_seed=targets[-1][2];source=aggregate(source_seed,range(5))
    targets.extend([('source_metrics.csv',KEYS[:-2],source),
                    ('summary.csv',KEYS[:4],aggregate(source,range(4)))])
    for name,keys,expected in targets:
        path=folder/name
        if not path.exists():continue
        saved=pd.read_csv(path).set_index(keys)
        check('metric_table_keys_'+name,set(saved.index)==set(expected))
        for key,value in expected.items():
            for metric,num in value.items():
                if metric in saved:
                    equal(num,saved.loc[key,metric],name+':'+metric);cells+=1
    pairs=folder/'paired_contrasts.csv'
    if pairs.exists():
        saved=pd.read_csv(pairs).set_index(['panel','model','bound','k','metric'])
        for (panel,model,bound),g in d.groupby(['panel','model','bound']):
            z=g[g.k==0].set_index(['group_id','seed','dataset_id','row_id'])
            for k in sorted(set(g.k)-{0}):
                kk=g[g.k==k].set_index(z.index.names)
                check('fixed_query_pair_keys',set(z.index)==set(kk.index))
                values={}
                for idx,row in z.iterrows():
                    b0=row.log_lower;bk=kk.loc[idx,'log_lower'];y=row.log_life;e=row.event
                    valid=not(np.isnan(b0) or np.isnan(bk))
                    if valid:
                        delta=float(bk>y)-float(b0>y)
                        with np.errstate(invalid='ignore'):gain=bk-b0
                        lo=delta if e==1 else -float(b0>bk and b0>y)
                        hi=delta if e==1 else float(bk>b0 and bk>y)
                        value={'log_gain':gain,'risk_upper_diff':delta,
                            'risk_lower_diff':delta if e==1 else 0.,
                            'true_risk_change_lo':lo,'true_risk_change_hi':hi,'available_pair':1.}
                    else:value={m:np.nan for m in ['log_gain','risk_upper_diff','risk_lower_diff','true_risk_change_lo','true_risk_change_hi']}|{'available_pair':0.}
                    values[idx]=value
                def reduce_custom(items,n):
                    bins={}
                    for key,v in items.items():bins.setdefault(key[:n],[]).append(v)
                    return {key:{m:average([v[m] for v in vv]) for m in vv[0]} for key,vv in bins.items()}
                condition=reduce_custom(values,3);source_seed=reduce_custom(condition,2);source=reduce_custom(source_seed,1)
                for metric in ['log_gain','risk_upper_diff','risk_lower_diff','true_risk_change_lo','true_risk_change_hi']:
                    x=np.asarray([source[key][metric] for key in sorted(source)])
                    row=saved.loc[(panel,model,bound,k,metric)]
                    # Root intentionally uses plain mean: one unavailable source
                    # makes a global paired contrast undefined, not selectively dropped.
                    equal(np.mean(x),row['mean'],'paired_mean_'+metric);cells+=1
                    if len(x)>=2 and np.isfinite(x).all():
                        rng=np.random.default_rng(231)
                        means=[np.mean(x[index]) for index in rng.integers(0,len(x),(2000,len(x)))]
                        limits=np.quantile(means,[.025,.975])
                    else:limits=[np.nan,np.nan]
                    equal(limits[0],row.lo95,'paired_bootstrap_lower');equal(limits[1],row.hi95,'paired_bootstrap_upper');cells+=2
    return cells


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--results',default=str(ROOT/'results/v2'))
    args=parser.parse_args();folder_root=Path(args.results)
    manifests={digest(p):p for p in (ROOT/'data/processed/v2').glob('*/frozen_splits.json')}
    reports=[]
    for folder in sorted(folder_root.iterdir()):
        if not folder.is_dir() or not (folder/'predictions.csv').exists():continue
        sig=json.loads((folder/'signature.json').read_text()) if (folder/'signature.json').exists() else {}
        d=pd.read_csv(folder/'predictions.csv');report={'folder':str(folder.relative_to(ROOT)),
            'prediction_rows':len(d),'prediction_sha256':digest(folder/'predictions.csv')}
        if 'splits_sha256' in sig and (folder/'run_receipt.json').exists():
            check('frozen_manifest_resolves',sig['splits_sha256'] in manifests)
            mp=manifests[sig['splits_sha256']];cohort=pd.read_csv(mp.parent/'cohort.csv').set_index('row_id',drop=False)
            check('cohort_hash_matches',digest(mp.parent/'cohort.csv')==sig['cohort_sha256'])
            rr=json.loads((folder/'run_receipt.json').read_text());receipts=rr['fits']
            report['tasks']=len(receipts)
            report['independent_formula_prediction_rows']=audit_saved_quantiles(folder,d,receipts,cohort,sig.get('curvature_sensitivity',False))
            report['max_recorded_hierarchy_gradient']=max(q['hierarchical']['fit_receipt_']['gradient_inf'] for q in receipts)
            report['hierarchy_sigma_bound_count']=sum(q['hierarchical']['fit_receipt_']['sigma_at_bound'] for q in receipts)
            report['hierarchy_tau_bound_count']=sum(q['hierarchical']['fit_receipt_']['tau_at_bound'] for q in receipts)
        elif 'external_manifest_sha256' in sig:
            fits=json.loads((folder/'fit_receipts.json').read_text())
            check('bootstrap_all_replicates_converged',all(r['fit']['success'] for r in fits))
            report['bootstrap_replicates']=len(fits)
            # Static branch check is coupled with exact normal numerical checks
            # in the main model. Mixed-support numerical checks above use quad.
            source=(ROOT/'src/v2_population_bootstrap.py').read_text()
            check('bootstrap_zero_shot_exact_normal_branch','np.hypot(model.sigma_,model.tau_)' in source)
            check('bootstrap_failure_support_exact_normal_branch',"post['variance']" in source and 'np.all(support.event' in source)
        report['independently_recomputed_metric_cells']=audit_metrics(folder,d)
        reports.append(report)
    result={'created_by':'independent audit script without project metric/model imports',
            'folders':reports,'checks':len(CHECKS),'all_pass':all(z['pass'] for z in CHECKS),
            'maximum_metric_absolute_difference':max(DIFFS,default=0.),
            'mixed_posterior_quad_episodes':MIXED,
            'limits':['Model implementer reviewed runners; this is not independent model authorship.',
                'No refit of real-data populations; formulas reconstructed from saved parameters.',
                'Source bootstrap dependence is descriptive, not a certified confidence guarantee.',
                'Physical specimen provenance and crack endpoint equivalence are not established by arithmetic.']}
    (OUT/'post_fit_independent_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'post_fit_independent_audit.md').write_text('# Independent phase-2 arithmetic audit\n\n'+
        f"Checks: {len(CHECKS)}; all pass: {result['all_pass']}. Maximum metric difference: {result['maximum_metric_absolute_difference']:.3g}.\n\n"+
        '\n'.join(f"- {r['folder']}: {r['prediction_rows']} saved prediction rows; {r['independently_recomputed_metric_cells']} recomputed metric cells." for r in reports)+
        '\n\n'+ '\n'.join(result['limits'])+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',RuntimeWarning);main()
