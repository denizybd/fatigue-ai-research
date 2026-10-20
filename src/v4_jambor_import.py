"""Curate cyclic histories; do not manufacture independent Nf observations."""
from __future__ import annotations
import csv,gzip,hashlib,json
from pathlib import Path
import pandas as pd
from src.v3_prepare import ROOT,digest

def run():
    base=ROOT/'data/external_v4/jambor2025'
    source=base/'selected_original_files/1 Fatigue_tests'
    specs={};records=[];inputs={}
    for p in sorted(source.glob('*.csv')):
        rows=list(csv.reader(p.open(encoding='utf-8-sig')))
        inputs[str(p.relative_to(ROOT))]=digest(p)
        kind='peak_valley' if 'peak-valley' in p.name else 'selected_whole_cycles'
        assert rows[8][1]=='mm/mm' and rows[8][2]=='kN'
        for j in range(0,len(rows[2]),4):
            if not rows[2][j].strip():continue
            shape=rows[2][j].strip();no=rows[2][j+1].strip()
            sid=f'jambor2025_{shape.split()[0].lower()}_{no}'
            amplitude=float(rows[3][j+1].strip('%'))/100
            stop=int(rows[4][j+1]);area=float(rows[5][j+1])
            info=dict(canonical_history_id=sid,author_specimen_label=shape+' '+no,
                geometry=shape,source_doi='10.5281/zenodo.14763342',
                source_family='jambor_pelegatti_316L_precautionary_family',
                total_strain_amplitude=amplitude,planned_interruption_cycles=stop,
                area_mm2=area,endpoint='planned_interruption_for_microstructure; not_failure_life',
                build_id='',powder_lot_id='',material='316L',manufacturing='LPBF',
                primary_life_benchmark_eligible=False)
            if sid in specs:assert specs[sid]==info
            specs[sid]=info
            for ri,row in enumerate(rows[9:],start=10):
                cells=row[j:j+3]
                if not any(c.strip() for c in cells):continue
                if len(cells)!=3 or not all(c.strip() for c in cells):
                    raise ValueError((p.name,ri,j,cells))
                cycle,strain,force=map(float,cells)
                records.append(dict(canonical_history_id=sid,record_type=kind,
                    source_file=p.name,source_line=ri,cycle_count=cycle,
                    total_strain_mm_mm=strain,axial_force_kN=force,
                    nominal_stress_MPa=force*1000/area))
    assert len(specs)==7
    d=pd.DataFrame(records);s=pd.DataFrame(specs.values()).sort_values('canonical_history_id')
    # Deterministic gzip header; preserve every original source record in a long table.
    blob=d.to_csv(index=False).encode()
    with (base/'cyclic_response_long.csv.gz').open('wb') as f:
        with gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as g:g.write(blob)
    s.to_csv(base/'seven_interrupted_specimens.csv',index=False)
    d.groupby(['canonical_history_id','record_type']).agg(
        records=('source_line','size'),cycle_min=('cycle_count','min'),cycle_max=('cycle_count','max'),
        stress_min_MPa=('nominal_stress_MPa','min'),stress_max_MPa=('nominal_stress_MPa','max')).to_csv(base/'history_inventory.csv')
    rec=dict(inputs=inputs,specimens=7,force_record_rows=len(d),independent_Nf_rows_created=0,
        transformation='Nominal stress MPa = reported axial force kN*1000/reported cross-section mm2; total strain remains dimensionless.',
        identity='Geometry-qualified author labels; analyst canonical keys, no specimen-to-build/powder crosswalk.',
        endpoint='CSV Number of cycles is the planned interrupted exposure, not cycles to failure. These remain strain-control histories.',
        reuse='Same author program as Zenodo17985589 conservatively; do not sum as independent campaigns or assume distinct specimen union.',
        license='CC-BY-4.0; Jambor et al. Dataset DOI10.5281/zenodo.14763342. Changes: CSVs reshaped and nominal stress derived.',
        outputs={p.name:digest(p) for p in [base/'cyclic_response_long.csv.gz',base/'seven_interrupted_specimens.csv',base/'history_inventory.csv']})
    (base/'normalization_receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec,indent=2))

if __name__=='__main__':run()
