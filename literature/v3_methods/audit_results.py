"""Independent table/identity arithmetic; no model refits or selection calls."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
import pandas as pd


def _mean(values):
    a=np.asarray(values,float)
    return float(np.mean(a[np.isfinite(a)])) if np.any(np.isfinite(a)) else np.nan


def collapse(d,keys,metrics):
    # Explicit nested averaging independently of v3_summarize helpers.
    records=[]
    for key,g in d.groupby(keys+['campaign_id','dataset_id','seed']):
        records.append(dict(zip(keys+['campaign_id','dataset_id','seed'],key))|
                       {m:_mean(g[m]) for m in metrics})
    cond=pd.DataFrame(records)
    expected={}
    for key,g in cond.groupby(keys):
        campaign_values={}
        for campaign,cg in g.groupby('campaign_id'):
            per_seed={seed:{m:_mean(sg[m]) for m in metrics}
                      for seed,sg in cg.groupby('seed')}
            campaign_values[campaign]={m:_mean([v[m] for v in per_seed.values()]) for m in metrics}
        for m in metrics:
            expected[key+(m,)]=_mean([v[m] for v in campaign_values.values()])
    return expected


def compare_means(table,expected,keys):
    maxerr=0.
    for _,row in table.iterrows():
        key=tuple(row[k] for k in keys)+(row.metric,)
        value=expected[key]
        if np.isnan(value):assert np.isnan(row['mean'])
        else:maxerr=max(maxerr,abs(value-float(row['mean'])))
    assert maxerr<2e-7,maxerr
    return maxerr


def audit(folder,dataset):
    folder,dataset=Path(folder),Path(dataset)
    pred=pd.read_csv(folder/'predictions.csv')
    parent=folder if (folder/'run_receipt.json').exists() else folder.parent
    selections=pd.read_csv(parent/'selections.csv')
    receipt=json.loads((parent/'run_receipt.json').read_text())
    split=json.loads((dataset/'frozen_splits.json').read_text())
    cohort=pd.read_csv(dataset/'cohort.csv').set_index('row_id')
    assert hashlib.sha256((dataset/'frozen_splits.json').read_bytes()).hexdigest()==receipt['splits_sha256']
    enabled=set(zip(pred.dataset_id,pred.seed))
    taskmap={(t['dataset_id'],t['seed']):t for t in receipt['tasks']
             if (t['dataset_id'],t['seed']) in enabled}
    selections=selections[[x in enabled for x in zip(selections.dataset_id,selections.seed)]]
    subset_relation=None
    if parent!=folder:
        full=pd.read_csv(parent/'predictions.csv')
        eligible=cohort.groupby('dataset_id').log_stress.nunique()
        eligible=set(eligible[eligible>=2].index)
        expected_subset=full[full.dataset_id.isin(eligible)]
        sortcols=['dataset_id','seed','policy','model','k','row_id','cap']
        pd.testing.assert_frame_equal(pred.sort_values(sortcols).reset_index(drop=True),
                                      expected_subset.sort_values(sortcols).reset_index(drop=True))
        subset_relation=True
    for (ds,seed),g in pred.groupby(['dataset_id','seed']):
        task=taskmap[ds,seed]
        assert set(task['query_ids']).isdisjoint(task['pool_ids'])
        assert set(task['query_ids'])==set(g.row_id)
        for _,s in g.groupby(['policy','model','k']):
            assert len(s)==len(task['query_ids']) and set(s.row_id)==set(task['query_ids'])
        for signature in g.fit_signature.unique():
            fit=receipt['fits'][signature]
            assert set(fit['training_sources'])==set(task['fit_blocks'])
            if task['panel']=='historical_reused':
                assert task['campaign_id'] not in fit['training_sources']
    selection_prediction_groups={key:g for key,g in pred.groupby(['dataset_id','seed','policy'])}
    for (ds,seed,policy),s in selections.groupby(['dataset_id','seed','policy']):
        s=s.sort_values('k');task=taskmap[ds,seed]
        assert s.row_id.is_unique and set(s.row_id)<=set(task['pool_ids'])
        assert set(s.row_id).isdisjoint(task['query_ids'])
        rows=cohort.loc[s.row_id]
        observed=np.minimum(np.power(10.,rows.log_life.to_numpy()),float(receipt['cap']))
        cumulative=np.cumsum(observed)
        for k,g in selection_prediction_groups[ds,seed,policy].groupby('k'):
            expected=0. if k==0 else cumulative[int(k)-1]
            np.testing.assert_allclose(g.support_cycles,expected,rtol=2e-14,atol=1e-4)
    L,y,e=pred.log_lower.to_numpy(),pred.log_life.to_numpy(),pred.event.to_numpy()
    available=~np.isnan(L);finite=np.isfinite(L)
    derived={
        'availability':available.astype(float),'finite_availability':finite.astype(float),
        'positive_infinite':np.isposinf(L).astype(float),
        'known_risk':np.where(available,(L>y)&(e==1),0.).astype(float),
        'upper_risk':np.where(available,L>y,1.).astype(float),
        'finite_log_lower':np.where(finite,L,np.nan),
        'failure_shortfall':np.where((e==1)&finite,np.maximum(y-L,0),np.nan),
        'support_cycles':pred.support_cycles.to_numpy(),
        'all_support_runout':((pred.k.to_numpy()>0)&(pred.n_support_failure.to_numpy()==0)).astype(float)}
    for key,value in derived.items():pred[key]=value
    keys=['panel','policy','model','k','cap']
    summary=pd.read_csv(folder/'summary.csv')
    maxerr=compare_means(summary,collapse(pred,keys,list(derived)),keys)
    index=['campaign_id','dataset_id','seed','row_id']
    paired_records=[]
    policy_prediction_groups={key:g for key,g in pred.groupby(keys)}
    for key,g in pred.groupby(keys):
        base=dict(zip(keys,key));a=g.set_index(index).sort_index()
        for comparison in ['versus_random','versus_k0']:
            basekey=(base['panel'],('random' if comparison=='versus_random' else base['policy']),
                     base['model'],(base['k'] if comparison=='versus_random' else 0),base['cap'])
            b=policy_prediction_groups[basekey].set_index(index).loc[a.index]
            np.testing.assert_array_equal(a.log_life,b.log_life)
            np.testing.assert_array_equal(a.event,b.event)
            la,lb,y,e=[np.asarray(x) for x in (a.log_lower,b.log_lower,a.log_life,a.event)]
            valid=(~np.isnan(la))&(~np.isnan(lb));ff=np.isfinite(la)&np.isfinite(lb)
            exact=(la>y).astype(int)-(lb>y).astype(int)
            lower,upper=exact.astype(float),exact.astype(float)
            for i in range(len(a)):
                if not valid[i]:lower[i],upper[i]=-1.,1.
                elif e[i]==0:
                    lower[i]=-1. if lb[i]>la[i] and lb[i]>y[i] else 0.
                    upper[i]=1. if la[i]>lb[i] and la[i]>y[i] else 0.
            c=a.reset_index()[['campaign_id','dataset_id','seed']].copy()
            for k,v in base.items():c[k]=v
            c['comparison']=comparison;c['paired_availability']=valid.astype(float)
            c['paired_finite_availability']=ff.astype(float)
            with np.errstate(invalid='ignore'):c['log_life_gain']=np.where(ff,la-lb,np.nan)
            c['true_risk_change_lo']=lower;c['true_risk_change_hi']=upper
            c['support_cycle_change']=a.support_cycles.to_numpy()-b.support_cycles.to_numpy()
            paired_records.append(c)
    paired=pd.read_csv(folder/'paired_comparisons.csv')
    paired_metrics=['paired_availability','paired_finite_availability','log_life_gain',
                    'true_risk_change_lo','true_risk_change_hi','support_cycle_change']
    paired_error=compare_means(paired,collapse(pd.concat(paired_records),keys+['comparison'],
                                             paired_metrics),keys+['comparison'])
    return {'folder':str(folder),'prediction_rows':len(pred),'selection_rows':len(selections),
            'tasks':len(taskmap),'summary_cells_checked':len(summary),
            'max_summary_mean_abs_error':maxerr,'common_query_pool_identity_pass':True,
            'paired_cells_checked':len(paired),'max_paired_mean_abs_error':paired_error,
            'support_cycle_recalculation_pass':True,'training_source_exclusion_pass':True,
            'multistress_covariate_subset_relation_pass':subset_relation,
            'all_checks_pass':True}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folders',nargs='+')
    p.add_argument('--dataset',default='data/processed/v3/common')
    p.add_argument('--output',default='literature/v3_methods/independent_result_audit.json')
    a=p.parse_args();result=[audit(f,a.dataset) for f in a.folders]
    Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
