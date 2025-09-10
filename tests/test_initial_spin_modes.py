import numpy as np
import pytest

from tskb import Environment, make_controller, make_craft, run_simulation


@pytest.mark.parametrize(
    "mode", ["tidally_locked", "no_rotation", "prograde", "retrograde", "fast_prograde"]
)
def test_initial_spin_modes(mode):
    cfg = {
        "craft": {"type": "barbell", "mass": 1000.0},
        "controller": {
            "type": "passive",
            "initial": {"altitude_m": 200000.0, "length0": 1000.0, "omega0": mode},
        },
        "integrator": {"t_final": 1.0, "dt_output": 1.0},
    }
    env = Environment()
    craft = make_craft(cfg["craft"])
    ctrl = make_controller(cfg["controller"])
    log = run_simulation(env, craft, ctrl, cfg)
    r0 = 6378e3 + cfg["controller"]["initial"]["altitude_m"]
    n0 = np.sqrt(env.mu_earth / r0**3)
    n_syn = n0 - env.n_moon
    expected = {
        "tidally_locked": n0,
        "no_rotation": 0.0,
        "prograde": n0 + n_syn,
        "retrograde": n0 - n_syn,
        "fast_prograde": 5.0 * (n0 + n_syn),
    }[mode]
    assert np.isclose(log["omega"][0], expected)
