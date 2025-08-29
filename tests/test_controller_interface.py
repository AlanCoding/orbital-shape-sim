import numpy as np
from tskb.controller import (
    BangBangController,
    PassiveController,
    LandisController,
    NeuralNetController,
    MoonAngleController,
    make_controller,
)
from tskb.env import Environment


def test_controller_action_interface():
    cfg = {"extend_accel": 1.0, "retract_accel": 1.0}
    state = np.zeros(10)
    state[0] = 1.0  # non-zero position for controller geometry
    env = Environment()
    action = BangBangController(cfg).action(0.0, state, env)
    assert isinstance(action, float)
    action = PassiveController().action(0.0, state, env)
    assert isinstance(action, float)
    action = LandisController(cfg).action(0.0, state, env)
    assert isinstance(action, float)
    action = NeuralNetController({"max_accel": 1.0}).action(0.0, state, env)
    assert isinstance(action, float)
    action = MoonAngleController({"max_accel": 1.0}).action(0.0, state, env)
    assert isinstance(action, float)
    action = make_controller({"type": "moon_angle", "max_accel": 1.0}).action(0.0, state, env)
    assert isinstance(action, float)
