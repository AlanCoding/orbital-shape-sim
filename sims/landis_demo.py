"""Reproduce the Landis orbit-raising maneuver in a moonless environment."""

from __future__ import annotations

import os

from tskb import DualBarbell, Environment, make_controller, plotting, run_simulation


def main(t_final: float = 86400.0) -> None:
    """Run the Landis controller demo.

    Parameters
    ----------
    t_final : float, optional
        Duration of the simulation in seconds.  The default of 86400 seconds
        corresponds to roughly one day in low Earth orbit.
    """

    cfg = {
        "mass": 1000.0,
        "altitude_m": 200000.0,
        "length0": 1000.0,
        "omega0": "tidally_locked",
        "include_moon": False,
        "controller": {
            "type": "landis",
            "extend_accel": 0.01,
            "retract_accel": 0.01,
        },
        "integrator": {
            "t_final": t_final,
            "dt_output": 10.0,
        },
    }

    env = Environment(include_moon=cfg["include_moon"])
    craft = DualBarbell(cfg["mass"])
    ctrl = make_controller(cfg["controller"])
    log = run_simulation(env, craft, ctrl, cfg)

    os.makedirs("docs", exist_ok=True)
    plotting.quicklook(log, os.path.join("docs", "landis_demo.png"))


if __name__ == "__main__":
    main()
