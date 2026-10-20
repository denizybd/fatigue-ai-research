"""Curate exact 316L aggregate facts; do not fabricate individual fatigue lives.

The numerical transcriptions were checked against PDF pages 72, 165 and 166.
All source group counts are non-additive across the supplied tables/figures.
"""
from pathlib import Path
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
OUT = ROOT / 'data/external_v5/bremen2025'
OUT.mkdir(parents=True, exist_ok=True)
DOI = '10.26092/elib/4986'
FAMILY = 'jun_zhang_bremen_145651_4986'
URL = 'https://media-api.suub.uni-bremen.de/server/api/core/bitstreams/bc5381b1-aece-4712-83d0-a7fe422a8663/content'


def save(name, rows):
    with (OUT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


# Table8.1: source-fitted fracture-stress quantiles, NOT observed Nf or life quantiles.
strength = [
    ('CS_annealed', 'CS annealed', 'conventional', 'no HT', 33, 326, 329, 331, 222, .45, 'reference', ''),
    ('CH4_S10_0_highporosity', 'S10 0°, high porosity', 'LPBF', 'high porosity; turned', 7, 91, 95, 97, 51, None, 'condition', ''),
    ('CH4_S10_0_rough', 'S10 0°, as-built surface', 'LPBF', 'low porosity; rough', 6, 116, 120, 123, 51, .24, 'condition', ''),
    ('CH4_S10_0_all', 'S10 0° - all', 'LPBF', 'low porosity; turned', 20, 138, 229, 317, 4, .41, 'pooled_parent', 'CH4_S10_0_batches12;CH4_S10_0_batch3'),
    ('CH4_S10_0_batches12', 'S10 0° - batch 1 & 2', 'LPBF', 'low porosity; turned', 7, 205, 269, 320, 7, .48, 'nested_subgroup', 'CH4_S10_0_all'),
    ('CH4_S10_0_batch3', 'S10 0° - batch 3', 'LPBF', 'low porosity; turned', 11, 64, 110, 154, 4, .20, 'nested_subgroup', 'CH4_S10_0_all'),
    ('CH4_S3_0', 'S3 0°', 'LPBF', 'low porosity; turned', 17, 232, 266, 290, 14, .50, 'condition', ''),
    ('CH4_C3_0', 'C3 0°', 'LPBF', 'low porosity; turned', 21, 134, 230, 323, 4, .37, 'condition', ''),
    ('CH4_C3_45', 'C3 45°', 'LPBF', 'low porosity; turned', 20, 131, 149, 161, 15, .25, 'condition', ''),
    ('CH4_C3_90', 'C3 90°', 'LPBF', 'low porosity; turned', 19, 105, 153, 195, 5, .27, 'condition', ''),
    ('CH5_C3_0_AB', 'C3 0°, as-built', 'LPBF', 'no HT', 16, 333, 335, 337, 239, .51, 'condition', ''),
    ('CH5_C3_0_SR600', 'C3 0°, 600 °C 2 h', 'LPBF', 'stress relieved', 19, 357, 359, 360, 326, .58, 'condition', ''),
    ('CH5_C3_0_AN900', 'C3 0°, 900 °C 2 h', 'LPBF', 'annealed', 16, 282, 307, 324, 22, .53, 'condition', ''),
]
save('table8_1_fatigue_strength_13.csv', [dict(
    record_id=k, source_variant=v, material='AISI316L', manufacturing_process=proc,
    source_feature=feat, source_reported_No=n, source_fitted_sigma10_mpa=s10,
    source_fitted_sigma50_mpa=s50, source_fitted_sigma90_mpa=s90,
    source_fitted_Weibull_m=m, source_sigma50_over_UTS=ratio,
    grouping_role=role, overlapping_group_ids=overlap,
    record_type='aggregate_fitted_fracture_stress_distribution',
    source_equation='3.4: PF(s)=1-2^(-(s/sigma_w)^m)',
    life_training_eligible=False, source_doi=DOI, source_pdf_page=165,
    source_printed_page=151, source_table='8.1', source_family_block=FAMILY
) for k,v,proc,feat,n,s10,s50,s90,m,ratio,role,overlap in strength])

# Table3.5 repeats S10 and C3 controls in multiple investigation packages.
counts = [
    ('porosity_roughness','CH4_S10_0_highporosity',0,7,False),
    ('porosity_roughness','CH4_S10_0_rough',6,6,False),
    ('porosity_roughness','CH4_S10_0_all',7,20,True),
    ('scan_pattern','CH4_S10_0_all',7,20,True),
    ('scan_pattern','CH4_S3_0',5,17,False),
    ('scan_pattern','CH4_C3_0',5,21,True),
    ('polar_angle','CH4_C3_0',5,21,True),
    ('polar_angle','CH4_C3_45',6,20,False),
    ('polar_angle','CH4_C3_90',5,19,False),
    ('heat_treatment','CH5_C3_0_AB',5,17,False),
    ('heat_treatment','CH5_C3_0_SR600',5,19,False),
    ('heat_treatment','CH5_C3_0_AN900',5,16,False),
    ('control','CS_annealed',5,33,False),
]
save('table3_5_316L_investigation_counts_13.csv', [dict(
    investigation_package=p, condition_id=k, source_tensile_count=None if t==0 else t,
    source_fatigue_count=n, repeated_across_packages=rep, additive_across_rows=False,
    record_type='reported_group_test_count', source_doi=DOI,
    source_pdf_page=72, source_printed_page=58, source_table='3.5'
) for p,k,t,n,rep in counts])

# Table8.3 base No values and footnote adjustments are preserved separately.
# '-': unavailable or tapped-head failure; '+': an additional fracture origin,
# not an additional specimen. These are NOT additional fatigue-test observations.
status = [
    ('CS_annealed',22,11,33,0,0,0,0),
    ('CH4_S10_0_highporosity',6,1,7,0,0,0,0),
    ('CH4_S10_0_rough',4,2,6,0,0,0,0),
    ('CH4_S10_0_all',12,8,20,0,2,0,1),
    ('CH4_S10_0_batches12',3,6,9,0,2,0,1),
    ('CH4_S10_0_batch3',9,2,11,0,0,0,0),
    ('CH4_S3_0',6,11,17,0,0,0,0),
    ('CH4_C3_0',11,10,21,0,0,0,1),
    ('CH4_C3_45',9,11,20,0,0,0,0),
    ('CH4_C3_90',14,6,20,1,0,0,0),
    ('CH5_C3_0_AB',10,10,20,5,4,0,0),
    ('CH5_C3_0_SR600',11,8,19,0,0,0,0),
    ('CH5_C3_0_AN900',11,9,20,4,0,0,0),
]
save('table8_3_316L_status_counts_13.csv', [dict(
    condition_id=k, source_fail_No=fail, source_runout_No=runout, source_all_No=total,
    excluded_or_unavailable_fail_a=exf, excluded_or_unavailable_runout_a=exr,
    additional_fail_fracture_origins_b=plusf, additional_runout_fracture_origins_b=plusr,
    individual_Nf_available=False, additive_across_conditions=False,
    initial_status_is_preserved_for_fractography=True,
    record_type='aggregate_status_and_fractography_count', source_doi=DOI,
    source_pdf_page=166, source_printed_page=152, source_table='8.3'
) for k,fail,runout,total,exf,exr,plusf,plusr in status])

method_rows=[]
for k,v,proc,feat,n,*_ in strength:
    if 'batches12' in k or 'batch3' in k:continue
    high='highporosity' in k
    angle=45 if k=='CH4_C3_45' else 90 if k=='CH4_C3_90' else 0
    pattern='stripe' if 'S10' in k or 'S3_' in k else 'chessboard'
    method_rows.append(dict(
        condition_id=k, source_variant=v, material='AISI316L',
        manufacturing_process=proc, source_family_block=FAMILY,
        source_investigation_chapter='control' if proc=='conventional' else '5.1' if k.startswith('CH5') else '4.1',
        machine=None if proc=='conventional' else 'ReaLizer SLM250',
        laser_power_w=None if proc=='conventional' else 170 if high else 110,
        scan_speed_mm_s=None if proc=='conventional' else 350 if high else 100,
        layer_thickness_um=None if proc=='conventional' else 50,
        layer_rotation_deg=None if proc=='conventional' else 79,
        baseplate_preheat_c=None if proc=='conventional' else 240,
        shielding_gas=None if proc=='conventional' else 'argon',
        scan_pattern=None if proc=='conventional' else pattern,
        stripe_or_tile_width_mm=None if proc=='conventional' else 10 if 'S10' in k else 3,
        build_angle_from_plate_deg=None if proc=='conventional' else angle,
        surface_condition='conventional reference; not transferred from LPBF' if proc=='conventional' else 'as-built rough' if k.endswith('_rough') else 'turned',
        heat_treatment='source conventional annealed; no additional HT' if proc=='conventional' else '600C2h' if 'SR600' in k else '900C2h' if 'AN900' in k else 'no post heat treatment',
        test_mode='uniaxial cyclic load-controlled resonance',
        test_machine='Amsler 2HFP', stress_definition='stress amplitude',R=-1,
        frequency_hz=124, frequency_reported_plusminus_hz=11,
        runout_initial_limit_cycles=10000000, runouts_reloaded_at_higher_stress=True,
        test_temperature_c=None, environment=None, geometric_Kt=None,
        author_specimen_id=None, powder_lot_id=None, physical_build_id=None,
        batch_scope='mixture across manufacturing batches explicitly stated; no specimen crosswalk' if k.startswith('CH5') else 'S10 batches1/2/3 separately discussed; no specimen crosswalk' if k=='CH4_S10_0_all' else 'not individually mapped',
        virgin_first_exposure_per_point_verified=False,
        source_doi=DOI, source_methods_pdf_pages='63;65;66;67;68;72;73;80;119',
        life_training_eligible=False,
        eligible_reason='Methods/condition evidence only; no individual numeric Nf imported',
    ))
save('condition_methods_11.csv',method_rows)

chem = [
    ('Powder A',.02,17.30,12.10,2.10,.50,.65,None,None),
    ('Powder B',.03,16.70,12.50,2.10,.80,.50,.011,.007),
]
save('316L_powder_composition_2.csv',[dict(
    author_powder_label=k,C_weight_pct=C,Cr_weight_pct=Cr,Ni_weight_pct=Ni,
    Mo_weight_pct=Mo,Si_weight_pct=Si,Mn_weight_pct=Mn,P_weight_pct=P,S_weight_pct=S,
    material='AISI316L', author_powder_lot_code=None, condition_crosswalk_verified=False,
    provider_names_reported='NMD New Materials Development GmbH;Deutsche Edelstahlwerke',
    provider_to_A_B_join_verified=False, source_pdf_page=63, source_printed_page=49,
    source_table='3.1', source_doi=DOI
) for k,C,Cr,Ni,Mo,Si,Mn,P,S in chem])

figures = [
    ('4.6a',79,'CH4_S10_0_highporosity;CH4_S10_0_rough;CH4_S10_0_all;CS_annealed','8.3a'),
    ('4.6c',79,'CH4_S10_0_batches12;CH4_S10_0_batch3','8.3c'),
    ('4.6e',79,'CH4_S10_0_batches12;CH4_S3_0;CH4_C3_0;CS_annealed','8.3b'),
    ('4.6g',79,'CH4_C3_0;CH4_C3_45;CH4_C3_90;CS_annealed','8.4a'),
    ('5.4a',121,'CH5_C3_0_AB;CH5_C3_0_SR600;CH5_C3_0_AN900;CH4_C3_0;CS_annealed','8.4b'),
]
save('candidate_SN_figure_inventory_5.csv',[dict(
    source_figure=f,source_pdf_page=pg,condition_ids=ks,overlapping_figure=other,
    graph_only=True, individual_numeric_life_table_found=False,
    failure_runout_symbols_distinct=True, unique_multiplicities_fully_resolved=False,
    first_block_and_retest_membership_per_point_verified=False,
    exact_runout_cycle=10000000, extra_horizontal_jitter_is_not_extra_life=True,
    additional_individual_Nf_imported=0,
    next_qualification='Count and distinguish original markers vs overplot jitter/fit bars; reconcile counts and verify first-exposure display before CA digitization',
    source_doi=DOI
) for f,pg,ks,other in figures])

reuse=[dict(
    source_doi=DOI,linked_doi='10.1016/j.msea.2023.145651',
    relation='Thesis chapter4.1 and figures explicitly partly reuse the authors2023 paper',
    source_family_block=FAMILY, source_evidence_pdf_pages='8;79;165;166',
    cross_source_point_crosswalk_available=False,
    count_as_independent_campaign=False,
    caveat='Bremen Jun Zhang program must not be merged solely by surname with earlier unrelated Zhang2017/2019 source families',
)]
save('paper_thesis_reuse_links.csv',reuse)

assert len(strength)==13 and len(method_rows)==11
assert all(s10<s50<s90 for _,_,_,_,_,s10,s50,s90,*_ in strength)
assert all(f+r==t for _,f,r,t,*_ in status)
pdf=SRC/'Zhang2025_Bremen_dissertation.pdf'
meta=json.loads((SRC/'bitstream_metadata.json').read_text())
assert hashlib.md5(pdf.read_bytes()).hexdigest()==meta['checkSum']['value']
receipt=dict(
    status='PASS for aggregate/method curation; individual life admission not yet qualified',
    source_doi=DOI, source_url=URL, source_family_block=FAMILY,
    material_scope='AISI316L only; H13 intentionally excluded',
    aggregate_fatigue_strength_rows=13, LPBF_aggregate_strength_rows=12,
    distinct_LPBF_conditions_without_nested_subgroups=10,
    conventional_reference_conditions=1, unique_author_specimen_IDs_recovered=0,
    specimen_build_or_lot_crosswalks_recovered=0,
    individual_numeric_failure_life_rows_imported=0,
    individual_life_training_rows_added=0,
    source_condition_batch_information=True,
    source_fatigue_temperature_explicit=False,
    no_raw_supplement_in_original_bundle=True, no_PDF_attachments=True,
    methods='Load-controlled R=-1 resonance;316L124+/-11Hz;first runout1e7 then higher-stress reloads',
    graph_scope='Visible failure/runout symbols preserve initial status, so no assertion that every graph failure is retested. Pointwise history separation remains to be verified.',
    fitted_parameter_scope='Table8.1 source-fitted fracture-stress distribution parameters, not observed Nf and not reliability confidence bounds',
    non_additive_counts=True,
    unresolved_source_count_differences=[
        'CH5_C3_0_AB:Table3.5 fatigue count17;Table8.1No16;Table8.3all20 with exclusions9 for fracture-origin availability.',
        'CH4_S10_0_batches12:Table8.1No7;Table8.3base9, excluding2 unavailable/tapped-head specimens and allowing1 extra fracture origin.',
        'CH4_C3_90:Table3.5/Table8.1No19;Table8.3base20 with1excluded.',
        'CH5_C3_0_AN900:Table8.1No16;Table8.3base20 with4excludedfailures.',
    ],
    exclusions_are_not_source_error_allegations=True,
    source_pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
    output_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(OUT.glob('*.csv'))},
)
(SRC/'curation_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(OUT/'data_dictionary.json').write_text(json.dumps(dict(
    source_doi=DOI, scope=receipt['material_scope'],
    table8_1='One source fitted fracture-STRESS distribution per overlapping group; No is a reported count. Sigma10/50/90 are stress quantiles in MPa, never life quantiles.',
    table3_5='Investigation-package counts; repeated S10/C3 controls are not extra samples.',
    table8_3='Initial failure/runout group sizes used for later fractography. Minus footnotes mean unavailable/tapped-head specimens; plus footnotes mean extra origins, not specimens.',
    condition_methods='Method and pretest-condition facts; unknown temperature/Kt/lab/build/powder identity stays blank. Common method values are source group summaries, not measured per specimen.',
    powder='Source powder labelsA/B and nominal chemistry; no lot code or fatigue-condition crosswalk.',
    figures='Potential future graph curation inventory, not additional observation rows.',
    point_counts_are_not_unique_physical_specimen_counts=True,
    readme='No individual Nf values are fabricated from fitted stress quantiles or aggregate counts. No current model run uses these files.',
),indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ['status','aggregate_fatigue_strength_rows','distinct_LPBF_conditions_without_nested_subgroups','individual_numeric_failure_life_rows_imported','source_pdf_sha256']},indent=2))
