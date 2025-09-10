"""Run a simple point-mass orbit simulation."""
from __future__ import annotations

import argparse
import numpy as np
import yaml

from tskb import Environment, PointMass, make_controller, run_simulation


def main(cfg_path: str) -> dict:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    env = Environment(include_moon=cfg.get("include_moon", True))
    mass = cfg.get("craft", {}).get("mass", cfg.get("mass", 0.0))
    craft = PointMass(mass)
    ctrl = make_controller(cfg.get("controller", {"type": "passive"}))
    log = run_simulation(env, craft, ctrl, cfg)
    return log


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    main(args.config)
