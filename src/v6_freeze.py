"""One-time prefit seal; refuses to overwrite or seal an existing actual run."""
from datetime import datetime,timezone
import importlib.metadata
import json
from pathlib import Path
import platform
from src.v6_run import ROOT,FREEZE,candidate_grid,digest,write_json

RUNTIME=[
 'src/v6_run.py','src/v6_dispatch.py','src/v6_pipeline.py','src/v6_freeze.py','run_v6.sh',
 'src/v6_controls.py','src/v6_selection.py','src/v6_gp.py','src/v6_metrics.py','src/v6_analyze.py',
 'src/v6_student_aft.py','src/v6_rfl_adapter.py','src/v6_prepare.py',
 'src/v2_models.py','src/v2_curved_models.py','src/v3_design.py','src/v3_rfl.py',
 'protocols/v6/nested_design.txt','protocols/v6/grid.json',
 'data/processed/v4/controlled_expansion/expanded441.csv',
 'data/processed/v6/episode_design.json']


def freeze():
    from src.v6_pipeline import acquire_run_lock
    with acquire_run_lock(ROOT/'work/v6/locks/freeze.lock',dict(kind='prefit_seal')):
        return _freeze_locked()


def _freeze_locked():
    if FREEZE.exists():raise FileExistsError('phase6 already sealed; never overwrite the historical freeze')
    if list((ROOT/'results/v6').glob('inner/pair_*/*.csv')) or list((ROOT/'results/v6').glob('outer*/task_*.pkl')):
        raise RuntimeError('actual phase6 results already exist; a prefit claim would be false')
    write_json(ROOT/'protocols/v6/grid.json',candidate_grid())
    design=json.loads((ROOT/'data/processed/v6/episode_design.json').read_text())
    assert len(design['outer_families'])==12 and len(design['excluded_family_pair_trainsets'])==66
    assert len(design['outer_tasks'])==370 and len(candidate_grid())==146
    value=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        status='sealed before first actual phase6 fatigue population fit',
        historical_outcomes_already_seen=True,analysis_is_exploratory=True,
        outer_source_families=12,inner_pair_trainsets=66,candidate_count=146,
        phase6_actual_model_fits_at_seal=0,
        sha256={path:digest(ROOT/path) for path in RUNTIME},
        environment=dict(python=platform.python_version(),platform=platform.platform(),
            packages={x:importlib.metadata.version(x) for x in ['numpy','scipy','pandas','pytest']},
            execution_threads='OPENBLAS/VECLIB/OMP/MKL=1 in run_v6.sh'),
        authority='public-source reading and reversible local computation only; no correspondence/publication',
        completion='seal is permission to execute declared comparisons, not proof of scientific success')
    write_json(FREEZE,value)
    print(json.dumps(value,indent=2))


if __name__=='__main__':freeze()
