import numpy as np
from tskb.controller import BangBangController


def test_power_sign_switching():
    cfg = {
        "extend_accel": 1.0,
        "retract_accel": 1.0,
        "min_dwell_s": 0.0,
        "power_tau_s": 0.01,
        "power_deadband": 0.0,
        "adapt_phase": False,
    }
    ctrl = BangBangController(cfg)
    r = np.array([1.0, 0.0, 0.0])
    rhat = r / np.linalg.norm(r)
    aQ = np.array([1.0, 0.0, 0.0])

    q1 = ctrl.step(1.0, r, np.array([1.0, 0.0, 0.0]), aQ, rhat)
    assert q1 > 0.0
    q2 = ctrl.step(2.0, r, np.array([-1.0, 0.0, 0.0]), aQ, rhat)
    assert q2 < 0.0
