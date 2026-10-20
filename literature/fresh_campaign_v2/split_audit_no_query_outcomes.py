"""Poison query outcome fields to test few-shot prediction API isolation.
Uses fixed artificial parameters, not fitted real outcomes; imports models only.
"""
from pathlib import Path
import sys,json,math
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.v2_models import CensoredBasquin,HierarchicalCensoredBasquin,FixedSlopeShiftPredictor
D=ROOT/'data/processed/v2/strict';m=json.loads((D/'frozen_splits.json').read_text());task=m['tasks'][0];c=task['targets'][0];d=pd.read_csv(D/'cohort.csv').set_index('row_id',drop=False);query=d.loc[c['query_ids']].copy();support=d.loc[c['support_pool']].copy()
poison=query.copy();poison['log_life']=np.nan;poison['event']=-999;poison['cycles_observed']=float('inf');poison['runout']=-999
base=CensoredBasquin();base.params_=np.array([6.,-4.,.1,math.log(.3)]);base.center_=np.array([2.,0.]);base.ratio_median_=0.;base.sigma_=.3
hier=HierarchicalCensoredBasquin(nodes=41);hier.params_=np.r_[base.params_,math.log(.5)];hier.center_=base.center_.copy();hier.ratio_median_=0.;hier.sigma_=.3;hier.tau_=.5
checks=[]
for name,model in [('pooled',base),('unpooled_shift',FixedSlopeShiftPredictor(base)),('hierarchical',hier)]:
 for k in [0,3]:
  a=model.predict_quantiles(query,support=support.iloc[:k]);b=model.predict_quantiles(poison,support=support.iloc[:k]);assert np.array_equal(a,b,equal_nan=True),(name,k)
  checks.append({'model':name,'k':k,'n_queries':len(query),'max_difference':0.,'query_outcome_poisoning':'PASS'})
receipt={'status':'PASS','checks':checks,'parameters':'Fixed arbitrary artificial numerical parameters, not a real-data fit.','poisoned_columns':['log_life','event','cycles_observed','runout'],'meaning':'Predictive lower quantiles do not inspect query outcomes, while legitimate support outcomes remain supplied. This does not by itself audit every possible source of leakage.'}
p=ROOT/'literature/fresh_campaign_v2/split_audit_no_query_outcomes.json';p.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
