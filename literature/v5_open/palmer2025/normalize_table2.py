"""Normalize primary Table 2 cells; preserve cycles and strain-control scope."""
from pathlib import Path
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
LIT = ROOT / 'literature/v5_open/palmer2025'
OUT = ROOT / 'data/external_v5/palmer2025'
OUT.mkdir(parents=True, exist_ok=True)
cells = json.loads((LIT / 'table2_source_cells.json').read_text())
assert cells[0] == ['Strain amplitude (mm/mm)', 'Build angle (°)', 'Cycles to failure']
text = (LIT / 'paper.txt').read_text()
rows = []
for i, c in enumerate(cells[1:], 1):
    assert len(c) == 3
    strain, angle, life = float(c[0]), int(c[1]), int(c[2].replace(',', ''))
    # Compare the independent PDF text extraction before normalizing HTML cells.
    assert re.search(rf'{re.escape(c[0])}\s+{angle}\s+{re.escape(c[2])}', text)
    rows.append(dict(
        extraction_id=f'wietecha_reiman2025_table2_row{i:02d}',
        extraction_id_is_physical_specimen_id=False,
        author_specimen_id='',
        physical_specimen_id='',
        author_build_id='',
        canonical_physical_build_id='',
        powder_lot_id='',
        physical_build_count='',
        physical_build_count_status='unreported; singular reference to build plate is not a verified one-build statement',
        source_doi='10.1007/s10853-025-11259-w',
        source_family_id='WietechaReiman_Palmer_HIP_strain_campaign',
        source_table='Table2',
        source_data_row=i,
        source_pdf_page=8,
        source_printed_page=18339,
        source_cell_strain=f'Table2 data row{i} column1: {c[0]}',
        source_cell_angle=f'Table2 data row{i} column2: {c[1]}',
        source_cell_life=f'Table2 data row{i} column3: {c[2]}',
        source_url='https://link.springer.com/article/10.1007/s10853-025-11259-w/tables/2',
        observation_origin='exact author tabulated experimental outcome; not digitized',
        author_summary_statistic=False,
        material='316L austenitic stainless steel',
        process='laser powder bed fusion',
        machine='EOS M290',
        powder_supplier='Carpenter Additive, formerly LPW Technology',
        build_angle_to_plate_deg=angle,
        surface='as-deposited gauge surface; no gauge machining',
        gauge_length_mm=25.4,
        gauge_diameter_mm=6.35,
        surface_test_coating='M-Coat A polyurethane used to prevent extensometer slip',
        treatment='HIP',
        HIP_nominal_temperature_C=1050,
        HIP_nominal_pressure_MPa=138,
        HIP_duration_h=2.25,
        HIP_gas='argon',
        feedback_control_mode='strain controlled',
        frequency_Hz=0.25,
        fatigue_temperature_C='',
        waveform='',
        strain_ratio_R_epsilon='',
        stress_ratio_R_sigma='',
        strain_amplitude_mm_per_mm=strain,
        strain_definition='author reported strain amplitude, mm/mm; no elastic-equivalent conversion',
        stress_amplitude_MPa='',
        cycles_to_failure=life,
        cycle_unit='cycles Nf; not reversals2Nf',
        event=1,
        endpoint='reported cycles to fatigue failure, not the separately discussed crack-initiation Ni',
        runout_threshold_cycles='',
        stress_controlled_CA_HCF_eligible=False,
        physical_identity_qualified=False,
        secondary_panel='separate strain-controlled HIP fatigue table; incomplete batch/R/temperature metadata',
        archival_Figure1_data=False,
        duplicate_in_Figure4=True,
        primary_training_admitted=False,
    ))

csv_path = OUT / 'palmer2025_exact_strain_fatigue_table2.csv'
with csv_path.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

# Table 1 composition facts are source measurements, not a recovered powder-lot key.
elements = ['Fe','Cr','Ni','Mo','Mn','Si','Cu','C','S','P','O','N']
powder = ['Balance','17.5','12.5','2.32','0.54','0.66','0.02','0.017','0.005','0.007','0.030','0.10']
hip = ['','','','','','','','0.019','0.007','0.007','0.029','0.09']
with (OUT / 'palmer2025_powder_composition_table1.csv').open('w', newline='') as f:
    names = ['source_doi','source_table','source_pdf_page','measurement','element','mass_fraction_percent_source_string','powder_lot_id','lot_identity_verified']
    w = csv.DictWriter(f, fieldnames=names);w.writeheader()
    for name, values in [('As-received powder', powder), ('Post-HIP material', hip)]:
        for element, value in zip(elements, values):
            w.writerow(dict(source_doi='10.1007/s10853-025-11259-w', source_table='Table1', source_pdf_page=4, measurement=name, element=element, mass_fraction_percent_source_string=value, powder_lot_id='', lot_identity_verified=False))

exclusions = [
    dict(source_region='Figure1a', disposition='not imported', reason='Archival strain-controlled source data, not new own specimens'),
    dict(source_region='Figure1b', disposition='not imported', reason='Archival stress data converted using elastic moduli; not own strain-controlled measurements'),
    dict(source_region='Figure4 markers', disposition='not separately imported', reason='Same12Table2 outcomes; no double counting'),
    dict(source_region='Figure4 bands and curves', disposition='not imported', reason='Archival comparison bands and fitted curves, not individual own outcomes'),
    dict(source_region='Figure3 and Figure7 example captions', disposition='crosscheck only', reason='Representative lives3713/27855/8240/1112 match Table2; not new rows'),
    dict(source_region='ANCOVA Equation3/Table3', disposition='not imported as outcomes', reason='Regression uses2Nf; Table2 reports Nf cycles and must retain its unit'),
    dict(source_region='HIP temperature1050C and metallography etching97C', disposition='not fatigue temperature', reason='Process and specimen-preparation temperatures cannot be assigned to fatigue testing'),
    dict(source_region='SSRN4773097/conference versions', disposition='conservative same-family block pending full-text join', reason='Same authors and material/mechanism; not counted as independent new specimens'),
]
with (OUT/'exclusion_and_interpretation_ledger.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(exclusions[0]));w.writeheader();w.writerows(exclusions)

assert len(rows) == 12
assert {a:sum(r['build_angle_to_plate_deg']==a for r in rows) for a in [90,60,45]} == {90:5,60:4,45:3}
assert {(r['strain_amplitude_mm_per_mm'],r['build_angle_to_plate_deg']) for r in rows}.__len__() == 12
assert all(r['event']==1 and not r['physical_specimen_id'] and not r['canonical_physical_build_id'] for r in rows)
assert [(r['strain_amplitude_mm_per_mm'],r['cycles_to_failure']) for r in rows if r['build_angle_to_plate_deg']==90] == [(0.002,123402),(0.003,27855),(0.004,10969),(0.006,3713),(0.008,577)]
receipt=dict(rows=12,events=12,runouts=0,angle_counts={a:sum(r['build_angle_to_plate_deg']==a for r in rows) for a in [90,60,45]},exact_source_cells=True,visual_pdf_page_checked=8,pdf_text_vs_html_all_rows_agree=True,physical_IDs_recovered=0,physical_builds_identified=0,powder_lots_identified=0,stress_controlled_primary_admitted=0,csv_sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest())
(OUT/'normalization_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
