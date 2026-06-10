from __future__ import annotations

import os

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.patches import Rectangle
from scipy.interpolate import interp1d

import numpy as np

from .geometry import solve_geometry
from .physics import diagnostics


def render_gif(scenario, t_eval, states, output_path, fps, duration) -> None:
    num_frames = int(fps * duration)
    t_render = np.linspace(float(t_eval[0]), float(t_eval[-1]), num_frames)
    states_interp = interp1d(t_eval, states, axis=0, kind="cubic")
    states_render = states_interp(t_render)

    body_points_all = []
    world_points_all = []
    diagnostics_all = []
    for t, state in zip(t_render, states_render):
        body_points = solve_geometry(float(state[4]), scenario)
        world_points = state[0:2] + body_points
        body_points_all.append(body_points)
        world_points_all.append(world_points)
        diagnostics_all.append(diagnostics(t, state, scenario, body_points=body_points))

    body_points_all = np.asarray(body_points_all)
    world_points_all = np.asarray(world_points_all)

    fig = plt.figure(figsize=(8.0, 7.0), dpi=90)
    fig.patch.set_facecolor("#0b1020")
    gs = fig.add_gridspec(2, 1, height_ratios=[4.5, 1.1], hspace=0.15)
    ax = fig.add_subplot(gs[0])
    ax_over = fig.add_subplot(gs[1])

    for axis in (ax, ax_over):
        axis.set_facecolor("#0b1020")
        axis.tick_params(colors="#c7d0dd", labelsize=8)

    ax.set_title(scenario.title, color="#f4f7fb", fontsize=12, pad=10)
    ax.set_xlim(-scenario.plot_half_width_m, scenario.plot_half_width_m)
    ax.set_ylim(-scenario.plot_half_width_m, scenario.plot_half_width_m)
    ax.set_aspect("equal")
    ax.grid(color="#25314d", linestyle=":", linewidth=0.6, alpha=0.6)
    ax.set_xlabel("L1-centered x (km)", color="#c7d0dd")
    ax.set_ylabel("L1-centered y (km)", color="#c7d0dd")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val/1000.0:.0f}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val/1000.0:.0f}"))

    ax_over.set_xlim(scenario.earth_pos[0] - 0.05 * scenario.moon_pos[0], scenario.moon_pos[0] + 0.05 * scenario.moon_pos[0])
    ax_over.set_ylim(-1.0, 1.0)
    ax_over.set_yticks([])
    ax_over.set_xlabel("Earth-Moon line (km)", color="#c7d0dd")
    ax_over.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val/1000.0:.0f}"))
    ax_over.spines["left"].set_visible(False)
    ax_over.spines["right"].set_visible(False)
    ax_over.spines["top"].set_visible(False)
    ax_over.grid(False)

    cm_trail, = ax.plot([], [], color="#67e8f9", linewidth=1.3, alpha=0.85)
    diamond_line, = ax.plot([], [], color="#f8fafc", linewidth=1.8)
    center_dot = ax.scatter([], [], s=26, color="#f8fafc", zorder=4)
    axis_line, = ax.plot([], [], color="#f97316", linewidth=1.0, alpha=0.9)
    hud = ax.text(
        0.03,
        0.03,
        "",
        transform=ax.transAxes,
        color="#d7e1ea",
        fontsize=8,
        family="monospace",
        bbox=dict(facecolor="#08101d", edgecolor="#4db6ac", alpha=0.85, boxstyle="round,pad=0.35"),
    )

    earth_dot, = ax_over.plot([], [], "o", color="#4db6ac", markersize=8)
    moon_dot, = ax_over.plot([], [], "o", color="#c8d1e0", markersize=6)
    l1_dot, = ax_over.plot([], [], "o", color="#f97316", markersize=6)
    window_box = Rectangle((0.0, -0.35), 0.0, 0.7, fill=False, ec="#67e8f9", lw=1.2)
    ax_over.add_patch(window_box)
    craft_dot_over, = ax_over.plot([], [], "o", color="#f8fafc", markersize=4)

    def init():
        cm_trail.set_data([], [])
        diamond_line.set_data([], [])
        center_dot.set_offsets(np.empty((0, 2)))
        axis_line.set_data([], [])
        hud.set_text("")
        earth_dot.set_data([], [])
        moon_dot.set_data([], [])
        l1_dot.set_data([], [])
        craft_dot_over.set_data([], [])
        return [
            cm_trail,
            diamond_line,
            center_dot,
            axis_line,
            hud,
            earth_dot,
            moon_dot,
            l1_dot,
            craft_dot_over,
            window_box,
        ]

    def update(frame):
        state = states_render[frame]
        points = world_points_all[frame]
        diag = diagnostics_all[frame]
        center = state[0:2]
        center_rel = np.array([center[0] - scenario.l1_x, center[1]], dtype=float)

        cm_trail.set_data(states_render[: frame + 1, 0] - scenario.l1_x, states_render[: frame + 1, 1])
        closed = np.vstack([points - np.array([scenario.l1_x, 0.0]), (points[0] - np.array([scenario.l1_x, 0.0]))])
        diamond_line.set_data(closed[:, 0], closed[:, 1])
        center_dot.set_offsets(np.array([center_rel]))

        axis_line.set_data(
            [center_rel[0] - scenario.half_span_m, center_rel[0] + scenario.half_span_m],
            [center_rel[1], center_rel[1]],
        )

        hud_lines = [
            f"t = {t_render[frame] / 86400.0:7.2f} days",
            f"x_rel = {diag['x_rel']/1000.0:7.1f} km",
            f"y_rel = {diag['y_rel']/1000.0:7.1f} km",
            f"vx = {diag['vx']:7.3f} m/s",
            f"rho_act = {diag['rho_act']: .3f}",
            f"rho_cmd = {diag['rho_cmd']: .3f}",
        ]
        hud.set_text("\n".join(hud_lines))

        earth_dot.set_data([scenario.earth_pos[0]], [0.0])
        moon_dot.set_data([scenario.moon_pos[0]], [0.0])
        l1_dot.set_data([scenario.l1_x], [0.0])
        craft_dot_over.set_data([center[0]], [0.0])
        window_box.set_x(center[0] - scenario.plot_half_width_m)
        window_box.set_width(2.0 * scenario.plot_half_width_m)
        return [
            cm_trail,
            diamond_line,
            center_dot,
            axis_line,
            hud,
            earth_dot,
            moon_dot,
            l1_dot,
            craft_dot_over,
            window_box,
        ]

    ani = animation.FuncAnimation(fig, update, init_func=init, frames=num_frames, blit=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ani.save(output_path, writer="pillow", fps=fps)
    plt.close(fig)
