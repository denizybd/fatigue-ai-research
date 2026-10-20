"""Independent raw-to-long history verification, never a fatigue-life importer."""
from pathlib import Path
import csv,json,hashlib,datetime
import pandas as pd,numpy as np
ROOT=Path('/Users/deniz2/Documents/ChatGPT/fatigue-ai-research');BASE=ROOT/'data/external_v4/jambor2025';OUT=ROOT/'literature/v4_open/inventory'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
expected=[];specs={}
for p in sorted((BASE/'selected_original_files/1 Fatigue_tests').glob('*.csv')):
 rows=list(csv.reader(p.open(encoding='utf-8-sig')))
 offsets=[i for i,s in enumerate(rows[2]) if 'specimen'in s.lower()]
 kind='peak_valley'if'peak-valley'in p.name else'selected_whole_cycles'
 for i in offsets:
  shape=rows[2][i];number=rows[2][i+1];sid='jambor2025_'+shape.split()[0].lower()+'_'+number;area=float(rows[5][i+1]);header={'author_label':shape+' '+number,'amplitude':float(rows[3][i+1][:-1])/100,'exposure':int(rows[4][i+1]),'area':area}
  if sid in specs:assert specs[sid]==header
  specs[sid]=header
  for line,r in enumerate(rows[9:],10):
   cells=r[i:i+3]
   if not any(c.strip()for c in cells):continue
   assert len(cells)==3 and all(c.strip()for c in cells)
   cycle,eps,force=map(float,cells)
   expected.append((sid,kind,p.name,line,cycle,eps,force,1000*force/area))
cols=['canonical_history_id','record_type','source_file','source_line','cycle_count','total_strain_mm_mm','axial_force_kN','nominal_stress_MPa']
e=pd.DataFrame(expected,columns=cols);d=pd.read_csv(BASE/'cyclic_response_long.csv.gz');s=pd.read_csv(BASE/'seven_interrupted_specimens.csv');h=pd.read_csv(BASE/'history_inventory.csv')
checks={'217368records_exact':len(e)==len(d)==217368,'all14views_same7author_specimens':e.groupby(['canonical_history_id','record_type']).ngroups==14 and len(specs)==7 and s.canonical_history_id.nunique()==7,'order_and_source_key_preserved':e[cols[:4]].equals(d[cols[:4]]),'all_force_strain_cycle_values_preserved':np.allclose(e[cols[4:7]],d[cols[4:7]],rtol=0,atol=1e-12),'all_force_area_derived_stress_correct':np.allclose(e.nominal_stress_MPa,d.nominal_stress_MPa,rtol=1e-14,atol=1e-10),'no_Nf_event_or_fixed_stressR_columns':not bool({'event','runout','Nf','cycles_to_failure','cycles_observed','load_ratio','stress_ratio'}&(set(d.columns)|set(s.columns))),'all7primary_life_benchmark_ineligible':s.primary_life_benchmark_eligible.eq(False).all().item(),'no_build_powder_ID_invented':s[['build_id','powder_lot_id']].isna().all().all().item(),'source_family_precautionary_not_independence_claim':s.source_family.eq('jambor_pelegatti_316L_precautionary_family').all().item()}
for row in s.itertuples():
 raw=specs[row.canonical_history_id];assert row.total_strain_amplitude==raw['amplitude']==.004;assert row.area_mm2==raw['area'];assert row.planned_interruption_cycles==raw['exposure'];assert row.author_specimen_label==raw['author_label']
checks['all7header_metadata_match']=True
agg=e.groupby(['canonical_history_id','record_type']).agg(records=('source_line','size'),cycle_min=('cycle_count','min'),cycle_max=('cycle_count','max'),stress_min_MPa=('nominal_stress_MPa','min'),stress_max_MPa=('nominal_stress_MPa','max')).reset_index();m=agg.merge(h,on=['canonical_history_id','record_type'],suffixes=('_independent','_normalized'),validate='one_to_one')
for c in ['records','cycle_min','cycle_max','stress_min_MPa','stress_max_MPa']:assert np.allclose(m[c+'_independent'],m[c+'_normalized'],rtol=1e-14,atol=1e-10)
checks['all14history_summary_rows_match']=True
assert all(checks.values()),checks
receipt={'audited_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'all_checks_pass':True,'checks':checks,'numeric_stress_max_abs_error_MPa':float(np.max(np.abs(e.nominal_stress_MPa-d.nominal_stress_MPa))),'source_data_domain':'Seven specimens at total-strain amplitude 0.4% yield 217368 repeated cyclic-response samples, with geometry-qualified author labels and recorded exposure headers.','header_endpoint_limit':'Number of cycles is an exposure header; no fracture/event flag is supplied by theseCSV files. Treat as interrupted response histories and make no Nf/right-censor assertion from the CSV alone.','duplicate_view_limit':'Peak-valley and selected whole-cycle data are overlapping views of same7specimens. Flat3/4 peak-valley have2007/8024records; preserve duplicates/samples rather than forcing2points/cycle.','stress_ratio_limit':'Fixed total-strain amplitude does not imply stressR=-1. Force/stress responses evolve and are asymmetric. No fixed stressR imported.','Jambor2026_reuse_limit':'No exact cross-dataset specimen join has been established; do not sum2025+2026as independent physical specimen union or independent campaigns. Shared precautionary family is correct.','original_zip_check':'jambor2025_raw_audit.json verifies producerMD5 and all4selectedCSV bytes against original407468869byteZIP.','input_hashes':{str(p.relative_to(ROOT)):sha(p)for p in [BASE/'cyclic_response_long.csv.gz',BASE/'seven_interrupted_specimens.csv',BASE/'history_inventory.csv',ROOT/'src/v4_jambor_import.py']},'no_model_runs_or_source_edits':True}
(OUT/'jambor2025_normalized_independent_audit.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2,default=lambda v:v.item()if hasattr(v,'item')else str(v))+'\n')
print(json.dumps({'all_checks_pass':True,'checks':len(checks),'rows':len(d),'specimens':len(s),'stress_max_abs_error_MPa':receipt['numeric_stress_max_abs_error_MPa']},indent=2))
