from __future__ import annotations

import os
from dataclasses import dataclass

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from matplotlib.patches import Circle
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from .physics import derivatives


LUNAR_ORBIT_DAYS = 27.321661
RELEASE_SPEED_MPS = 100.0
SCAN_ANGLE_STEP_DEG = 5.0
DAY_SECONDS = 86400.0
SCAN_SAMPLES = 6000
ROOT_SAMPLES = 25000


@dataclass(frozen=True)
class GrazingCase:
    angle_rad: float
    speed_mps: float
    t_eval: np.ndarray
    states: np.ndarray
    closest_index: int
    min_distance_m: float
    contact_time_s: float
    moon_relative_point_m: np.ndarray
    longitude_deg: float

    @property
    def angle_deg(self) -> float:
        return float(np.degrees(self.angle_rad))


@dataclass(frozen=True)
class GrazingAnalysis:
    speed_mps: float
    scan_angles_rad: np.ndarray
    scan_min_distances_m: np.ndarray
    grazing_cases: list[GrazingCase]


@dataclass(frozen=True)
class ScanAnalysis:
    speed_mps: float
    max_days: float
    scan_angles_rad: np.ndarray
    scan_min_distances_m: np.ndarray


def _evaluate_release(
    scenario,
    angle_rad: float,
    speed_mps: float,
    samples: int,
    max_days: float = LUNAR_ORBIT_DAYS,
) -> GrazingCase:
    t_max = max_days * DAY_SECONDS
    t_eval = np.linspace(0.0, t_max, samples)
    y0 = np.array(
        [
            scenario.l1_x,
            0.0,
            speed_mps * np.cos(angle_rad),
            speed_mps * np.sin(angle_rad),
        ],
        dtype=float,
    )
    sol = solve_ivp(
        fun=lambda t, y: derivatives(t, y, scenario),
        t_span=(0.0, t_max),
        y0=y0,
        t_eval=t_eval,
        method="DOP853",
        rtol=1e-10,
        atol=1e-12,
    )

    states = sol.y.T
    moon_pos = np.array(scenario.moon_pos, dtype=float)
    moon_rel = states[:, 0:2] - moon_pos
    distances = np.hypot(moon_rel[:, 0], moon_rel[:, 1])
    closest_index = int(np.argmin(distances))
    contact_moon_rel = moon_rel[closest_index]
    longitude_deg = float(np.degrees(np.arctan2(contact_moon_rel[1], contact_moon_rel[0])))
    return GrazingCase(
        angle_rad=float(angle_rad),
        speed_mps=float(speed_mps),
        t_eval=t_eval,
        states=states,
        closest_index=closest_index,
        min_distance_m=float(distances[closest_index]),
        contact_time_s=float(t_eval[closest_index]),
        moon_relative_point_m=contact_moon_rel,
        longitude_deg=longitude_deg,
    )


def analyze_grazing_releases(scenario, speed_mps: float = RELEASE_SPEED_MPS) -> GrazingAnalysis:
    scan = analyze_release_scan(scenario, speed_mps=speed_mps)
    scan_angles_rad = scan.scan_angles_rad
    scan_min_distances_m = scan.scan_min_distances_m
    moon_radius_m = float(scenario.moon_radius_m)
    signed = scan_min_distances_m - moon_radius_m

    grazing_cases: list[GrazingCase] = []

    def min_distance_minus_radius(angle_rad: float) -> float:
        return _evaluate_release(scenario, angle_rad, speed_mps, ROOT_SAMPLES).min_distance_m - moon_radius_m

    for idx in range(len(scan_angles_rad)):
        next_idx = (idx + 1) % len(scan_angles_rad)
        left_angle = float(scan_angles_rad[idx])
        right_angle = float(scan_angles_rad[next_idx])
        left_value = float(signed[idx])
        right_value = float(signed[next_idx])

        # Skip the wrap-around interval unless it genuinely changes sign.
        if next_idx == 0 and left_value * right_value > 0:
            continue
        if left_value == 0.0:
            root_angle = left_angle
        elif left_value * right_value < 0.0:
            root_angle = float(
                brentq(
                    min_distance_minus_radius,
                    left_angle,
                    right_angle,
                    xtol=1e-10,
                    rtol=1e-11,
                    maxiter=100,
                )
            )
        else:
            continue

        grazing_cases.append(_evaluate_release(scenario, root_angle, speed_mps, ROOT_SAMPLES))

    grazing_cases.sort(key=lambda case: case.angle_rad)
    return GrazingAnalysis(
        speed_mps=float(speed_mps),
        scan_angles_rad=scan_angles_rad,
        scan_min_distances_m=scan_min_distances_m,
        grazing_cases=grazing_cases,
    )


