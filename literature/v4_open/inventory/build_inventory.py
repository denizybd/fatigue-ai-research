"""Inventory existing public fatigue evidence; no cohort admission or model fitting."""
from pathlib import Path
import json,hashlib,datetime
import pandas as pd
import numpy as np
from scipy.io import loadmat
ROOT=Path('/Users/deniz2/Documents/ChatGPT/fatigue-ai-research')
OUT=ROOT/'literature/v4_open/inventory';OUT.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def records(x):
 if isinstance(x,dict):return [x]
 if isinstance(x,np.ndarray):return x.ravel().tolist()
 return x if isinstance(x,list) else []
def raw_text(x):
 if isinstance(x,str):return x or None
 a=np.asarray(x) if x is not None else np.asarray([])
 return None if not a.size else (str(a.item()) if a.size==1 else json.dumps(a.tolist()))
def counts(d):
 return {'rows':len(d),'database_conditions':int(d.dataset_id.nunique()),'source_dois':int(d.doi.nunique()),'failures':int(d.event.sum()),'right_censors':int((d.event==0).sum())}
paths={'ordinary1473':'data/processed/ss316l_lpbf_all.csv','old_primary1126':'data/processed/primary.csv','strict309':'data/processed/v2/strict_fulltraining/cohort.csv','old_broader565':'data/processed/v2/broader_fulltraining/cohort.csv','all_except_stepped1028':'data/processed/v2/all/cohort.csv','coordinate_dedup_sensitivity942':'data/processed/primary_deduplicated_sensitivity.csv'}
sets={k:pd.read_csv(ROOT/v) for k,v in paths.items()}
base=sets['ordinary1473'].copy();primary=sets['old_primary1126'];strict=sets['strict309']
gate=pd.read_csv(ROOT/'literature/provenance_v2/final_source_gate.csv').fillna('')
correction=pd.read_csv(ROOT/'literature/provenance_v2/frozen_point_corrections.csv')
base['event_database']=base.event;base['runout_database']=base.runout
for c in ['event','runout','thermal','heat_temperature','heat_time']:base[c+'_source_audited']=base[c]
base['source_correction_fields']=''
for r in correction.to_dict('records'):
 z=base.row_id==r['row_id'];value=r['corrected_value'] if r['field']=='thermal' else (float(r['corrected_value']) if pd.notna(r['corrected_value']) else np.nan);base.loc[z,r['field']+'_source_audited']=value;base.loc[z,'source_correction_fields']+=r['field']+';'
