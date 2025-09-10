import numpy as np
from tskb import Environment, make_controller, make_craft, run_simulation


def test_diamond_passive_runs():
    cfg = {
        "craft": {"type": "diamond", "mass": 1000.0},
        "controller": {"type": "passive"},
        "integrator": {"t_final": 10.0, "dt_output": 5.0},
    }
    env = Environment()
    craft = make_craft(cfg["craft"])
    ctrl = make_controller(cfg["controller"])
    log = run_simulation(env, craft, ctrl, cfg)
    r0 = env.l1_position(0.0)
    assert np.allclose(log["r"][0], r0)
    assert log["r"].shape[0] == log["t"].size
