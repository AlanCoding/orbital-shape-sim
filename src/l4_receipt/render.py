from __future__ import annotations

import os

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from matplotlib.patches import Circle


def _style_axes(ax):
    ax.set_facecolor("#0b1020")
    ax.grid(color="#25314d", linestyle=":", linewidth=0.6, alpha=0.6)
    ax.tick_params(colors="#c7d0dd", labelsize=8)
    ax.set_aspect("equal")


def _set_legend_text_color(legend, color: str = "#d7e1ea") -> None:
    if legend is None:
        return
    for text in legend.get_texts():
        text.set_color(color)


def _plot_window_mask(t_eval: np.ndarray, plot_days: float) -> np.ndarray:
    return t_eval <= min(float(t_eval[-1]), float(plot_days) * 86400.0)


def _compact_km_formatter(val: float, _pos: int) -> str:
    km = float(val) / 1000.0
    if abs(km) < 1e-9:
        return "0"
    s = f"{km:.1e}"
    mantissa, exponent = s.split("e")
    exponent = exponent.replace("+", "")
    if exponent.startswith("-0"):
        exponent = "-" + exponent[2:]
    elif exponent.startswith("0"):
        exponent = exponent[1:]
    return f"{mantissa}e{exponent}"


def _earth_centered_xy(states: np.ndarray, scenario) -> tuple[np.ndarray, np.ndarray]:
    x = states[:, 0] - scenario.earth_pos[0]
    y = states[:, 1]
    return x, y


def _roll_orbit_for_display(states: np.ndarray, scenario) -> np.ndarray:
    rel = np.asarray(states[:, :2], dtype=float) - np.asarray(scenario.l4_pos, dtype=float)
    idx = int(np.argmax(np.linalg.norm(rel, axis=1)))
    if idx <= 0:
        return np.asarray(states, dtype=float)
    return np.vstack([states[idx:], states[:idx]])


def _draw_bodies(ax, scenario, title: str):
    fig = ax.figure
    fig.patch.set_facecolor("#0b1020")
    _style_axes(ax)
    ax.set_title(title, color="#f4f7fb", fontsize=14, pad=12)
    moon_orbit = Circle((0.0, 0.0), scenario.distance, fill=False, ec="#5f6b83", lw=1.2, ls="--", alpha=0.7)
    ax.add_patch(moon_orbit)
    ax.scatter([0.0], [0.0], s=140, color="#4db6ac", edgecolors="#1f6f6a", linewidths=1.1, zorder=4)
    ax.scatter([scenario.distance], [0.0], s=80, color="#c8d1e0", edgecolors="#8c95a6", linewidths=1.1, zorder=4)
    ax.text(0.0, -22_000.0, "Earth", color="#4db6ac", fontsize=8, ha="center")
    ax.text(scenario.distance + 12_000.0, 16_000.0, "Moon", color="#c8d1e0", fontsize=8, ha="left")
    l4 = scenario.l4_pos - scenario.earth_pos
    l5 = scenario.l5_pos - scenario.earth_pos
    ax.plot([l4[0]], [l4[1]], marker="*", markersize=11, color="#f97316", zorder=5)
    ax.plot([l5[0]], [l5[1]], marker="*", markersize=9, color="#a78bfa", zorder=5, alpha=0.75)
    ax.text(l4[0] + 7000.0, l4[1] + 14_000.0, "L4", color="#f97316", fontsize=8, weight="bold")
    ax.text(l5[0] + 7000.0, l5[1] - 20_000.0, "L5", color="#a78bfa", fontsize=8, weight="bold")


