import numpy as np
from tskb.controller import BangBangController, PassiveController


def test_controller_action_interface():
    cfg = {"extend_accel": 1.0, "retract_accel": 1.0}
    state = np.zeros(10)
    action = BangBangController(cfg).action(0.0, state)
    assert isinstance(action, float)
    action = PassiveController().action(0.0, state)
    assert isinstance(action, float)
