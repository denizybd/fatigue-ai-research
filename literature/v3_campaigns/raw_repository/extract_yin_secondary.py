"""Decode a public JMP table without executing its embedded author scripts."""
from pathlib import Path
import sys, json, hashlib
import pandas as pd

LIT=Path(__file__).resolve().parent
ROOT=LIT.parents[2]
OUT=ROOT/'data/external_v3/raw_repository/yin2026_secondary'
vendor=next((LIT/'jmpio_vendor').glob('marty*'))
sys.path.insert(0,str(vendor/'src'))
import jmpio

d=jmpio.read_jmp(OUT/'Ar_vs_N2_JMP_Final.jmp')
d.to_csv(OUT/'author_jmp_allrows_extracted.csv',index=False)
a=d[d['Source'].isin(['APL_FY24','APL_FY23'])].copy()
assert len(a)==18 and a['Specimen ID'].nunique()==18
assert set(a['Gas'])=={'Argon','Nitrogen'}
assert set(a['R'])=={-1.0} and set(a['Test Method'])=={'RBF'}
assert set(a['Fabrication'])=={'L-W-DED'} and set(a['Rate (Hz)'])=={100.0}
residual=(a['Bending Stress (ksi)']*6.8947572932-a['Bending Stress (MPa)']).abs().max()
assert residual<1e-9
rows=[]
for index,r in a.iterrows():
    n=r['Cycles'];stress=r['Bending Stress (MPa)'];status=r['Failure/Run-out']
    complete=pd.notna(n) and pd.notna(stress) and status in ['Failure','Run-out']
    rows.append(dict(row_id='yin2026_'+r['Specimen ID'],specimen_id=r['Specimen ID'],
                     original_jmp_row_1based=index+1,source_dataset_doi='10.17632/h97k6w9vm5.1',
                     source_url='https://data.mendeley.com/datasets/h97k6w9vm5/1',
                     source_author=r['Source'],gas_author=r['Gas'],
                     condition_id=r['Source']+'_'+r['Gas'],
                     build_id='',powder_or_wire_batch_id='',batch_mapping_verified=False,
                     strict_eligible=False,in_primary_scope=False,
                     exclusion_reason='laser_wire_DED_and_rotating_beam;physical_build_map_absent',
                     material='316L',am_type='laser wire DED',machine=r['Fabrication Machine'],
                     build_orientation=r['Build Orientation'],loading_mode='rotating beam',
                     load_ratio=r['R'],frequency_Hz=r['Rate (Hz)'],
                     cycles_observed=n if pd.notna(n)else '',
                     nominal_bending_stress_MPa=stress if pd.notna(stress)else '',
                     stress_amplitude_MPa=stress if pd.notna(stress)else '',
                     stress_definition='nominal_bending_stress;amplitude_equals_maximum_for_R_minus1',
                     failure_status_author=status,event=int(status=='Failure')if complete else '',
                     runout=int(status=='Run-out')if complete else '',
                     fatigue_record_complete=complete,notes_author=r['Notes'],license='CC-BY-4.0'))
o=pd.DataFrame(rows);o.to_csv(OUT/'yin_named18_outside_scope.csv',index=False)
o[o['fatigue_record_complete']].to_csv(OUT/'yin_complete14_outside_scope.csv',index=False)
receipt=dict(parser='jmpio-python',commit='5e9d49f',
             source='https://github.com/martyblaber/jmpio-python',
             local_patch='column.py casts each NumPy length scalar to Python int before byte-offset arithmetic; fixes NumPy2 overflow. Original downloaded source ZIP preserved.',
             all_table_rows=len(d),all_table_columns=len(d.columns),named_APL_FY23_FY24_rows=len(o),
             complete_rows=int(o['fatigue_record_complete'].sum()),
             failures=int((o.event==1).sum()),runouts=int((o.runout==1).sum()),
             maximum_unit_conversion_absolute_residual_MPa=float(residual),
             strict_build_mapped_campaigns=0, embedded_scripts_executed=False,
             no_model_fitting_performed=True)
(LIT/'yin2026_extraction_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
