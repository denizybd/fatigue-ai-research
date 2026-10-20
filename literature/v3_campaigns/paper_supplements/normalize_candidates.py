from pathlib import Path
import csv,json,math,hashlib
L=Path('literature/v3_campaigns/paper_supplements'); D=Path('data/external_v3/paper_supplements')
def write(path,rows):
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
rows=[]
for group,stress,values in [(1,170,[122877,145320,125763,131932]),(2,190,[96955,99650,89548,104003])]:
 for i,n in enumerate(values):
  sid=f'sample{group}-'+(str(i+1) if i<3 else 'XCT')
  rows.append(dict(campaign_id='dastgerdi2023_single_build',source_id='10.1016/j.addma.2023.103559',author_specimen_id=sid,author_notation=f'N_f,{sid}',canonical_specimen_id='dastgerdi2023:'+sid,author_build_id='',canonical_build_id='dastgerdi2023:single_build_section2.1',build_id_origin='analyst canonical label for explicitly reported single physical build; no author build code',specimen_build_mapping_evidence='Section2.1 journalp2/PDFp3: same platform in a single build; applies to all test samples',specimen_id_evidence='Table1 journalp3/PDFp4',material='316L',process='LPBF EOS M290',orientation_degrees=90,surface='as_built_net_shape',heat_treatment='none',stress_amplitude_mpa=stress,stress_ratio=.1,frequency_hz=10,cycles_observed=n,event=1,runout=0,load_control='force',loading_mode='uniaxial',amplitude_schedule='constant',interrupted_for_xct=int(i==3),temperature_c='',temperature_evidence='test temperature not stated in Methods2.2; do not silently impute room temperature',life_endpoint='total fatigue life / final failure',observation_kind='pretest' if i<3 else 'interrupted_XCT',metadata_identity_qualified=1,strict_rt_admitted=0,pilot_usable_if_rt_not_required=int(i<3),source_family_block='dastgerdi_2022_2023_precautionary',fresh_confirmatory_independence=0,freshness_note='2023 table predates protocol; 2-XCT near-matches prior AM2022 point from 2022 same-author paper; entire family must be removed from any source training if used as target',data_license='CC BY 4.0 published article/table; raw CT data available on request',source_url='https://doi.org/10.1016/j.addma.2023.103559',source_pdf='literature/v3_campaigns/paper_supplements/Dastgerdi2023.pdf'))
write(D/'dastgerdi2023_identity_records.csv',rows)
# Preserve every table row. Numeric specimen IDs are NOT globally disambiguated without the PDF color/underline coding.
liang=[]
AB=[(26,120,711318),(50,100,1090413),(41,90,None),(33,100,1399298),(24,90,None),(20,100,1222525),(22,90,1588420),(9,80,None),(9,150,389131),(37,90,None),(37,130,563075),(46,100,1420531),(17,110,969382),(29,160,281144)]
SP=[(12,130,866574),(25,120,1353541),(48,110,None),(48,150,725523),(39,120,950773),(36,110,None),(36,140,1062775),(35,120,1162360),(3,110,None),(19,120,1434796),(27,110,None),(15,120,1278695),(8,170,447987),(10,180,329954),(31,200,250285)]
for surface,vals in [('as_built',AB),('simple_polished',SP)]:
 seen=set()
 for order,(sid,stress,n) in enumerate(vals,1):
  liang.append(dict(source_id='tel-02951486',linked_publication='10.1016/j.ijfatigue.2022.106843',table='AppendixA TableA-3 thesisp198',surface=surface,table_row_within_surface=order,author_numeric_sample_number=sid,stress_amplitude_mpa=stress,source_rupture_cycles='-' if n is None else n,cycles_observed_if_dash_is_runout=2000000 if n is None else n,event_if_dash_is_runout=int(n is not None),numeric_id_seen_previously_within_surface=int(sid in seen),author_tray='',tray_mapping_status='UNVERIFIED: TableA.2 identifies tray1 blue+italic and tray2 red+underlined; color unavailable in indexed HTML',physical_specimen_id='',admitted=0,retention_status='raw textual table transcription only; do not fit or label independent specimens',method='SectionIII.1.1 ambient air and temperature; stress control; R=-1;15Hz;2e6 cycle threshold',source_url='https://www.researchgate.net/publication/344425485_high_cycle_fatigue_behavior_of_additive_manufactured_stainless_steel_316L_free_surface_effect_and_microstructural_heterogeneity'))
  seen.add(sid)
write(L/'liang2020_tableA3_text_transcription_quarantine.csv',liang)
# Audit exact author table lifetimes against previous digitized data: nearest coordinates are flags, not proof of physical identity.
prior=list(csv.DictReader(open('data/processed/primary.csv')))
overlap=[]
for row in rows:
 family=[p for p in prior if p['source_id']=='10.1016/j.ijfatigue.2022.107025']
 near=min(family,key=lambda p:(math.log10(float(p['cycles_observed'])/row['cycles_observed'])/.02)**2+((float(p['stress_amplitude'])-row['stress_amplitude_mpa'])/2)**2)
 dr=abs(float(near['cycles_observed'])/row['cycles_observed']-1); ds=abs(float(near['stress_amplitude'])-row['stress_amplitude_mpa'])
 overlap.append(dict(author_specimen_id=row['author_specimen_id'],stress_amplitude_mpa=row['stress_amplitude_mpa'],cycles=row['cycles_observed'],prior_row_id=near['row_id'],prior_dataset_id=near['dataset_id'],prior_source_id=near['source_id'],prior_stress_amplitude_mpa=near['stress_amplitude'],prior_cycles=near['cycles_observed'],relative_cycle_difference=dr,absolute_stress_difference_mpa=ds,near_coordinate_flag=int(dr<.025 and ds<2),interpretation='possible reuse; whole source-family precautionary block' if dr<.025 and ds<2 else 'not a near-coordinate match; absence does not certify independence'))
write(L/'dastgerdi2023_prior_overlap.csv',overlap)
print(json.dumps(dict(dastgerdi_records=len(rows),dastgerdi_uninterrupted=sum(x['pilot_usable_if_rt_not_required'] for x in rows),liang_table_rows=len(liang),liang_distinct_numeric_ids_by_surface={s:len({x['author_numeric_sample_number'] for x in liang if x['surface']==s}) for s in ['as_built','simple_polished']},liang_color_verified=False,near_coordinate_flags=sum(x['near_coordinate_flag'] for x in overlap)),indent=2))
