#!/usr/bin/env python3
"""Generate an animation of the passive diamond craft near Earth–Moon L1."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np

# Ensure ``tskb`` can be imported when running the script directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from tskb import Environment, make_controller, make_craft, run_simulation
from tskb.plotting import downsample_log


def _rotate_to_moon_frame(samples: np.ndarray, phases: np.ndarray) -> np.ndarray:
    """Rotate ``samples`` into the frame co-rotating with the Moon.

    Parameters
    ----------
    samples:
        Array of shape ``(N, ..., 3)`` containing inertial-frame vectors.
    phases:
        Array of shape ``(N,)`` with the lunar orbital phase at each sample.
    """

    samples = np.asarray(samples, dtype=float)
    phases = np.asarray(phases, dtype=float)
    if samples.shape[0] != phases.shape[0]:
        raise ValueError("samples and phases must share the leading dimension")

    reshape = (phases.size,) + (1,) * (samples.ndim - 2)
    cos_p = np.cos(phases).reshape(reshape)
    sin_p = np.sin(phases).reshape(reshape)

    x = samples[..., 0]
    y = samples[..., 1]
    x_rot = cos_p * x + sin_p * y
    y_rot = -sin_p * x + cos_p * y
    rot = np.stack((x_rot, y_rot, samples[..., 2]), axis=-1)
    return rot


def _approx_l2_distance(env: Environment) -> float:
    """Approximate the Earth–Moon L2 distance from Earth."""

    mu = env.mu_moon / (env.mu_earth + env.mu_moon)
    return env.r_moon * (1.0 + (mu / 3.0) ** (1.0 / 3.0))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/diamond_passive.gif"),
        help="Path for the generated animation.",
    )
    parser.add_argument(
        "--t-final-days",
        type=float,
        default=7.0,
        help="Simulation duration in days (default: 7).",
    )
    parser.add_argument(
        "--dt-output-hours",
        type=float,
        default=0.5,
        help="Integrator sampling interval in hours (default: 0.5).",
    )
    parser.add_argument(
        "--downsample-hours",
        type=float,
        default=1.0,
        help="Maximum time step between animation frames in hours (default: 1).",
    )
    parser.add_argument(
        "--circle-radius-km",
        type=float,
        default=5000.0,
        help="Radius in kilometres for the dotted circle highlighting L2 (default: 5000).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    env = Environment()
    cfg = {
        "craft": {"type": "diamond", "mass": 1000.0},
        "controller": {"type": "passive"},
        "integrator": {
            "t_final": float(args.t_final_days) * 86400.0,
            "dt_output": float(args.dt_output_hours) * 3600.0,
        },
    }

    craft = make_craft(cfg["craft"])
    ctrl = make_controller(cfg["controller"])
    log = run_simulation(env, craft, ctrl, cfg)
    log = downsample_log(log, max(1.0, float(args.downsample_hours)) * 3600.0)

    t = np.asarray(log["t"], dtype=float)
    r = np.asarray(log["r"], dtype=float)

    phases = env.n_moon * t
    r_rot = _rotate_to_moon_frame(r, phases)

    d = 0.5 * craft.diameter
    offsets = np.array(
        [
            [d, 0.0, 0.0],
            [-d, 0.0, 0.0],
            [0.0, d, 0.0],
            [0.0, -d, 0.0],
        ]
    )
    masses = r[:, None, :] + offsets[None, :, :]
    masses_rot = _rotate_to_moon_frame(masses, phases)
    masses_xy = masses_rot[..., :2]

    order = [2, 0, 3, 1, 2]
    diamond_path = masses_xy[:, order, :]

    l2_dist = _approx_l2_distance(env)
    circle_radius = float(args.circle_radius_km) * 1000.0

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_aspect("equal", "box")

    x_vals = np.concatenate(
        [
            masses_xy[..., 0].ravel(),
            r_rot[:, 0],
            np.array([l2_dist - circle_radius, l2_dist + circle_radius]),
        ]
    )
    y_vals = np.concatenate(
        [masses_xy[..., 1].ravel(), r_rot[:, 1], np.array([-circle_radius, circle_radius])]
    )
    xmin = float(np.min(x_vals))
    xmax = float(np.max(x_vals))
    ymin = float(np.min(y_vals))
    ymax = float(np.max(y_vals))
    span = max(xmax - xmin, ymax - ymin)
    pad = 0.1 * span
    half = 0.5 * span + pad
    x_mid = 0.5 * (xmax + xmin)
    y_mid = 0.5 * (ymax + ymin)
    ax.set_xlim(x_mid - half, x_mid + half)
    ax.set_ylim(y_mid - half, y_mid + half)

    ax.axhline(0.0, color="tab:gray", linestyle=":", linewidth=1.0, label="Earth–Moon line")

    moon = env.moon_position(0.0)
    moon_rot = _rotate_to_moon_frame(moon[None, :], np.array([0.0]))[0]
    ax.plot(moon_rot[0], moon_rot[1], marker="o", color="tab:blue", markersize=4, label="Moon")

    circle = plt.Circle(
        (l2_dist, 0.0),
        circle_radius,
        fill=False,
        linestyle=":",
        linewidth=1.0,
        color="tab:purple",
        label="L2 vicinity",
    )
    ax.add_patch(circle)
    ax.plot(l2_dist, 0.0, marker="x", color="tab:purple", markersize=6)

    mass_plots = [
        ax.plot([], [], "o", color="tab:red", markersize=4)[0]
        for _ in range(4)
    ]
    tether_line, = ax.plot([], [], color="tab:red", linewidth=1.0)
    com_trail, = ax.plot([], [], color="tab:orange", linewidth=1.0, alpha=0.6, label="Centre of mass")

    ax.set_xlabel("x in Moon-rotating frame [m]")
    ax.set_ylabel("y in Moon-rotating frame [m]")
    ax.legend(loc="upper left", frameon=False)

    def init():  # pragma: no cover - animation boilerplate
        for plot in mass_plots:
            plot.set_data([], [])
        tether_line.set_data([], [])
        com_trail.set_data([], [])
        return [*mass_plots, tether_line, com_trail]

    def update(frame: int):  # pragma: no cover - animation boilerplate
        xy = masses_xy[frame]
        for plot, pos in zip(mass_plots, xy):
            plot.set_data([pos[0]], [pos[1]])
        path = diamond_path[frame]
        tether_line.set_data(path[:, 0], path[:, 1])
        com_trail.set_data(r_rot[: frame + 1, 0], r_rot[: frame + 1, 1])
        return [*mass_plots, tether_line, com_trail]

    ani = FuncAnimation(
        fig,
        update,
        frames=t.size,
        init_func=init,
        blit=True,
        interval=100,
    )
    ani.save(output_path, writer=PillowWriter(fps=12))
    plt.close(fig)

    print(f"Animation written to {output_path.resolve()}")


if __name__ == "__main__":
    main()
