"""Run baseline 100 km LEO simulation."""

from __future__ import annotations

import argparse
import csv
import os

import yaml

from tskb import DualBarbell, Environment, make_controller, plotting, run_simulation


def main(cfg_path: str, animate: bool = False, t_final: float | None = None) -> dict:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if t_final is not None:
        cfg.setdefault("integrator", {})["t_final"] = t_final
    env = Environment(include_moon=cfg.get("include_moon", True))
    craft = DualBarbell(cfg["mass"])
    ctrl = make_controller(cfg["controller"])
    log = run_simulation(env, craft, ctrl, cfg)
    log_ds = plotting.downsample_log(log, 120.0)
    os.makedirs("outputs", exist_ok=True)
    out_csv = os.path.join("outputs", "leo_100km.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["t", "x", "y", "z", "vx", "vy", "vz", "power_control"])
        for t, r, v, p in zip(
            log_ds["t"], log_ds["r"], log_ds["v"], log_ds["power_control"]
        ):
            writer.writerow([t, *r, *v, p])
    plotting.quicklook(log_ds, os.path.join("outputs", "leo_100km.png"))
    if animate:
        plotting.animate(log_ds, os.path.join("outputs", "leo_100km.gif"))
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
