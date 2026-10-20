"""Freeze common queries before any phase-3 predictions; raw inputs untouched."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from src.v3_design import rank
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prepare(additions,output,include_previous=True):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    hp=ROOT/'data/processed/v2/strict_fulltraining/cohort.csv'
    h=pd.read_csv(hp)
    h['panel']='historical_reused';h['identity_gate']='database_curve_not_build'
    h['campaign_id']=h.group_id;h['specimen_id']=h.row_id
    h['fit_exclude_groups']=h.group_id
    inputs=[{'path':str(hp.relative_to(ROOT)),'sha256':digest(hp)}]
    frames=[h]
    if include_previous:
        tp=ROOT/'data/external_v2/trombley2025/fatigue_asbuilt_available129.csv'
        t=pd.read_csv(tp);t['dataset_id']=t.condition_id
        t['group_id']='trombley2025_one_campaign';t['campaign_id']=t.group_id
        t['doi']='10.1038/s41598-025-97031-1';t['panel']='external_previous_unmapped_build'
        t['identity_gate']='author_specimen_id_no_build_mapping'
        t['specimen_id']=t.row_id;t['fit_exclude_groups']=''
        frames.append(t);inputs.append({'path':str(tp.relative_to(ROOT)),'sha256':digest(tp)})
    for source in additions:
        p=Path(source).resolve();d=pd.read_csv(p)
        required={'row_id','dataset_id','group_id','campaign_id','specimen_id',
                  'log_stress','log_life','event','load_ratio','panel','identity_gate'}
        if not required.issubset(d):raise ValueError((str(p),sorted(required-set(d))))
        if 'fit_exclude_groups' not in d:d['fit_exclude_groups']=''
        frames.append(d);inputs.append({'path':str(p.relative_to(ROOT)),'sha256':digest(p)})
    cohort=pd.concat(frames,ignore_index=True)
    assert cohort.row_id.is_unique,'duplicate specimen ID'
    assert np.isfinite(cohort[['log_stress','log_life']].to_numpy()).all()
    assert cohort.event.isin([0,1]).all()
    cohort.to_csv(output/'cohort.csv',index=False)
    tasks=[]
    for dataset,d in cohort.groupby('dataset_id',sort=True):
        if len(d)<6:continue
        assert d.campaign_id.nunique()==1 and d.group_id.nunique()==1
        nq=max(3,int(np.floor(.4*len(d))))
        ks=[0]+[k for k in [3,5,10] if k<=len(d)-nq]
        if len(ks)==1:continue
        for seed in range(10):
            order=rank(d.row_id,'v3-common-query',seed,dataset)
            query,pool=order[:nq],order[nq:]
            exclude=set(str(d.fit_exclude_groups.iloc[0]).split(';'))-{''}
            if d.panel.iloc[0]=='historical_reused':exclude.add(str(d.group_id.iloc[0]))
            tasks.append({'dataset_id':dataset,'campaign_id':str(d.campaign_id.iloc[0]),
                'panel':str(d.panel.iloc[0]),'identity_gate':str(d.identity_gate.iloc[0]),
                'seed':seed,'ks':ks,'query_ids':query,'pool_ids':pool,
                'fit_blocks':sorted(set(h.group_id)-exclude)})
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),
        'timing':'exploratory; source outcomes and phase-2 results already read',
        'protocol_sha256':digest(ROOT/'protocols/v3/frozen_design.txt'),
        'inputs':inputs,'cohort_sha256':digest(output/'cohort.csv'),'tasks':tasks,
        'common_query_assertion':'Each task has one query/pool shared by every policy/model/cap',
        'n_rows':len(cohort),'n_tasks':len(tasks)}
    if 'external_identity_qualified_firstblock' in set(cohort.panel):
        rel='protocols/v3/virgin_first_exposure_extension.txt'
        manifest['extension_protocols']={rel:digest(ROOT/rel)}
    (output/'frozen_splits.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ['tasks']},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--additions',nargs='*',default=[])
    p.add_argument('--output',default=str(ROOT/'data/processed/v3/common'))
    p.add_argument('--without-previous',action='store_true',help='Omit unused earlier external campaign from a new extension replay')
    a=p.parse_args();prepare(a.additions,a.output,include_previous=not a.without_previous)
