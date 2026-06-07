from tskb import Environment, make_controller, make_craft, run_simulation


def test_point_mass_runs():
    cfg = {
        "craft": {"type": "point", "mass": 1000.0},
        "controller": {"type": "passive", "initial": {"altitude_m": 200000.0}},
        "integrator": {"t_final": 10.0, "dt_output": 5.0},
    }
    env = Environment()
    craft = make_craft(cfg["craft"])
    ctrl = make_controller(cfg["controller"])
    log = run_simulation(env, craft, ctrl, cfg)
    assert log["t"][0] == 0.0
    assert log["r"].shape[0] == log["t"].size
