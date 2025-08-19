import numpy as np
from tskb.controller import BangBangController


def test_tidal_forcing_switch():
    cfg = {
        "extend_accel": 1.0,
        "retract_accel": 1.0,
        "delta_phase_deg": 0.0,
        "nu_window_deg": 5.0,
    }
    ctrl = BangBangController(cfg)
    state = np.zeros(10)
    state[0:3] = [1.0, 0.0, 0.0]
    assert ctrl.action(0.0, state) == -1.0
    state[0:3] = [-1.0, 0.0, 0.0]
    assert ctrl.action(0.0, state) == 1.0
    state[0:3] = [0.0, 1.0, 0.0]
    assert ctrl.action(0.0, state) == 0.0
