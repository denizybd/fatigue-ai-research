"""Source-backed virgin blocks; no equivalent life or later-step information."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from src.v3_prepare import ROOT,digest
BUILD={2:'FS18-019',3:'FS18-020',4:'FS19-006'}
POWDER={2:'TLS0993/1/1',3:'TLS0993/1/1',4:'TLS1051/1/1'}
CONDITION={'Référence air':'reference_air','Corrodé air':'precorroded_air',
 'Electroérodé air':'edm_defect_air','Usiné air':'machined_defect_air',
 'Petit volume air':'small_volume_air'}

def prepare(source,output):
    source=Path(source).resolve();d=pd.read_csv(source)
    d=d[(d.environment=='air')&(d.temperature_C==20)].copy()
    assert len(d)>0
    for field in ['physical_plate_semantics_verified','primary_axial_control_mode_verified']:
        assert d[field].astype(str).str.lower().isin(['1','true','1.0']).all(),field
    assert d.first_step_candidate_eligible.astype(str).str.lower().isin(['1','true','1.0']).all()
    assert (d.Step==0).all();assert d.Sample.is_unique
    d['author_sample_alias']=d.Sample
    d['author_plate_number']=d.source_plate_id.astype(int)
    d['author_position_on_plate']=d.source_specimen_number_on_plate.astype(int)
    d['build_id']=d.author_plate_number.map(BUILD)
    d['powder_batch_id']=d.author_plate_number.map(POWDER)
    assert d.build_id.notna().all() and d.powder_batch_id.notna().all()
    d['specimen_id']=d.Sample
    d['row_id']=['merot_'+b+'_position'+str(p) for b,p in zip(d.build_id,d.author_position_on_plate)]
    assert d.row_id.is_unique
    condition=d.treatment_batch_raw.map(CONDITION);assert condition.notna().all()
    d['dataset_id']=['merot_'+b+'_'+c+'_Rminus1' for b,c in zip(d.build_id,condition)]
    d['campaign_id']='merot2021_2022_one_author_program';d['group_id']=d.campaign_id
    eligible=d.primary_nominal_stress_eligible.astype(str).str.lower().isin(['1','true','1.0'])
    d['panel']=np.where(eligible,'external_identity_qualified_firstblock',
                       'external_identity_localstress_firstblock')
    d['identity_gate']='author_sample_plate_position_build_and_powder_crosswalk_verified'
    d['load_ratio']=d.stress_ratio_R;d['stress_amplitude']=d.sigma_a_MPa
    d['log_stress']=np.log10(d.stress_amplitude);d['log_life']=np.log10(d.cycles_first_block)
    d['cycles_observed']=d.cycles_first_block
    assert np.allclose(d.sigma_a_MPa,d.sigma_max_MPa*(1-d.load_ratio)/2)
    assert (d.load_ratio==-1).all()
    assert d.event.isin([0,1]).all()
    d['doi']='10.1016/j.ijfatigue.2021.106552'
    d['source_dataset_doi']='10.5281/zenodo.6653187'
    d['fit_exclude_groups']='10.1016/j.ijfatigue.2021.106552;10.1016/j.engfracmech.2022.108883;10.1016/j.ijfatigue.2025.109107'
    # Later steps, damage-equivalent lives and postfailure defect observations
    # never enter normalized benchmark rows or the selection function.
    keep=['row_id','specimen_id','author_sample_alias','author_plate_number','author_position_on_plate',
      'build_id','powder_batch_id','dataset_id','campaign_id','group_id','panel','identity_gate',
      'doi','source_dataset_doi','fit_exclude_groups','load_ratio','stress_amplitude','log_stress',
      'cycles_observed','log_life','event','treatment_batch_raw','environment','temperature_C',
      'frequency_Hz','endpoint_type','source_data_record_index','source_sha256']
    keep+=['stress_definition','primary_nominal_stress_eligible']
    out=Path(output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    d[keep].to_csv(out,index=False)
    receipt={'source':str(source.relative_to(ROOT)),'source_sha256':digest(source),
      'output':str(out.relative_to(ROOT)),'output_sha256':digest(out),
      'rows':len(d),'failures':int(d.event.sum()),'right_censors':int((1-d.event).sum()),
      'build_ids':sorted(d.build_id.unique()),'powder_batch_ids':sorted(d.powder_batch_id.unique()),
      'author_campaigns':1,'conditions':d.groupby('dataset_id').size().to_dict(),
      'panels':d.groupby('panel').size().to_dict(),
      'source_build_table':'Merot2021 thesis printedp61/Table2.1 (PDFp85); source audit retained separately',
      'timing':'exploratory source recovery; fixed first-exposure protocol before extraction/fits',
      'protocol_extension_sha256':digest(ROOT/'protocols/v3/virgin_first_exposure_extension.txt')}
    out.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--output',default=str(ROOT/'data/processed/v3/firstblock/merot52.csv'))
    a=p.parse_args();prepare(a.source,a.output)
