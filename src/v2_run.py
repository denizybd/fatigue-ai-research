"""Frozen, source-held-out few-shot experiments; immutable per-task receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')

import numpy as np
import pandas as pd

from src.evaluation import conformal_quantile
from src.v2_prepare import ROOT, digest


def obj_json(x):
    if isinstance(x, np.ndarray): return x.tolist()
    if isinstance(x, np.generic): return x.item()
    if hasattr(x,'to_dict'): return x.to_dict()
    if hasattr(x,'__dict__'): return x.__dict__
    raise TypeError(type(x).__name__)


def status(model):
    result={}
    for key in ['status_','params_','sigma_','tau_','coef_','intercept_',
                'converged_','sigma_at_bound_','tau_at_bound_','fit_receipt_']:
        if hasattr(model,key):result[key]=getattr(model,key)
    return result


def predict(model, query, support, method, alpha=.1):
    return np.asarray(model.predict_quantiles(query, support=support,
        alphas=[alpha]),float).reshape(len(query),-1)[:,0]


def run(dataset, output, panels=None, max_tasks=None, quadrature=41):
    from src.v2_models import CensoredBasquin, HierarchicalCensoredBasquin, FixedSlopeShiftPredictor
    dataset,output=Path(dataset),Path(output)
    output.mkdir(parents=True,exist_ok=True)
    frozen=dataset/'frozen_splits.json';cohort=dataset/'cohort.csv'
    manifest=json.loads(frozen.read_text())
    assert digest(cohort)==manifest['cohort_sha256']
    d=pd.read_csv(cohort).set_index('row_id',drop=False)
    sig={'splits_sha256':digest(frozen), 'cohort_sha256':digest(cohort),
         'code':{str(p.relative_to(ROOT)):digest(p) for p in
           [ROOT/'src/v2_run.py',ROOT/'src/v2_models.py',ROOT/'src/evaluation.py']},
         'quadrature':quadrature, 'models':['pooled','unpooled_shift','hierarchical'],
         'bound_types':['raw','endpoint_calibrated'], 'alpha':.1}
    sign=output/'signature.json'
    if sign.exists() and json.loads(sign.read_text())!=sig:
        raise RuntimeError('Checkpoint signature differs; use a fresh output folder')
    sign.write_text(json.dumps(sig,indent=2)+'\n')
    tasks=[t for t in manifest['tasks'] if panels is None or t['panel'] in panels]
    if max_tasks is not None:tasks=tasks[:max_tasks]
    all_predictions=[];fit_receipts=[];begin=time.monotonic()
    for i,t in enumerate(tasks):
        key=hashlib.sha256(json.dumps(t,sort_keys=True).encode()).hexdigest()[:16]
        taskfolder=output/'tasks'/key;taskfolder.mkdir(parents=True,exist_ok=True)
        predictionfile=taskfolder/'predictions.csv';receiptfile=taskfolder/'receipt.json'
        if predictionfile.exists() and receiptfile.exists():
            all_predictions.append(pd.read_csv(predictionfile))
            fit_receipts.append(json.loads(receiptfile.read_text()))
            continue
        started=time.monotonic()
        train=d[d.group_id.isin(t['fit_blocks'])].copy()
        assert t['outer'] not in set(train.group_id)
        assert set(t['fit_blocks']).isdisjoint(t['cal_blocks'])
        pooled=CensoredBasquin().fit(train)
        hier=HierarchicalCensoredBasquin(nodes=quadrature).fit(train)
        preliminary={'task':t,'fit_n':len(train),'pooled':status(pooled),
                     'hierarchical':status(hier),'phase':'population_fit'}
        (taskfolder/'population_fit_receipt.json').write_text(
            json.dumps(preliminary,default=obj_json,indent=2)+'\n')
        for model in (pooled,hier):
            if not model.fit_receipt_['success'] or not np.all(np.isfinite(model.params_)):
                raise RuntimeError(f'Unusable population fit {key}; receipt retained, no predictions made')
        models={'pooled':(pooled,'pooled'), 'unpooled_shift':(FixedSlopeShiftPredictor(pooled),'unpooled_shift'),
                'hierarchical':(hier,'hierarchical')}
        rows=[];calibrations=[]
        for modelname,(model,method) in models.items():
            for k in t['ks']:
                scores=[];cal_failed=[]
                for c in t['calibration']:
                    support=d.loc[c['support_pool'][:k]].copy()
                    query=d.loc[[c['query_id']]].copy()
                    assert set(support.row_id).isdisjoint(query.row_id)
                    q=predict(model,query,support,method)[0]
                    if np.isfinite(q):scores.append(float(q-query.log_life.iloc[0]))
                    else:cal_failed.append(c['block'])
                # An unavailable unpooled support fit never silently drops a
                # difficult calibration source. Its calibrated bound is unavailable.
                cutoff=(conformal_quantile(scores,.1) if scores and not cal_failed
                        else (np.inf if not t['calibration'] else np.nan))
                calibrations.append({'model':modelname,'k':k,'scores':scores,
                    'failed_blocks':cal_failed,'cutoff':cutoff,'m':len(scores)})
                for c in t['targets']:
                    support=d.loc[c['support_pool'][:k]].copy()
                    query=d.loc[c['query_ids']].copy()
                    assert set(support.row_id).isdisjoint(query.row_id)
                    assert set(support.group_id)=={t['outer']} if len(support) else True
                    q=predict(model,query,support,method)
                    for bound,value in [('raw',q),('endpoint_calibrated',q-cutoff)]:
                        for pos,(_,record) in enumerate(query.iterrows()):
                            row={x:record[x] for x in ['row_id','dataset_id','group_id','doi',
                                  'log_life','event','log_stress','stress_amplitude','load_ratio']}
                            row.update({'panel':t['panel'],'seed':t['seed'],'model':modelname,
                                'k':k,'bound':bound,'log_lower':float(value[pos]),
                                'raw_log_lower':float(q[pos]),'calibration_cutoff':cutoff,
                                'n_cal_blocks':len(scores),'n_support_failures':int(support.event.sum()),
                                'n_support_runouts':int(len(support)-support.event.sum()),
                                'n_fit_blocks':len(t['fit_blocks']),'task_id':key})
                            rows.append(row)
        receipt={'task':t,'fit_n':len(train),'pooled':status(pooled),'hierarchical':status(hier),
                 'calibration':calibrations,'seconds':time.monotonic()-started}
        pd.DataFrame(rows).to_csv(predictionfile,index=False)
        receiptfile.write_text(json.dumps(receipt,default=obj_json,indent=2)+'\n')
        all_predictions.append(pd.DataFrame(rows));fit_receipts.append(receipt)
        print(f"{i+1}/{len(tasks)} panel={t['panel']} seed={t['seed']} source={t['outer']} "
              f"seconds={receipt['seconds']:.2f}",flush=True)
    if all_predictions:pd.concat(all_predictions,ignore_index=True).to_csv(output/'predictions.csv',index=False)
    (output/'run_receipt.json').write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),
        'tasks':len(tasks),'seconds':time.monotonic()-begin,'fits':fit_receipts},default=obj_json,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',default=str(ROOT/'data/processed/v2/clean'))
    p.add_argument('--output',default=str(ROOT/'results/v2/main'));p.add_argument('--panels',nargs='+')
    p.add_argument('--max-tasks',type=int);p.add_argument('--quadrature',type=int,default=41)
    a=p.parse_args();run(a.dataset,a.output,a.panels,a.max_tasks,a.quadrature)
