"""Read-only candidate duplicate detection before model fitting.

This flags approximate reuse, not confirmed identical specimens, and never drops
rows or mutates grouping. It compares same-alloy L-PBF datasets across publications
using physical stress/life coordinates and recorded runout/load-ratio agreement.
Run after src/prepare_data.py; standard-library Python is sufficient.
"""
from pathlib import Path
from collections import defaultdict
import csv
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    input_file = ROOT / 'data/processed/ss316l_lpbf_all.csv'
    if not input_file.exists():
        raise SystemExit('Awaiting processed ss316l_lpbf_all.csv; no comparison was run.')
    groups = defaultdict(list)
    with input_file.open() as f:
        for r in csv.DictReader(f):
            r['n'] = float(r['cycles_observed'])
            r['s'] = float(r['stress_amplitude'])
            groups[r['dataset_id']].append(r)
    sets = list(groups.values())
    flagged = []
    exact_coordinate_pairs = []
    for i,a in enumerate(sets):
        for b in sets[i+1:]:
            if a[0]['source_id'] == b[0]['source_id']:
                continue
            # A different load ratio or loading mode is not the same test record.
            if a[0]['load_ratio'] != b[0]['load_ratio'] or a[0]['test_type'] != b[0]['test_type']:
                continue
            candidates = []
            for ai,x in enumerate(a):
                for bi,y in enumerate(b):
                    if x['runout'] != y['runout']:
                        continue
                    dn = abs(math.log(x['n']/y['n']))
                    ds = abs(math.log(x['s']/y['s']))
                    if dn <= math.log(1.02) and ds <= math.log(1.01):
                        candidates.append((dn/math.log(1.02)+ds/math.log(1.01),ai,bi,dn,ds))
                    if dn < 1e-10 and ds < 1e-10:
                        exact_coordinate_pairs.append(dict(row_a=x['row_id'],source_a=x['source_id'],
                            row_b=y['row_id'],source_b=y['source_id'],cycles=x['n'],stress_amplitude=x['s'],
                            caveat='matching coordinates do not prove repeated specimen'))
            # Greedy unique matching prevents one common runout from matching all
            # repeated records. This is a screening heuristic, not an identity test.
            matched = []
            used_a,used_b = set(),set()
            for score,ai,bi,dn,ds in sorted(candidates):
                if ai not in used_a and bi not in used_b:
                    used_a.add(ai);used_b.add(bi);matched.append((ai,bi,dn,ds))
            fraction = len(matched)/min(len(a),len(b))
            if len(matched) >= 3 and fraction >= .5:
                flagged.append(dict(dataset_a=a[0]['dataset_id'],source_a=a[0]['source_id'],
                    title_a=a[0]['title'],dataset_b=b[0]['dataset_id'],source_b=b[0]['source_id'],
                    title_b=b[0]['title'],n_a=len(a),n_b=len(b),matched=len(matched),
                    fraction_of_smaller=fraction,load_ratio=a[0]['load_ratio'],test_type=a[0]['test_type'],
                    matched_rows=';'.join(a[ai]['row_id']+'|'+b[bi]['row_id'] for ai,bi,_,_ in matched),
                    status='candidate reuse; verify source figures before changing groups'))
    for name,rows in [('duplicate_curve_candidates.csv',flagged),('exact_crosssource_coordinates.csv',exact_coordinate_pairs)]:
        with (HERE / name).open('w') as f:
            if rows:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary=dict(input=str(input_file.relative_to(ROOT)),datasets=len(sets),sources=len(set(x[0]['source_id'] for x in sets)),
        screening_tolerance=dict(cycles_relative=.02,stress_relative=.01),
        candidate_curves=len(flagged),exact_coordinate_pairs=len(exact_coordinate_pairs),
        caveat='No automatic grouping or row removal. Negative screen cannot exclude overlap at other digitization tolerances.')
    (HERE / 'duplicate_audit_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
