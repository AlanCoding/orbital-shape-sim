"""Smoke test loading LEO config and running a short sim."""
import yaml
import numpy as np
from pathlib import Path

from tskb import Environment, DualBarbell, make_controller, run_simulation


def test_yaml_config_simulates():
    cfg_path = Path("configs/leo_100km.yaml")
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # shorten integration for test runtime
    cfg["integrator"]["t_final"] = 60.0
    cfg["integrator"]["dt_output"] = 10.0
    env = Environment()
    craft = DualBarbell(cfg["mass"])
    ctrl = make_controller(cfg["controller"])
    log = run_simulation(env, craft, ctrl, cfg)
    assert log["t"][0] == 0.0
    assert log["t"][-1] == cfg["integrator"]["t_final"]
    assert len(log["t"]) > 1
    assert np.all(np.isfinite(log["r"]))
