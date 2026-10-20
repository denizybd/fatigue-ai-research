"""Single-owner phase6 pipeline; every child independently checks the seal."""
from contextlib import contextmanager
from datetime import datetime, timezone
import errno
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from src.v6_run import Experiment, ROOT, write_json


def single_thread_environment():
    env = os.environ.copy()
    env.update({key: '1' for key in ('OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
                                   'OMP_NUM_THREADS', 'MKL_NUM_THREADS')})
    return env


@contextmanager
def acquire_run_lock(path, metadata):
    """Refuse a duplicate immediately; inherited children retain ownership.

    Closing, rather than explicitly unlocking, keeps the flock held if a child
    still owns this open-file description after its parent is interrupted.
    A stale file alone never counts as a held lock. No process is killed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open('a+')
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno not in (errno.EACCES, errno.EAGAIN):
                raise
            handle.seek(0)
            previous = handle.read(4096)
            raise RuntimeError(f'phase6 already running; lock {path}; owner {previous}') from error
        owner = dict(metadata, pid=os.getpid(),
                     started_utc=datetime.now(timezone.utc).isoformat())
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(owner)+'\n')
        handle.flush()
        os.fsync(handle.fileno())
        yield handle
    finally:
        handle.close()


def pipeline_stages():
    return [
        ('inner', ['src.v6_dispatch', 'inner', '--workers', '3']),
        ('select', ['src.v6_run', 'select']),
        ('outer_cap1e6', ['src.v6_dispatch', 'outer', '--workers', '3', '--cap', '1000000']),
        ('combine_cap1e6', ['src.v6_run', 'combine', '--cap', '1000000']),
        ('analyze_cap1e6', ['src.v6_analyze', 'results/v6/outer_cap1e6']),
        ('outer_cap1e7', ['src.v6_dispatch', 'outer', '--workers', '3', '--cap', '10000000']),
        ('combine_cap1e7', ['src.v6_run', 'combine', '--cap', '10000000']),
        ('analyze_cap1e7', ['src.v6_analyze', 'results/v6/outer_cap1e7']),
    ]


def run_pipeline():
    with acquire_run_lock(ROOT/'work/v6/locks/pipeline.lock', dict(kind='pipeline')) as owner:
        logdir = ROOT/'logs/v6'
        logdir.mkdir(parents=True, exist_ok=True)
        status_path = logdir/'pipeline_status.json'
        started = time.monotonic()
        state = dict(status='starting', pipeline_pid=os.getpid(), freeze_sha256=None,
                     started_utc=datetime.now(timezone.utc).isoformat(),
                     total_stages=len(pipeline_stages()), completed_stages=[], active_stage=None)
        write_json(status_path, state)
        try:
            e = Experiment()  # No child starts before verified freeze.json.
            state.update(status='running', freeze_sha256=e.freeze_hash)
            write_json(status_path, state)
            for number, (name, args) in enumerate(pipeline_stages(), 1):
                log = logdir/f'pipeline_{number:02d}_{name}.log'
                stage = dict(name=name, status='starting', pid=None,
                             command=[sys.executable, '-m']+args, log=str(log),
                             started_utc=datetime.now(timezone.utc).isoformat())
                state['active_stage'] = stage
                write_json(status_path, state)
                print(f'phase6 starting {number}/{state["total_stages"]} {name}', flush=True)
                before = time.monotonic()
                with log.open('a') as handle:
                    handle.write('\n'+str(stage)+'\n')
                    handle.flush()
                    process = subprocess.Popen(stage['command'], cwd=ROOT,
                        env=single_thread_environment(), stdout=handle,
                        stderr=subprocess.STDOUT, pass_fds=(owner.fileno(),))
                    stage.update(status='running', pid=process.pid)
                    write_json(status_path, state)
                    code = process.wait()
                stage.update(status='complete' if code == 0 else 'failed', returncode=code,
                             completed_utc=datetime.now(timezone.utc).isoformat(),
                             elapsed_seconds=time.monotonic()-before)
                state['completed_stages'].append(stage.copy())
                state['active_stage'] = None
                write_json(status_path, state)
                if code != 0:
                    raise RuntimeError(f'phase6 stage failed: {name}; inspect {log}')
        except BaseException as error:
            state.update(status='failed', completed_utc=datetime.now(timezone.utc).isoformat(),
                         elapsed_seconds=time.monotonic()-started, error=repr(error))
            if state['active_stage'] is not None:
                state['active_stage'].update(status='failed',
                    child_may_still_be_running=state['active_stage'].get('pid') is not None)
            write_json(status_path, state)
            raise
        else:
            state.update(status='complete', completed_utc=datetime.now(timezone.utc).isoformat(),
                         elapsed_seconds=time.monotonic()-started)
            write_json(status_path, state)
            return state


if __name__ == '__main__':
    run_pipeline()
