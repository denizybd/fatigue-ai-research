"""Frozen publication-held-out benchmark; all thresholds are calibration-only.

Models are related censored-life implementations, not a numerical reproduction
of Centola's unavailable original data/code or its variational output layer.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('VECLIB_MAXIMUM_THREADS','1')
from pathlib import Path
import argparse,json,time,hashlib
import numpy as np
import pandas as pd
from scipy.stats import norm
from src.models import LinearCensoredAFT,MLPCensoredAFT
from src.features import Encoder,support_distance
from src.evaluation import conformal_quantile,empirical_rank

ROOT=Path(__file__).resolve().parents[1]
SEEDS=[0,17,42]

def source_weights(groups):
    u,c=np.unique(groups,return_counts=True);sizes=dict(zip(u,c))
    return np.array([1./sizes[g] for g in groups])

def fit_fold(df,train_ix,cal_ix,test_ix,seed,fold,scheme,outdir,n_boot=8,model_names=('basquin','linear','mlp'),naive_events=False,mlp_maxiter=1500):
    tr=df.loc[train_ix];cal=df.loc[cal_ix];te=df.loc[test_ix]
    gtr=tr.group_id.to_numpy();w=source_weights(gtr)
    y=tr.log_life.to_numpy();event=tr.event.to_numpy()
    if naive_events:event=np.ones_like(event)
    rich=Encoder().fit(tr);x=rich.transform(tr);xc=rich.transform(cal);xt=rich.transform(te)
    dc=support_distance(x,xc);dt=support_distance(x,xt)
    fits=[];preds=[]
    # Source bootstrap instability, not a Bayesian posterior/prediction interval.
    uq_cal=[];uq_test=[];rng=np.random.default_rng(seed+500)
    unique=np.unique(gtr)
    for b in range(n_boot):
        sampled=rng.choice(unique,len(unique),replace=True)
        count={g:int((sampled==g).sum()) for g in unique}
        wb=w*np.array([count[g] for g in gtr])
        mod=LinearCensoredAFT(max_iter=1000).fit(x,y,event,wb)
        uq_cal.append(mod.predict_location(xc));uq_test.append(mod.predict_location(xt))
        fits.append(dict(model='linear_bootstrap',bootstrap=b,**mod.status_.to_dict(),sigma=mod.sigma_,sigma_at_bound=mod.sigma_at_bound_))
    uc=np.std(uq_cal,axis=0,ddof=1);ut=np.std(uq_test,axis=0,ddof=1)
    # Each rank is computed only from calibration X; test outcomes never affect it.
    cc=(empirical_rank(dc,dc)+empirical_rank(uc,uc))/2
    ct=(empirical_rank(dc,dt)+empirical_rank(uc,ut))/2
    thresholds={s:{str(a):float(np.quantile(v,a)) for a in [.5,.8]} for s,v in [('distance',dc),('instability',uc),('combined',cc)]}
    for model in model_names:
        enc=Encoder('basquin').fit(tr) if model=='basquin' else rich
        tx=enc.transform(tr);cx=enc.transform(cal);qx=enc.transform(te)
        mod=(MLPCensoredAFT(seed=seed,max_iter=mlp_maxiter) if model=='mlp' else LinearCensoredAFT(max_iter=1000)).fit(tx,y,event,w)
        fits.append(dict(model=model,**mod.status_.to_dict(),sigma=mod.sigma_,sigma_at_bound=mod.sigma_at_bound_))
        muc=mod.predict_location(cx);mut=mod.predict_location(qx)
        plus=te.copy();minus=te.copy();plus['log_stress']+=.01;minus['log_stress']-=.01
        stress_slope=(mod.predict_location(enc.transform(plus))-mod.predict_location(enc.transform(minus)))/.02
        basec=muc+norm.ppf(.1)*mod.sigma_;baset=mut+norm.ppf(.1)*mod.sigma_
        residual=basec-cal.log_life.to_numpy()
        qpool=conformal_quantile(residual)
        maxima=pd.DataFrame({'r':residual,'g':cal.group_id.to_numpy()}).groupby('g').r.max().to_numpy()
        qgroup=conformal_quantile(maxima)
        for bound,shift in [('model_q10',0.),('endpoint_pooled',qpool),('cohort_max',qgroup)]:
            p=te[['row_id','dataset_id','source_id','group_id','event','runout','log_life','log_stress','stress_amplitude']].copy()
            p['seed']=seed;p['fold']=fold;p['scheme']=scheme;p['model']=model;p['bound']=bound
            p['mu']=mut;p['sigma']=mod.sigma_;p['log_lower']=baset-shift;p['stress_slope']=stress_slope
            p['calibration_shift']=shift;p['n_calibration_groups']=len(maxima)
            p['distance']=dt;p['instability']=ut;p['combined']=ct
            for score in ['distance','instability','combined']:
                for a in [.5,.8]: p[f'accept_{score}_{a}']=p[score]<=thresholds[score][str(a)]
            preds.append(p)
    record={'scheme':scheme,'fold':fold,'seed':seed,'train_rows':tr.row_id.tolist(),'cal_rows':cal.row_id.tolist(),'test_rows':te.row_id.tolist(),
        'train_groups':sorted(tr.group_id.unique()),'cal_groups':sorted(cal.group_id.unique()),'test_groups':sorted(te.group_id.unique()),
        'encoder':rich.receipt(),'gate_thresholds':thresholds,'fits':fits}
    (outdir/'folds'/f'{scheme}_{fold}_{seed}.json').write_text(json.dumps(record,indent=2))
    return pd.concat(preds,ignore_index=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',default='data/processed/primary.csv');ap.add_argument('--output',default='results/primary');ap.add_argument('--scheme',choices=['source','random'],default='source');ap.add_argument('--seeds',default='0,17,42');ap.add_argument('--bootstraps',type=int,default=8);ap.add_argument('--limit-folds',type=int);ap.add_argument('--models',default='basquin,linear,mlp');ap.add_argument('--naive-events',action='store_true');ap.add_argument('--mlp-maxiter',type=int,default=1500);args=ap.parse_args()
    df=pd.read_csv(ROOT/args.input);out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True);(out/'folds').mkdir(exist_ok=True)
    groups=np.sort(df.group_id.unique());seeds=[int(s) for s in args.seeds.split(',')]
    assert len(groups)>=14,'Too few independent groups for >=4 fit groups after nine-source calibration; report feasibility failure.'
    outputs=[];started=time.time();data_hash=hashlib.sha256((ROOT/args.input).read_bytes()).hexdigest()
    code_hash=hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'src').glob('*.py')))).hexdigest()
    signature={'data_sha256':data_hash,'code_sha256':code_hash,'scheme':args.scheme,'bootstraps':args.bootstraps,'seeds':seeds,'models':args.models,'naive_events':args.naive_events,'mlp_maxiter':args.mlp_maxiter}
    manifest=out/'checkpoint_signature.json'
    if manifest.exists(): assert json.loads(manifest.read_text())==signature,'Checkpoint signature mismatch: choose a new output directory.'
    else:
        assert not list(out.glob('pred_*.csv')),'Unsigned prior checkpoints: choose a new output directory.'
        manifest.write_text(json.dumps(signature,indent=2))
    for seed in seeds:
        for i,g in enumerate(groups if args.scheme=='source' else ['random']):
            if args.limit_folds is not None and i>=args.limit_folds:break
            key=f'{args.scheme}_{i:03d}_{seed}';checkpoint=out/f'pred_{key}.csv'
            if checkpoint.exists():outputs.append(pd.read_csv(checkpoint));continue
            rng=np.random.default_rng(seed)
            if args.scheme=='source':
                other=groups[groups!=g];order=rng.permutation(other);ncal=max(9,int(np.ceil(.25*len(other))))
                calgroups=order[:ncal];traingroups=order[ncal:]
                assert len(traingroups)>=4
                ti=df.index[df.group_id.isin(traingroups)];ci=df.index[df.group_id.isin(calgroups)];qi=df.index[df.group_id==g]
                assert set(df.loc[ti].group_id).isdisjoint(df.loc[ci].group_id)
                assert not (set(df.loc[ti].group_id)|set(df.loc[ci].group_id)) & set(df.loc[qi].group_id)
            else:
                order=rng.permutation(df.index);nt=int(.6*len(order));nc=int(.2*len(order));ti=order[:nt];ci=order[nt:nt+nc];qi=order[nt+nc:]
            p=fit_fold(df,ti,ci,qi,seed,f'{i:03d}',args.scheme,out,args.bootstraps,args.models.split(','),args.naive_events,args.mlp_maxiter);p.to_csv(checkpoint,index=False);outputs.append(p)
            print(json.dumps({'fold':i,'heldout_group':g,'seed':seed,'n_train':len(ti),'n_cal':len(ci),'n_test':len(qi),'elapsed_s':round(time.time()-started,2)}),flush=True)
    pd.concat(outputs,ignore_index=True).to_csv(out/'predictions.csv',index=False)
    (out/'run_receipt.json').write_text(json.dumps({'arguments':vars(args),'data_sha256':data_hash,'groups':len(groups),'seeds':seeds,'duration_seconds':time.time()-started,'completed_folds':len(outputs)},indent=2))

if __name__=='__main__':main()
