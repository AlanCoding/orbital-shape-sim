"""
Rendering utilities for tether-length control GIFs.
"""

from __future__ import annotations

import os

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from matplotlib.patches import Circle
from scipy.interpolate import interp1d

from .physics import endpoint_positions, endpoint_velocities, get_diagnostics


def render_gif(scenario, t_eval, states, output_path, fps=20, duration=8.0):
    num_frames = int(fps * duration)
    t_render = np.linspace(t_eval[0], t_eval[-1], num_frames)
    interpolator = interp1d(t_eval, states, axis=0, kind="cubic")
    states_render = interpolator(t_render)

    r1_all = []
    r2_all = []
    v1_all = []
    v2_all = []
    R_all = []
    L_all = []
    omega_all = []
    H_all = []

    for idx, state in enumerate(states_render):
        t = t_render[idx]
        diag = get_diagnostics(t, state, scenario)
        length = diag["length"]
        omega = diag["omega"]
        H = diag["H"]
        r1, r2 = endpoint_positions(state, scenario.m1, scenario.m2, length)
        v1, v2 = endpoint_velocities(state, scenario.m1, scenario.m2, length, omega)
        r1_all.append(r1)
        r2_all.append(r2)
        v1_all.append(v1)
        v2_all.append(v2)
        R_all.append(state[0:2])
        L_all.append(length)
        omega_all.append(omega)
        H_all.append(H)

    r1_all = np.array(r1_all)
    r2_all = np.array(r2_all)
    v1_all = np.array(v1_all)
    v2_all = np.array(v2_all)
    R_all = np.array(R_all)
    L_all = np.array(L_all)
    omega_all = np.array(omega_all)
    H_all = np.array(H_all)

    earth_radius = 2.7075e6

    fig, ax = plt.subplots(figsize=(6, 6), dpi=80)
    fig.patch.set_facecolor("#0b0c10")
    ax.set_facecolor("#0b0c10")

    earth = Circle((0, 0), earth_radius, color="#1f2833", ec="#45a29e", lw=2.0, zorder=1)
    ax.add_patch(earth)
    ax.grid(color="#1f2833", linestyle=":", linewidth=0.5, alpha=0.7)

    max_dist = 0.0
    for i in range(len(states_render)):
        max_dist = max(max_dist, np.linalg.norm(r1_all[i]), np.linalg.norm(r2_all[i]), np.linalg.norm(R_all[i]))

    plot_limit = max(max_dist * 1.05, earth_radius * 1.1)
    ax.set_xlim(-plot_limit, plot_limit)
    ax.set_ylim(-plot_limit, plot_limit)
    ax.set_aspect("equal")

    ax.set_xlabel("Inertial X (10^3 km)", color="#c9d1d9", fontsize=9)
    ax.set_ylabel("Inertial Y (10^3 km)", color="#c9d1d9", fontsize=9)
    ax.tick_params(colors="#c9d1d9", labelsize=8)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val/1e6:.1f}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val/1e6:.1f}"))
    ax.set_title(scenario.title, color="#f0f6fc", fontsize=11, fontweight="bold", pad=10)

    cm_trail_line, = ax.plot([], [], color="#66fcf1", linestyle="-", linewidth=1.2, alpha=0.8, zorder=2)
    ep1_trail_line, = ax.plot([], [], color="#ff007f", linestyle=":", linewidth=0.8, alpha=0.4, zorder=2)
    ep2_trail_line, = ax.plot([], [], color="#00e676", linestyle=":", linewidth=0.8, alpha=0.4, zorder=2)
    barbell_line, = ax.plot([], [], color="#e5e5e5", linestyle="-", linewidth=1.5, zorder=3)

    max_m = max(scenario.m1, scenario.m2)
    s1 = 20 + 80 * (scenario.m1 / max_m)
    s2 = 20 + 80 * (scenario.m2 / max_m)
    ep1_dot = ax.scatter([], [], color="#ff007f", s=s1, zorder=4)
    ep2_dot = ax.scatter([], [], color="#00e676", s=s2, zorder=4)
    cm_dot = ax.scatter([], [], color="#66fcf1", s=15, marker="o", zorder=4)

    if scenario.show_velocity_arrows:
        q_x = [0.0, 0.0, 0.0]
        q_y = [0.0, 0.0, 0.0]
        q_u = [0.0, 0.0, 0.0]
        q_v = [0.0, 0.0, 0.0]
        quiver_obj = ax.quiver(
            q_x,
            q_y,
            q_u,
            q_v,
            color=["#ff007f", "#00e676", "#66fcf1"],
            angles="xy",
            scale_units="xy",
            scale=1.0 / 120.0,
            zorder=5,
            width=0.005,
            headwidth=4,
            headlength=5,
        )
    else:
        quiver_obj = None

    hud_text = ax.text(
        0.03,
        0.03,
        "",
        transform=ax.transAxes,
        color="#c9d1d9",
        fontsize=8,
        fontfamily="monospace",
        bbox=dict(facecolor="#0b0c10", edgecolor="#45a29e", alpha=0.8, boxstyle="round,pad=0.4"),
    )

    r0_ref = np.linalg.norm(states_render[0, 0:2])
    T_orbit_ref = 2.0 * np.pi * np.sqrt(r0_ref**3 / scenario.mu)

    def init():
        cm_trail_line.set_data([], [])
        ep1_trail_line.set_data([], [])
        ep2_trail_line.set_data([], [])
        barbell_line.set_data([], [])
        hud_text.set_text("")
        artists = [cm_trail_line, ep1_trail_line, ep2_trail_line, barbell_line, hud_text]
        if quiver_obj is not None:
            artists.append(quiver_obj)
        return artists

    def update(frame):
        state = states_render[frame]
        t = t_render[frame]
        r1 = r1_all[frame]
        r2 = r2_all[frame]
        v1 = v1_all[frame]
        v2 = v2_all[frame]
        R = R_all[frame]

        cm_trail_line.set_data(R_all[: frame + 1, 0], R_all[: frame + 1, 1])
        ep1_trail_line.set_data(r1_all[: frame + 1, 0], r1_all[: frame + 1, 1])
        ep2_trail_line.set_data(r2_all[: frame + 1, 0], r2_all[: frame + 1, 1])
        barbell_line.set_data([r1[0], r2[0]], [r1[1], r2[1]])
        ep1_dot.set_offsets(np.array([r1]))
        ep2_dot.set_offsets(np.array([r2]))
        cm_dot.set_offsets(np.array([R]))

        if quiver_obj is not None:
            V = np.array([state[2], state[3]])
            q_x = [r1[0], r2[0], R[0]]
            q_y = [r1[1], r2[1], R[1]]
            q_u = [v1[0], v2[0], V[0]]
            q_v = [v1[1], v2[1], V[1]]
            quiver_obj.set_offsets(np.column_stack((q_x, q_y)))
            quiver_obj.set_UVC(q_u, q_v)

        diag = get_diagnostics(t, state, scenario)
        alt = diag["r"] - earth_radius
        psi_deg = np.degrees(diag["psi_wrapped"])
        orbit_fraction = t / T_orbit_ref

        hud_lines = [
            f"Time:      {t:6.0f} s",
            f"Orbit:     {orbit_fraction:6.2f}",
            f"Altitude:  {alt/1e3:6.1f} km",
            f"Length:    {diag['length']/1e3:6.1f} km",
            f"Omega:     {diag['omega']:6.4e} rad/s",
            f"Angular-m: {diag['H']:6.4e} kg m^2/s",
            f"Libration: {psi_deg:6.1f}°",
        ]
        hud_text.set_text("\n".join(hud_lines))

        artists = [cm_trail_line, ep1_trail_line, ep2_trail_line, barbell_line, ep1_dot, ep2_dot, cm_dot, hud_text]
        if quiver_obj is not None:
            artists.append(quiver_obj)
        return artists

    ani = animation.FuncAnimation(fig, update, init_func=init, frames=num_frames, blit=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ani.save(output_path, writer="pillow", fps=fps)
    plt.close(fig)
