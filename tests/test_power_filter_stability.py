import numpy as np
from tskb.controller import BangBangController


def test_low_pass_filter_stable(recwarn):
    """Step controller with extreme dt without emitting warnings."""
    ctrl = BangBangController({})
    r = np.array([1.0, 0.0, 0.0])
    rhat = r / np.linalg.norm(r)
    v = np.array([0.0, 1.0, 0.0])
    aQ = np.array([0.0, 0.0, 1.0])

    ctrl.step(0.0, r, v, aQ, rhat)
    ctrl.step(1e12, r, v, aQ, rhat)
    ctrl.step(-1e12, r, v, aQ, rhat)

    assert np.isfinite(ctrl.state.p_lp)
    assert not recwarn.list
