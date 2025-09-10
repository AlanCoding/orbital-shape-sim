import pytest
from tskb import (
    Environment,
    SimulationError,
    make_controller,
    make_craft,
    run_simulation,
)


def test_collision_raises_runtime_error():
    env = Environment()
    cfg = {
        "craft": {"type": "barbell", "mass": 1000.0},
        "controller": {"type": "passive", "initial": {"altitude_m": -1.0}},
        "integrator": {"t_final": 10.0, "dt_output": 1.0},
    }
    craft = make_craft(cfg["craft"])
    ctrl = make_controller(cfg["controller"])
    with pytest.raises(SimulationError) as excinfo:
        run_simulation(env, craft, ctrl, cfg)
    assert " at t=" in str(excinfo.value)
