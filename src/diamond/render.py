from __future__ import annotations

import os

import matplotlib.animation as animation
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from scipy.interpolate import interp1d

import numpy as np

from .geometry import body_to_inertial, solve_geometry
from .physics import diagnostics


def render_gif(scenario, t_eval, states, output_path, fps, duration) -> None:
    num_frames = int(fps * duration)
    t_render = np.linspace(float(t_eval[0]), float(t_eval[-1]), num_frames)
    interpolator = interp1d(t_eval, states, axis=0, kind="cubic")
    states_render = interpolator(t_render)

    body_points_all = []
    inertial_points_all = []
    diag_all = []
    for t, state in zip(t_render, states_render):
        alpha_cmd = scenario.alpha_law(t, state, scenario)
        body_points = solve_geometry(alpha_cmd, float(state[6]), scenario)
        inertial_points = body_to_inertial(body_points, float(state[4]), state[0:2])
        body_points_all.append(body_points)
        inertial_points_all.append(inertial_points)
        diag_all.append(diagnostics(t, state, scenario, body_points=body_points))

    body_points_all = np.asarray(body_points_all)
    inertial_points_all = np.asarray(inertial_points_all)

    fig, ax = plt.subplots(figsize=(6.5, 6.5), dpi=90)
    fig.patch.set_facecolor("#0b1020")
    ax.set_facecolor("#0b1020")
    ax.grid(color="#25314d", linestyle=":", linewidth=0.6, alpha=0.6)

    if scenario.mu > 0.0 and scenario.show_primary_body:
        body = Circle((0.0, 0.0), scenario.primary_radius, color="#1e2a44", ec="#4db6ac", lw=1.8, zorder=1)
        ax.add_patch(body)

    max_dist = 0.0
    for state, points in zip(states_render, inertial_points_all):
        max_dist = max(
            max_dist,
            float(np.linalg.norm(state[0:2])),
            float(np.max(np.linalg.norm(points, axis=1))),
        )
    if scenario.mu > 0.0 and scenario.show_primary_body:
        max_dist = max(max_dist, scenario.primary_radius)
    lim = max_dist * 1.2 if max_dist > 0.0 else scenario.R0 * 4.0
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_title(scenario.title, color="#f4f7fb", fontsize=12, pad=10)
    ax.set_xlabel("Inertial X (m)", color="#c7d0dd")
    ax.set_ylabel("Inertial Y (m)", color="#c7d0dd")
    ax.tick_params(colors="#c7d0dd", labelsize=8)

    cm_trail, = ax.plot([], [], color="#67e8f9", linewidth=1.1, alpha=0.8, zorder=2)
    polygon, = ax.plot([], [], color="#f8fafc", linewidth=1.6, zorder=4)
    action_axis, = ax.plot([], [], color="#f97316", linewidth=1.0, alpha=0.95, zorder=3)
    tidal_axis, = ax.plot([], [], color="#a78bfa", linewidth=1.0, alpha=0.9, zorder=3)
    mass_scatter = ax.scatter([], [], s=28, color="#f8fafc", zorder=5)
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

    def init():
        cm_trail.set_data([], [])
        polygon.set_data([], [])
        action_axis.set_data([], [])
        tidal_axis.set_data([], [])
        mass_scatter.set_offsets(np.empty((0, 2)))
        hud.set_text("")
        return [cm_trail, polygon, action_axis, tidal_axis, mass_scatter, hud]

    def update(frame):
        state = states_render[frame]
        points = inertial_points_all[frame]
        diag = diag_all[frame]
        center = state[0:2]
        cm_trail.set_data(states_render[: frame + 1, 0], states_render[: frame + 1, 1])

        closed = np.vstack([points, points[0]])
        polygon.set_data(closed[:, 0], closed[:, 1])
        mass_scatter.set_offsets(points)

        alpha_world = float(state[4] + diag["alpha_cmd"])
        n_hat = np.array([np.cos(alpha_world), np.sin(alpha_world)], dtype=float)
        t_hat = np.array([-np.sin(alpha_world), np.cos(alpha_world)], dtype=float)
        action_axis.set_data(
            [center[0] - scenario.R0 * n_hat[0], center[0] + scenario.R0 * n_hat[0]],
            [center[1] - scenario.R0 * n_hat[1], center[1] + scenario.R0 * n_hat[1]],
        )

        if scenario.mu > 0.0 and diag["r"] > 0.0:
            g_hat = -center / diag["r"]
            tidal_axis.set_data(
                [center[0] - scenario.R0 * g_hat[0], center[0] + scenario.R0 * g_hat[0]],
                [center[1] - scenario.R0 * g_hat[1], center[1] + scenario.R0 * g_hat[1]],
            )
        else:
            tidal_axis.set_data([], [])

        hud_lines = [
            f"t = {t_render[frame]:8.1f} s",
            f"phi = {np.degrees(state[4]):7.2f} deg",
            f"omega = {diag['omega']: .4e} rad/s",
            f"rho_cmd = {diag['rho_cmd']: .3f}",
            f"rho_act = {diag['rho_act']: .3f}",
        ]
        if np.isfinite(diag["rho_geom"]):
            hud_lines.append(f"rho_geom = {diag['rho_geom']: .3f}")
        hud.set_text("\n".join(hud_lines))
        return [cm_trail, polygon, action_axis, tidal_axis, mass_scatter, hud]

    ani = animation.FuncAnimation(fig, update, init_func=init, frames=num_frames, blit=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ani.save(output_path, writer="pillow", fps=fps)
    plt.close(fig)

