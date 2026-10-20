"""Explicit post-result diagnostic isolating target-intercept prior borrowing.

Reconstructs saved hierarchical populations, changes only target intercept
updating, and preserves exact target support/query IDs. No population refit.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from src.v2_models import HierarchicalCensoredBasquin,FixedSlopeShiftPredictor
from src.v2_summarize import summarize

ROOT=Path(__file__).resolve().parents[1]


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def contrast(folder):
    d=pd.read_csv(folder/'predictions.csv');rows=[]
    for panel in sorted(d.panel.unique()):
        for k in sorted(d[d.panel==panel].k.unique()):
            a=d[(d.panel==panel)&(d.k==k)&(d.model=='hierarchical_reference')].set_index(
                ['group_id','seed','dataset_id','row_id'])
            b=d[(d.panel==panel)&(d.k==k)&(d.model=='same_population_unpooled')].set_index(a.index.names)
            assert set(a.index)==set(b.index)
            b=b.loc[a.index];valid=np.isfinite(a.log_lower)&np.isfinite(b.log_lower)
            y=a.log_life.to_numpy();event=a.event.to_numpy()
            ha=a.log_lower.to_numpy();hb=b.log_lower.to_numpy()
            faildiff=((ha>y).astype(float)-(hb>y).astype(float))
            # Difference is hierarchy minus matched unpooled, on common queries.
            v=pd.DataFrame(index=a.index)
            v['availability_pair']=valid.astype(float)
            for name,array in {
                'log_life_gain_hier_minus_control':ha-hb,
                'hier_risk_lower':(ha>y)&(event==1),
                'hier_risk_upper':ha>y,
                'control_risk_lower':(hb>y)&(event==1),
                'control_risk_upper':hb>y,
                'true_risk_change_lo':np.where(event==1,faildiff,-((hb>ha)&(hb>y)).astype(float)),
                'true_risk_change_hi':np.where(event==1,faildiff,((ha>hb)&(ha>y)).astype(float))}.items():
                v[name]=np.where(valid,np.asarray(array,float),np.nan)
            curves=v.groupby(level=['group_id','seed','dataset_id']).mean()
            sources=curves.groupby(level=['group_id','seed']).mean().groupby(level='group_id').mean()
            for metric in sources:
                x=sources[metric].to_numpy();mean=float(np.mean(x))
                if len(x)>1 and np.isfinite(x).all():
                    rng=np.random.default_rng(231)
                    boot=x[rng.integers(0,len(x),(2000,len(x)))].mean(1)
                    lo,hi=np.quantile(boot,[.025,.975])
                else:lo,hi=np.nan,np.nan
                rows.append({'panel':panel,'k':int(k),'metric':metric,'mean':mean,
                             'lo95':float(lo),'hi95':float(hi),'n_sources':len(x),
                             'interpretation':'post-result diagnostic; paired available queries only'})
    pd.DataFrame(rows).to_csv(folder/'matched_population_comparison.csv',index=False)


def run(original,dataset,output):
    original,dataset,output=map(Path,(original,dataset,output))
    output.mkdir(parents=True,exist_ok=True)
    sig=json.loads((original/'signature.json').read_text())
    assert not sig.get('curvature_sensitivity',False),'Straight hierarchy diagnostic only'
    assert digest(dataset/'frozen_splits.json')==sig['splits_sha256']
    assert digest(dataset/'cohort.csv')==sig['cohort_sha256']
    cohort=pd.read_csv(dataset/'cohort.csv').set_index('row_id',drop=False)
    previous=pd.read_csv(original/'predictions.csv')
    previous=previous[(previous.model=='hierarchical')&(previous.bound=='raw')]
    receipts=json.loads((original/'run_receipt.json').read_text())['fits']
    output_rows=[];reconstruction=[]
    for receipt in receipts:
        task=receipt['task'];train=cohort[cohort.group_id.isin(task['fit_blocks'])]
        rr=receipt['hierarchical'];fit=rr['fit_receipt_']
        assert fit['success']
        model=HierarchicalCensoredBasquin(nodes=sig['quadrature'])
        model.params_=np.asarray(rr['params_'],float)
        model.sigma_=rr['sigma_'];model.tau_=rr['tau_']
        model.ratio_median_=fit['ratio_median_train']
        model.center_=np.array([train.log_stress.mean(),train.load_ratio.fillna(model.ratio_median_).mean()])
        control=FixedSlopeShiftPredictor(model)
        statuses=[]
        for target in task['targets']:
            query=cohort.loc[target['query_ids']]
            for k in task['ks']:
                support=cohort.loc[target['support_pool'][:k]]
                # Reconstruct hierarchy to ensure the reused transformations are
                # exact; no fitted model object is deserialized or re-optimized.
                expected=model.predict_quantiles(query,support=support,alphas=(.1,))[:,0]
                old=previous[(previous.panel==task['panel'])&(previous.seed==task['seed'])&
                    (previous.group_id==task['outer'])&(previous.dataset_id==target['curve'])&
                    (previous.k==k)].set_index('row_id').loc[query.row_id]
                max_error=float(np.max(np.abs(expected-old.log_lower.to_numpy())))
                assert max_error<1e-9,(task['outer'],target['curve'],k,max_error)
                if k==0:
                    new=expected.copy();state='shared_hierarchical_zero_shot_reference'
                else:
                    new=control.predict_quantiles(query,support=support,alphas=(.1,))[:,0]
                    state=control.last_prediction_receipt_['status']
                statuses.append({'curve':target['curve'],'k':k,'status':state,
                                 'support_failures':int(support.event.sum()),
                                 'support_runouts':int(len(support)-support.event.sum()),
                                 'hierarchy_reconstruction_max_error':max_error})
                for i,(_,record) in enumerate(query.iterrows()):
                    base={field:record[field] for field in ['row_id','dataset_id','group_id','doi',
                          'log_life','event','log_stress','stress_amplitude','load_ratio']}
                    base.update(panel=task['panel'],seed=task['seed'],k=k,bound='raw',
                                diagnostic_timing='post-result exploratory',
                                n_support_failures=int(support.event.sum()),
                                n_support_runouts=int(len(support)-support.event.sum()))
                    output_rows.append(base|{'model':'hierarchical_reference','log_lower':expected[i]})
                    output_rows.append(base|{'model':'same_population_unpooled','log_lower':new[i]})
        reconstruction.append({'panel':task['panel'],'seed':task['seed'],'outer':task['outer'],
                               'saved_population_params':model.params_.tolist(),
                               'training_center_reconstructed':model.center_.tolist(),
                               'statuses':statuses})
    pd.DataFrame(output_rows).to_csv(output/'predictions.csv',index=False)
    signature={'created_utc':datetime.now(timezone.utc).isoformat(),
        'timing':'EXPLICIT POST-RESULT EXPLORATORY ABLATION',
        'original_predictions_sha256':digest(original/'predictions.csv'),
        'original_population_receipt_sha256':digest(original/'run_receipt.json'),
        'splits_sha256':sig['splits_sha256'],'cohort_sha256':sig['cohort_sha256'],
        'code_sha256':digest(__file__),'model_sha256':digest(ROOT/'src/v2_models.py'),
        'protocol_sha256':digest(ROOT/'protocols/v2/postresult_matched_population_control.md'),
        'population_refitted':False,'population_parameter_uncertainty_included':False}
    (output/'signature.json').write_text(json.dumps(signature,indent=2)+'\n')
    (output/'reconstruction_receipt.json').write_text(json.dumps(reconstruction,indent=2)+'\n')
    summarize(output);contrast(output)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--original',required=True)
    p.add_argument('--dataset',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();run(a.original,a.dataset,a.output)
