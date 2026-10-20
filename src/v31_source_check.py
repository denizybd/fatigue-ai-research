"""Verify the frozen manual source gate against licensed raw first exposures.

The thesis page/ID crosswalk is an audited source fact, not regenerated from OCR
or inferred from model outcomes. No thesis full text is needed in the archive.
"""
from pathlib import Path
import hashlib,json
import pandas as pd
from src.v3_prepare import ROOT,digest

def check():
    for path,expected_sha in {
      'data/processed/v2/strict_fulltraining/cohort.csv':'a582866ead9f6bc79b53dd4ec6bac27877dddc22d5bf7594ba7e6687eaf93ba3',
      'data/processed/v3/new_candidates/dastgerdi.csv':'cb76dcfaf7de5e18cc48a5f9db7a88aeaaacff617fbd4b9e07af80847fcebfda'
    }.items():assert digest(ROOT/path)==expected_sha,path
    folder=ROOT/'data/external_v3/continuation_papers'
    raw=folder/'data_fatigue_merot.csv'
    assert digest(raw)=='bb5e9ce46a7f7827aef50f2188f059c6833ca3dab9110cec1613c628a2e16b5e'
    d=pd.read_csv(raw,skiprows=[1]);d['record']=range(1,len(d)+1)
    final=folder/'merot_first_exposure_unique_physical70_verified.csv'
    assert digest(final)=='2b6b775484ba5eb25f0d5a90ff944bac175f092c74ceb3387e00d18cf608e618'
    f=pd.read_csv(final)
    keyed=d.dropna(subset=['Numéro plateau','Numéro eprouvette'])
    collisions=keyed.groupby(['Numéro plateau','Numéro eprouvette']).Sample.nunique()
    collisions=set(collisions[collisions>1].index)
    zero=d[pd.to_numeric(d.Step)==0].copy()
    counts=zero.groupby('Sample').size()
    expected=zero[(zero.Sample.map(counts)==1)&zero['Numéro plateau'].notna()&zero['Numéro eprouvette'].notna()]
    expected=expected[[tuple(z) not in collisions for z in expected[['Numéro plateau','Numéro eprouvette']].to_numpy()]]
    assert len(expected)==len(f)==70 and set(expected.Sample)==set(f.Sample)
    r=d.set_index('record')
    builds={2:'FS18-019',3:'FS18-020',4:'FS19-006'}
    powders={2:'TLS 0993/1/1',3:'TLS 0993/1/1',4:'TLS 1051/1/1'}
    for row in f.itertuples(index=False):
        x=r.loc[row.source_data_record_index]
        assert row.Sample==x.Sample and row.Step==0
        assert row.source_plate_id==x['Numéro plateau'] and row.source_specimen_number_on_plate==x['Numéro eprouvette']
        assert row.source_build_id==builds[row.source_plate_id]
        assert row.source_powder_batch_id==powders[row.source_plate_id]
        assert row.sigma_a_MPa==float(x.s_amp) and row.sigma_max_MPa==float(x.s_max)
        assert row.stress_ratio_R==float(x.R) and row.cycles_first_block==float(x.N)
        assert row.event==int(x.Fracture=='oui')
        assert row.treatment_batch_raw==x.Batch
    print(json.dumps({'raw_sha256':digest(raw),'frozen_source_gate_sha256':digest(final),
       'first_step_rows':len(zero),'retained_physical_specimens':len(f),'status':'PASS',
       'manual_source_fact':'Thesis build/long-ID map independently visually audited; no model-based inference'}))
if __name__=='__main__':check()
