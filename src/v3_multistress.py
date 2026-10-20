"""Covariate-defined >=2 stress-level subset; frozen predictions unchanged."""
import argparse
from pathlib import Path
import pandas as pd
from src.v3_prepare import ROOT
from src.v3_summarize import summarize
def subset(folder,cohort=None):
    folder=Path(folder)
    d=pd.read_csv(folder/'predictions.csv')
    full=pd.read_csv(cohort or ROOT/'data/processed/v3/common/cohort.csv')
    n=full.groupby('dataset_id').log_stress.nunique()
    out=folder/'multistress';out.mkdir(exist_ok=True)
    d[d.dataset_id.isin(n[n>=2].index)].to_csv(out/'predictions.csv',index=False)
    summarize(out)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('--cohort')
    a=p.parse_args();subset(a.folder,a.cohort)
