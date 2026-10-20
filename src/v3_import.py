"""Explicit adapters for audited candidate files; no invented build identities."""
from pathlib import Path
import numpy as np
import pandas as pd
from src.v3_prepare import ROOT

def prepare():
    output=ROOT/'data/processed/v3/new_candidates';output.mkdir(parents=True,exist_ok=True)
    files=[]
    for slug,filename in [('tomaszewski','tomaszewski2023_all137_secondary.csv'),
                          ('diller','diller2024_asbuilt29_secondary.csv')]:
        d=pd.read_csv(ROOT/'data/external_v3/raw_repository'/filename)
        d['dataset_id']=d.condition_id;d['campaign_id']=slug+'_one_source_campaign'
        d['group_id']=d.campaign_id;d['panel']='external_new_specimen_only'
        d['identity_gate']='author_specimen_id_no_verified_build_mapping'
        d['log_stress']=np.log10(d.stress_amplitude);d['log_life']=np.log10(d.cycles_observed)
        d['doi']=d.source_doi;d['fit_exclude_groups']=''
        p=output/(slug+'.csv');d.to_csv(p,index=False);files.append(p)
    d=pd.read_csv(ROOT/'data/external_v3/paper_supplements/dastgerdi2023_uninterrupted_pilot6.csv')
    d['row_id']=d.canonical_specimen_id;d['specimen_id']=d.author_specimen_id
    d['dataset_id']='dastgerdi2023_uninterrupted'
    d['group_id']='dastgerdi2022_2023_precautionary';d['campaign_id']=d.group_id
    d['panel']='external_small_temperature_unstated'
    d['identity_gate']='source_backed_single_build_no_author_build_code'
    d['stress_amplitude']=d.stress_amplitude_mpa;d['load_ratio']=d.stress_ratio
    d['log_stress']=np.log10(d.stress_amplitude);d['log_life']=np.log10(d.cycles_observed)
    d['doi']=d.source_id
    d['fit_exclude_groups']='10.1016/j.ijfatigue.2022.107025'
    p=output/'dastgerdi.csv';d.to_csv(p,index=False);files.append(p)
    print('\n'.join(str(p) for p in files))
if __name__=='__main__':prepare()
