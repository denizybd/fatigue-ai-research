"""Independent raw-to-first-block/source-build audit; does not fit any model."""
from pathlib import Path
import hashlib,json,re
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
DATA=ROOT/'data/external_v3/continuation_papers'
rawpath=DATA/'data_fatigue_merot.csv'
raw=pd.read_csv(rawpath)
raw=raw[pd.to_numeric(raw.Step,errors='coerce').notna()].copy()
for key in ['Step','N','s_max','s_amp','R','Temp','f','Numéro plateau','Numéro eprouvette']:
    raw[key]=pd.to_numeric(raw[key],errors='coerce')
assert len(raw)==262 and raw.Sample.nunique()==103
assert np.all(raw.groupby('Sample').Step.min()==0)
assert set(raw.Fracture)=={'oui','non'}
np.testing.assert_allclose(raw.s_amp,raw.s_max*(1-raw.R)/2,atol=0,rtol=0)
assert np.isfinite(raw.N).all() and (raw.N>0).all()
identities=raw[['Sample','Numéro plateau','Numéro eprouvette']].drop_duplicates()
assert identities.Sample.is_unique
count=identities.groupby(['Numéro plateau','Numéro eprouvette']).Sample.nunique()
collisions=set(count[count>1].index)
first=raw[raw.Step==0].copy()
firstcount=first.groupby('Sample').size()
unique=first[first.Sample.isin(firstcount[firstcount==1].index)].copy()
complete=unique['Numéro plateau'].notna()&unique['Numéro eprouvette'].notna()
collision=np.array([(p,n) in collisions for p,n in zip(unique['Numéro plateau'],unique['Numéro eprouvette'])])
expected=unique[complete&~collision].copy().set_index('Sample')
assert len(expected)==70
assert 'D0' not in expected.index and 'K2' not in expected.index
for alias,sub in raw.groupby('Sample'):
    if ((sub.Step==0)&(sub.Fracture=='oui')).any():assert sub.Step.max()==0

final=pd.read_csv(DATA/'merot_first_exposure_unique_physical70_verified.csv').set_index('Sample')
assert set(final.index)==set(expected.index)
assert final.canonical_physical_key.is_unique and np.all(final.Step==0)
for col,rawcol in [('cycles_first_block','N'),('sigma_a_MPa','s_amp'),('sigma_max_MPa','s_max'),
                   ('stress_ratio_R','R'),('temperature_C','Temp'),('frequency_Hz','f'),
                   ('source_plate_id','Numéro plateau'),('source_specimen_number_on_plate','Numéro eprouvette')]:
    np.testing.assert_array_equal(final[col],expected.loc[final.index,rawcol])
np.testing.assert_array_equal(final.event,(expected.loc[final.index,'Fracture']=='oui').astype(int))
np.testing.assert_allclose(final.log10_cycles_first_block,np.log10(final.cycles_first_block),atol=1e-13)
for forbidden in ['N_basquin','sum_N_basquin','s_corr_basquin','s_corr_nicholas','Defect_nature',
                  'Surface_defect','Trust','Type','contour','Def_init_SEM_size_mean']:
    assert forbidden not in final

# Transcribed after visual inspection of thesis PDF84-85 / Table2.1, rather than
# importing the other agent's normalizer or its source-build dictionary.
builds={2:('FS18-019','TLS 0993/1/1'),3:('FS18-020','TLS 0993/1/1'),4:('FS19-006','TLS 1051/1/1')}
text=(ROOT/'literature/v3_campaigns/continuation_papers/Merot2021_thesis.txt').read_text()
for alias,row in final.iterrows():
    plate,position=int(row.source_plate_id),int(row.source_specimen_number_on_plate)
    assert (row.source_build_id,row.source_powder_batch_id)==builds[plate]
    assert row.source_full_specimen_reference==f'PM-{plate:02d}-F{position:02d}'
    pattern=re.escape(row.source_full_specimen_reference)+r'\s+'+re.escape(alias)+r'\b'
    assert re.search(pattern,text),(alias,row.source_full_specimen_reference)

air=expected[(expected.Temp==20)&expected.Batch.str.endswith(' air')]
nominal=air[air.Batch!='Petit volume air']
small=air[air.Batch=='Petit volume air']
assert (len(air),len(nominal),len(small))==(52,43,9)
for name,truth in [('merot_first_exposure_air_nominal43.csv',nominal),
                   ('merot_first_exposure_air_localstress9_exploratory.csv',small)]:
    table=pd.read_csv(DATA/name)
    assert set(table.Sample)==set(truth.index)
    np.testing.assert_array_equal(table.event,(truth.loc[table.Sample,'Fracture']=='oui').astype(int))
assert np.all(air.R==-1) and np.all(air[air.Fracture=='non'].N==1_000_000)
family={'10.1016/j.ijfatigue.2021.106552','10.1016/j.engfracmech.2022.108883','10.1016/j.ijfatigue.2025.109107'}
historical=pd.read_csv(ROOT/'data/processed/v2/strict_fulltraining/cohort.csv')
assert set(historical.group_id).isdisjoint(family)
if 'source_id' in historical:assert set(historical.source_id).isdisjoint(family)
collision_rows=[]
for (plate,position) in sorted(collisions):
    names=identities[(identities['Numéro plateau']==plate)&(identities['Numéro eprouvette']==position)].Sample.tolist()
    collision_rows.append({'plate':int(plate),'position':int(position),'aliases':names})
receipt={'raw_sha256':hashlib.sha256(rawpath.read_bytes()).hexdigest(),
         'protocol_sha256':hashlib.sha256((ROOT/'protocols/v3/virgin_first_exposure_extension.txt').read_bytes()).hexdigest(),
         'raw_step_rows':len(raw),'author_aliases':raw.Sample.nunique(),'step0_rows':len(first),
         'repeated_step0_aliases':firstcount[firstcount>1].to_dict(),
         'complete_coordinate_missing_simple_aliases':int((~complete).sum()),
         'colliding_physical_keys':collision_rows,'simple_aliases_excluded_by_any_alias_collision':int(collision.sum()),
         'verified_complete_unique_first_blocks':70,'air20C_first_blocks':52,
         'nominal_air_primary':43,'local_stress_air_sensitivity':9,'salt_spray35C_separate':18,
         'air_initial_events':int((air.Fracture=='oui').sum()),'air_initial_censors':int((air.Fracture=='non').sum()),
         'raw_endpoint_and_stress_conversion_pass':True,'source_build_and_powder_mapping_pass':True,
         'no_later_outcome_or_postfailure_covariates_retained':True,'historical_family_exclusion_pass':True,
         'physical_builds':builds,'campaign_count':1,
         'source_review':'ThesisPDF84/85 physicalIDs+Table2.1 visually verified;PDF111-115 geometry/forcecontrol/air20C methods;PDF279/280 TablesG.1/G.2 reviewed',
         'claim_boundary':'recorded virgin first blocks after conservative identity quarantine; retrospective source recovery, not a new physical campaign or original full-step-row rehabilitation',
         'model_fits_performed':False,'all_checks_pass':True}
(OUT/'extraction_audit_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ['colliding_physical_keys','physical_builds']},indent=2))
