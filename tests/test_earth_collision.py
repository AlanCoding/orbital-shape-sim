import pytest
from tskb import Environment, DualBarbell, PassiveController, run_simulation


def test_collision_raises_runtime_error():
    env = Environment()
    craft = DualBarbell(1000.0)
    ctrl = PassiveController()
    cfg = {
        "altitude_m": 0.0,
        "integrator": {"t_final": 10.0, "dt_output": 1.0},
    }
    with pytest.raises(RuntimeError):
        run_simulation(env, craft, ctrl, cfg)
