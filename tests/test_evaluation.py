import numpy as np
from src.evaluation import conformal_quantile,risk_metrics,risk_status
from src.features import Encoder
import pandas as pd

def test_finite_group_quantile_resolution():
    assert np.isinf(conformal_quantile(np.arange(8)))
    assert conformal_quantile(np.arange(9))==8
    assert conformal_quantile(np.arange(19))==17

def test_censoring_identification_exact_boundary_and_factor():
    k,u=risk_status([5,5.1,5,5.1],[5,5,5,5],[1,1,0,0])
    assert k.tolist()==[False,True,False,False]
    assert u.tolist()==[False,False,False,True]
    m=risk_metrics([5,5.1,5,5.1],[5,5,5,5],[1,1,0,0])
    assert m['risk_lower']==.25 and m['risk_upper']==.5
    k,u=risk_status([5.2,5.4],[5,5],[1,0],2.)
    assert not k.any() and u.tolist()==[False,True]

def test_empty_acceptance_is_not_zero_risk():
    m=risk_metrics([5],[4],[1],[False]);assert np.isnan(m['risk_lower'])

def test_lower_bound_calibration_direction():
    from src.evaluation import conformal_quantile
    base=np.arange(10.)+5; y=base-.3
    q=conformal_quantile(base-y)
    assert np.allclose(base-q,y)

def test_encoder_never_learns_from_query():
    train=pd.DataFrame({'log_stress':[1.,3.],'load_ratio':[0.,0.]})
    e=Encoder('basquin').fit(train);saved=e.receipt()
    x=e.transform(pd.DataFrame({'log_stress':[np.nan,1000.],'load_ratio':[0.,np.nan]}))
    assert np.isfinite(x).all() and e.receipt()==saved and x[0,0]==0

