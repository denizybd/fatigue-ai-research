"""Read-only author workbook extraction. No fatigue model fitting or inferred IDs."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import math
import sys
import openpyxl

LIT = Path(__file__).resolve().parent
ROOT = LIT.parents[2]
DATA = ROOT / 'data/external_v4/raw_search'
sys.path.insert(0, str(LIT / 'xlrd-2.0.2-py2.py3-none-any.whl'))
import xlrd


def write(name, records):
    with (DATA / name).open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bartosak():
    path = DATA / 'bartosak2024_316L_fatigue_and_defects.xlsx'
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    values = list(book['Fatigue'].values)
    assert values[0] == ('ID', 'PSWT [MPa]', 'Nf [-]', 'Loading path')
    fatigue, defects = [], []
    for excelrow, (sid, swt, nf, loading) in enumerate(values[1:], 2):
        assert int(sid) == sid and nf > 0 and swt > 0
        fatigue.append({
            'observation_id': f'bartosak_zenodo12515773_specimen{sid}',
            'author_specimen_id': str(sid), 'specimen_id_status': 'author_numbered_specimen_ID_per_readme',
            'source_condition_id': f'bartosak108608_{loading.lower()}',
            'source_family_block': 'Bartosak108608_Zenodo12515773',
            'material': 'AISI316L', 'manufacturing_process': 'LPBF',
            'load_control': 'strain', 'loading_path': loading,
            'cycles_to_author_endpoint': nf, 'event': 1, 'runout': 0,
            'endpoint_definition': '10pct_drop_of_equivalent_stress_amplitude_from_tangent_to_saturated_evolution',
            'swt_parameter_MPa': swt, 'stress_amplitude_MPa': '',
            'prescribed_total_strain_amplitude': '', 'strain_ratio': '',
            'temperature_C': '', 'frequency_Hz': '', 'build_id': '', 'powder_batch_id': '',
            'identity_tier': 'author_specimen_and_source_condition;build_unknown',
            'ordinary_force_controlled_stress_life_eligible': False,
            'catalog_panel': 'separate_multiaxial_strain_control_LCF_SWT',
            'reason_for_separate_panel': 'SWT is stress-times-strain response parameter; not prescribed stress amplitude',
            'source_dataset_doi': '10.5281/zenodo.12515773',
            'source_article_doi': '10.1016/j.ijfatigue.2024.108608',
            'source_license': 'CC-BY-4.0', 'source_file_sha256': digest(path),
            'source_location': f'Fatigue!A{excelrow}:D{excelrow}',
        })
        sheet = book[f'Specimen_{sid}']
        dv = list(sheet.values)
        assert len(dv) == 11
        for rank, row in enumerate(dv[1:], 1):
            area, sphericity, distance, diameter = row
            defects.append({
                'author_specimen_id': str(sid), 'source_defect_row_rank': rank,
                'rank_is_author_defect_identifier': False,
                'projected_area_mm2': area, 'sphericity': sphericity,
                'distance_from_free_surface_mm': distance, 'defect_diameter_mm': diameter,
                'critical_plane': 'maximum_tensile_strain_plane_per_author_readme',
                'measurement_timing': 'not_explicitly_verified_pretest',
                'acquisition_covariate_admitted': False,
                'source_dataset_doi': '10.5281/zenodo.12515773',
                'source_license': 'CC-BY-4.0',
                'source_location': f'Specimen_{sid}!A{rank+1}:D{rank+1}',
            })
    assert len(fatigue) == 20 and len(defects) == 200
    assert len({x['author_specimen_id'] for x in fatigue}) == 20
    assert all(math.isfinite(float(x['swt_parameter_MPa'])) for x in fatigue)
    write('bartosak2024_LCF_SWT20.csv', fatigue)
    write('bartosak2024_defects200_auxiliary.csv', defects)
    return {'specimens': 20, 'author_loading_paths': dict(Counter(x['loading_path'] for x in fatigue)),
            'defect_measurements': 200, 'ordinary_stress_life_rows': 0,
            'scope': 'Published Section4 subset; do not claim complete experimental campaign.'}


def jambor():
    path = DATA / 'jambor2026_extracted/Dataset/1. LCF data/Fig 3_LCF data.xls'
    book = xlrd.open_workbook(str(path))
    sheet = book.sheet_by_name('Sa, eap, Vh')
    histories, summaries, orphan_cells = [], [], []
    for group, start, total_percent in [('eat0.5pct', 1, .5), ('eat0.8pct', 6, .8), ('eat0.4pct', 11, .4)]:
        assert 'Cycle number' == sheet.cell_value(1, start)
        series = []
        for i in range(2, sheet.nrows):
            v = [sheet.cell_value(i, start+j) for j in range(4)]
            if all(x == '' for x in v):
                continue
            assert all(x == '' or isinstance(x, (int, float)) and math.isfinite(x) for x in v)
            n, sa, eap, vh = v
            if n == '' or sa == '':
                orphan_cells.append({'source_sheet': 'Sa, eap, Vh', 'source_row': i+1,
                    'series_header': group, 'cycle_number': n, 'stress_amplitude_MPa': sa,
                    'plastic_strain_amplitude_fraction': eap, 'loop_shape_parameter': vh,
                    'status': 'preserved_orphan_cells_missing_cycle_or_stress;not_a_history_observation'})
                continue
            row = {
                'series_locator': f'jambor17985589_{group}',
                'locator_is_author_specimen_id': False, 'author_specimen_id': '',
                'material': '316L', 'manufacturing_process': 'SLM_LPBF',
                'source_family_block': 'Jambor14763342_17985589_precautionary',
                'load_control': 'total_strain', 'total_strain_amplitude_percent': total_percent,
                'total_strain_amplitude_fraction': total_percent/100,
                'strain_ratio': -1, 'test_temperature_author': 'room_temperature',
                'temperature_C': '', 'strain_rate_per_second': .005,
                'cycle_number_recorded': n, 'stress_amplitude_response_MPa': sa,
                'plastic_strain_amplitude_fraction': eap, 'loop_shape_parameter': vh,
                'build_id': '', 'powder_batch_id': '',
                'observation_type': 'within_specimen_cyclic_response_history',
                'independent_fatigue_life_observation': False,
                'source_dataset_doi': '10.5281/zenodo.17985589',
                'source_article_doi': '10.1016/j.msea.2026.150590',
                'source_license': 'CC-BY-4.0',
                'source_location': f'Sa, eap, Vh;row{i+1};columns{start+1}-{start+4}',
            }
            histories.append(row)
            series.append(row)
        summaries.append({
            'series_locator': series[0]['series_locator'],
            'author_specimen_id': '', 'locator_is_author_specimen_id': False,
            'total_strain_amplitude_percent': total_percent,
            'strain_ratio': -1, 'test_temperature_author': 'room_temperature',
            'recorded_cycle_response_rows': len(series),
            'first_recorded_cycle': series[0]['cycle_number_recorded'],
            'last_recorded_cycle': series[-1]['cycle_number_recorded'],
            'missing_loop_shape_parameter_rows': sum(x['loop_shape_parameter'] == '' for x in series),
            'cycles_to_failure': '', 'event': '',
            'endpoint_caution': 'Last recorded cycle is not silently relabelled as a certified failure endpoint.',
            'source_family_block': 'Jambor14763342_17985589_precautionary',
            'source_dataset_doi': '10.5281/zenodo.17985589',
            'source_license': 'CC-BY-4.0', 'source_file_sha256': digest(path),
        })
        assert all(b['cycle_number_recorded'] > a['cycle_number_recorded'] for a, b in zip(series, series[1:]))
    write('jambor2026_cyclic_response_history.csv', histories)
    write('jambor2026_series_catalog3.csv', summaries)
    if orphan_cells:
        write('jambor2026_orphan_cells_quarantined.csv', orphan_cells)
    return {'histories': len(summaries), 'cycle_response_rows': len(histories),
            'independent_Nf_observations_created': 0,
            'orphan_source_rows_quarantined': len(orphan_cells),
            'same_family_as_14763342': 'precautionary block; no independent-campaign claim',
            'excluded_from_original_experimental_rows': ['Soft ratio_DED sheet contains cited literature.',
                'Other softening-ratio workbooks include other published alloys/materials.',
                'Microstructure-only sheets and composition table do not create fatigue lives.']}


def raw_lcf_catalog():
    records = []
    for path in sorted((DATA / 'lcftest2025_selected_members').glob('*.csv')):
        count, low, high, delta = 0, {}, {}, Counter()
        last_time = None
        with path.open(encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                count += 1
                for key in ['Total Cycles', 'Total Cycle Count(8800MTB25266 Linear Waveform)',
                            'Strain 1 (%)', 'Stress']:
                    value = float(row[key])
                    assert math.isfinite(value)
                    low[key], high[key] = min(low.get(key, value), value), max(high.get(key, value), value)
                time = float(row['Total Time (s)'])
                if last_time is not None:
                    delta[round(time-last_time, 6)] += 1
                last_time = time
        records.append({
            'author_test_file_id': path.name, 'author_specimen_id': '',
            'file_id_is_verified_physical_specimen_id': False,
            'material': 'AM_stainless_steel_grade_unverified', 'manufacturing_process': 'LPBF',
            'condition_prefix': path.name.split('_')[1],
            'orientation_description_per_repository': 'orthogonal_to_substrate' if '_H_' in path.name else 'parallel_to_substrate',
            'strain_level_filename_author': '1am', 'load_control': 'strain',
            'test_temperature_C': '', 'build_id': '', 'powder_batch_id': '',
            'recording_rows': count, 'last_recorded_total_cycle': high['Total Cycles'],
            'last_recorded_controller_cycle': high['Total Cycle Count(8800MTB25266 Linear Waveform)'],
            'cycles_to_failure': '', 'event': '',
            'observed_strain_min_percent': low['Strain 1 (%)'],
            'observed_strain_max_percent': high['Strain 1 (%)'],
            'observed_stress_author_min': low['Stress'], 'observed_stress_author_max': high['Stress'],
            'stress_author_unit': 'unlabelled_in_raw_CSV_header',
            'time_step_mode_s': delta.most_common(1)[0][0], 'metadata_recording_frequency_Hz': 10,
            'frequency_caution': 'Recorded time increments disagree with a simple10Hz sampling claim; raw values preserved.',
            'life_endpoint_caution': 'Last counter is not silently converted to failure life; no scalar Nf created.',
            'source_dataset_doi': '10.5281/zenodo.17086687', 'source_license': 'CC-BY-4.0',
            'source_member_crc_verified': True, 'raw_file_sha256': digest(path),
            'catalog_panel': 'separate_LCF_raw_history_grade_unverified',
            'ordinary_stress_life_eligible': False,
        })
    assert len(records) == 2
    write('lcftest2025_selected_trace_catalog2.csv', records)
    return {'raw_ZIP_member_inventory': 25, 'LPBF_history_members_listed': 10,
            'selected_members_downloaded': 2,
            'selected_raw_time_samples': sum(row['recording_rows'] for row in records),
            'material_grade': 'AM stainless grade not explicitly verified; not admitted as316L',
            'source_file_aliases_are_not_physical_specimen_IDs': True,
            'new_scalar_Nf_created': 0,
            'metadata_time_sampling_caution': 'Claimed10Hz versus selected records modal0.012s steps; original values retained.'}


if __name__ == '__main__':
    result = {'bartosak': bartosak(), 'jambor': jambor(),
              'lcftest2025': raw_lcf_catalog(), 'models_fitted': False}
    (LIT / 'normalization_receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
