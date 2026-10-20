"""Declared censoring identification and source-level descriptive arithmetic."""
from __future__ import annotations
import numpy as np


def risk_bounds(log_quantile,log_endpoint,event):
    q,y,e=np.broadcast_arrays(np.asarray(log_quantile,float),np.asarray(log_endpoint,float),np.asarray(event,float))
    if not np.isfinite(y).all() or not np.isin(e,[0,1]).all():raise ValueError('finite endpoints and binary events required')
    available=~np.isnan(q)
    lower=np.where(available,(q>y)&(e==1),False).astype(float)
    upper=np.where(available,q>y,True).astype(float)
    return lower,upper


def paired_risk_change_bounds(log_new,log_reference,log_endpoint,event):
    """Extrema of I(Y<q_new)-I(Y<q_ref) over the SAME censored future Y."""
    a,b,y,e=np.broadcast_arrays(np.asarray(log_new,float),np.asarray(log_reference,float),
        np.asarray(log_endpoint,float),np.asarray(event,float))
    if not np.isfinite(y).all() or not np.isin(e,[0,1]).all():raise ValueError('finite endpoints and binary events required')
    available=~np.isnan(a)&~np.isnan(b)
    difference=(a>y).astype(float)-(b>y).astype(float)
    low=np.where(available,np.where(e==1,difference,-((b>a)&(b>y)).astype(float)),-1.)
    high=np.where(available,np.where(e==1,difference,((a>b)&(a>y)).astype(float)),1.)
    return low,high


def paired_cost_bounds(new_lower,new_upper,reference_lower,reference_upper):
    a,A,b,B=np.broadcast_arrays(*[np.asarray(x,float) for x in
        (new_lower,new_upper,reference_lower,reference_upper)])
    if (not np.isfinite([a,A,b,B]).all() or np.any(a<0) or np.any(b<0) or
            np.any(A<a) or np.any(B<b)):
        raise ValueError('finite nonnegative ordered cost intervals required')
    zero=(a==0)&(A==0)&(b==0)&(B==0)
    with np.errstate(divide='ignore',invalid='ignore'):
        ratio_low=np.where(zero,1.,a/B);ratio_high=np.where(zero,1.,A/b)
    return dict(change_lower=a-B,change_upper=A-b,
        ratio_lower=ratio_low,ratio_upper=ratio_high,
        savings_lower=1-ratio_high,savings_upper=1-ratio_low)


def paired_ledger_cost_bounds(new,reference):
    """Couple the SAME selected row's unknown capped cost across two policies.

    Inputs map row_id to (cost_lower,cost_upper), at one common cap. Shared
    costs cancel in differences and enter both numerator/denominator of ratios.
    Unknown costs of different rows retain conservative rectangular bounds.
    """
    new_count=len(new);reference_count=len(reference)
    new={str(k):tuple(map(float,v)) for k,v in new.items()}
    reference={str(k):tuple(map(float,v)) for k,v in reference.items()}
    if len(new)!=new_count or len(reference)!=reference_count:
        raise ValueError('row identity collision after string conversion')
    for lo,hi in list(new.values())+list(reference.values()):
        if not np.isfinite([lo,hi]).all() or lo<=0 or hi<lo:
            raise ValueError('finite positive ordered per-specimen costs required; k0 uses an empty ledger')
    common=set(new)&set(reference)
    for key in common:
        if new[key]!=reference[key]:raise ValueError('same row must have same cost bounds at matched cap')
    def sum_bounds(keys,table):return np.sum([table[k] for k in sorted(keys)],axis=0) if keys else np.zeros(2)
    c,C=sum_bounds(common,new)
    x,X=sum_bounds(set(new)-common,new)
    y,Y=sum_bounds(set(reference)-common,reference)
    if not new and not reference:low=high=1.
    else:
        cmin=c if Y>=x else C
        cmax=C if y>=X else c
        low=(cmin+x)/(cmin+Y) if cmin+Y>0 else (1. if cmin+x==0 else np.inf)
        high=(cmax+X)/(cmax+y) if cmax+y>0 else (1. if cmax+X==0 else np.inf)
    return dict(change_lower=x-Y,change_upper=X-y,ratio_lower=low,ratio_upper=high,
        savings_lower=1-high,savings_upper=1-low,shared_selected_rows=len(common),
        distinct_selected_rows=len(set(new)|set(reference)))


def source_means(frame,metric,strict=False):
    """Equal query rows, seeds within condition, conditions within source."""
    def mean(x):return x.mean(skipna=not strict)
    episode=frame.groupby(['group_id','dataset_id','seed'],dropna=False)[metric].agg(mean)
    condition=episode.groupby(['group_id','dataset_id'],dropna=False).agg(mean)
    return condition.groupby('group_id',dropna=False).agg(mean)


def source_bootstrap(values,strict=True):
    """Descriptive source-block interval; no physical independence theorem."""
    values=np.asarray(values,float);finite=np.isfinite(values);x=values[finite]
    result=dict(mean=float(x.mean()) if len(x) else np.nan,n_sources=len(values),n_finite_sources=len(x),
        lo95=np.nan,hi95=np.nan)
    if len(x)>=2 and (not strict or finite.all()):
        rng=np.random.default_rng(231)
        draws=x[rng.integers(0,len(x),(2000,len(x)))].mean(axis=1)
        result['lo95'],result['hi95']=map(float,np.quantile(draws,[.025,.975]))
    return result
