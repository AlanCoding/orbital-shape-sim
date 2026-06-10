from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from scipy.optimize import root_scalar

from .physics import G


ControllerLike = Callable[[float, Any, Any], float]


@dataclass
class Scenario:
    id: str
    title: str
    description: str
    state0: np.ndarray
    t_max: float
    half_span_m: float
    plot_half_width_m: float
    render_duration: float
    fps: int
    num_samples: int
    mass_total: float
    rho_eq: float
    rho_min: float
    rho_max: float
    rho_tau: float
    rho_kp: float
    rho_kd: float
    v_scale: float
    mu_earth: float
    mu_moon: float
    earth_pos: np.ndarray
    moon_pos: np.ndarray
    omega: float
    l1_x: float


def earth_moon_constants():
    mass_earth = 5.972168e24
    mass_moon = 7.342e22
    distance = 384400e3
    mu_earth = G * mass_earth
    mu_moon = G * mass_moon
    omega = np.sqrt(G * (mass_earth + mass_moon) / distance**3)
    mu = mass_moon / (mass_earth + mass_moon)
    earth_pos = np.array([-mu * distance, 0.0], dtype=float)
    moon_pos = np.array([(1.0 - mu) * distance, 0.0], dtype=float)
    return {
        "mass_earth": mass_earth,
        "mass_moon": mass_moon,
        "distance": distance,
        "mu_earth": mu_earth,
        "mu_moon": mu_moon,
        "omega": omega,
        "earth_pos": earth_pos,
        "moon_pos": moon_pos,
    }


def l1_x_position(constants: dict[str, float]) -> float:
    distance = constants["distance"]
    earth_pos = constants["earth_pos"]
    moon_pos = constants["moon_pos"]
    mu_earth = constants["mu_earth"]
    mu_moon = constants["mu_moon"]
    omega = constants["omega"]

    def net_ax(x: float) -> float:
        p = np.array([x, 0.0], dtype=float)
        rel_e = p - earth_pos
        rel_m = p - moon_pos
        a = -mu_earth * rel_e[0] / np.linalg.norm(rel_e) ** 3
        a += -mu_moon * rel_m[0] / np.linalg.norm(rel_m) ** 3
        a += omega**2 * x
        return float(a)

    left = earth_pos[0] + 1.0
    right = moon_pos[0] - 1.0
    sol = root_scalar(net_ax, bracket=(left, right), method="brentq")
    return float(sol.root)


def make_state(x: float, y: float, vx: float, vy: float, rho_act: float) -> np.ndarray:
    return np.array([x, y, vx, vy, rho_act], dtype=float)


