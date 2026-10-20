"""External raw hierarchical ensemble; invert mixture CDF, not mean quantiles."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import ndtr
from src.v2_models import HierarchicalCensoredBasquin
from src.v2_prepare import ROOT,digest


def bootstrap(external_folder,output,replicates=20):
    external_folder,output=Path(external_folder),Path(output)
    output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((external_folder/'frozen_splits.json').read_text())
    d=pd.read_csv(external_folder/'cohort.csv').set_index('row_id',drop=False)
    assert digest(external_folder/'cohort.csv')==manifest['cohort_sha256']
    tasks=manifest['tasks'];fit=set(tasks[0]['fit_blocks'])
    assert all(set(t['fit_blocks'])==fit for t in tasks),'Use full-training external splits'
    train=d[d.group_id.isin(fit)]
    blocks=sorted(fit);rng=np.random.default_rng(27021)
    models=[];receipts=[]
    start=time.monotonic()
    for rep in range(replicates):
        selected=rng.choice(blocks,len(blocks),replace=True)
        chunks=[]
        for copy,source in enumerate(selected):
            g=train[train.group_id==source].copy()
            g['group_id']=str(source)+'__bootstrap_'+str(copy)
            g['dataset_id']=g.dataset_id+'__bootstrap_'+str(copy)
            chunks.append(g)
        model=HierarchicalCensoredBasquin(nodes=41).fit(pd.concat(chunks,ignore_index=True))
        receipt={'replicate':rep,'selected_blocks':selected.tolist(),
                 'params':model.params_.tolist(),'center':model.center_.tolist(),
                 'ratio_median':model.ratio_median_,'fit':model.fit_receipt_}
        receipts.append(receipt)
        (output/'fit_receipts.json').write_text(json.dumps(receipts,indent=2)+'\n')
        if not model.fit_receipt_['success']:
            raise RuntimeError('Unusable bootstrap fit; see receipt, no replicate deleted')
        models.append(model)
        print(f'bootstrap {rep+1}/{replicates} seconds={time.monotonic()-start:.1f}',flush=True)
    rows=[]
    for task in tasks:
        for target in task['targets']:
            query=d.loc[target['query_ids']]
            for k in task['ks']:
                support=d.loc[target['support_pool'][:k]]
                conditional=[]
                for model in models:
                    post=model.target_posterior(support)
                    conditional.append((model.predict_location(query),post,model.sigma_))
                lowers=[]
                for j in range(len(query)):
                    def cdf(y):
                        if k==0:
                            return np.mean([ndtr((y-mu[j])/np.hypot(model.sigma_,model.tau_))
                                            for model,(mu,post,sigma) in zip(models,conditional)])
                        if np.all(support.event.to_numpy()==1):
                            return np.mean([ndtr((y-mu[j]-post['mean'])/
                                                np.sqrt(sigma**2+post['variance']))
                                            for mu,post,sigma in conditional])
                        return np.mean([ndtr((y-mu[j]-post['u'])/sigma)@post['weight']
                                        for mu,post,sigma in conditional])
                    lo=min(mu[j]+post['u'].min()-12*sigma for mu,post,sigma in conditional)
                    hi=max(mu[j]+post['u'].max()+12*sigma for mu,post,sigma in conditional)
                    lowers.append(brentq(lambda y:cdf(y)-.1,lo,hi,xtol=1e-9))
                for j,(_,record) in enumerate(query.iterrows()):
                    row={c:record[c] for c in ['row_id','dataset_id','group_id','doi',
                                              'log_life','event','log_stress','stress_amplitude','load_ratio']}
                    row.update(panel=task['panel'],seed=task['seed'],model='hierarchical_population_bootstrap',
                               k=k,bound='raw',log_lower=lowers[j],n_bootstrap=replicates)
                    rows.append(row)
    pd.DataFrame(rows).to_csv(output/'predictions.csv',index=False)
    (output/'signature.json').write_text(json.dumps({'external_manifest_sha256':digest(external_folder/'frozen_splits.json'),
        'code_sha256':digest(Path(__file__)),'model_sha256':digest(ROOT/'src/v2_models.py'),
        'replicates':replicates,'seed':27021,'seconds':time.monotonic()-start},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--external',default=str(ROOT/'data/processed/v2/external_fulltraining'))
    p.add_argument('--output',default=str(ROOT/'results/v2/external_bootstrap'));p.add_argument('--replicates',type=int,default=20)
    a=p.parse_args();bootstrap(a.external,a.output,a.replicates)