base['in_old_primary1126']=base.row_id.isin(primary.row_id)
base['in_strict309']=base.row_id.isin(strict.row_id)
base['in_old_broader565']=base.row_id.isin(sets['old_broader565'].row_id)
base['in_coordinate_dedup_sensitivity942']=base.row_id.isin(sets['coordinate_dedup_sensitivity942'].row_id)
base=base.merge(gate[['source_id','source_gate_status','evidence_level','url','locator','note','family_id']],on='source_id',how='left',validate='many_to_one')
base['gate_applies_to_exact_condition']=base.in_old_primary1126
base['gate_scope_caution']='Existing source gate audited old1126 primary only; do not inherit method verification to other conditions merely by DOI.'
base['source_gate_status']=base.source_gate_status.fillna('outside_old_primary_no_source_gate')
base['family_id']=base.family_id.fillna(base.source_id)
# These are conservative evaluation blocks, not physical-independence claims.
base.loc[base.doi.isin(['10.1016/j.ijfatigue.2021.106552','10.1016/j.engfracmech.2022.108883']),'family_id']='merot_2021_2025_precautionary'
base.loc[base.doi=='10.1016/j.ijfatigue.2022.107025','family_id']='dastgerdi_2022_2023_precautionary'
base['proposed_source_holdout_block']=base.family_id
base['scope_exclusion_reasons']=''
for cond,label in [(base.test_type!='uniaxial','non_primary_loading_mode;'),(base.load_control!='force','non_force_control;'),(~base.temperature.between(20,30),'outside_database_20_to30C;'),(~base.kt.between(.99,1.01),'not_database_Kt_approximately1;')]:base.loc[cond,'scope_exclusion_reasons']+=label
base['evidence_tier']='E0_catalog_pending_source_or_curve_audit'
base.loc[base.in_strict309,'evidence_tier']='E2_source_method_verified_CA_no_physical_ID'
base.loc[base.in_old_primary1126&base.source_gate_status.eq('exclude_variable_amplitude'),'evidence_tier']='Q_variable_amplitude_transformed_not_CA'
base.loc[base.in_old_primary1126&base.source_gate_status.eq('exclude_republished_316l_curves'),'evidence_tier']='Q_republished_curve_relink_original_before_use'
base.loc[base.in_old_primary1126&base.source_gate_status.eq('quarantine_reuse_prefer_JMST_representative'),'evidence_tier']='Q_linked_curve_prefer_existing_representative'
base.loc[base.in_old_primary1126&base.source_gate_status.eq('quarantine_nearcurve_family'),'evidence_tier']='E1_database_CA_candidate_reuse_family_pending'
base['author_specimen_id']='';base['author_physical_build_id']='';base['author_powder_lot_id']=''
base['row_identity_role']='database address; not author specimen ID'
base['use_training_now']=base.in_strict309
base['use_source_holdout_now']=base.in_strict309
base['use_physical_build_generalization_now']=False
base['allow_missing_IDs_for_future_source_verified_training']=True
base['admission_status']='inventory_only; parent must freeze v4 scope and admission before fitting'
base.to_csv(OUT/'ordinary_row_ledger1473.csv',index=False)
# Expanded metadata from immutable MAT; no outcome-derived feature extraction.
db=loadmat(ROOT/'data/raw/FatigueData-AM2022.mat',simplify_cells=True)['fatiguedata_am2022'];rawmeta={}
for ai,a in enumerate(records(db['articles'])):
 for di,z in enumerate(records(a.get('scidata',{}).get('datasets',[]))):
  key=f'a{ai:04d}_d{di:03d}'
  if key not in set(base.dataset_id):continue
  am=z.get('am',{});para=am.get('am_para',{});proc=z.get('processing',{})
  rawmeta[key]={'raw_am_machine':raw_text(para.get('am_machine')),'raw_layer_rotation':json.dumps(para.get('layer_rot',[]),default=lambda x:np.asarray(x).tolist()),'raw_scan_pattern':raw_text(para.get('scan_pattern')),'raw_process_sequence':json.dumps(proc,default=lambda x:np.asarray(x).tolist()),'raw_testing_fields':json.dumps(z.get('testing',{}),default=lambda x:np.asarray(x).tolist())}
cond=[]
for key,d in base.groupby('dataset_id',sort=True):
 r=d.iloc[0];x={c:r[c] for c in ['dataset_id','doi','title','material','am_type','surface','thermal','power','scan_speed','hatch_space','layer_thickness','direction','load_ratio','frequency','test_type','temperature','environment','kt','load_control','specimen_size','source_gate_status','evidence_level','url','locator','note','proposed_source_holdout_block','evidence_tier','scope_exclusion_reasons','scalar_metadata_provenance']}
 x.update({'rows':len(d),'failures_database':int(d.event_database.sum()),'right_censors_database':int((d.event_database==0).sum()),'unique_stress_levels':int(d.stress_amplitude.nunique()),'stress_amplitude_min_MPa':d.stress_amplitude.min(),'stress_amplitude_max_MPa':d.stress_amplitude.max(),'in_old_primary1126':bool(r.in_old_primary1126),'in_strict309':bool(r.in_strict309),'source_corrections':';'.join(sorted(set(d.source_correction_fields)-{''})),'physical_specimen_ID_available':False,'physical_build_ID_available':False})
 x.update(rawmeta[key]);cond.append(x)
conditions=pd.DataFrame(cond);conditions.to_csv(OUT/'condition_inventory160.csv',index=False)
source=[]
cm=pd.read_csv(ROOT/'data/processed/centola_source_overlap.csv')
for doi,d in base.groupby('doi',sort=True):
 r=d.iloc[0];x={'doi':doi,'title':r.title,'ordinary_rows':len(d),'ordinary_conditions':d.dataset_id.nunique(),'database_failures':int(d.event_database.sum()),'database_runouts':int((d.event_database==0).sum()),'old_primary_rows':int(d.in_old_primary1126.sum()),'old_primary_conditions':d.loc[d.in_old_primary1126,'dataset_id'].nunique(),'strict_rows':int(d.in_strict309.sum()),'strict_conditions':d.loc[d.in_strict309,'dataset_id'].nunique(),'outside_narrow_primary_rows':int((~d.in_old_primary1126).sum()),'old_broader_rows':int(d.in_old_broader565.sum()),'source_gate_status_old_primary':r.source_gate_status,'gate_note_old_primary':r.note,'source_evidence_level':r.evidence_level,'source_url':r.url,'source_locator':r.locator,'source_holdout_block_proposed':r.proposed_source_holdout_block,'Centola17_source_DOI_overlap':doi in set(cm.doi),'named_specimen_rows_in_database':0,'physical_build_mapped_rows_in_database':0}
 source.append(x)