def get_scenarios(half_span_km: float = 200.0) -> dict[str, Scenario]:
    constants = earth_moon_constants()
    l1_x = l1_x_position(constants)
    half_span_m = half_span_km * 1000.0
    mass_total = 1000.0
    rho_eq = 1.0
    rho_min = 0.1
    rho_max = 1.9
    rho_tau = 60.0
    rho_kp = 32.0
    rho_kd = 4.0
    v_scale = 10.0
    t_max = 45.0 * 24.0 * 3600.0
    render_duration = 8.0
    fps = 80
    num_samples = 1800
    plot_half_width_m = 5_000_000.0

    def base_state(vx: float = 0.0, vy: float = 0.0, dx: float = 0.0, dy: float = 0.0) -> np.ndarray:
        return make_state(l1_x + dx, dy, vx, vy, rho_eq)

    scenarios: dict[str, Scenario] = {}
    suffix = f"{int(half_span_km):03d}km"

    scenarios[f"01_noop_{suffix}"] = Scenario(
        id=f"01_noop_{suffix}",
        title=f"01: L1 No-Op Baseline ({half_span_km:.0f} km)",
        description="Nominal L1 configuration with the control law active but commanding the neutral diamond shape.",
        state0=base_state(),
        t_max=t_max,
        half_span_m=half_span_m,
        plot_half_width_m=plot_half_width_m,
        render_duration=render_duration,
        fps=fps,
        num_samples=num_samples,
        mass_total=mass_total,
        rho_eq=rho_eq,
        rho_min=rho_min,
        rho_max=rho_max,
        rho_tau=rho_tau,
        rho_kp=0.0,
        rho_kd=0.0,
        v_scale=v_scale,
        mu_earth=constants["mu_earth"],
        mu_moon=constants["mu_moon"],
        earth_pos=constants["earth_pos"],
        moon_pos=constants["moon_pos"],
        omega=constants["omega"],
        l1_x=l1_x,
    )

    scenarios[f"02_earthward_{suffix}"] = Scenario(
        id=f"02_earthward_{suffix}",
        title=f"02: Earthward Perturbation ({half_span_km:.0f} km)",
        description="The craft starts at L1 with a velocity toward Earth so the controller has to work against the unstable direction.",
        state0=base_state(vx=-0.2),
        t_max=t_max,
        half_span_m=half_span_m,
        plot_half_width_m=plot_half_width_m,
        render_duration=render_duration,
        fps=fps,
        num_samples=num_samples,
        mass_total=mass_total,
        rho_eq=rho_eq,
        rho_min=rho_min,
        rho_max=rho_max,
        rho_tau=rho_tau,
        rho_kp=rho_kp,
        rho_kd=rho_kd,
        v_scale=v_scale,
        mu_earth=constants["mu_earth"],
        mu_moon=constants["mu_moon"],
        earth_pos=constants["earth_pos"],
        moon_pos=constants["moon_pos"],
        omega=constants["omega"],
        l1_x=l1_x,
    )

    scenarios[f"03_tangential_{suffix}"] = Scenario(
        id=f"03_tangential_{suffix}",
        title=f"03: Tangential Perturbation ({half_span_km:.0f} km)",
        description="The craft starts at L1 with a tangential velocity so the response is dominated by the sideways motion instead of the unstable axis.",
        state0=base_state(vy=0.2),
        t_max=t_max,
        half_span_m=half_span_m,
        plot_half_width_m=plot_half_width_m,
        render_duration=render_duration,
        fps=fps,
        num_samples=num_samples,
        mass_total=mass_total,
        rho_eq=rho_eq,
        rho_min=rho_min,
        rho_max=rho_max,
        rho_tau=rho_tau,
        rho_kp=rho_kp,
        rho_kd=rho_kd,
        v_scale=v_scale,
        mu_earth=constants["mu_earth"],
        mu_moon=constants["mu_moon"],
        earth_pos=constants["earth_pos"],
        moon_pos=constants["moon_pos"],
        omega=constants["omega"],
        l1_x=l1_x,
    )

    scenarios[f"04_offset_{suffix}"] = Scenario(
        id=f"04_offset_{suffix}",
        title=f"04: Offset Position, Zero Velocity ({half_span_km:.0f} km)",
        description="The craft begins slightly displaced from L1 with no initial velocity to test whether the controller can pull it back gently.",
        state0=base_state(dx=10e3),
        t_max=t_max,
        half_span_m=half_span_m,
        plot_half_width_m=plot_half_width_m,
        render_duration=render_duration,
        fps=fps,
        num_samples=num_samples,
        mass_total=mass_total,
        rho_eq=rho_eq,
        rho_min=rho_min,
        rho_max=rho_max,
        rho_tau=rho_tau,
        rho_kp=rho_kp,
        rho_kd=rho_kd,
        v_scale=v_scale,
        mu_earth=constants["mu_earth"],
        mu_moon=constants["mu_moon"],
        earth_pos=constants["earth_pos"],
        moon_pos=constants["moon_pos"],
        omega=constants["omega"],
        l1_x=l1_x,
    )

    return scenarios


def get_scenarios_from_env() -> dict[str, Scenario]:
    import os

    half_span_km = float(os.environ.get("DIAMOND_L1_HALF_SPAN_KM", "400"))
    return get_scenarios(half_span_km=half_span_km)
