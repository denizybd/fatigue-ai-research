"""Outcome-blind few-shot splits. Run only after reviewing provenance gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PANELS = {'A': (8, [0, 3]), 'B': (10, [0, 3, 5]), 'C': (15, [0, 3, 5, 10])}
SEEDS = [0, 17, 42]
INVALID_CONSTANT_AMPLITUDE = ['10.1016/j.ijfatigue.2021.106552']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rank(items, *salt):
    prefix = '|'.join(map(str, salt)) + '|'
    return sorted(map(str, items), key=lambda x: hashlib.sha256((prefix+x).encode()).hexdigest())


def remove_near_clusters(frame):
    """Conservative one-per-near-coordinate component; not specimen dedup proof."""
    retained, mapping = [], []
    for curve, d in frame.groupby('dataset_id', sort=True):
        d = d.sort_values('row_id').reset_index(drop=True)
        parent = list(range(len(d)))
        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        for a in range(len(d)):
            for b in range(a+1, len(d)):
                if (d.event[a] == d.event[b] and
                    abs(d.log_stress[a]-d.log_stress[b]) <= np.log10(1.01) and
                    abs(d.log_life[a]-d.log_life[b]) <= np.log10(1.02)):
                    pa, pb = find(a), find(b)
                    parent[max(pa, pb)] = min(pa, pb)
        for i, row in d.iterrows():
            representative = d.iloc[find(i)].row_id
            if representative == row.row_id:
                retained.append(row.row_id)
            else:
                mapping.append({'dataset_id': curve, 'removed': row.row_id,
                                'retained': representative})
    return frame[frame.row_id.isin(retained)].copy(), mapping


def prepare(cohort='clean', near_clusters=False, destination=None, calibration=True):
    raw = ROOT/'data/processed/primary.csv'
    d = pd.read_csv(raw)
    d=d[~d.doi.isin(INVALID_CONSTANT_AMPLITUDE)].copy()
    if cohort == 'strict':
        gate=pd.read_csv(ROOT/'literature/provenance_v2/final_source_gate.csv')
        eligible=gate.loc[gate.source_gate_status.str.startswith('eligible'),'source_id']
        d=d[d.doi.isin(eligible)].copy()
        family=gate.set_index('source_id').family_id.to_dict()
        d['group_id']=d.doi.map(family)
    elif cohort == 'clean':
        d = d[~d.group_id.str.startswith('curve_reuse_family')].copy()
    elif cohort == 'weak':
        d = pd.read_csv(ROOT/'data/processed/primary_weak_edge.csv')
    elif cohort != 'all':
        raise ValueError(cohort)
    mapping = []
    if cohort == 'weak':
        d=d[~d.doi.isin(INVALID_CONSTANT_AMPLITUDE)].copy()
    corrections=ROOT/'literature/provenance_v2/frozen_point_corrections.csv'
    if corrections.exists():
        for correction in pd.read_csv(corrections).to_dict('records'):
            selected=d.row_id==correction['row_id']
            if selected.any():
                field=correction['field'];value=correction['corrected_value']
                if field in ['event','runout']:value=int(float(value))
                elif field not in ['thermal','surface']:value=float(value)
                d.loc[selected,field]=value
    if near_clusters:
        d, mapping = remove_near_clusters(d)
    folder = Path(destination) if destination else ROOT/'data/processed/v2'/(
        cohort+('_nearcluster' if near_clusters else ''))
    folder.mkdir(parents=True, exist_ok=True)
    d = d.sort_values('row_id').reset_index(drop=True)
    d.to_csv(folder/'cohort.csv', index=False)
    pd.DataFrame(mapping, columns=['dataset_id','removed','retained']).to_csv(
        folder/'near_cluster_removals.csv', index=False)
    sizes = d.groupby('dataset_id').size()
    curves = {k: g for k,g in d.groupby('dataset_id', sort=True)}
    blocks = sorted(d.group_id.unique())
    tasks, counts = [], []
    for panel, (minimum, ks) in PANELS.items():
        eligible = sorted(sizes[sizes >= minimum].index)
        eligible_blocks = sorted(d[d.dataset_id.isin(eligible)].group_id.unique())
        counts.append({'panel':panel, 'min_rows':minimum, 'support_sizes':ks,
                       'curves':len(eligible), 'blocks':len(eligible_blocks),
                       'rows':int(sizes.loc[eligible].sum())})
        for seed in SEEDS:
            partitions = {}
            for curve in eligible:
                order = rank(curves[curve].row_id, 'v2', panel, seed, 'support-query')
                partitions[curve] = {'support_pool':order[:max(ks)],
                                     'query_ids':order[max(ks):]}
            for outer in eligible_blocks:
                # Preserve at least four fitting blocks. Fewer than nine
                # calibration blocks produce the honest zero 90% bound.
                m=min(9,max(0,len(blocks)-1-4)) if calibration else 0
                cal = rank([b for b in eligible_blocks if b != outer],
                           'v2', panel, seed, outer, 'calibration')[:m]
                fit = sorted(set(blocks)-{outer}-set(cal))
                if not fit:
                    raise ValueError('No fitting blocks')
                chosen = []
                for b in cal:
                    candidate = [c for c in eligible if curves[c].group_id.iloc[0] == b]
                    c = rank(candidate, 'v2', panel, seed, outer, b, 'cal-curve')[0]
                    q = rank(partitions[c]['query_ids'], 'v2', panel, seed, outer,
                             b, 'cal-query')[0]
                    chosen.append({'block':b, 'curve':c, 'query_id':q,
                                   **partitions[c]})
                targets = [{'curve':c, **partitions[c]} for c in eligible
                           if curves[c].group_id.iloc[0] == outer]
                tasks.append({'panel':panel, 'seed':seed, 'outer':outer,
                              'ks':ks, 'fit_blocks':fit, 'cal_blocks':cal,
                              'calibration':chosen, 'targets':targets})
    receipt = {'created_utc':datetime.now(timezone.utc).isoformat(),
               'source_sha256':digest(raw), 'cohort_sha256':digest(folder/'cohort.csv'),
               'cohort':cohort, 'near_cluster_sensitivity':near_clusters,
               'calibration_enabled':calibration,
               'n_rows':len(d), 'n_curves':d.dataset_id.nunique(),
               'n_blocks':d.group_id.nunique(), 'panels':counts, 'tasks':tasks,
               'row_id_role':'database address, not original physical specimen ID',
               'scope':'retrospective phase2; no real-data model outcomes used by this splitter'}
    receipt['protocol_hashes']={str(p.relative_to(ROOT)):digest(p)
        for p in sorted((ROOT/'protocols/v2').glob('*.md'))}
    receipt['gate_hashes']={str(p.relative_to(ROOT)):digest(p)
        for p in sorted((ROOT/'literature/provenance_v2').glob('frozen_*.csv'))}
    finalgate=ROOT/'literature/provenance_v2/final_source_gate.csv'
    if finalgate.exists():receipt['gate_hashes'][str(finalgate.relative_to(ROOT))]=digest(finalgate)
    (folder/'frozen_splits.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='tasks'}, indent=2))
    return folder


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--cohort',choices=['strict','clean','all','weak'],default='clean')
    p.add_argument('--near-clusters',action='store_true');p.add_argument('--destination')
    p.add_argument('--no-calibration',action='store_true')
    a=p.parse_args();prepare(a.cohort,a.near_clusters,a.destination,not a.no_calibration)
