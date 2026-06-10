from __future__ import annotations

import os
import time

import numpy as np
from scipy.integrate import solve_ivp

from .physics import derivatives
from .render import render_gif
from .scenarios import get_scenarios


def run_simulation(scenario):
    t_eval = np.linspace(0.0, scenario.t_max, scenario.num_samples)
    sol = solve_ivp(
        fun=lambda t, y: derivatives(t, y, scenario),
        t_span=(0.0, scenario.t_max),
        y0=scenario.state0,
        t_eval=t_eval,
        method="DOP853",
        rtol=1e-10,
        atol=1e-12,
    )
    return sol.t, sol.y.T


def main():
    scenarios = get_scenarios()
    scenario_filter = os.environ.get("DIAMOND_SCENARIOS")
    if scenario_filter:
        wanted = {item.strip() for item in scenario_filter.split(",") if item.strip()}
        scenarios = {k: v for k, v in scenarios.items() if k in wanted}

    output_dir = os.path.join("docs", "assets", "diamond_planning")
    os.makedirs(output_dir, exist_ok=True)

    for scenario_id, scenario in scenarios.items():
        print(f"Running diamond scenario {scenario_id}...", flush=True)
        start = time.time()
        t_eval, states = run_simulation(scenario)
        sim_elapsed = time.time() - start
        print(f"  Integration finished in {sim_elapsed:.2f} s", flush=True)

        output_path = os.path.join(output_dir, f"{scenario_id}.gif")
        start = time.time()
        render_gif(
            scenario=scenario,
            t_eval=t_eval,
            states=states,
            output_path=output_path,
            fps=scenario.fps,
            duration=scenario.render_duration,
        )
        render_elapsed = time.time() - start
        print(f"  Wrote {output_path} in {render_elapsed:.2f} s", flush=True)
        print("-" * 60, flush=True)


if __name__ == "__main__":
    main()

