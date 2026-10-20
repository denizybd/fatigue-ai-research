"""Source/condition-qualified expansion; no model fitting and no invented physical identities."""
from pathlib import Path
import csv,json,hashlib,math,collections,datetime
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'data/external_v4/source_expansion';DOC=ROOT/'literature/v4_open/source_expansion'
SOURCE=ROOT/'data/processed/ss316l_lpbf_all.csv'
rows=list(csv.DictReader(SOURCE.open()));cols=list(rows[0])
MSEA='10.1016/j.msea.2017.07.071';HCF='10.1016/j.ijfatigue.2018.12.016';EL='10.1016/j.ijfatigue.2019.01.013'
MD='10.1016/j.matdes.2018.02.054';ML='10.1016/j.ijfatigue.2019.105194';MATEC='10.1051/matecconf/201816522006';E2020='10.1016/j.matdes.2020.108962';E2022='10.1016/j.addma.2021.102570';EBOOK='10.1007/978-3-030-05861-6_36'
targets={MSEA,HCF,EL,MD,ML,MATEC,E2020,E2022,EBOOK}
families={d:('v4_zhang_linked_original_experiments'if d in {MSEA,HCF,MD,ML,MATEC}else'v4_elangeswaran_linked_experiments')for d in targets}
sourcefiles={MSEA:'literature/provenance_v2/zhang_msea2017.pdf',HCF:'literature/v4_open/source_expansion/zhang2019_hcf.pdf',EL:'literature/v4_open/source_expansion/elangeswaran2019.pdf',MD:'literature/provenance_v2/zhang_matdes2018_alt.pdf',ML:'literature/provenance_v2/zhang_ml2019_alt.pdf'}
loc={MSEA:'PDF6 section2.3;PDF13 Figure8',HCF:'PDF5 section2;PDF7 Figure2a/b',EL:'PDF4/5 section2/Table2;PDF9 Figure5'}
urls={MSEA:'https://pure.coventry.ac.uk/ws/files/11561081/fatiguecomb.pdf',HCF:'https://pure.coventry.ac.uk/ws/portalfiles/portal/22293800/Binder6.pdf',EL:'https://lirias.kuleuven.be/retrieve/1ee43236-45c1-4dee-9f39-d2251e9b0b33'}
selected=[];decisions=[];corrections=[]
extra=['source_family_id','source_qualification','physical_independence_verified','author_specimen_id','author_build_id','author_powder_lot_id','source_condition_label','condition_semantics','primary_source_path','primary_source_url','primary_source_locator','source_stress_definition','source_stress_conversion','source_temperature_statement','temperature_as_database','kt_as_database','cycles_as_digitized','event_as_database','runout_stop_provenance','observation_id_meaning','source_notes']
for orig in rows:
 doi=orig['doi']
 if doi not in targets:continue
 rr=orig.copy();rid=rr['row_id'];ds=rr['dataset_id'];reason='';admit=False
 if doi==MSEA:admit=True;reason='Original own-study Figure8 fixed-stress force-controlled R0.1 S-N markers;5 relative-laser-power conditions;source family blocked.'
 elif doi==HCF:
  if ds=='a0142_d002':reason='Conservatively remove entire horizontal as-built R0.1 curve because it corresponds to earlier MSEA P0/related validation curves; do not inflate unique observation count.'
  else:admit=True;reason='Original Figure2 own-study as-built R−1/R0.7/verticalR0.1 or HIP S-N curve; retained under the same Zhang family as MSEA.'
 elif doi==EL:admit=True;reason='Original Figure5 four own LPBF316L groups only; conventional overlays absent from extracted source rows;explicit CA force-control.'
 elif doi==MD:reason='Methods support CA tests, but original Figure11a is borrowed T1 validation and much of paper is response/model curves. Do not certify all33database rows as new own experimental observations without exact panel mapping.'
 elif doi==ML:reason='Explicitly compiles139fatigue records from prior author experiments;6extracted curves are not a new independent campaign. Prefer earlier original source representatives.'
 elif doi==MATEC:reason='Related near-curve family, original HCF/MSEA representatives preferred; no complete public PDF recovered in this pass; do not add duplicate-looking rows.'
 elif doi in {E2020,E2022,EBOOK}:reason='Related near-curve family; full source-to-curve new-data mapping not completed in this pass. Prefer38verified Elangeswaran2019original rows; retain pending rows outside increment.'
 decisions.append(dict(row_id=rid,dataset_id=ds,doi=doi,source_family_id=families[doi],decision='admit_source_condition_CA'if admit else'exclude_from_primary_increment',reason=reason))
 if not admit:continue
 rr.update(source_family_id=families[doi],source_qualification='primary_methods_and_figure_source_condition_qualified',physical_independence_verified='false',author_specimen_id='',author_build_id='',author_powder_lot_id='',primary_source_path=sourcefiles[doi],primary_source_url=urls[doi],primary_source_locator=loc[doi],source_stress_definition='nominal macroscopic stress amplitude MPa',temperature_as_database=rr['temperature'],kt_as_database=rr['kt'],cycles_as_digitized=rr['cycles_observed'],event_as_database=rr['event'],observation_id_meaning='FatigueData-AM2022 digitized coordinate ID; not an author physical specimen ID',runout_stop_provenance='failure life remains approximately digitized')
 rr['group_id']=families[doi]
 if doi==MSEA:
  rr.update(source_condition_label='Figure8 five-power experimental series '+ds,condition_semantics='Five actual relative laser-power conditions. Exact individual database-series-to-power-legend mapping not asserted here; source power W remains absent.',source_stress_conversion='Source Figure8 plots maximum stress; existing database amplitude already equals0.45×maximum atR0.1; no second conversion.',source_temperature_statement='ambient conditions; exact numeric temperature not stated',source_notes='ASTM E466 flat wire-EDM and manually ground horizontal-loading specimens;no heat treatment. Original fig8 experimental markers, not fig9 extrapolated high-stress0.5P0 estimate.')
  stop=1e6
 elif doi==HCF:
  orient='vertical'if rr['direction']=='90.0'else'horizontal';treat='HIP1190C145MPa4h'if rr['thermal']=='HIP'else'asbuilt'
  rr.update(source_condition_label=orient+'_'+treat+'_R'+rr['load_ratio'],condition_semantics='Figure2 legend, R, orientation and HIP/as-built state source verified.',source_stress_conversion='Source Figure2 plots stress amplitude directly; unchanged.',source_temperature_statement='ambient condition; exact numeric temperature not stated',source_notes='5Hz load-control, sinusoidal fatigue. Whole horizontal as-builtR0.1curve omitted for conservative reuse. Figure3/normalized equivalent-stress Figure10 not imported.')
  stop=1e6
  if rid=='a0142_d005_p001':rr['source_notes']+=' SourceFigure2a shows an unarrowed horizontalR0.7marker beyond1e6;retain plotted failure and digitized lifetime despite nominal1e6runout rule;do not silently recode as a censor.'
 else:
  labels={'a0146_d000':'ABNM','a0146_d001':'SRNM','a0146_d002':'ABM','a0146_d003':'SRM'}
  rr.update(source_condition_label=labels[ds],condition_semantics='Table2 own material/surface condition. SR470C5h;all vertically built.',source_stress_conversion='Figure5 plots nominal stress amplitude directly atR−1;unchanged. Axis isCycles, so no2Nfactor conversion despite equation notation.',source_temperature_statement='Exact test ambient temperature not stated; self-heating checked at30/60Hz;database25C not certified.',source_notes='60Hz force-controlled constant amplitude until total fracture or2e6runout. Excludes conventional316Loverlays[14,25]. Fitted Basquin lines not observations.')
  stop=2e6
 # Do not turn database numeric25C or Kt1 into primary source evidence.
 rr['temperature']='';rr['kt']=''
 for field in ['temperature','kt']:
  corrections.append(dict(row_id=rid,field=field,old_value=orig[field],new_value='',reason='Numeric database value not independently specified by inspected primary method; original preserved in '+field+'_as_database',source=loc[doi]))
 if rr['runout']=='1':
  old=rr['cycles_observed'];rr['cycles_observed']=str(int(stop));rr['log_life']=str(math.log10(stop));rr['runout_stop_provenance']='Exact author administrative stop from methods plus arrowed source S-N marker; raw digitized coordinate preserved.'
  corrections.append(dict(row_id=rid,field='cycles_observed',old_value=old,new_value=rr['cycles_observed'],reason='Author statedrunoutstop;correct small approximate graph-x error,retain right censor.',source=loc[doi]))
 selected.append(rr)
