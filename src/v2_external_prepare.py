"""Freeze random and chronological external support/query episodes."""
from __future__ import annotations
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from src.v2_prepare import ROOT,digest,rank,SEEDS


def prepare(historical,output,calibration=True):
    historical,output=Path(historical),Path(output)
    raw=ROOT/'data/external_v2/trombley2025/fatigue_asbuilt_available129.csv'
    x=pd.read_csv(raw)
    x['dataset_id']=x.condition_id
    x['group_id']='trombley2025_one_campaign'
    x['doi']='10.1038/s41598-025-97031-1'
    h=pd.read_csv(historical/'cohort.csv')
    output.mkdir(parents=True,exist_ok=True)
    common=pd.concat([h,x],ignore_index=True)
    common.to_csv(output/'cohort.csv',index=False)
    sizes=h.groupby('dataset_id').size()
    eligible=sizes[sizes>=11].index.tolist()
    candidate_blocks=sorted(h[h.dataset_id.isin(eligible)].group_id.unique())
    blocks=sorted(h.group_id.unique())
    tasks=[]
    for mechanism in ['random','chronological']:
        for seed in (SEEDS if mechanism=='random' else [0]):
            m=min(9,max(0,len(blocks)-4)) if calibration else 0
            cal=rank(candidate_blocks,'v2-external',seed,'calibration')[:m]
            fit=sorted(set(blocks)-set(cal))
            chosen=[]
            for b in cal:
                cs=h[(h.group_id==b)&h.dataset_id.isin(eligible)].dataset_id.unique()
                c=rank(cs,'v2-external',seed,b,'cal-curve')[0]
                order=rank(h[h.dataset_id==c].row_id,'v2-external',seed,'cal-support-query')
                chosen.append({'block':b,'curve':c,'support_pool':order[:10],
                               'query_id':order[10],'query_ids':order[10:]})
            targets=[]
            for c,d in x.groupby('dataset_id',sort=True):
                if mechanism=='random':
                    order=rank(d.row_id,'v2-external',seed,'support-query')
                else:
                    d=d.copy();d['parsed_date']=pd.to_datetime(d.test_date_author,format='%m/%d/%Y',errors='raise')
                    tie={rid:i for i,rid in enumerate(rank(d.row_id,'v2-external','chronological-tie'))}
                    d['tie']=d.row_id.map(tie)
                    order=d.sort_values(['parsed_date','tie']).row_id.tolist()
                targets.append({'curve':c,'support_pool':order[:10],'query_ids':order[10:]})
            tasks.append({'panel':'external_'+mechanism,'seed':seed,
                          'outer':'trombley2025_one_campaign','ks':[0,3,5,10],
                          'fit_blocks':fit,'cal_blocks':cal,'calibration':chosen,'targets':targets})
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),
              'external_raw_sha256':digest(raw),'historical_sha256':digest(historical/'cohort.csv'),
              'cohort_sha256':digest(output/'cohort.csv'),'calibration_enabled':calibration,
              'external_unique_specimens':len(x),'external_conditions':x.dataset_id.nunique(),
              'external_independent_campaign_count':1,'tasks':tasks,
              'license':'External Materials Commons license unspecified; do not redistribute raw/normalized external records.'}
    manifest['protocol_hashes']={str(p.relative_to(ROOT)):digest(p)
        for p in sorted((ROOT/'protocols/v2').glob('*.md'))}
    manifest['historical_split_sha256']=digest(historical/'frozen_splits.json')
    (output/'frozen_splits.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='tasks'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--historical',default=str(ROOT/'data/processed/v2/strict'))
    p.add_argument('--output',default=str(ROOT/'data/processed/v2/external'))
    p.add_argument('--no-calibration',action='store_true');a=p.parse_args()
    prepare(a.historical,a.output,not a.no_calibration)
