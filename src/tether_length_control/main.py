"""
Entry point for tether-length control GIF generation.
"""

from __future__ import annotations

import os
import time

import numpy as np
from scipy.integrate import solve_ivp

from .physics import tether_derivatives
from .render import render_gif
from .scenarios import get_scenarios


def _make_logged_derivative(scenario, log_every=5000):
    call_count = 0
    last_logged_t = None

    def derivative(t, y):
        nonlocal call_count, last_logged_t
        call_count += 1
        if call_count == 1 or call_count % log_every == 0:
            length = scenario.length_law(t, y, scenario)
            print(
                f"    [ode] calls={call_count:6d} t={t: .3e} "
                f"r={np.hypot(y[0], y[1]):.3e} phi={y[4]: .3e} H={y[5]: .3e} L={length:.3e}",
                flush=True,
            )
            last_logged_t = t
        return tether_derivatives(t, y, scenario)

    return derivative


def _integrate_piecewise(scenario, t_eval, derivative, *, log_every=5000):
    t_start = float(t_eval[0])
    t_final = float(t_eval[-1])
    y_start = np.array(scenario.state0, dtype=float)
    t_segments = []
    y_segments = []
    eps = max(1e-3, 1e-9 * t_final)
    segment_index = 0

    while t_start < t_final - 1e-12:
        segment_index += 1
        event = scenario.switch_function
        print(f"  Segment {segment_index} start t={t_start:.3e}", flush=True)

        event_wrapper = None
        if event is not None:
            def event_wrapper(t, y, _event=event):
                return _event(t, y, scenario)

            event_wrapper.terminal = True
            event_wrapper.direction = 0

        segment_mask = (t_eval >= t_start) & (t_eval <= t_final)
        if event is not None:
            # Let solve_ivp stop at the first surface crossing; the remaining
            # samples are handled in the next segment.
            pass

        sol = solve_ivp(
            fun=derivative,
            t_span=(t_start, t_final),
            y0=y_start,
            t_eval=t_eval[segment_mask],
            method="DOP853",
            rtol=1e-10,
            atol=1e-12,
            events=event_wrapper,
        )

        t_values = np.asarray(sol.t, dtype=float)
        y_values = np.asarray(sol.y, dtype=float)

        if len(t_values):
            if t_segments and np.isclose(t_values[0], t_segments[-1][-1]):
                t_segments.append(t_values[1:])
                y_segments.append(y_values[:, 1:])
            else:
                t_segments.append(t_values)
                y_segments.append(y_values)

        if sol.status == 1 and sol.t_events and len(sol.t_events[0]) > 0:
            t_hit = float(sol.t_events[0][0])
            y_hit = np.array(sol.y_events[0][0], dtype=float)
            dydt = np.array(derivative(t_hit, y_hit), dtype=float)
            print(f"    Event at t={t_hit:.3e}; restarting across length switch", flush=True)
            t_start = t_hit + eps
            if scenario.branch_nudge is not None:
                y_start = scenario.branch_nudge(y_hit, dydt, scenario)
            else:
                y_start = y_hit + dydt * eps
            continue

        break

    if t_segments:
        t_out = np.concatenate(t_segments)
        y_out = np.concatenate(y_segments, axis=1).T
    else:
        t_out = np.array([], dtype=float)
        y_out = np.empty((0, 6), dtype=float)
    return t_out, y_out


def run_simulation(scenario, *, log_every=5000):
    print(f"Running simulation for scenario: {scenario.id}...", flush=True)
    t_start = time.time()
    t_span = (0.0, scenario.t_max)
    if scenario.integration_dt is not None and scenario.integration_dt > 0.0:
        t_eval = np.arange(0.0, scenario.t_max + scenario.integration_dt * 0.5, scenario.integration_dt)
    else:
        t_eval = np.linspace(0.0, scenario.t_max, 1200)

    derivative = _make_logged_derivative(scenario, log_every=log_every)
    print(f"  Integrating {scenario.id} over {scenario.t_max:.3e} s...", flush=True)
    sol = solve_ivp(
        fun=derivative,
        t_span=t_span,
        y0=scenario.state0,
        t_eval=t_eval,
        method="DOP853",
        rtol=1e-10,
        atol=1e-12,
    )
    t_out, y_out = sol.t, sol.y.T
    sol_status = sol.status
    sol_message = sol.message

    t_end = time.time()
    print(
        f"  Simulation completed in {t_end - t_start:.2f} s. "
        f"Status: {sol_status} ({sol_message})",
        flush=True,
    )
    return t_out, y_out


def main():
    scenarios = get_scenarios()
    output_dir = os.path.join("outputs", "tether_length_control")
    os.makedirs(output_dir, exist_ok=True)

    scenario_filter = os.environ.get("TETHER_LENGTH_SCENARIOS")
    if scenario_filter:
        wanted = {item.strip() for item in scenario_filter.split(",") if item.strip()}
        scenarios = {k: v for k, v in scenarios.items() if k in wanted}
        print(f"Scenario filter active: {sorted(scenarios)}", flush=True)

    for scenario_id, scenario in scenarios.items():
        print(f"Starting scenario {scenario_id}", flush=True)
        t_eval, states = run_simulation(scenario)
        output_path = os.path.join(output_dir, f"{scenario_id}.gif")

        print(f"  Rendering {os.path.basename(output_path)}...", flush=True)
        t_start = time.time()
        render_gif(
            scenario=scenario,
            t_eval=t_eval,
            states=states,
            output_path=output_path,
            fps=80,
            duration=scenario.render_duration,
        )
        t_end = time.time()
        print(f"  Saved GIF to {output_path} in {t_end - t_start:.2f} s.", flush=True)
        print("-" * 50, flush=True)


if __name__ == "__main__":
    main()
