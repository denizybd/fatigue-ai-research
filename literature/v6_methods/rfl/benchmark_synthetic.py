"""Reproducible synthetic runtime/accuracy check; never reads campaign data."""
from pathlib import Path
import argparse
import hashlib
import json
import time
import numpy as np
import pandas as pd
from src.v3_rfl import NormalNormalRFL
from src.v6_rfl_adapter import JointRFLTargetAdapter

ROOT=Path(__file__).resolve().parents[3]


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument('--case',choices=['ordinary','broad'],default='broad')
    cli.add_argument('--nquery',type=int,default=3)
    cli.add_argument('--output',required=True)
    args=cli.parse_args()
    codehash=hashlib.sha256((ROOT/'src/v6_rfl_adapter.py').read_bytes()).hexdigest()
    broad=args.case=='broad';sigma=.1 if broad else .4;tg=.03 if broad else .12
    su=1.6 if broad else .3;sv=.15 if broad else .05
    pop=NormalNormalRFL(nodes=96)
    pop.params_=np.array([5.,-3.,-.2,np.log(sigma),2.,np.log(tg)])
    pop.sigma_=sigma;pop.tau_gamma_=tg
    pop.ratio_median_=.1;pop.ratio_center_=.1;pop.log_stress_ref_=2.2
    def frame(stress,ids,y,event):
        return pd.DataFrame(dict(row_id=ids,dataset_id='synthetic',log_stress=np.log10(stress),
            load_ratio=.1,log_life=y,event=event))
    support=frame([150.,200.,240.] if broad else [170.,200.,240.],
        ['s0','s1','s2'],[6.,5.5,5.2],[0,1,1])
    stress=[120.,180.,240.] if broad and args.nquery==3 else np.geomspace(115.,260.,args.nquery)
    y=[6.5,5.2,4.7] if broad and args.nquery==3 else np.linspace(6.4,4.8,args.nquery)
    query=frame(stress,[f'q{i}' for i in range(args.nquery)],y,np.resize([0,1,1],args.nquery))
    adapter=JointRFLTargetAdapter(pop,su,sv)
    t=time.monotonic();score=adapter.predict_log_score(query,support);score_time=time.monotonic()-t
    score_receipt=adapter.last_prediction_receipt_.copy()
    print(f'{args.case} q{args.nquery} cold score seconds {score_time:.3f}',flush=True)
    t=time.monotonic();q=adapter.predict_quantiles(query,support);qtime=time.monotonic()-t
    result=dict(scope='Generated synthetic observations with fixed parameter fixture; no actual data fits',
        source_code_sha256_at_start=codehash,case=args.case,n_query=args.nquery,
        sigma=sigma,tauGamma=tg,life_prior_sd=su,v_prior_sd=sv,
        score_seconds_including_support=score_time,quantile_after_support_seconds=qtime,
        score=score.tolist(),quantiles=q.tolist(),score_receipt=score_receipt,
        prediction_receipt=adapter.last_prediction_receipt_,real_fatigue_rows_fitted=0)
    if broad and args.nquery==3:
        legacy=json.loads((ROOT/'literature/v6_methods/rfl/broad_prior_runtime_legacy_conditional_u.json').read_text())
        result['max_log_score_difference_from_original_uniform_rule']=float(np.max(np.abs(score-legacy['score'])))
        result['max_quantile_difference_from_original_uniform_rule']=float(np.max(np.abs(q-legacy['quantile'])))
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
