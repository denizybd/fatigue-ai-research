"""Censoring-aware evaluation and finite-sample quantiles (no fitted outcomes)."""
import math
import numpy as np

def conformal_quantile(scores, alpha=.1):
    """Order ceil((m+1)*(1-alpha)); +infinity when rank exceeds m."""
    scores=np.asarray(scores,float)
    assert scores.ndim==1 and len(scores)>0 and np.all(np.isfinite(scores))
    k=math.ceil((len(scores)+1)*(1-alpha)-1e-12)
    return float(np.sort(scores)[k-1]) if k<=len(scores) else np.inf

def risk_status(log_lower, log_observed, event, factor=1.):
    """Known-danger/unknown indicators for lower > factor*true life.

    A surviving runout has T>C. If L<=factor*C the event is impossible;
    otherwise it is unknown. Equality is safe for the strict event.
    """
    lower=np.asarray(log_lower); y=np.asarray(log_observed); event=np.asarray(event)
    threshold=y+np.log10(factor)
    return (event==1)&(lower>threshold), (event==0)&(lower>threshold)

def risk_metrics(log_lower, log_observed, event, accepted=None, factor=1.):
    n=len(log_observed)
    a=np.ones(n,bool) if accepted is None else np.asarray(accepted,bool)
    k,u=risk_status(log_lower,log_observed,event,factor)
    na=int(a.sum()); known=int((k&a).sum()); unknown=int((u&a).sum())
    return {'n':n,'accepted':na,'availability':na/n if n else np.nan,
        'known_danger':known,'unknown_runouts':unknown,
        'risk_lower':known/na if na else np.nan,
        'risk_upper':(known+unknown)/na if na else np.nan}

def empirical_rank(reference, values):
    """Right-continuous reference CDF; no outcomes needed."""
    r=np.sort(np.asarray(reference));return np.searchsorted(r,values,side='right')/len(r)

