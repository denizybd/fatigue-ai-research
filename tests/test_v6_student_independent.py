"""Parent's independent numerical checks; generated values only, no fatigue fits."""
import numpy as np
import pytest
from scipy.integrate import quad
from scipy.optimize._numdiff import approx_derivative
from scipy.stats import norm, t

from src.v6_student_aft import CensoredStudentAFT, StudentAFTConfig
from tests.test_v6_student_aft import configured, frame


@pytest.mark.parametrize('nu',[4,10,np.inf])
@pytest.mark.parametrize('scatter',['constant','loglinear'])
@pytest.mark.parametrize('mean',['linear','two_knots'])
def test_full_marginal_objective_score_across_model_classes(nu,scatter,mean):
    m=configured(nu,.7,scatter,mean)
    d=frame((-1.9,-1.1,-.2,.25,.8,1.7),
        y=[6.6,6.9,5.7,6.3,5.8,5.2],event=[0,1,1,0,0,1])
    d['load_ratio']=[-1,.1,-1,.5,-1,.1]
    indices=[np.arange(3),np.arange(3,6)]
    _,gradient=m._objective(m.params_,d,indices)
    numeric=approx_derivative(lambda p:m._objective(p,d,indices)[0],
        m.params_,method='3-point',rel_step=3e-5).reshape(-1)
    np.testing.assert_allclose(gradient,numeric,rtol=3e-5,atol=3e-5)


@pytest.mark.parametrize('nu',[4,10,np.inf])
def test_selected_support_predictive_matches_direct_joint_integral(nu):
    m=configured(nu,3.,scale=.05)
    # Two contradictory failures create separated t-posterior modes. A third
    # runout prevents symmetry from hiding a wrong posterior weighting.
    s=frame((0.,0.,0.),y=[3.8,7.8,6.2],event=[1,1,0])
    q=frame((0.,))
    law=norm if np.isinf(nu) else t(nu)
    def support_kernel(u):
        return (law.pdf((-2-u)/.05)/.05*law.pdf((2-u)/.05)/.05*
                law.sf((.4-u)/.05)*norm.pdf(u,scale=3))
    # Rescale analytically by a constant to avoid tiny-evidence absolute-error
    # tolerance. The scaling cancels in numerator / denominator.
    anchors=np.array([-2.,0.,.4,2.])
    normalizer=max(support_kernel(u) for u in anchors)
    if np.isinf(nu):
        # Gaussian conflicting endpoints are extraordinarily improbable; its
        # conjugate failure part gives a stable center and rescaled kernel.
        v=1/(1/9+2/.05**2)
        def kernel(u):
            return norm.pdf(u,scale=np.sqrt(v))*norm.sf((.4-u)/.05)
        points=[0.,.1,.2,.3,.4]
        lower,upper=-1,1
    else:
        def kernel(u):return support_kernel(u)/normalizer
        points=anchors.tolist();lower,upper=-30,30
    z=quad(kernel,lower,upper,points=points,epsabs=1e-13,epsrel=1e-10,limit=600)[0]
    for endpoint in (4.1,5.9,7.6):
        numerator=quad(lambda u:kernel(u)*law.cdf((endpoint-5.8-u)/.05),
            lower,upper,points=sorted(set(points+[endpoint-5.8])),
            epsabs=1e-13,epsrel=1e-10,limit=600)[0]
        np.testing.assert_allclose(m.predict_cdf(endpoint,q,s),numerator/z,atol=3e-8)


def test_mean_knot_basis_and_heteroscedastic_scale_against_literal_formula():
    m=configured(4,.3,'loglinear','two_knots')
    s=np.array([-2.,-.4,0.,.4,2.])
    q=frame(s);q['load_ratio']=[-.5,-1,.1,-1,-1]
    mu,sd,_,_=m._evaluate(q)
    b=np.array([-.2,-.6,-.35]);k=np.array([-.4,.4])
    h=[np.maximum(s-x,0)-max(-x,0) for x in k]
    literal=5.8+.1*(q.load_ratio.to_numpy()+1)+b[0]*s+(b[1]-b[0])*h[0]+(b[2]-b[1])*h[1]
    np.testing.assert_allclose(mu,literal,atol=1e-14)
    np.testing.assert_allclose(sd,.25*np.exp(.2*s),atol=1e-14)
