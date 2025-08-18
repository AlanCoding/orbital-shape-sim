import numpy as np
from tskb.controller import BangBangController


def test_tidal_forcing_switch():
    cfg = {
        "q_plus_scale": 1.0,
        "q_minus_scale": -1.0,
        "delta_phase_deg": 0.0,
        "nu_window_deg": 5.0,
    }
    ctrl = BangBangController(cfg)
    assert ctrl.select_q(0.0) == -1.0
    assert ctrl.select_q(np.pi) == 1.0
    assert ctrl.select_q(np.pi / 2) is None
