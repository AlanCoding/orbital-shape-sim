"""Run baseline 100 km LEO simulation."""

from __future__ import annotations

import argparse
import csv
import os

import yaml

from tskb import BangBangController, DualBarbell, Environment, plotting, run_simulation


def main(cfg_path: str) -> dict:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    env = Environment()
    craft = DualBarbell(cfg["mass"])
    ctrl = BangBangController(cfg["controller"])
    log = run_simulation(env, craft, ctrl, cfg)
    os.makedirs("outputs", exist_ok=True)
    out_csv = os.path.join("outputs", "leo_100km.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["t", "x", "y", "z", "vx", "vy", "vz", "power_tide"])
        for t, r, v, p in zip(log["t"], log["r"], log["v"], log["power_tide"]):
            writer.writerow([t, *r, *v, p])
    plotting.quicklook(log, os.path.join("outputs", "leo_100km.png"))
    return log


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    main(args.config)
