"""At most three local workers, with stage ownership and resumable shards."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import os
import subprocess
import sys
import time
import traceback

from src.v6_run import Experiment, ROOT, write_json
from src.v6_pipeline import acquire_run_lock, single_thread_environment


def dispatch(stage, workers=3, cap=1e6):
    if stage not in ('inner', 'outer'):
        raise ValueError(stage)
    if workers not in (1, 2, 3):
        raise ValueError('phase6 permits1..3local worker processes')
    if cap not in (1e6, 1e7) or (stage == 'inner' and cap != 1e6):
        raise ValueError('inner tuning uses1M; outer cap must be1M or10M')
    # Shared across all caps/stages: concurrent callers cannot exceed3workers.
    with acquire_run_lock(ROOT/'work/v6/locks/dispatch.lock',
                          dict(kind='dispatch', stage=stage, cap=cap)) as owner:
        return _dispatch_locked(stage, workers, cap, owner)


def _dispatch_locked(stage, workers, cap, owner):
    logdir = ROOT/'logs/v6'/(stage if stage == 'inner' else f'outer_cap{int(cap)}')
    logdir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    results = []
    state = dict(stage=stage, cap=cap, workers=workers, status='starting',
                 dispatcher_pid=os.getpid(), freeze_sha256=None,
                 started_utc=datetime.now(timezone.utc).isoformat(),
                 total_jobs=0, completed_jobs=0, results=[])
    status_path = logdir/'dispatch_status.json'
    write_json(status_path, state)
    try:
        e = Experiment()  # Verify frozen bytes before starting a child.
        if stage == 'inner':
            jobs = [(f'pair_{i:02d}', ['inner', '--pairs', str(i)]) for i in range(66)]
        else:
            jobs = [(f'family_{i:02d}', ['outer', '--family', family, '--cap', str(cap)])
                    for i, family in enumerate(e.design['outer_families'])]
        state.update(status='running', freeze_sha256=e.freeze_hash, total_jobs=len(jobs))
        write_json(status_path, state)

        def run(job):
            name, args = job
            log = logdir/(name+'.log')
            receipt = logdir/(name+'.json')
            command = [sys.executable, '-m', 'src.v6_run']+args
            stamp = datetime.now(timezone.utc).isoformat()
            before = time.monotonic()
            result = dict(status='starting', pid=None, started_utc=stamp,
                          command=command, freeze_sha256=e.freeze_hash, log=str(log))
            try:
                with log.open('a') as handle:
                    handle.write('\n'+str(result)+'\n')
                    handle.flush()
                    process = subprocess.Popen(command, cwd=ROOT,
                        env=single_thread_environment(), stdout=handle,
                        stderr=subprocess.STDOUT, pass_fds=(owner.fileno(),))
                    result.update(status='running', pid=process.pid)
                    write_json(receipt, result)
                    code = process.wait()
                result.update(status='complete' if code == 0 else 'failed', returncode=code)
            except Exception as error:
                result.update(status='failed', returncode=None, error=repr(error),
                              traceback=traceback.format_exc())
            result.update(completed_utc=datetime.now(timezone.utc).isoformat(),
                          elapsed_seconds=time.monotonic()-before)
            write_json(receipt, result)
            return dict(name=name, **result)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending = [pool.submit(run, job) for job in jobs]
            for future in as_completed(pending):
                result = future.result()
                results.append(result)
                state.update(status='running', completed_jobs=len(results), results=results,
                             elapsed_seconds=time.monotonic()-started)
                write_json(status_path, state)
                print(f'{stage} {result["name"]} {result["status"]} '
                      f'{len(results)}/{len(jobs)} {result["elapsed_seconds"]:.1f}s', flush=True)
        if any(r['status'] != 'complete' for r in results):
            raise RuntimeError('one or more leaf jobs failed; inspect logs, keep completed shards')
    except BaseException as error:
        state.update(status='failed', completed_jobs=len(results), results=results,
                     completed_utc=datetime.now(timezone.utc).isoformat(),
                     elapsed_seconds=time.monotonic()-started, error=repr(error))
        write_json(status_path, state)
        raise
    else:
        state.update(status='complete', completed_jobs=len(results), results=results,
                     completed_utc=datetime.now(timezone.utc).isoformat(),
                     elapsed_seconds=time.monotonic()-started)
        write_json(status_path, state)
        return state


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('stage', choices=['inner', 'outer'])
    p.add_argument('--workers', type=int, choices=[1, 2, 3], default=3)
    p.add_argument('--cap', type=float, choices=[1e6, 1e7], default=1e6)
    a = p.parse_args()
    dispatch(a.stage, a.workers, a.cap)
