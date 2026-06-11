from __future__ import annotations

import os
import time

import numpy as np
from scipy.integrate import solve_ivp

from .physics import derivatives
from .render import render_reachability_map
from .scenarios import get_launch_cases, get_scenario


def run_trajectory(scenario, speed_mps: float, angle_rad: float) -> np.ndarray:
    t_max = scenario.t_max_days * 86400.0
    num_samples = int(scenario.t_max_days * scenario.samples_per_day) + 1
    t_eval = np.linspace(0.0, t_max, num_samples)
    y0 = np.array(
        [
            scenario.l1_x,
            0.0,
            speed_mps * np.cos(angle_rad),
            speed_mps * np.sin(angle_rad),
        ],
        dtype=float,
    )
    sol = solve_ivp(
        fun=lambda t, y: derivatives(t, y, scenario),
        t_span=(0.0, t_max),
        y0=y0,
        t_eval=t_eval,
        method="DOP853",
        rtol=1e-10,
        atol=1e-12,
    )
    return sol.y.T


def main():
    scenario = get_scenario()
    launch_cases = get_launch_cases(scenario)
    trajectories = {"launch_cases": launch_cases, "states": {}}

    for speed_label, speed, angle_idx, angle in launch_cases:
        print(
            f"Running reachability case {speed_label} angle={np.degrees(angle):.0f} deg...",
            flush=True,
        )
        start = time.time()
        states = run_trajectory(scenario, speed, angle)
        trajectories["states"][(speed_label, angle_idx)] = states
        print(f"  Integration finished in {time.time() - start:.2f} s", flush=True)

    output_dir = os.path.join("docs", "assets", "diamond_l1_reachability")
    os.makedirs(output_dir, exist_ok=True)
    for view, output_name in (("global", "reachability_global.png"), ("zoom", "reachability_l1.png")):
        output_path = os.path.join(output_dir, output_name)
        start = time.time()
        render_reachability_map(scenario, trajectories, output_path, view=view)
        print(f"Wrote {output_path} in {time.time() - start:.2f} s", flush=True)


if __name__ == "__main__":
    main()
