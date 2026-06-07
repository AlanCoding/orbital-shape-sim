import numpy as np
from tskb.controller import LandisController
from tskb.env import Environment

def test_landis_controller_signs():
    cfg = {"extend_accel": 1.0, "retract_accel": 2.0}
    ctrl = LandisController(cfg)
    env = Environment()
    state = np.zeros(10)
    state[0:3] = np.array([1.0, 0.0, 0.0])
    # outward radial velocity -> extend
    state[3:6] = np.array([0.1, 0.0, 0.0])
    assert ctrl.action(0.0, state, env) == cfg["extend_accel"]
    # inward radial velocity -> retract
    state[3:6] = np.array([-0.1, 0.0, 0.0])
    assert ctrl.action(0.0, state, env) == -cfg["retract_accel"]
    # tangential -> no command
    state[3:6] = np.array([0.0, 0.1, 0.0])
    assert ctrl.action(0.0, state, env) == 0.0