sources=pd.DataFrame(source);sources.to_csv(OUT/'source_inventory46.csv',index=False)
summary=[]
for name,d in sets.items():summary.append({'cohort':name,'path':paths[name],**counts(d),'interpretation':{'ordinary1473':'All positive ordinary316L LPBF database S-N records, including unresolved/derived/reused records and nonaxial modes.','old_primary1126':'Database-filtered axial force20–30C Kt≈1 candidates; default fields are not certified primary-source measurements.','strict309':'Existing source-method-reviewed CA cohort; no need for specimen/build IDs to train or do source-family holdout.','old_broader565':'Exploratory legacy sensitivity, not source-verified broad training; contains known republished/linked duplicate points.','all_except_stepped1028':'Legacy primary minus98 known stepped records; still includes other quarantine/reuse categories.','coordinate_dedup_sensitivity942':'Geometric-coordinate sensitivity; not942 proven physical specimens.'}[name]})
pd.DataFrame(summary).to_csv(OUT/'cohort_counts.csv',index=False)
relations=[]
for a,da in sets.items():
 for b,dbb in sets.items():
  sa,sb=set(da.row_id),set(dbb.row_id);relations.append({'set_a':a,'set_b':b,'intersection_database_addresses':len(sa&sb),'only_a':len(sa-sb),'only_b':len(sb-sa),'a_subset_b':sa<=sb,'identity_kind':'same immutable database address; not physical specimen deduplication'})
pd.DataFrame(relations).to_csv(OUT/'database_set_relationships.csv',index=False)
# Mutually exclusive scope breakdown and gate breakdown.
base[~base.in_old_primary1126].groupby(['test_type','load_control','temperature','kt'],dropna=False).agg(rows=('row_id','size'),conditions=('dataset_id','nunique'),sources=('doi','nunique')).reset_index().to_csv(OUT/'outside_narrow_primary347.csv',index=False)
base[base.in_old_primary1126].groupby('source_gate_status').agg(rows=('row_id','size'),conditions=('dataset_id','nunique'),sources=('doi','nunique')).reset_index().to_csv(OUT/'primary_gate_breakdown.csv',index=False)
base.groupby('evidence_tier').agg(rows=('row_id','size'),conditions=('dataset_id','nunique'),source_dois=('doi','nunique')).reset_index().to_csv(OUT/'current_evidence_tier_counts.csv',index=False)
base.groupby('proposed_source_holdout_block').agg(rows=('row_id','size'),conditions=('dataset_id','nunique'),source_dois=('doi','nunique'),old_primary_rows=('in_old_primary1126','sum'),strict_rows=('in_strict309','sum')).reset_index().to_csv(OUT/'proposed_source_blocks.csv',index=False)
# Field coverage is not evidence that database defaults were source-measured.
coverage=[]
for label,d in [('ordinary1473',base),('old_primary1126',base[base.in_old_primary1126]),('strict309',base[base.in_strict309])]:
 for c in ['power','scan_speed','hatch_space','layer_thickness','direction','surface','thermal','heat_temperature','heat_time','frequency','load_ratio','test_type','temperature','environment','kt','load_control','specimen_size']:
  valid=d[c].notna() if d[c].dtype!=object else d[c].notna()&~d[c].isin(['','unknown'])
  coverage.append({'cohort':label,'field':c,'present_rows':int(valid.sum()),'total_rows':len(d),'present_fraction':float(valid.mean()),'provenance_caution':'Scalar coverage does not distinguish source-reported from database-default values; no imputed unknowns.'})
pd.DataFrame(coverage).to_csv(OUT/'field_coverage.csv',index=False)
# DOI-level comparison only; neither point nor condition identity is available.
for name,d in sets.items():
 cm[name+'_rows_with_DOI']=cm.doi.map(d.groupby('doi').size()).fillna(0).astype(int)
 cm[name+'_conditions_with_DOI']=cm.doi.map(d.groupby('doi').dataset_id.nunique()).fillna(0).astype(int)
 cm[name+'_DOI_present']=cm.doi.isin(set(d.doi))