def analyze_release_scan(
    scenario,
    speed_mps: float,
    angle_step_deg: float = SCAN_ANGLE_STEP_DEG,
    dense_band_deg: tuple[float, float] | None = None,
    dense_factor: int = 1,
    max_days: float = LUNAR_ORBIT_DAYS,
) -> ScanAnalysis:
    scan_angles_deg = list(np.arange(0.0, 360.0, angle_step_deg))
    if dense_band_deg is not None and dense_factor > 1:
        band_start_deg, band_end_deg = dense_band_deg
        dense_step_deg = angle_step_deg / float(dense_factor)
        dense_angles_deg = list(np.arange(band_start_deg, band_end_deg, dense_step_deg))
        scan_angles_deg = sorted({float(val) for val in scan_angles_deg + dense_angles_deg})
    scan_angles_rad = np.deg2rad(np.array(scan_angles_deg, dtype=float))
    scan_results = [_evaluate_release(scenario, angle, speed_mps, SCAN_SAMPLES, max_days=max_days) for angle in scan_angles_rad]
    scan_min_distances_m = np.array([item.min_distance_m for item in scan_results], dtype=float)
    return ScanAnalysis(
        speed_mps=float(speed_mps),
        max_days=float(max_days),
        scan_angles_rad=scan_angles_rad,
        scan_min_distances_m=scan_min_distances_m,
    )


def analyze_bounded_grazing_releases(
    scenario,
    speed_mps: float,
    angle_min_deg: float,
    angle_max_deg: float,
    angle_step_deg: float = 0.25,
    max_days: float = LUNAR_ORBIT_DAYS,
) -> GrazingAnalysis:
    scan_angles_rad = np.deg2rad(np.arange(angle_min_deg, angle_max_deg + 0.5 * angle_step_deg, angle_step_deg))
    scan_results = [_evaluate_release(scenario, angle, speed_mps, ROOT_SAMPLES, max_days=max_days) for angle in scan_angles_rad]
    scan_min_distances_m = np.array([item.min_distance_m for item in scan_results], dtype=float)
    moon_radius_m = float(scenario.moon_radius_m)
    signed = scan_min_distances_m - moon_radius_m

    grazing_cases: list[GrazingCase] = []

    def min_distance_minus_radius(angle_rad: float) -> float:
        return _evaluate_release(scenario, angle_rad, speed_mps, ROOT_SAMPLES, max_days=max_days).min_distance_m - moon_radius_m

    for idx in range(len(scan_angles_rad) - 1):
        left_angle = float(scan_angles_rad[idx])
        right_angle = float(scan_angles_rad[idx + 1])
        left_value = float(signed[idx])
        right_value = float(signed[idx + 1])

        if left_value == 0.0:
            root_angle = left_angle
        elif left_value * right_value < 0.0:
            root_angle = float(
                brentq(
                    min_distance_minus_radius,
                    left_angle,
                    right_angle,
                    xtol=1e-10,
                    rtol=1e-11,
                    maxiter=100,
                )
            )
        else:
            continue

        grazing_cases.append(_evaluate_release(scenario, root_angle, speed_mps, ROOT_SAMPLES, max_days=max_days))

    grazing_cases.sort(key=lambda case: case.angle_rad)
    return GrazingAnalysis(
        speed_mps=float(speed_mps),
        scan_angles_rad=scan_angles_rad,
        scan_min_distances_m=scan_min_distances_m,
        grazing_cases=grazing_cases,
    )


def render_grazing_scan(scenario, analysis: GrazingAnalysis, output_path: str) -> None:
    render_grazing_scan_with_limits(scenario, analysis, output_path, y_limit_km=2.0 * (float(scenario.moon_radius_m) / 1000.0))


