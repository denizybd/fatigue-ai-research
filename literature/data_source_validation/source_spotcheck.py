"""Recalculate source-specific spotchecks from retained manual markers and data.

Run with standard-library Python. No fitting or experimental outcome selection.
Manual marker coordinates are approximate and were visually chosen on unaltered
embedded figures. They do not constitute author-provided raw measurements.
"""
from pathlib import Path
import csv
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def stern():
    data = json.loads((HERE / 'Stern_database_article_partial_json_snapshot.json').read_text())
    values = data['scidata']['datasets'][0]['fatigue']['fat_data']
    markers = [(258,114,520),(406,154,480),(505,197,440),(581,244,400),(672,296,360),(877,354,320)]
    rows = []
    for point, ((x,y,sigma_max), (n, amplitude, runout)) in enumerate(zip(markers, values)):
        manual_n = 10 ** (4 + (x - 147) / 367)
        expected_a = .45 * sigma_max
        rows.append(dict(dataset_local_index=0,point_local_index=point,
            manual_marker_x_pixel=x,manual_marker_y_pixel=y,
            axis_x_1e4_pixel=147,axis_x_1e5_pixel=514,
            independent_N_approx=manual_n,original_sigma_max_MPa=sigma_max,
            source_R=.1,expected_sigma_a_MPa=expected_a,database_N=n,
            database_sigma_a_MPa=amplitude,database_runout=runout,
            relative_N_difference=abs(n-manual_n)/manual_n,
            relative_sigma_difference=abs(amplitude-expected_a)/expected_a))
    write_csv(HERE / 'Stern_Fig10_spotcheck.csv', rows)
    return dict(points=len(rows),max_relative_N_difference=max(x['relative_N_difference'] for x in rows),
        max_relative_sigma_difference=max(x['relative_sigma_difference'] for x in rows))


def voloskov():
    expected = list(csv.DictReader((HERE / 'Voloskov_Fig3_manual_expected.csv').open()))
    processed = ROOT / 'data/processed/all_sn_observations.csv'
    if not processed.exists():
        return {'status':'pending processed source rows'}
    data = [x for x in csv.DictReader(processed.open()) if x['doi'].lower() == '10.3390/ma13153293']
    if not data:
        return {'status':'no source rows in processed table'}
    # Pair only within the physical loading group using independently read stress
    # and log-cycle location. This is audit matching, not model optimization.
    used = set()
    rows = []
    for e in expected:
        ratio = float(e['source_R'])
        candidates = [i for i,d in enumerate(data) if i not in used and abs(float(d['load_ratio'])-ratio) < .001]
        if not candidates:
            rows.append(dict(manual_point_index=e['manual_point_index'],status='unmatched manual point',row_id='',
                source_group=e['source_group'],source_N_approx=e['source_N_approx'],database_N='',
                expected_sigma_a_MPa=e['expected_sigma_a_MPa'],database_sigma_a_MPa='',
                source_arrow_runout=e['source_arrow_runout'],database_runout='',
                relative_N_difference='',relative_sigma_difference=''))
            continue
        i = min(candidates, key=lambda i:abs(math.log10(float(data[i]['cycles_observed'])/float(e['source_N_approx'])))+
            abs(float(data[i]['stress_amplitude'])-float(e['expected_sigma_a_MPa']))/float(e['expected_sigma_a_MPa']))
        used.add(i)
        d = data[i]
        rows.append(dict(manual_point_index=e['manual_point_index'],status='matched nearest marker',row_id=d['row_id'],
            source_group=e['source_group'],source_N_approx=e['source_N_approx'],database_N=d['cycles_observed'],
            expected_sigma_a_MPa=e['expected_sigma_a_MPa'],database_sigma_a_MPa=d['stress_amplitude'],
            source_arrow_runout=e['source_arrow_runout'],database_runout=d['runout'],
            relative_N_difference=abs(float(d['cycles_observed'])/float(e['source_N_approx'])-1),
            relative_sigma_difference=abs(float(d['stress_amplitude'])/float(e['expected_sigma_a_MPa'])-1)))
    write_csv(HERE / 'Voloskov_Fig3_spotcheck.csv', rows)
    matched = [x for x in rows if x['row_id']]
    return dict(status='matched',manual_points=len(expected),database_points=len(data),matched=len(matched),
        unmatched_database_row_ids=[d['row_id'] for i,d in enumerate(data) if i not in used],
        runout_disagreements=[x['row_id'] for x in matched if int(x['source_arrow_runout']) != int(x['database_runout'])],
        max_relative_N_difference=max(x['relative_N_difference'] for x in matched),
        max_relative_sigma_difference=max(x['relative_sigma_difference'] for x in matched))


if __name__ == '__main__':
    summary = {'stern':stern(),'voloskov':voloskov()}
    (HERE / 'spotcheck_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
