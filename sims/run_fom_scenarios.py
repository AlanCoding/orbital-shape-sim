"""Run scenarios and compute semimajor-axis growth figure of merit."""

from __future__ import annotations

import copy

import numpy as np
import yaml

from tskb import Environment, DualBarbell, make_controller, run_simulation
from tskb import diagnostics


MONTH = 30 * 24 * 3600.0
ORBIT_BUFFER = 6000.0


def run_case(base_cfg: dict, omega0, ctrl_type: str) -> float:
    """Run a single scenario and return the semimajor-axis FOM."""

    cfg = copy.deepcopy(base_cfg)
    cfg["omega0"] = omega0
    cfg["controller"]["type"] = ctrl_type
    cfg["integrator"]["t_final"] = MONTH + ORBIT_BUFFER

    env = Environment()
    craft = DualBarbell(cfg["mass"])
    ctrl = make_controller(cfg["controller"])
    log = run_simulation(env, craft, ctrl, cfg)
    return diagnostics.semimajor_axis_fom(log)


def main() -> None:
    with open("configs/leo_100km.yaml", "r", encoding="utf-8") as f:
        base_cfg = yaml.safe_load(f)

    env = Environment()
    r0 = 6378e3 + base_cfg["altitude_m"]
    n0 = np.sqrt(env.mu_earth / r0**3)

    spin_modes = [
        ("tidally_locked", "tidally_locked"),
        ("no_rotation", "no_rotation"),
        ("prograde", "prograde"),
        ("retrograde", "retrograde"),
        ("1.5n0", 1.5 * n0),
    ]
    ctrl_types = ["bang_bang", "passive"]

    print(f"{'omega0':<15}{'controller':<12}{'FOM (m)':>10}")
    for label, omega in spin_modes:
        for ctrl_type in ctrl_types:
            fom = run_case(base_cfg, omega, ctrl_type)
            print(f"{label:<15}{ctrl_type:<12}{fom:>10.3f}")


if __name__ == "__main__":  # pragma: no cover - manual invocation script
    main()