def render_release_scan_only(
    scenario,
    scan: ScanAnalysis,
    output_path: str,
    y_limit_km: float,
    title: str,
) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 6.6), dpi=180)
    fig.patch.set_facecolor("#0b1020")
    ax.set_facecolor("#0b1020")
    ax.grid(color="#25314d", linestyle=":", linewidth=0.6, alpha=0.6)
    ax.tick_params(colors="#c7d0dd", labelsize=8)
    ax.set_title(title, color="#f4f7fb", fontsize=14, pad=12)

    angles_deg = np.degrees(scan.scan_angles_rad)
    moon_radius_km = float(scenario.moon_radius_m) / 1000.0
    min_distances_km = scan.scan_min_distances_m / 1000.0
    ax.plot(
        angles_deg,
        min_distances_km,
        color="#67e8f9",
        lw=1.6,
        marker="o",
        markersize=3.4,
        markerfacecolor="#cfefff",
        markeredgecolor="#67e8f9",
        alpha=0.9,
        label="closest approach",
    )
    ax.axhspan(0.0, moon_radius_km, color="#f97316", alpha=0.06)
    ax.axhline(moon_radius_km, color="#f97316", lw=1.4, ls="--", label="lunar radius")
    ax.set_xlim(0.0, 360.0)
    ax.set_ylim(0.0, y_limit_km)
    ax.set_xlabel("release angle (deg from +x toward Moon)", color="#c7d0dd")
    ax.set_ylabel("closest approach to Moon (km)", color="#c7d0dd")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val:.0f}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val:.0f}"))
    legend = ax.legend(
        loc="upper right",
        fontsize=8,
        frameon=True,
        facecolor="#08101d",
        edgecolor="#4db6ac",
        framealpha=0.88,
    )
    for text in legend.get_texts():
        text.set_color("#d7e1ea")

    ax.text(
        0.02,
        0.03,
        f"release speed = {scan.speed_mps:.0f} m/s\nscan points = {len(scan.scan_angles_rad)}\nmax days = {scan.max_days:.1f}",
        transform=ax.transAxes,
        color="#d7e1ea",
        fontsize=8,
        family="monospace",
        bbox=dict(facecolor="#08101d", edgecolor="#4db6ac", alpha=0.85, boxstyle="round,pad=0.35"),
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def render_grazing_scan_with_limits(
    scenario,
    analysis: GrazingAnalysis,
    output_path: str,
    y_limit_km: float,
    x_limits_deg: tuple[float, float] | None = None,
    title: str | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 6.6), dpi=180)
    fig.patch.set_facecolor("#0b1020")
    ax.set_facecolor("#0b1020")
    ax.grid(color="#25314d", linestyle=":", linewidth=0.6, alpha=0.6)
    ax.tick_params(colors="#c7d0dd", labelsize=8)
    ax.set_title(title or "Lunar surface grazing scan", color="#f4f7fb", fontsize=14, pad=12)

    angles_deg = np.degrees(analysis.scan_angles_rad)
    moon_radius_km = float(scenario.moon_radius_m) / 1000.0
    min_distances_km = analysis.scan_min_distances_m / 1000.0
    ax.plot(
        angles_deg,
        min_distances_km,
        color="#67e8f9",
        lw=1.6,
        marker="o",
        markersize=3.4,
        markerfacecolor="#cfefff",
        markeredgecolor="#67e8f9",
        alpha=0.9,
        label="closest approach",
    )
    ax.axhspan(0.0, moon_radius_km, color="#f97316", alpha=0.06)
    ax.axhline(moon_radius_km, color="#f97316", lw=1.4, ls="--", label="lunar radius")

    for idx, case in enumerate(analysis.grazing_cases[:2]):
        angle_deg = case.angle_deg
        color = "#f8fafc" if idx == 0 else "#facc15"
        ax.axvline(angle_deg, color=color, lw=1.0, ls=":", alpha=0.8)
        ax.scatter([angle_deg], [case.min_distance_m / 1000.0], color=color, s=52, zorder=5)
        ax.annotate(
            f"{angle_deg:.2f}°",
            (angle_deg, case.min_distance_m / 1000.0),
            textcoords="offset points",
            xytext=(8, 8),
            color=color,
            fontsize=8,
        )

    if x_limits_deg is None:
        ax.set_xlim(0.0, 360.0)
    else:
        ax.set_xlim(float(x_limits_deg[0]), float(x_limits_deg[1]))
    ax.set_ylim(0.0, y_limit_km)
    ax.set_xlabel("release angle (deg from +x toward Moon)", color="#c7d0dd")
    ax.set_ylabel("closest approach to Moon (km)", color="#c7d0dd")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val:.0f}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val:.0f}"))
    legend = ax.legend(
        loc="upper right",
        fontsize=8,
        frameon=True,
        facecolor="#08101d",
        edgecolor="#4db6ac",
        framealpha=0.88,
    )
    for text in legend.get_texts():
        text.set_color("#d7e1ea")

    ax.text(
        0.02,
        0.03,
        f"release speed = {analysis.speed_mps:.0f} m/s\nscan points = {len(analysis.scan_angles_rad)}",
        transform=ax.transAxes,
        color="#d7e1ea",
        fontsize=8,
        family="monospace",
        bbox=dict(facecolor="#08101d", edgecolor="#4db6ac", alpha=0.85, boxstyle="round,pad=0.35"),
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def render_grazing_moon_frame(scenario, analysis: GrazingAnalysis, output_path: str) -> None:
    if len(analysis.grazing_cases) < 1:
        raise ValueError("expected at least one grazing case")

    fig, ax = plt.subplots(figsize=(9.0, 6.8), dpi=180)
    fig.patch.set_facecolor("#0b1020")
    ax.set_facecolor("#0b1020")
    ax.grid(color="#25314d", linestyle=":", linewidth=0.6, alpha=0.6)
    ax.tick_params(colors="#c7d0dd", labelsize=8)
    ax.set_aspect("equal")
    ax.set_title("Moon-centered grazing trajectories", color="#f4f7fb", fontsize=14, pad=12)

    moon_radius_km = float(scenario.moon_radius_m) / 1000.0
    moon = Circle((0.0, 0.0), moon_radius_km, facecolor="#c8d1e0", edgecolor="#8c95a6", lw=1.4, alpha=0.18, zorder=1)
    ax.add_patch(moon)
    ax.scatter([0.0], [0.0], s=150, color="#c8d1e0", edgecolors="#8c95a6", linewidths=1.1, zorder=4)
    ax.text(0.0, 1200.0, "Moon", color="#d7e1ea", fontsize=9, ha="center")

    l1_x_km = (float(scenario.l1_x) - float(scenario.moon_pos[0])) / 1000.0
    ax.plot([l1_x_km], [0.0], marker="*", markersize=11, color="#f97316", zorder=5)
    ax.text(l1_x_km, 2800.0, "L1", color="#f97316", fontsize=9, ha="center", weight="bold")

    colors = ["#67e8f9", "#f97316"]
    for idx, case in enumerate(analysis.grazing_cases[:2]):
        moon_rel = (case.states[:, 0:2] - np.array(scenario.moon_pos, dtype=float)) / 1000.0
        stop = case.closest_index + 1
        color = colors[idx]
        ax.plot(
            moon_rel[:stop, 0],
            moon_rel[:stop, 1],
            color=color,
            lw=1.7,
            alpha=0.88,
            marker="o",
            markersize=2.4,
            markerfacecolor=color,
            markeredgecolor=color,
            markevery=list(range(0, stop, max(1, stop // 24))),
            label=f"{case.angle_deg:.2f}° release",
        )
        ax.scatter(
            [case.moon_relative_point_m[0] / 1000.0],
            [case.moon_relative_point_m[1] / 1000.0],
            color=color,
            marker="*",
            s=85,
            zorder=6,
        )
    ax.set_xlim(-90_000.0, 22_000.0)
    ax.set_ylim(-25_000.0, 25_000.0)
    ax.set_xlabel("moon-centered x (km, toward Earth)", color="#c7d0dd")
    ax.set_ylabel("moon-centered y (km)", color="#c7d0dd")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val:.0f}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val:.0f}"))

    legend = ax.legend(
        loc="upper right",
        fontsize=8,
        frameon=True,
        facecolor="#08101d",
        edgecolor="#4db6ac",
        framealpha=0.88,
    )
    for text in legend.get_texts():
        text.set_color("#d7e1ea")

    box_lines = [f"release speed = {analysis.speed_mps:.0f} m/s"]
    for case in analysis.grazing_cases[:2]:
        box_lines.append(f"{case.angle_deg:.2f}° -> lon {case.longitude_deg:.1f}°")
    ax.text(
        0.02,
        0.03,
        "\n".join(box_lines),
        transform=ax.transAxes,
        color="#d7e1ea",
        fontsize=8,
        family="monospace",
        bbox=dict(facecolor="#08101d", edgecolor="#4db6ac", alpha=0.85, boxstyle="round,pad=0.35"),
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
