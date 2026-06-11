from __future__ import annotations

import os

import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import matplotlib.ticker as ticker
import numpy as np


def earth_centered_xy(states: np.ndarray, scenario) -> tuple[np.ndarray, np.ndarray]:
    x = states[:, 0] - scenario.earth_pos[0]
    y = states[:, 1]
    return x, y


def render_reachability_map(scenario, trajectories, output_path: str, view: str) -> None:
    if view == "global":
        fig = plt.figure(figsize=(8.0, 8.0), dpi=180)
    elif view == "zoom":
        fig = plt.figure(figsize=(6.8, 6.8), dpi=180)
    else:
        raise ValueError(f"unknown view: {view}")

    fig.patch.set_facecolor("#0b1020")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#0b1020")
    ax.grid(color="#25314d", linestyle=":", linewidth=0.6, alpha=0.6)
    ax.tick_params(colors="#c7d0dd", labelsize=8)
    ax.set_aspect("equal")

    if view == "global":
        fig.suptitle(f"{scenario.title} - co-rotating frame", color="#f4f7fb", fontsize=15, y=0.97)
        moon_orbit = Circle((0.0, 0.0), scenario.distance, fill=False, ec="#5f6b83", lw=1.2, ls="--", alpha=0.7)
        ax.add_patch(moon_orbit)
        ax.scatter([0.0], [0.0], s=140, color="#4db6ac", edgecolors="#1f6f6a", linewidths=1.1, zorder=4)
        ax.scatter([scenario.distance], [0.0], s=80, color="#c8d1e0", edgecolors="#8c95a6", linewidths=1.1, zorder=4)
        ax.plot([scenario.earth_centered_l1_x], [0.0], marker="*", markersize=11, color="#f97316", zorder=5)
        ax.text(0.0, -22_000.0, "Earth", color="#4db6ac", fontsize=8, ha="center")
        ax.text(scenario.distance + 12_000.0, 16_000.0, "Moon", color="#c8d1e0", fontsize=8, ha="left")
        ax.text(scenario.earth_centered_l1_x + 7_000, 14_000, "L1", color="#f97316", fontsize=8, weight="bold")
    else:
        fig.suptitle(f"{scenario.title} - L1 neighborhood", color="#f4f7fb", fontsize=15, y=0.97)
        ax.scatter([0.0], [0.0], s=900, color="#4db6ac", edgecolors="#1f6f6a", linewidths=1.1, zorder=4)
        ax.plot([0.0], [0.0], marker="*", markersize=10, color="#f97316", zorder=5)
        ax.text(0.0, 14_000, "L1", color="#f97316", fontsize=8, weight="bold", ha="center")

    colors = plt.cm.twilight(np.linspace(0.0, 1.0, len(scenario.launch_angles_rad), endpoint=False))
    linestyles = {"small": "-", "large": "--"}
    line_widths = {"small": 1.3, "large": 1.05}
    for speed_label, _speed, angle_idx, _angle in trajectories["launch_cases"]:
        states = trajectories["states"][(speed_label, angle_idx)]
        x_ec, y_ec = earth_centered_xy(states, scenario)
        if view == "global":
            x_plot, y_plot = x_ec, y_ec
        else:
            x_plot, y_plot = x_ec - scenario.earth_centered_l1_x, y_ec
        color = colors[angle_idx]
        markevery = list(range(0, len(states), scenario.samples_per_day))
        label = None
        if angle_idx == 0:
            label = f"{speed_label} Δv"
        ax.plot(
            x_plot,
            y_plot,
            color=color,
            lw=line_widths[speed_label],
            ls=linestyles[speed_label],
            alpha=0.78,
            marker="o",
            markersize=2.3,
            markerfacecolor=color,
            markeredgecolor=color,
            markevery=markevery,
            label=label,
        )

    if view == "global":
        global_limit = scenario.distance * 1.12
        ax.set_xlim(-global_limit, global_limit)
        ax.set_ylim(-global_limit, global_limit)
        ax.set_xlabel("Earth-centered x (km)", color="#c7d0dd")
        ax.set_ylabel("Earth-centered y (km)", color="#c7d0dd")
        ax.set_title("Co-rotating Earth-Moon frame", color="#d7e1ea", fontsize=10, pad=8)
        legend = ax.legend(
            loc="lower left",
            fontsize=8,
            frameon=True,
            facecolor="#08101d",
            edgecolor="#4db6ac",
            framealpha=0.85,
        )
        for text in legend.get_texts():
            text.set_color("#d7e1ea")
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val/1000.0:.0f}"))
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val/1000.0:.0f}"))
    else:
        x_zoom_lim = 90_000.0
        y_zoom_lim = 90_000.0
        ax.set_xlim(-x_zoom_lim, x_zoom_lim)
        ax.set_ylim(-y_zoom_lim, y_zoom_lim)
        ax.set_xlabel("L1-centered x (km)", color="#c7d0dd")
        ax.set_ylabel("L1-centered y (km)", color="#c7d0dd")
        ax.set_title("L1 neighborhood", color="#d7e1ea", fontsize=10, pad=8)
        ax.text(
            0.03,
            0.03,
            "dots mark each day\nsmall = 0.05 m/s\nlarge = 50 m/s",
            transform=ax.transAxes,
            color="#d7e1ea",
            fontsize=8,
            family="monospace",
            bbox=dict(facecolor="#08101d", edgecolor="#4db6ac", alpha=0.85, boxstyle="round,pad=0.35"),
        )
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val/1000.0:.0f}"))
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val/1000.0:.0f}"))
        legend = ax.legend(
            loc="upper right",
            fontsize=8,
            frameon=True,
            facecolor="#08101d",
            edgecolor="#4db6ac",
            framealpha=0.85,
        )
        for text in legend.get_texts():
            text.set_color("#d7e1ea")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
