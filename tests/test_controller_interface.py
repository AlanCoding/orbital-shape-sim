import numpy as np
from tskb.controller import BangBangController


def test_controller_action_interface():
    cfg = {"extend_accel": 1.0, "retract_accel": 1.0}
    ctrl = BangBangController(cfg)
    state = np.zeros(10)
    action = ctrl.action(0.0, state)
    assert isinstance(action, float)
