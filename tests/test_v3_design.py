import unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
from src.v3_design import choose_next,expected_information,truncate_support,LocalSlopeControl

class Base:
    center_=np.array([2.,.1]);params_=np.array([6.,-4.,0.]);sigma_=.3;tau_=.5
    def predict_location(self,x):return 6-4*(x.log_stress.to_numpy()-2)

class DesignTests(unittest.TestCase):
    def setUp(self):
        self.pool=pd.DataFrame({'row_id':['a','b','c','d'],'log_stress':[1.8,2.,2.2,2.4],
                                'load_ratio':[.1]*4})
        self.query=self.pool.iloc[[1,2]].copy()
    def test_information_limits(self):
        v=expected_information(np.array([-20.,0.,20.]),.3)
        self.assertLess(v[0],1e-20)
        self.assertAlmostEqual(v[2],1/.3**2)
        self.assertTrue(0<v[1]<v[2])
    def test_unrevealed_outcomes_are_forbidden(self):
        for field in ('event','log_life','runout','cycles_observed'):
            x=self.pool.copy();x[field]=999
            with self.assertRaises(ValueError):
                choose_next('active_query_variance',x,[],None,self.query,Base(),0,1e7)
    def test_selection_is_independent_of_hidden_outcomes(self):
        raw=self.pool.copy();raw['event']=1;raw['log_life']=4.
        cov=lambda x:x[['row_id','log_stress','load_ratio']]
        a=choose_next('active_query_variance',cov(raw),[],None,self.query,Base(),0,1e7)[0]
        raw['event']=0;raw['log_life']=100.
        b=choose_next('active_query_variance',cov(raw),[],None,self.query,Base(),0,1e7)[0]
        self.assertEqual(a,b)
    def test_span_starts_with_extremes(self):
        a=choose_next('stress_span',self.pool,[],None,self.query,Base(),0,1e7)[0]
        b=choose_next('stress_span',self.pool,[a],None,self.query,Base(),0,1e7)[0]
        self.assertEqual((a,b),('d','a'))
    def test_cap_does_not_turn_existing_runout_into_failure(self):
        x=pd.DataFrame({'log_life':[5.,8.,6.],'event':[0,1,1]})
        y=truncate_support(x,1e7)
        self.assertEqual(y.event.tolist(),[0,0,1])
        self.assertEqual(y.log_life.tolist(),[5.,7.,6.])
    def test_more_exact_support_shrinks_local_variance(self):
        support=self.pool.copy();support['event']=1;support['log_life']=Base().predict_location(support)
        model=LocalSlopeControl(Base())
        zero=model.predict_quantiles(self.query)
        few=model.predict_quantiles(self.query,support)
        self.assertTrue(np.all(few>zero))

if __name__=='__main__':unittest.main()
