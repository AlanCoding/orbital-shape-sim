"""Random-search training for the neural-network controller."""

from __future__ import annotations

import argparse
import numpy as np
import yaml

from tskb import Environment, diagnostics, make_craft
from tskb.controller import NeuralNetController
from tskb.integrate import run_simulation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=str,
        default="configs/leo_100km.yaml",
        help="Base simulation config YAML",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=20,
        help="Number of random-search iterations",
    )
    parser.add_argument(
        "--noise",
        type=float,
        default=0.1,
        help="Standard deviation of parameter noise",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="nn_controller_weights.npy",
        help="File to save best parameters",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Total simulation time in seconds (default: two orbits)",
    )
    parser.add_argument(
        "--fom-time",
        type=float,
        default=None,
        help="Time offset for FOM evaluation in seconds",
    )
    return parser.parse_args()


def evaluate(env, craft, ctrl, cfg, fom_time, params) -> float:
    ctrl.set_parameters(params)
    log = run_simulation(env, craft, ctrl, cfg)
    return diagnostics.semimajor_axis_fom(log, month=fom_time)


def main() -> None:
    args = parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    env = Environment()
    craft = make_craft(cfg["craft"])

    alt = cfg["controller"]["initial"]["altitude_m"]
    r0_mag = env.r_earth + alt
    period = 2 * np.pi * np.sqrt(r0_mag**3 / env.mu_earth)

    duration = args.duration if args.duration is not None else 2 * period
    dt = cfg["integrator"]["dt_output"]
    cfg["integrator"]["t_final"] = float(np.ceil(duration / dt) * dt)

    fom_time = args.fom_time if args.fom_time is not None else min(period, duration / 2)

    ctrl_cfg = cfg.get("controller", {})
    ctrl_cfg["type"] = "neural_net"
    ctrl = NeuralNetController(ctrl_cfg)

    best_params = ctrl.get_parameters()
    best_score = evaluate(env, craft, ctrl, cfg, fom_time, best_params)
    noise = args.noise
    for i in range(args.iterations):
        cand = best_params + noise * np.random.randn(best_params.size)
        score = evaluate(env, craft, ctrl, cfg, fom_time, cand)
        if score > best_score:
            best_score = score
            best_params = cand
            noise *= 0.9
        else:
            noise *= 1.1
        print(f"iter {i}: FOM={score:.3f}, best={best_score:.3f}")

    np.save(args.output, best_params)
    print(f"Saved best parameters to {args.output}")


if __name__ == "__main__":  # pragma: no cover - manual script
    main()
