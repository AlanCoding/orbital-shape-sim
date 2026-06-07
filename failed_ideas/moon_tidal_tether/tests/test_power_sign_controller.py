import numpy as np
from tskb.controller import BangBangController


def test_power_sign_controller_mean_positive():
    """Controller should flip sign so commanded power is positive on average."""
    cfg = {
        "power_tau_s": 0.01,
        "power_deadband": 0.0,
        "min_dwell_s": 0.0,
        "adapt_phase": False,
    }
    ctrl = BangBangController(cfg)

    r = np.array([1.0, 0.0, 0.0])
    rhat = r / np.linalg.norm(r)
    aQ = np.array([1.0, 0.0, 0.0])

    v_seq = [np.array([1.0, 0.0, 0.0]), np.array([-1.0, 0.0, 0.0])] * 5
    p_unit = []
    p_cmd = []
    for i, v in enumerate(v_seq, start=1):
        q_cmd = ctrl.step(float(i), r, v, aQ, rhat)
        p_unit.append(np.dot(v, aQ))
        p_cmd.append(np.dot(v, aQ * np.sign(q_cmd)))

    p_unit = np.array(p_unit)
    p_cmd = np.array(p_cmd)
    assert p_cmd.mean() > max(0.0, 0.5 * p_unit.mean())
