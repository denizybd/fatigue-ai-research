"""Normalize factual reported Table1 points; no fitting, inference, or source mutation."""
from pathlib import Path
import collections
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
LIT = ROOT / 'literature/v4_open/rbf2026'
OUT = ROOT / 'data/external_v4/rbf2026'
OUT.mkdir(parents=True, exist_ok=True)
src = json.loads((LIT / 'table1_transcription.json').read_text())
rows = []
for rn, source_row in enumerate(src['rows'], 1):
    for ci, values in enumerate(source_row['cells']):
        condition = src['columns'][ci]
        temperature = 450 if condition.startswith('450') else 25
        hip = condition.endswith('_HIP')
        reused = ci == 0
        for vi, token in enumerate(values, 1):
            runout = token == 'Runout'
            nfail = '' if runout else int(float(token))
            rows.append({
                'source_point_locator': f'Table1.row{rn:02d}.col{ci+2}.point{vi}',
                'locator_is_author_specimen_id': False,
                'source_doi': src['source_doi'], 'source_url': src['source_url'],
                'source_table': 'Table 1 / Figure 7', 'condition': condition,
                'temperature_c': temperature, 'material': 'SS316L',
                'manufacturing_process': 'PBF-LB', 'test_mode': 'rotating bending',
                'stress_definition': 'nominal bending stress amplitude',
                'stress_amplitude_mpa': source_row['stress_mpa'],
                'stress_reported_plusminus_mpa': source_row['plusminus_mpa'],
                'stress_plusminus_semantics': 'source reported; do not treat as per-specimen measured deviations',
                'R': -1, 'frequency_hz': '',
                'source_life_token': token,
                'N_failure_cycles': nfail,
                'event': int(not runout), 'runout': int(runout),
                'censor_lower_bound_cycles': 5000000 if runout else '',
                'runout_exact_stop_cycles': '',
                'life_value_provenance': 'Table1 failure life' if not runout else 'Runout token plus methods lower-bound criterion; exact stop unreported',
                'failure_beyond_nominal_runout_threshold_retained': bool(not runout and nfail > 5000000),
                'surface_condition': 'polished',
                'author_condition_name': 'HIP' if hip else 'As-built',
                'stress_relief_temperature_c': '' if reused else 550,
                'stress_relief_hours': '' if reused else 6,
                'manufacturing_method_scope': 'Prior-curve processing not independently checked in108491; no current-paper processing transfer' if reused else 'Current-paper Methods2.1',
                'HIP_temperature_c': 1150 if hip else '',
                'HIP_pressure_mpa': 100 if hip else '', 'HIP_hours': 4 if hip else '',
                'author_specimen_id': '', 'physical_build_id': '', 'powder_lot_id': '',
                'specimen_plate_crosswalk_verified': False,
                'paper_build_description': 'Fig1 describes ambient and high-temperature sample plates; no unique author plate identifiers or table-point crosswalk supplied',
                'prior_exposure_or_virgin_status': 'not explicitly established per table point',
                'reused_25C_asbuilt_reference_curve': reused,
                'prior_curve_source_doi': '10.1016/j.ijfatigue.2024.108491' if reused else '',
                'source_family_block': 'Behvar_Aghayar_108491_109365',
                'article_license': 'CC BY-NC-ND 4.0',
                'acquisition_provenance': 'exact factual numerical table transcription from indexed primary publisher text; no graph digitization; no manuscript PDF retrieved',
                'gold_identity_qualified': False, 'axial_pool_eligible': False,
                'catalog_scope': 'separate rotating-bending source/condition-qualified panel; no current model run',
            })

def write_csv(name, records):
    with (OUT / name).open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(records)

write_csv('table1_rbf67.csv', rows)
write_csv('table1_not_reused_RTcurve42.csv', [r for r in rows if not r['reused_25C_asbuilt_reference_curve']])
counts = []
for cond in src['columns']:
    rs = [r for r in rows if r['condition'] == cond]
    counts.append({'condition':cond, 'reported_points':len(rs), 'failure_points':sum(r['event'] for r in rs),
                   'runout_points':sum(r['runout'] for r in rs),
                   'stress_levels':len({r['stress_amplitude_mpa'] for r in rs}),
                   'reused_prior_reference_curve':rs[0]['reused_25C_asbuilt_reference_curve']})
with (OUT / 'condition_counts.csv').open('w', newline='') as handle:
    w = csv.DictWriter(handle, fieldnames=list(counts[0]));w.writeheader();w.writerows(counts)

assert len(rows) == 67 and sum(r['event'] for r in rows) == 63
assert len({r['source_point_locator'] for r in rows}) == 67
assert not any(r['author_specimen_id'] or r['physical_build_id'] or r['powder_lot_id'] for r in rows)
assert len([r for r in rows if not r['reused_25C_asbuilt_reference_curve']]) == 42
assert sum(r['failure_beyond_nominal_runout_threshold_retained'] for r in rows) == 1
receipt = {
    'status':'PASS', 'source_doi':src['source_doi'], 'reported_points':67,
    'failure_points':63, 'runout_points':4,
    'reported_points_not_from_reused_25C_asbuilt_curve':42,
    'reported_points_reused_from_108491':25, 'verified_unique_physical_specimens':None,
    'gold_identity_qualified_records':0, 'current_fit_rows_added':0,
    'condition_counts':counts,
    'censor_rule':'Runout label -> event0 and lower-bound5e6 from methods; exact individual stop remains blank',
    'beyond_threshold_rule':'Table reports450CAs-built140MPa6.07e6 failure; kept event1. Survival threshold≥5e6 does not prove mandatory stop at5e6, so no source-error claim.',
    'identity_rule':'Generated table point locators are never author specimen/build/powder identities',
    'run_command':'python3 literature/v4_open/rbf2026/normalize_table1.py',
    'input_sha256':hashlib.sha256((LIT/'table1_transcription.json').read_bytes()).hexdigest(),
    'output_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob('*.csv'))},
}
(LIT / 'normalization_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
