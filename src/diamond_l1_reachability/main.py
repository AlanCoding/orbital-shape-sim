from __future__ import annotations

import os
import time

import numpy as np
from scipy.integrate import solve_ivp

from .mass_driver import (
    analyze_bounded_grazing_releases,
    analyze_grazing_releases,
    analyze_release_scan,
    render_grazing_moon_frame,
    render_grazing_scan,
    render_grazing_scan_with_limits,
    render_release_scan_only,
)
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

    print("Running lunar surface grazing analysis...", flush=True)
    start = time.time()
    grazing = analyze_grazing_releases(scenario)
    print(f"  Analysis finished in {time.time() - start:.2f} s", flush=True)

    print("Running low-speed lunar grazing analysis...", flush=True)
    start = time.time()
    grazing_low = analyze_grazing_releases(scenario, speed_mps=0.05)
    print(f"  Analysis finished in {time.time() - start:.2f} s", flush=True)

    print("Running 102 m/s release scan...", flush=True)
    start = time.time()
    release_102 = analyze_release_scan(scenario, speed_mps=102.0, dense_band_deg=(50.0, 120.0), dense_factor=4)
    print(f"  Analysis finished in {time.time() - start:.2f} s", flush=True)

    print("Running bounded 102 m/s grazing search...", flush=True)
    start = time.time()
    grazing_102_window = analyze_bounded_grazing_releases(scenario, speed_mps=102.0, angle_min_deg=70.0, angle_max_deg=100.0)
    print(f"  Analysis finished in {time.time() - start:.2f} s", flush=True)

    print("Running bounded 120 m/s grazing search...", flush=True)
    start = time.time()
    grazing_120_window = analyze_bounded_grazing_releases(scenario, speed_mps=120.0, angle_min_deg=50.0, angle_max_deg=100.0)
    print(f"  Analysis finished in {time.time() - start:.2f} s", flush=True)

    print("Running capped 130 m/s release scan...", flush=True)
    start = time.time()
    release_130 = analyze_release_scan(scenario, speed_mps=130.0, max_days=8.4)
    print(f"  Analysis finished in {time.time() - start:.2f} s", flush=True)

    print("Running bounded 130 m/s grazing search...", flush=True)
    start = time.time()
    grazing_130_window = analyze_bounded_grazing_releases(
        scenario,
        speed_mps=130.0,
        angle_min_deg=50.0,
        angle_max_deg=100.0,
        max_days=8.4,
    )
    print(f"  Analysis finished in {time.time() - start:.2f} s", flush=True)

    for output_name, renderer, analysis in (
        ("08_lunar_grazing_scan.png", render_grazing_scan, grazing),
        (
            "09_lunar_grazing_low_speed_scan.png",
            lambda scenario, analysis, output_path: render_grazing_scan_with_limits(
                scenario,
                analysis,
                output_path,
                y_limit_km=7_000.0,
                title="Low-speed lunar scan (0.05 m/s release)",
            ),
            grazing_low,
        ),
        ("10_lunar_grazing_moon_frame.png", render_grazing_moon_frame, grazing),
        (
            "11_lunar_grazing_102ms_scan.png",
            lambda scenario, analysis, output_path: render_release_scan_only(
                scenario,
                analysis,
                output_path,
                y_limit_km=2.0 * (float(scenario.moon_radius_m) / 1000.0),
                title="Lunar surface scan (102 m/s release)",
            ),
            release_102,
        ),
        (
            "12_lunar_grazing_102ms_window_scan.png",
            lambda scenario, analysis, output_path: render_grazing_scan_with_limits(
                scenario,
                analysis,
                output_path,
                y_limit_km=2.0 * (float(scenario.moon_radius_m) / 1000.0),
                x_limits_deg=(70.0, 100.0),
                title="Bounded lunar grazing scan (102 m/s, 70°-100°)",
            ),
            grazing_102_window,
        ),
        (
            "13_lunar_grazing_102ms_window_moon_frame.png",
            render_grazing_moon_frame,
            grazing_102_window,
        ),
        (
            "14_lunar_grazing_120ms_window_scan.png",
            lambda scenario, analysis, output_path: render_grazing_scan_with_limits(
                scenario,
                analysis,
                output_path,
                y_limit_km=2.0 * (float(scenario.moon_radius_m) / 1000.0),
                x_limits_deg=(50.0, 100.0),
                title="Bounded lunar grazing scan (120 m/s, 50°-100°)",
            ),
            grazing_120_window,
        ),
        (
            "15_lunar_grazing_120ms_window_moon_frame.png",
            render_grazing_moon_frame,
            grazing_120_window,
        ),
        (
            "16_lunar_grazing_130ms_capped_scan.png",
            lambda scenario, analysis, output_path: render_release_scan_only(
                scenario,
                analysis,
                output_path,
                y_limit_km=2.0 * (float(scenario.moon_radius_m) / 1000.0),
                title="Capped lunar surface scan (130 m/s release, 8.4 days)",
            ),
            release_130,
        ),
        (
            "17_lunar_grazing_130ms_window_scan.png",
            lambda scenario, analysis, output_path: render_grazing_scan_with_limits(
                scenario,
                analysis,
                output_path,
                y_limit_km=2.0 * (float(scenario.moon_radius_m) / 1000.0),
                x_limits_deg=(50.0, 100.0),
                title="Bounded lunar grazing scan (130 m/s, 50°-100°)",
            ),
            grazing_130_window,
        ),
        (
            "18_lunar_grazing_130ms_window_moon_frame.png",
            render_grazing_moon_frame,
            grazing_130_window,
        ),
    ):
        output_path = os.path.join(output_dir, output_name)
        start = time.time()
        renderer(scenario, analysis, output_path)
        print(f"Wrote {output_path} in {time.time() - start:.2f} s", flush=True)


if __name__ == "__main__":
    main()
