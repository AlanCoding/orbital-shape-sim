import copy
import numpy as np
from tskb import Environment, make_controller, make_craft, run_simulation
from tskb.cr3bp import l1_unstable_mode


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


def _project_along_em_axis(env: Environment, log: dict, x_l1: float) -> np.ndarray:
    offsets = []
    for t, r in zip(log["t"], log["r"]):
        theta = env.n_moon * t
        c, s = np.cos(theta), np.sin(theta)
        rot = np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]])
        r_l1 = np.array([x_l1 * c, x_l1 * s, 0.0])
        offsets.append((rot @ (r - r_l1))[0])
    return np.asarray(offsets)


def test_diamond_stabilizer_reduces_drift():
    env = Environment()
    craft_cfg = {"type": "diamond", "mass": 1000.0}
    integrator_cfg = {"t_final": 24 * 3600.0, "dt_output": 1800.0}
    initial_cfg = {"vx0": -0.5}

    mu = env.mu_moon / (env.mu_earth + env.mu_moon)
    mode = l1_unstable_mode(mu, env.r_moon, env.n_moon)
    x_l1 = (mode.x_l1_bary + mu) * env.r_moon

    def run(ctrl_cfg: dict) -> np.ndarray:
        cfg = {
            "craft": copy.deepcopy(craft_cfg),
            "controller": copy.deepcopy(ctrl_cfg),
            "integrator": copy.deepcopy(integrator_cfg),
        }
        craft = make_craft(cfg["craft"])
        ctrl = make_controller(cfg["controller"])
        log = run_simulation(env, craft, ctrl, cfg)
        return _project_along_em_axis(env, log, x_l1)

    passive_offsets = run({"type": "passive", "initial": initial_cfg})
    stabilizer_offsets = run({
        "type": "diamond_l1_stabilizer",
        "initial": initial_cfg,
    })

    passive_max = float(np.max(np.abs(passive_offsets)))
    stabilizer_max = float(np.max(np.abs(stabilizer_offsets)))

    assert stabilizer_max < 0.4 * passive_max
