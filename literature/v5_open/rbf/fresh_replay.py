"""Isolated frozen RBF replay from empty caches; compare saved scientific CSVs."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,subprocess,time
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
AUDIT=ROOT/'literature/v5_open/rbf'
splits=json.loads((ROOT/'data/processed/v5/rbf/frozen_splits.json').read_text())
fresh=ROOT/'work/v5_fresh_replay'
if fresh.exists():fresh=fresh.with_name(fresh.name+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S'))
fresh.mkdir(parents=True,exist_ok=False)
files=set('src/'+p for p in splits['code_sha256'])
files.update(['src/v3_prepare.py','protocols/v5/rbf_design.txt'])
if (ROOT/'src/__init__.py').exists():files.add('src/__init__.py')
files.update(x['path'] for x in splits['inputs'].values())
files.update(str(p.relative_to(ROOT)) for p in (ROOT/'data/processed/v5/rbf').glob('*') if p.is_file())
for rel in sorted(files):
    dst=fresh/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dst)
assert not list(fresh.rglob('*.pkl'))
setup={'fresh_root':str(fresh),'created_utc':datetime.now(timezone.utc).isoformat(),
       'no_model_or_task_pickles_copied':True,'files':sorted(files),
       'source_hashes':{rel:hashlib.sha256((fresh/rel).read_bytes()).hexdigest() for rel in sorted(files)}}
(AUDIT/'fresh_replay_setup.json').write_text(json.dumps(setup,indent=2)+'\n')
env=os.environ.copy();env['PYTHONPATH']=str(fresh)
python=str(ROOT/'.venv/bin/python')
elapsed={}
# Sequential caps: fit two populations once, then reuse this new cache for cap2.
for tag,cap in [('5e6',5000000),('1e7',10000000)]:
    output=fresh/f'results/v5/rbf_cap{tag}';start=time.monotonic()
    with (fresh/f'run_cap{tag}.log').open('w') as log:
        subprocess.run([python,'-m','src.v5_rbf','run','--output',str(output),'--cap',str(cap)],
                       cwd=fresh,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run([python,'-m','src.v5_rbf','summarize','--output',str(output)],
                       cwd=fresh,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    elapsed[tag]=time.monotonic()-start
    print('Completed fresh cap'+tag+' in '+str(round(elapsed[tag],2))+'s',flush=True)
comparisons=[];maxdiff=0.
for tag in ['5e6','1e7']:
    original=ROOT/f'results/v5/rbf_cap{tag}';replay=fresh/f'results/v5/rbf_cap{tag}'
    for f in sorted(original.rglob('*.csv')):
        rel=f.relative_to(original);other=replay/rel
        same=f.read_bytes()==other.read_bytes()
        a,b=pd.read_csv(f),pd.read_csv(other)
        assert a.columns.equals(b.columns) and len(a)==len(b)
        err=0.
        for c in a.select_dtypes(include='number').columns:
            av,bv=a[c].to_numpy(),b[c].to_numpy()
            assert np.array_equal(np.isnan(av),np.isnan(bv))
            assert np.array_equal(np.isposinf(av),np.isposinf(bv))
            assert np.array_equal(np.isneginf(av),np.isneginf(bv))
            finite=np.isfinite(av)&np.isfinite(bv)
            if finite.any():err=max(err,float(np.max(np.abs(av[finite]-bv[finite]))))
        maxdiff=max(maxdiff,err)
        comparisons.append({'cap':tag,'file':str(rel),'byte_identical':same,'max_numeric_difference':err,
                            'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
fits=[]
for tag in ['5e6','1e7']:
    a=json.loads((ROOT/f'results/v5/rbf_cap{tag}/run_receipt.json').read_text())
    b=json.loads((fresh/f'results/v5/rbf_cap{tag}/run_receipt.json').read_text())
    for regime in a['fits']:
        x={k:v for k,v in a['fits'][regime].items() if k!='elapsed_seconds'}
        y={k:v for k,v in b['fits'][regime].items() if k!='elapsed_seconds'}
        fits.append({'cap':tag,'regime':regime,'all_parameters_diagnostics_equal':x==y,
                     'fresh_fit_elapsed_seconds':b['fits'][regime]['elapsed_seconds'],
                     'all_population_models_converged':all(z['success'] for z in b['fits'][regime]['fits'].values()),
                     'rfl_fallback_active':b['fits'][regime]['fits']['rfl']['fallback_active'],
                     'rfl_selected_bound_hits':b['fits'][regime]['fits']['rfl']['bound_hits']})
receipt={'status':'PASS' if all(x['byte_identical'] for x in comparisons) and all(x['all_parameters_diagnostics_equal'] for x in fits) else 'DIFFERENCES_REQUIRING_REVIEW',
         'fresh_root':str(fresh),'no_model_or_task_pickles_copied':True,
         'scientific_csv_count':len(comparisons),'all_csv_byte_identical':all(x['byte_identical'] for x in comparisons),
         'max_numeric_difference':maxdiff,'fit_checks':fits,'elapsed_seconds':elapsed,'tables':comparisons,
         'interpretation':'Independent empty-cache numerical replay. This is reproducibility, not physical/reliability validation.'}
(AUDIT/'fresh_replay_comparison.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ['tables','fit_checks']},indent=2))
