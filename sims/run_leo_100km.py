"""Run baseline 100 km LEO simulation."""

from __future__ import annotations

import argparse
import csv
import os
import shutil

import numpy as np
import yaml

from tskb import (
    Environment,
    SimulationError,
    diagnostics,
    make_controller,
    make_craft,
    plotting,
    run_simulation,
)


def main(cfg_path: str, animate: bool = False, t_final: float | None = None) -> dict:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if t_final is not None:
        cfg.setdefault("integrator", {})["t_final"] = t_final
    env = Environment(include_moon=cfg.get("include_moon", True))
    craft = make_craft(cfg["craft"])
    ctrl = make_controller(cfg["controller"])
    shutil.rmtree("outputs", ignore_errors=True)
    os.makedirs("outputs", exist_ok=True)
    out_csv = os.path.join("outputs", "leo_100km.csv")
    out_deriv = os.path.join("outputs", "leo_100km_derived.csv")
    out_sma = os.path.join("outputs", "semi_major_axis.png")
    out_len = os.path.join("outputs", "tether_length.png")
    out_omega = os.path.join("outputs", "angular_velocity.png")
    out_ecc = os.path.join("outputs", "eccentricity.png")
    out_gif = os.path.join("outputs", "orbit.gif")
    err = None
    try:
        log = run_simulation(env, craft, ctrl, cfg)
    except SimulationError as e:
        log = e.log
        err = e
    log_ds = plotting.downsample_log(log, 120.0)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["t", "x", "y", "z", "vx", "vy", "vz", "power_control"])
        for t, r, v, p in zip(
            log_ds["t"], log_ds["r"], log_ds["v"], log_ds["power_control"]
        ):
            writer.writerow([t, *r, *v, p])
    # Derived quantities at matching time steps
    alt = (np.linalg.norm(log_ds["r"], axis=1) - env.r_earth).tolist()
    ecc = diagnostics._eccentricity_from_rv(log_ds["r"], log_ds["v"]).tolist()
    sma = diagnostics._semimajor_axis_from_rv(log_ds["r"], log_ds["v"]).tolist()
    with open(out_deriv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "t",
                "altitude",
                "omega",
                "theta",
                "length",
                "accel",
                "eccentricity",
                "semimajor_axis",
            ]
        )
        for row in zip(
            log_ds["t"],
            alt,
            log_ds["omega"],
            log_ds["theta"],
            log_ds["length"],
            log_ds["accel"],
            ecc,
            sma,
        ):
            writer.writerow(row)
    plotting.quicklook(log_ds, out_sma)
    plotting.plot_timeseries(
        log_ds["t"], log_ds["length"], "Tether length [m]", out_len
    )
    plotting.plot_timeseries(
        log_ds["t"], log_ds["omega"], "Angular velocity [rad/s]", out_omega
    )
    plotting.plot_timeseries(log_ds["t"], ecc, "Eccentricity", out_ecc)
    html_dir = os.path.join("outputs", "html")
    os.makedirs(html_dir, exist_ok=True)
    html_path = os.path.join(html_dir, "run_summary.html")
    duration = float(log_ds["t"][-1]) if log_ds["t"].size else 0.0
    outcome = "Simulation completed successfully." if err is None else str(err)
    html_template = (
        "<h1>Simulation Report</h1>\n"
        f"<p>Duration: {duration:.1f} s</p>\n"
        f"<p>Outcome: {outcome}</p>\n"
        "<h2>Plots</h2>\n"
        '<img src="../semi_major_axis.png" alt="Semimajor axis"/><br/><br/>\n'
        '<img src="../tether_length.png" alt="Tether length"/><br/><br/>\n'
        '<img src="../angular_velocity.png" alt="Angular velocity"/><br/><br/>\n'
        '<img src="../eccentricity.png" alt="Eccentricity"/>\n'
    )
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    if animate:
        plotting.animate(log_ds, out_gif)
    if err is not None:
        raise err
    return log_ds


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--animate", action="store_true", help="write orbit animation")
    parser.add_argument(
        "--t-final",
        type=float,
        help="override simulation duration in seconds",
    )
    args = parser.parse_args()
    main(args.config, animate=args.animate, t_final=args.t_final)