OUT.mkdir(parents=True,exist_ok=True)
def write(name,data,fields):
 with (OUT/name).open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
write('source_qualified_ca_expansion.csv',selected,cols+extra)
write('row_exclusion_ledger.csv',decisions,list(decisions[0]))
write('row_correction_ledger.csv',corrections,list(corrections[0]))
anchors=[dict(doi=EL,source_locator='PDF10Figure6caption',source_condition='ABNM',stress_amplitude_MPa=350,cycles=28161,nearest_database_row='a0146_d000_p001'),dict(doi=EL,source_locator='PDF10Figure6caption',source_condition='SRNM',stress_amplitude_MPa=250,cycles=148663,nearest_database_row='a0146_d001_p006'),dict(doi=EL,source_locator='PDF11Figure8caption',source_condition='ABM',stress_amplitude_MPa=350,cycles=254980,nearest_database_row='a0146_d002_p005'),dict(doi=EL,source_locator='PDF11Figure8caption',source_condition='SRM',stress_amplitude_MPa=350,cycles=217990,nearest_database_row='a0146_d003_p006')]
for z in anchors:z.update(use='source-reported exact numeric anchors only; not additional specimens and not substituted into normalized digitized data without physical ID join')
write('source_reported_exact_anchors.csv',anchors,list(anchors[0]))
raw=json.load((ROOT/'data/raw/FatigueData-AM2022.json').open())['fatiguedata_am2022'];indices=sorted({int(rr['article_index'])for rr in rows if rr['doi']in targets});packet=dict(source='FatigueData-AM2022v2',license='CC-BY4.0',source_path='data/raw/FatigueData-AM2022.json',source_sha256=hashlib.sha256((ROOT/'data/raw/FatigueData-AM2022.json').read_bytes()).hexdigest(),articles={str(i):raw['articles'][i]for i in indices});(OUT/'unchanged_public_database_source_packet.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
counts=collections.Counter(rr['doi']for rr in selected);receipt=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Source/condition-qualified ordinaryCAincrement beyond strict309, not a specimen/build-qualified gold panel.',n_rows=len(selected),n_curves=len({rr['dataset_id']for rr in selected}),n_publications=len(counts),n_source_family_blocks=len({rr['source_family_id']for rr in selected}),source_counts=dict(counts),n_failures=sum(int(rr['event'])for rr in selected),n_right_censors=sum(int(rr['runout'])for rr in selected),n_row_decisions=len(decisions),n_corrections=len(corrections),physical_specimen_ids_invented=False,physical_build_independence_claimed=False,exact_caption_anchors_are_additional_rows=False,retained_source_pdf_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in set(sourcefiles.values())},artifact_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in OUT.iterdir()if p.is_file()})
assert len(selected)==132 and len(counts)==3 and len({rr['row_id']for rr in selected})==132
(DOC/'expansion_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k not in ['retained_source_pdf_hashes','artifact_sha256']},indent=2))
