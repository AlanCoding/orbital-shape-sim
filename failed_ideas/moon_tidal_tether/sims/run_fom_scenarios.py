"""Run scenarios and compute semimajor-axis growth figure of merit."""

from __future__ import annotations

import argparse
import copy
import itertools

import numpy as np
import yaml

from tskb import Environment, diagnostics, make_controller, make_craft, run_simulation


MONTH = 30 * 24 * 3600.0
ORBIT_BUFFER = 6000.0


def run_case(base_cfg: dict, omega0, ctrl_type: str, theta0: float) -> float:
    """Run a single scenario and return the semimajor-axis FOM."""

    cfg = copy.deepcopy(base_cfg)
    init = cfg.setdefault("controller", {}).setdefault("initial", {})
    init["omega0"] = omega0
    init["theta0"] = theta0
    cfg["controller"]["type"] = ctrl_type
    cfg["integrator"]["t_final"] = MONTH + ORBIT_BUFFER

    env = Environment(include_moon=cfg.get("include_moon", True))
    craft = make_craft(cfg["craft"])
    ctrl = make_controller(cfg["controller"])
    log = run_simulation(env, craft, ctrl, cfg)
    return diagnostics.semimajor_axis_fom(log)


def parse_overrides(values: list[str]) -> dict[str, list[object]]:
    """Parse override strings into a mapping of key paths to values."""

    overrides: dict[str, list[object]] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid override '{item}', expected key=value")
        key, raw_vals = item.split("=", 1)
        overrides[key] = [yaml.safe_load(v) for v in raw_vals.split(",") if v]
    return overrides


def set_nested(cfg: dict, keys: list[str], value: object) -> None:
    """Set ``value`` in ``cfg`` following ``keys`` path."""

    node = cfg
    for key in keys[:-1]:
        node = node.setdefault(key, {})
    node[keys[-1]] = value


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--controller",
        type=str,
        default=None,
        help=(
            "Comma-separated list of controller types to run. "
            "Defaults to bang_bang,passive."
        ),
    )
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        help=(
            "Override config option as key=value1,value2. "
            "Use dot notation for nested keys. Can be supplied multiple times."
        ),
    )
    parser.add_argument(
        "--omega0",
        type=str,
        default=None,
        help=(
            "Run only a single initial spin mode or numeric value. "
            "Examples: prograde, fast_prograde, 0.01"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    with open("configs/leo_100km.yaml", "r", encoding="utf-8") as f:
        base_cfg = yaml.safe_load(f)

    env = Environment()
    alt = base_cfg["controller"]["initial"]["altitude_m"]
    r0 = 6378e3 + alt
    n0 = np.sqrt(env.mu_earth / r0**3)

    if args.omega0 is not None:
        spin_modes = [("custom", yaml.safe_load(args.omega0))]
    else:
        spin_modes = [
            ("tidally_locked", "tidally_locked"),
            ("no_rotation", "no_rotation"),
            ("prograde", "prograde"),
            ("retrograde", "retrograde"),
            ("fast_prograde", "fast_prograde"),
            ("1.5n0", 1.5 * n0),
        ]
    overrides = parse_overrides(args.override)
    if args.controller:
        overrides["controller.type"] = [
            c.strip() for c in args.controller.split(",") if c.strip()
        ]
    else:
        overrides["controller.type"] = ["bang_bang", "passive"]

    keys = list(overrides)
    value_lists = [overrides[k] for k in keys]

    print(f"{'theta0(rad)':<12}{'omega0':<15}{'controller':<12}{'FOM (m)':>10}")
    for combo in itertools.product(*value_lists):
        cfg = copy.deepcopy(base_cfg)
        current = dict(zip(keys, combo))
        for path, val in current.items():
            set_nested(cfg, path.split("."), val)

        ctrl_type = current["controller.type"]
        theta0_values = cfg["controller"]["initial"].get("theta0", 0.0)
        if not isinstance(theta0_values, (list, tuple, np.ndarray)):
            theta0_values = [theta0_values]

        for theta0 in theta0_values:
            for label, omega in spin_modes:
                try:
                    fom = run_case(cfg, omega, ctrl_type, theta0)
                except Exception as exc:  # pragma: no cover - robustness for sweeps
                    print(
                        f"{theta0:<12.3f}{label:<15}{ctrl_type:<12}ERROR: {exc}"
                    )
                    continue
                print(f"{theta0:<12.3f}{label:<15}{ctrl_type:<12}{fom:>10.3f}")


if __name__ == "__main__":  # pragma: no cover - manual invocation script
    main()

