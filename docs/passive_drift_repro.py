#!/usr/bin/env python3
"""Reproduce passive controller drift after one month.

Runs month-long passive simulations for prograde and retrograde initial
spin states and reports the barbell angle relative to the Moon when the
craft passes beneath the Moon near the end of the run.

Usage
-----
PYTHONPATH=src python docs/passive_drift_repro.py
"""

from __future__ import annotations

import yaml
import numpy as np

from tskb import Environment, DualBarbell, make_controller, run_simulation

CFG_PATH = "configs/leo_100km.yaml"


def simulate(omega_mode: str) -> tuple[float, float]:
    """Run one simulation and return crossing time and barbell angle.

    Parameters
    ----------
    omega_mode: str
        One of ``"prograde"`` or ``"retrograde"``.

    Returns
    -------
    t_cross: float
        Simulation time (s) when the craft is under the Moon.
    angle_deg: float
        Barbell angle relative to the lunar vertical (deg) at that time.
    """

    with open(CFG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg["controller"]["type"] = "passive"
    cfg["omega0"] = omega_mode

    env = Environment()
    craft = DualBarbell(cfg["mass"])
    ctrl = make_controller(cfg["controller"])
    log = run_simulation(env, craft, ctrl, cfg)

    t = np.asarray(log["t"])
    r = np.asarray(log["r"])
    theta = np.asarray(log["theta"])

    moon_angle = env.n_moon * t
    craft_angle = np.arctan2(r[:, 1], r[:, 0])
    diff = (craft_angle - moon_angle + np.pi) % (2 * np.pi) - np.pi

    r0_mag = env.r_earth + cfg["altitude_m"]
    n0 = np.sqrt(env.mu_earth / r0_mag**3)
    period = 2 * np.pi / n0
    mask = t > t[-1] - period
    idx = np.argmin(np.abs(diff[mask]))
    i = np.nonzero(mask)[0][idx]

    angle_rel = (theta[i] - moon_angle[i] + np.pi) % (2 * np.pi) - np.pi
    return t[i], np.degrees(angle_rel)


def main() -> None:
    for mode in ("prograde", "retrograde"):
        t_cross, angle_deg = simulate(mode)
        print(f"{mode:9s}: t={t_cross:9.0f} s  barbell angle={angle_deg:+5.1f} deg")


if __name__ == "__main__":
    main()
