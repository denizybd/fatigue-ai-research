"""Runtime mocks and generated files only: no fatigue seal, plans or fits."""
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from unittest.mock import patch

import pytest

from src import v6_dispatch as dispatch
from src import v6_pipeline as pipeline
from src import v6_freeze as freezer


class FakeExperiment:
    freeze_hash = 'generated_mock_seal_not_an_actual_freeze'
    design = dict(outer_families=[f'generated_{i}' for i in range(12)])


def test_nonblocking_lock_and_child_inherited_ownership(tmp_path):
    path = tmp_path/'owner.lock'
    child = None
    try:
        with pipeline.acquire_run_lock(path, dict(test='generated')) as handle:
            with pytest.raises(RuntimeError, match='already running'):
                with pipeline.acquire_run_lock(path, {}):
                    pass
            child = subprocess.Popen([sys.executable, '-c',
                "import sys;print('ready',flush=True);sys.stdin.readline()"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                pass_fds=(handle.fileno(),))
            assert child.stdout.readline().strip() == 'ready'
        # Parent handle is closed; the artificial child retains the lock.
        with pytest.raises(RuntimeError, match='already running'):
            with pipeline.acquire_run_lock(path, {}):
                pass
    finally:
        if child is not None:
            child.communicate('\n', timeout=5)
    # A stale owner file does not prevent resuming after the child exits.
    with pipeline.acquire_run_lock(path, dict(test='resumed')):
        pass


def fake_popen_factory(module, duplicate=None, failed_call=None, spawn_failure=None):
    calls = []
    state = dict(active=0, peak=0, duplicate_rejected=False)
    mutex = threading.Lock()

    class Process:
        def __init__(self, command, **kwargs):
            with mutex:
                number = len(calls)+1
                calls.append((command, kwargs))
                if number == 1 and duplicate is not None:
                    with pytest.raises(RuntimeError, match='already running'):
                        duplicate()
                    state['duplicate_rejected'] = True
                if number == spawn_failure:
                    raise OSError('generated spawn failure')
                state['active'] += 1
                state['peak'] = max(state['peak'], state['active'])
            assert kwargs['cwd'] == module.ROOT
            assert kwargs['pass_fds'] and len(kwargs['pass_fds']) == 1
            assert all(kwargs['env'][name] == '1' for name in
                ['OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'])
            self.pid = 900000+number
            self.code = 7 if number == failed_call else 0

        def wait(self):
            time.sleep(.001)
            with mutex:
                state['active'] -= 1
            return self.code

    return Process, calls, state


@pytest.mark.parametrize('failure', [None, 'returncode', 'spawn'])
def test_dispatch_status_bounded_workers_duplicate_and_failures(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(dispatch, 'ROOT', tmp_path)
    monkeypatch.setattr(dispatch, 'Experiment', FakeExperiment)
    fake, calls, state = fake_popen_factory(dispatch,
        duplicate=lambda: dispatch.dispatch('outer', cap=1e7),
        failed_call=4 if failure=='returncode' else None,
        spawn_failure=4 if failure=='spawn' else None)
    with patch.object(dispatch.subprocess, 'Popen', fake):
        if failure:
            with pytest.raises(RuntimeError, match='leaf jobs failed'):
                dispatch.dispatch('inner', workers=3)
        else:
            dispatch.dispatch('inner', workers=3)
    result = json.loads((tmp_path/'logs/v6/inner/dispatch_status.json').read_text())
    assert result['status'] == ('failed' if failure else 'complete')
    assert result['completed_jobs'] == result['total_jobs'] == 66
    assert len(calls) == 66 and state['peak'] <= 3 and state['duplicate_rejected']
    assert result['freeze_sha256'] == FakeExperiment.freeze_hash
    assert sum(r['status']=='failed' for r in result['results']) == int(bool(failure))
    receipts = list((tmp_path/'logs/v6/inner').glob('pair_*.json'))
    assert len(receipts) == 66
    assert all(json.loads(p.read_text())['status'] in ('complete','failed') for p in receipts)


@pytest.mark.parametrize('failure', [None, 'returncode', 'spawn'])
def test_pipeline_duplicate_guard_and_stage_order(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(pipeline, 'ROOT', tmp_path)
    monkeypatch.setattr(pipeline, 'Experiment', FakeExperiment)
    fake, calls, state = fake_popen_factory(pipeline,
        duplicate=pipeline.run_pipeline,
        failed_call=3 if failure=='returncode' else None,
        spawn_failure=3 if failure=='spawn' else None)
    with patch.object(pipeline.subprocess, 'Popen', fake):
        if failure:
            with pytest.raises((RuntimeError,OSError)):
                pipeline.run_pipeline()
        else:
            pipeline.run_pipeline()
    result = json.loads((tmp_path/'logs/v6/pipeline_status.json').read_text())
    assert result['status'] == ('failed' if failure else 'complete')
    assert state['duplicate_rejected'] and len(calls) == (3 if failure else 8)
    expected = pipeline.pipeline_stages()[:len(calls)]
    assert [command[2:] for command, _ in calls] == [args for _, args in expected]
    assert result['freeze_sha256'] == FakeExperiment.freeze_hash
    if failure is None:
        assert all(s['status']=='complete' for s in result['completed_stages'])
    else:
        assert len(result['completed_stages']) == (3 if failure=='returncode' else 2)


@pytest.mark.parametrize('module,call,status_file', [
    (dispatch, lambda: dispatch.dispatch('inner'), 'inner/dispatch_status.json'),
    (pipeline, pipeline.run_pipeline, 'pipeline_status.json')])
def test_missing_or_changed_seal_cannot_launch_a_child(tmp_path, monkeypatch, module, call, status_file):
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    def unsealed():raise RuntimeError('generated missing/modified seal')
    monkeypatch.setattr(module, 'Experiment', unsealed)
    with patch.object(module.subprocess, 'Popen') as launch:
        with pytest.raises(RuntimeError, match='missing/modified seal'):
            call()
        launch.assert_not_called()
    status=json.loads((tmp_path/'logs/v6'/status_file).read_text())
    assert status['status']=='failed' and status['freeze_sha256'] is None


def test_invalid_dispatch_arguments_rejected_before_experiment(monkeypatch):
    with patch.object(dispatch, 'Experiment') as experiment:
        for args in [('inner',4,1e6),('outer',0,1e6),('inner',3,1e7),('outer',3,2e6)]:
            with pytest.raises(ValueError):dispatch.dispatch(*args)
        experiment.assert_not_called()


def test_synthetic_freezer_guards_only_generated_files(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(freezer, 'ROOT', tmp_path)
    seal = tmp_path/'protocols/v6/freeze.json'
    monkeypatch.setattr(freezer, 'FREEZE', seal)
    monkeypatch.setattr(freezer, 'RUNTIME', ['generated_runtime.txt'])
    monkeypatch.setattr(freezer, 'candidate_grid', lambda: [{} for _ in range(146)])
    (tmp_path/'generated_runtime.txt').write_text('no actual runtime or fatigue data\n')
    design = tmp_path/'data/processed/v6/episode_design.json'
    design.parent.mkdir(parents=True)
    design.write_text(json.dumps(dict(outer_families=list(range(12)),
        excluded_family_pair_trainsets=[{}]*66,outer_tasks=[{}]*370)))
    existing = tmp_path/'results/v6/inner/pair_00/generated.csv'
    existing.parent.mkdir(parents=True)
    existing.write_text('generated result\n')
    with pytest.raises(RuntimeError, match='results already exist'):freezer.freeze()
    assert not seal.exists()
    existing.unlink()  # Only this test's generated temporary file.
    freezer.freeze()
    contents = seal.read_bytes()
    with pytest.raises(FileExistsError):freezer.freeze()
    assert seal.read_bytes() == contents
    assert 'src/v6_pipeline.py' in Path(__file__).resolve().parents[1].joinpath('src/v6_freeze.py').read_text()
