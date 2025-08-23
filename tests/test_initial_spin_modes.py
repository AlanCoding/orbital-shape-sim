import numpy as np
import pytest

from tskb import Environment, DualBarbell, make_controller, run_simulation

@pytest.mark.parametrize(
    "mode, factor",
    [
        ("tidally_locked", 1.0),
        ("no_rotation", 0.0),
        ("prograde", 2.0),
        ("retrograde", -1.0),
    ],
)
def test_initial_spin_modes(mode, factor):
    cfg = {
        "mass": 1000.0,
        "altitude_m": 200000.0,
        "length0": 1000.0,
        "omega0": mode,
        "controller": {"type": "passive"},
        "integrator": {"t_final": 1.0, "dt_output": 1.0},
    }
    env = Environment()
    craft = DualBarbell(cfg["mass"])
    ctrl = make_controller(cfg["controller"])
    log = run_simulation(env, craft, ctrl, cfg)
    r0 = 6378e3 + cfg["altitude_m"]
    n0 = np.sqrt(env.mu_earth / r0**3)
    assert np.isclose(log["omega"][0], factor * n0)