cm.to_csv(OUT/'centola17_DOI_overlap.csv',index=False)
comparison={'Centola_reported':{'points':518,'conditions':51,'source_papers':17,'original_raw_and_cleaned_rows_obtained':False,'source':'literature/primary_audit/source_publications.csv and table1_audit.json; original article DOI10.1016/j.engfailanal.2024.109081'},'existing_public_database':{s:counts(d) for s,d in sets.items()},'DOI_overlap':{s:int(cm[s+'_DOI_present'].sum()) for s in sets},'point_identity_established':False,'condition_identity_established':False,'not_valid_comparisons':['1473 or1126 are not that many independent specimens or laboratories.','More database rows than518 does not demonstrate a larger validated training set or superior model.','160 or120 database curves are not proven equivalent to Centola51 process groups.','No original BNN/SWT/risk-volume/Owen R90C90 reproduction or model ranking follows.'],'documented_field_comparison':{'original_Table1_fields':['orientation','power','scan_speed','hatch','layer_thickness','risk_volume_mm3','thermal_temperature','thermal_duration','surface_and_treatment_indicators'],'public_database_available_fields':['source_DOI','curve_ID','N','stress_amplitude','runout','orientation','power','scan_speed','hatch','layer_thickness','surface','thermal','R','frequency','test_mode','temperature','Kt','specimen_size'],'important_non_equivalence':['Public specimen_size is not validated risk_volume.','SWT transformation/target definition not reconstructed here.','Some database25C/air/Kt1/control-mode values are defaulted; measured status is not globally recoverable.','Author physical specimen/build IDs are absent from the database address schema.']}}
(OUT/'centola_comparison.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2)+'\n')
# Existing author-data inventories: nested subsets are not summed.
specs=[
('trombley129','data/external_v2/trombley2025/fatigue_asbuilt_available129.csv','specimen_id','condition_id','event','129previousnamed_asbuilt','20kHz crack-related endpoint; same powder verified, four-build individual join absent; license unspecified.','E3_named_source_outcomes_different_endpoint','Not additive independent confirmation; no exact old-database specimen join.'),
('tomaszewski137','data/external_v3/raw_repository/tomaszewski2023_all137_secondary.csv','specimen_id','condition_id','event','137named_source_rows','Explicit stress-control workbook; temperature absent,10/20Hz conflict; individual build join absent.','E3_named_source_outcomes_method_conflicts','Related2023/2024 compilation; no exact author-ID/2023 article inclusion key; no DOI match to strict309.'),
('diller44candidate','data/external_v3/raw_repository/diller2024_all44_candidate.csv','specimen_id','condition_id','event','44candidate_superset','Includes polished ambiguous load-level rows; not all stress-normalized training candidates.','Q_mixed_stress_semantics','Contains retainedasbuilt29; do notsum44+29.'),
('diller29','data/external_v3/raw_repository/diller2024_asbuilt29_secondary.csv','specimen_id','condition_id','event','29asbuilt_subset','Raw stress-range normalization supported;µ15 conflict excluded; control/RT/build metadata incomplete.','E3_named_source_outcomes_method_limits','Subsetof44; no certified identity with olddatabase; nearcoordinate similarity is not specimen identity.'),
('merot70','data/external_v3/continuation_papers/merot_first_exposure_unique_physical70_verified.csv','source_full_specimen_reference','treatment_batch_raw','event','70physical_firstblocks_superset','43nominalair+9localair+18saline; exact3build/2powder mapping.','E4_physical_lineage_first_exposures','Same author family as database98stepped+10related points; no additive row-identity claim.'),
('merot43nominal','data/external_v3/continuation_papers/merot_first_exposure_air_nominal43.csv','source_full_specimen_reference','treatment_batch_raw','event','43nominal_air_subset','20C axial force firstblocks; actual1e6censor; specimen/build/powder verified.','E4_physical_lineage_CA_nominal_RT','Subsetof70/52; oneauthorcampaign.'),
('merot9local','data/external_v3/continuation_papers/merot_first_exposure_air_localstress9_exploratory.csv','source_full_specimen_reference','treatment_batch_raw','event','9local_air_subset','Specimen-specific localKt stress; no silent nominal conversion.','E4_physical_lineage_CA_local_stress','Subsetof70/52 anddisjointfrom43; oneauthorcampaign.'),
('dastgerdi6','data/external_v3/paper_supplements/dastgerdi2023_uninterrupted_pilot6.csv','author_specimen_id','campaign_id','event','6uninterrupted_named','CAforcecontrol, oneexplicitphysicalbuild, temperatureunstated; powdercodeabsent.','E4_source_backed_single_build_RT_unknown','Relatedtohistorical2022DOI107025; holdentirefamilyout; independenceunproven.'),
('yin18','data/external_v3/raw_repository/yin2026_secondary/yin_named18_outside_scope.csv','specimen_id','condition_id','event','18named_superset','LaserwireDED/rotatingbeam; incomplete fatigue rows among18; no build/lot.','E3_named_different_AM_mode','Contains14complete; do notsum18+14.'),
('yin14complete','data/external_v3/raw_repository/yin2026_secondary/yin_complete14_outside_scope.csv','specimen_id','condition_id','event','14complete_subset','LaserwireDED/rotatingbeam; stress/currentoutcomesverified; no build/lot.','E3_named_different_AM_mode','Subsetof18, separateprocess/modepanelbeforeanyfit.'),
('zhou14','data/external_v3/continuation_raw/zhou2026_fatigue14_quarantined.csv','author_specimen_id','author_geometry','event','14anonymous_fatigue_rows','Srstressdefinition,R,event,loadingmethodunresolved;8CTIDsnotjoined.','Q_missing_core_stress_and_censor_semantics','RowlocatorsnotauthorIDs; no admissionsolelybecause14positiveN/stressnumbers.')]
external=[]
for name,fn,idcol,condcol,eventcol,subset,note,tier,overlap in specs:
 d=pd.read_csv(ROOT/fn);events=pd.to_numeric(d[eventcol],errors='coerce')
 external.append({'cohort':name,'file':fn,'rows':len(d),'nonmissing_author_ID_rows':int(d[idcol].notna().sum()),'distinct_author_IDs':int(d[idcol].dropna().nunique()),'condition_labels_in_this_file':int(d[condcol].nunique()),'events_known':int(events.notna().sum()),'failures':int((events==1).sum()),'right_censors':int((events==0).sum()),'subset_relation':subset,'evidence_tier':tier,'use_limit':note,'overlap_caution':overlap,'sha256':sha(ROOT/fn)})
pd.DataFrame(external).to_csv(OUT/'named_external_inventory.csv',index=False)
# Core inventory validations are quantitative and independent of model outputs.
checks={'base_unique_database_addresses':base.row_id.is_unique,'base160conditions':base.dataset_id.nunique()==160,'base46DOIs':base.doi.nunique()==46,'primary1126_subset':set(primary.row_id)<=set(base.row_id),'strict309_subset_primary':set(strict.row_id)<=set(primary.row_id),'gate37sources_matches_primary':set(gate.source_id)==set(primary.source_id),'gate_rows_sum1126':int(gate.n_rows.astype(int).sum())==1126,'gate_eligible_rows309':int(gate[gate.source_gate_status.str.startswith('eligible')].n_rows.astype(int).sum())==309,'scope347_complement':int((~base.in_old_primary1126).sum())==347,'strict_rowset_equals_existing_eligible_gate':set(base[base.in_old_primary1126&base.source_gate_status.str.startswith('eligible')].row_id)==set(strict.row_id),'raw_condition_metadata160':len(rawmeta)==160,'all_positive_finite_N_S':bool(np.isfinite(base.cycles_observed).all() and np.isfinite(base.stress_amplitude).all() and (base.cycles_observed>0).all() and (base.stress_amplitude>0).all()),'event_runout_complement_database':bool((base.event_database+base.runout_database==1).all())}
assert all(checks.values()),checks
inputs=list(paths.values())+['data/raw/FatigueData-AM2022.mat','literature/provenance_v2/final_source_gate.csv','literature/provenance_v2/frozen_point_corrections.csv','data/processed/centola_source_overlap.csv']
receipt={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Existing-data inventory only; no models, no source-gate promotion, no frozen-v4 cohort.','validation_checks':checks,'all_checks_pass':all(checks.values()),'cohort_counts':summary,'inputs_sha256':{p:sha(ROOT/p) for p in inputs},'external_sets_are_nested_not_summed':True,'same_database_addresses_do_not_prove_physical_specimen_identity':True,'parent_must_freeze_v4_before_fits':True,'no_correspondence':True}
(OUT/'inventory_validation_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'all_checks_pass':all(checks.values()),'rows':len(base),'conditions':len(conditions),'sources':len(sources),'external_inventory_sets':len(external),'tier_counts':base.groupby('evidence_tier').size().to_dict(),'Centola_DOI_overlap':comparison['DOI_overlap']},indent=2))