def render_tadpole_orbit(scenario, t_eval: np.ndarray, states: np.ndarray, output_path: str) -> None:
    fig, ax = plt.subplots(figsize=(9.0, 8.4), dpi=180)
    _draw_bodies(ax, scenario, "L4 tadpole orbit")
    fig.subplots_adjust(bottom=0.10)

    display_states = states[_plot_window_mask(t_eval, 150.0)]
    x_ec, y_ec = _earth_centered_xy(display_states, scenario)
    ax.plot(x_ec, y_ec, color="#67e8f9", lw=1.4, alpha=0.9, label="station orbit")
    markevery = list(range(0, len(x_ec), max(1, int(scenario.samples_per_day))))
    ax.plot(
        x_ec,
        y_ec,
        color="#67e8f9",
        lw=0.0,
        marker="o",
        markersize=2.0,
        markerfacecolor="#cfefff",
        markeredgecolor="#67e8f9",
        markevery=markevery,
        alpha=0.8,
        label="daily markers",
    )
    ax.text(
        0.03,
        0.83,
        "tadpole orbit only\nteal dots = daily markers",
        transform=ax.transAxes,
        color="#d7e1ea",
        fontsize=7.2,
        family="monospace",
        bbox=dict(facecolor="#08101d", edgecolor="#4db6ac", alpha=0.85, boxstyle="round,pad=0.35"),
    )
    ax.set_xlim(-0.08 * scenario.distance, 1.08 * scenario.distance)
    ax.set_ylim(-1.05 * scenario.distance, 1.05 * scenario.distance)
    ax.set_xlabel("Earth-centered x (km)", color="#c7d0dd", labelpad=10)
    ax.set_ylabel("Earth-centered y (km)", color="#c7d0dd", labelpad=10)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(_compact_km_formatter))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(_compact_km_formatter))
    legend = ax.legend(loc="lower right", fontsize=8, frameon=True, facecolor="#08101d", edgecolor="#4db6ac", framealpha=0.85)
    _set_legend_text_color(legend)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def render_reference_orbit(scenario, t_eval: np.ndarray, states: np.ndarray, crossings, pickup_crossing, output_path: str) -> None:
    fig, ax = plt.subplots(figsize=(9.0, 8.4), dpi=180)
    _draw_bodies(ax, scenario, "L4 reference tadpole orbit")
    fig.subplots_adjust(bottom=0.10)

    display_states = _roll_orbit_for_display(states[_plot_window_mask(t_eval, 25.0)], scenario)
    x_ec, y_ec = _earth_centered_xy(display_states, scenario)
    ax.plot(x_ec, y_ec, color="#67e8f9", lw=1.4, alpha=0.9, label="station orbit")
    markevery = list(range(0, len(x_ec), max(1, int(scenario.samples_per_day))))
    ax.plot(
        x_ec,
        y_ec,
        color="#67e8f9",
        lw=0.0,
        marker="o",
        markersize=2.0,
        markerfacecolor="#cfefff",
        markeredgecolor="#67e8f9",
        markevery=markevery,
        alpha=0.8,
        label="daily markers",
    )

    crossing_xy = np.array([crossing.state[:2] - scenario.earth_pos for crossing in crossings], dtype=float)
    if len(crossing_xy) > 0:
        ax.scatter(
            crossing_xy[:, 0],
            crossing_xy[:, 1],
            s=16,
            color="#94a3b8",
            alpha=0.8,
            label="velocity-angle crossings",
        )

    pickup_pt = pickup_crossing.state[:2] - scenario.earth_pos
    ax.plot(pickup_pt[0], pickup_pt[1], marker="o", markersize=7.5, color="#f97316", zorder=6, label="sample pickup")
    ax.text(
        0.03,
        0.83,
        "20 velocity-angle bins\nhighlight = Moon-side pickup\nteal dots = daily markers",
        transform=ax.transAxes,
        color="#d7e1ea",
        fontsize=7.2,
        family="monospace",
        bbox=dict(facecolor="#08101d", edgecolor="#4db6ac", alpha=0.85, boxstyle="round,pad=0.35"),
    )
    ax.set_xlim(-0.08 * scenario.distance, 1.08 * scenario.distance)
    ax.set_ylim(-1.05 * scenario.distance, 1.05 * scenario.distance)
    ax.set_xlabel("Earth-centered x (km)", color="#c7d0dd", labelpad=10)
    ax.set_ylabel("Earth-centered y (km)", color="#c7d0dd", labelpad=10)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(_compact_km_formatter))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(_compact_km_formatter))
    legend = ax.legend(loc="lower right", fontsize=8, frameon=True, facecolor="#08101d", edgecolor="#4db6ac", framealpha=0.85)
    _set_legend_text_color(legend)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def render_payload_example(scenario, orbit_t: np.ndarray, orbit_states: np.ndarray, crossing, payload, output_path: str) -> None:
    fig, ax = plt.subplots(figsize=(9.0, 8.4), dpi=180)
    _draw_bodies(ax, scenario, "Example payload path to an L4 pickup")
    fig.subplots_adjust(bottom=0.10)

    orbit_states_display = _roll_orbit_for_display(orbit_states[_plot_window_mask(orbit_t, 30.0)], scenario)
    orbit_x, orbit_y = _earth_centered_xy(orbit_states_display, scenario)
    ax.plot(orbit_x, orbit_y, color="#475569", lw=1.0, alpha=0.55, label="reference orbit")

    payload_x, payload_y = _earth_centered_xy(payload.trajectory_states, scenario)
    ax.plot(payload_x, payload_y, color="#f97316", lw=2.0, alpha=0.95, label="payload back-propagation")
    ax.plot(payload_x[0], payload_y[0], marker="o", markersize=6.5, color="#c8d1e0", zorder=6)
    ax.plot(payload_x[-1], payload_y[-1], marker="*", markersize=10, color="#f97316", zorder=7)

    catch_pt = crossing.state[:2] - scenario.earth_pos
    ax.plot(catch_pt[0], catch_pt[1], marker="o", markersize=7.0, color="#67e8f9", zorder=7)
    moon_surface = payload.surface_state[:2] - scenario.earth_pos
    ax.plot(moon_surface[0], moon_surface[1], marker="o", markersize=7.0, color="#22c55e", zorder=7)

    ax.text(
        0.03,
        0.83,
        f"pickup angle = {crossing.target_angle_deg:.0f}°\nlaunch speed ≈ {payload.launch_speed_mps:.0f} m/s\nsurface longitude = {payload.longitude_deg:.1f}°",
        transform=ax.transAxes,
        color="#d7e1ea",
        fontsize=7.2,
        family="monospace",
        bbox=dict(facecolor="#08101d", edgecolor="#4db6ac", alpha=0.85, boxstyle="round,pad=0.35"),
    )
    ax.set_xlim(-0.08 * scenario.distance, 1.08 * scenario.distance)
    ax.set_ylim(-1.05 * scenario.distance, 1.05 * scenario.distance)
    ax.set_xlabel("Earth-centered x (km)", color="#c7d0dd", labelpad=10)
    ax.set_ylabel("Earth-centered y (km)", color="#c7d0dd", labelpad=10)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(_compact_km_formatter))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(_compact_km_formatter))
    legend = ax.legend(loc="lower right", fontsize=8, frameon=True, facecolor="#08101d", edgecolor="#4db6ac", framealpha=0.85)
    _set_legend_text_color(legend)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def render_catch_chain(scenario, chain, output_path: str) -> None:
    fig = plt.figure(figsize=(9.6, 9.2), dpi=180)
    fig.patch.set_facecolor("#0b1020")
    gs = fig.add_gridspec(2, 1, height_ratios=[4.6, 1.1], hspace=0.20)
    ax = fig.add_subplot(gs[0])
    ax_summary = fig.add_subplot(gs[1])
    _style_axes(ax)
    fig.patch.set_facecolor("#0b1020")
    ax.set_title("Repeated catches at L4", color="#f4f7fb", fontsize=14, pad=12)
    fig.subplots_adjust(bottom=0.10)

    if chain.segments_states:
        all_states = np.vstack(chain.segments_states)
        x_rel = (all_states[:, 0] - scenario.l4_pos[0]) / 1000.0
        y_rel = (all_states[:, 1] - scenario.l4_pos[1]) / 1000.0
        ax.plot(x_rel, y_rel, color="#67e8f9", lw=1.5, alpha=0.9, label="station orbit")
        ax.plot(x_rel[0], y_rel[0], marker="o", markersize=4.0, color="#c8d1e0", zorder=7, label="first catch")
        ax.plot(x_rel[-1], y_rel[-1], marker="o", markersize=5.5, color="#f97316", zorder=7, label="final state")
        x_pad = max(1.0, 0.15 * max(abs(float(np.min(x_rel))), abs(float(np.max(x_rel)))))
        y_pad = max(1.0, 0.15 * max(abs(float(np.min(y_rel))), abs(float(np.max(y_rel)))))
        ax.set_xlim(float(np.min(x_rel) - x_pad), float(np.max(x_rel) + x_pad))
        ax.set_ylim(float(np.min(y_rel) - y_pad), float(np.max(y_rel) + y_pad))

    ax.text(
        0.03,
        0.83,
        f"target pickup angle = {np.degrees(chain.target_angle_rad) % 360.0:.0f}°\nfinal station mass = {chain.final_station_mass:.1f}\n delivered mass = {chain.total_delivered_mass:.1f}",
        transform=ax.transAxes,
        color="#d7e1ea",
        fontsize=7.2,
        family="monospace",
        bbox=dict(facecolor="#08101d", edgecolor="#4db6ac", alpha=0.85, boxstyle="round,pad=0.35"),
    )
    ax.set_xlabel("L4-centered x (km)", color="#c7d0dd", labelpad=10)
    ax.set_ylabel("L4-centered y (km)", color="#c7d0dd", labelpad=10)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val:.0f}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val:.0f}"))
    legend = ax.legend(loc="lower right", fontsize=8, frameon=True, facecolor="#08101d", edgecolor="#4db6ac", framealpha=0.85)
    _set_legend_text_color(legend)

    ax_summary.axis("off")
    if chain.segments_states:
        all_states = np.vstack(chain.segments_states)
        x_rel = (all_states[:, 0] - scenario.l4_pos[0]) / 1000.0
        y_rel = (all_states[:, 1] - scenario.l4_pos[1]) / 1000.0
        r_rel = np.sqrt(x_rel**2 + y_rel**2)
        summary = (
            f"orbit bounds relative to L4 (km)\n"
            f"x: {float(np.min(x_rel)):.1f} to {float(np.max(x_rel)):.1f}\n"
            f"y: {float(np.min(y_rel)):.1f} to {float(np.max(y_rel)):.1f}\n"
            f"r: {float(np.min(r_rel)):.1f} to {float(np.max(r_rel)):.1f}\n"
            f"final station mass: {chain.final_station_mass:.1f}\n"
            f"delivered mass: {chain.total_delivered_mass:.1f}"
        )
        ax_summary.text(
            0.03,
            0.5,
            summary,
            transform=ax_summary.transAxes,
            va="center",
            color="#d7e1ea",
            fontsize=8,
            family="monospace",
            bbox=dict(facecolor="#08101d", edgecolor="#4db6ac", alpha=0.85, boxstyle="round,pad=0.35"),
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def render_final_orbit(scenario, final_state: np.ndarray, days: float, output_path: str) -> None:
    fig, ax = plt.subplots(figsize=(9.0, 8.4), dpi=180)
    _draw_bodies(ax, scenario, "Final orbit after repeated catches")
    fig.subplots_adjust(bottom=0.10)

    from .analysis import integrate_orbit

    t_eval, states = integrate_orbit(scenario, state0=final_state, days=days)
    x_ec, y_ec = _earth_centered_xy(states, scenario)
    ax.plot(x_ec, y_ec, color="#67e8f9", lw=1.5, alpha=0.9, label="final orbit")
    ax.plot(
        x_ec,
        y_ec,
        color="#67e8f9",
        lw=0.0,
        marker="o",
        markersize=2.0,
        markerfacecolor="#cfefff",
        markeredgecolor="#67e8f9",
        markevery=list(range(0, len(x_ec), max(1, int(scenario.samples_per_day)))),
        alpha=0.8,
        label="daily markers",
    )

    orbit_points = np.column_stack([x_ec, y_ec])
    body_points = np.array(
        [
            [0.0, 0.0],
            [scenario.distance, 0.0],
        ],
        dtype=float,
    )
    all_points = np.vstack([orbit_points, body_points])
    x_min = float(np.min(all_points[:, 0]))
    x_max = float(np.max(all_points[:, 0]))
    y_min = float(np.min(all_points[:, 1]))
    y_max = float(np.max(all_points[:, 1]))
    x_pad = max(1_000.0, 0.08 * max(abs(x_min), abs(x_max), 1.0))
    y_pad = max(1_000.0, 0.08 * max(abs(y_min), abs(y_max), 1.0))

    moon_rel = np.asarray(final_state[:2], dtype=float) - np.asarray(scenario.moon_pos, dtype=float)
    moon_rel_norm = float(np.linalg.norm(moon_rel))
    moon_speed = float(np.linalg.norm(final_state[2:4]))
    moon_escape = float(np.sqrt(2.0 * scenario.mu_moon / moon_rel_norm))
    ratio = moon_speed / moon_escape if moon_escape > 0.0 else float("nan")

    ax.text(
        0.03,
        0.83,
        f"month after final catch = {days:.0f} days\nmoon-relative speed = {moon_speed/1000.0:.3f} km/s\nescape speed = {moon_escape/1000.0:.3f} km/s\nspeed / escape = {ratio:.2f}",
        transform=ax.transAxes,
        color="#d7e1ea",
        fontsize=7.2,
        family="monospace",
        bbox=dict(facecolor="#08101d", edgecolor="#4db6ac", alpha=0.85, boxstyle="round,pad=0.35"),
    )
    ax.set_xlim(x_min - x_pad, x_max + x_pad)
    ax.set_ylim(y_min - y_pad, y_max + y_pad)
    ax.set_xlabel("Earth-centered x (km)", color="#c7d0dd", labelpad=10)
    ax.set_ylabel("Earth-centered y (km)", color="#c7d0dd", labelpad=10)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(_compact_km_formatter))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(_compact_km_formatter))
    legend = ax.legend(loc="lower right", fontsize=8, frameon=True, facecolor="#08101d", edgecolor="#4db6ac", framealpha=0.85)
    _set_legend_text_color(legend)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
