from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from scipy.optimize import root_scalar

from .controllers import controller
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
    zoom_half_width_m: float
    zoom_body_scale: float
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
    rho_kp = 2000.0
    rho_kd = 180.0
    v_scale = 10.0
    earthward_vx = -0.006
    tangential_vy = 0.001
    moonward_vx = 0.009
    offset_dx = 500.0
    t_max = 45.0 * 24.0 * 3600.0
    render_duration = 8.0
    fps = 80
    num_samples = 1800
    plot_half_width_m = 5_000_000.0
    zoom_half_width_m = 20_000.0
    zoom_body_scale = 0.02

    def base_state(vx: float = 0.0, vy: float = 0.0, dx: float = 0.0, dy: float = 0.0) -> np.ndarray:
        return make_state(l1_x + dx, dy, vx, vy, rho_eq)

    scenarios: dict[str, Scenario] = {}
    suffix = f"{int(half_span_km):03d}km"

    scenarios[f"01_noop_{suffix}"] = Scenario(
        id=f"01_noop_{suffix}",
        title=f"01: L1 No-Op Baseline ({half_span_km:.0f} km)",
        description="Nominal L1 configuration with x = 0 m, y = 0 m, vx = 0 m/s, vy = 0 m/s; the same control law is active, but there is no initial perturbation so this serves as the baseline response.",
        state0=base_state(),
        t_max=t_max,
        half_span_m=half_span_m,
        plot_half_width_m=plot_half_width_m,
        zoom_half_width_m=zoom_half_width_m,
        zoom_body_scale=zoom_body_scale,
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
    scenarios[f"01_noop_{suffix}"].state0[4] = controller(0.0, scenarios[f"01_noop_{suffix}"].state0, scenarios[f"01_noop_{suffix}"])

    active = Scenario(
        id=f"02_earthward_{suffix}",
        title=f"02: Earthward Perturbation ({half_span_km:.0f} km)",
        description="The craft starts at L1 with vx = -0.006 m/s toward Earth and vy = 0 m/s so the controller has to work against the unstable direction.",
        state0=base_state(vx=earthward_vx),
        t_max=t_max,
        half_span_m=half_span_m,
        plot_half_width_m=plot_half_width_m,
        zoom_half_width_m=zoom_half_width_m,
        zoom_body_scale=zoom_body_scale,
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
    active.state0 = active.state0.copy()
    active.state0[4] = controller(0.0, active.state0, active)
    scenarios[active.id] = active

    active = Scenario(
        id=f"03_tangential_{suffix}",
        title=f"03: Tangential Perturbation ({half_span_km:.0f} km)",
        description="The craft starts at L1 with vy = 0.001 m/s tangentially and vx = 0 m/s so the response is dominated by sideways motion instead of the unstable axis.",
        state0=base_state(vy=tangential_vy),
        t_max=t_max,
        half_span_m=half_span_m,
        plot_half_width_m=plot_half_width_m,
        zoom_half_width_m=zoom_half_width_m,
        zoom_body_scale=zoom_body_scale,
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
    active.state0 = active.state0.copy()
    active.state0[4] = controller(0.0, active.state0, active)
    scenarios[active.id] = active

    active = Scenario(
        id=f"04_offset_{suffix}",
        title=f"04: Offset Recovery ({half_span_km:.0f} km)",
        description="The craft begins displaced by dx = +500 m from L1 with zero initial velocity so the case stays inside the practical control envelope while still showing recovery behavior.",
        state0=base_state(dx=offset_dx),
        t_max=t_max,
        half_span_m=half_span_m,
        plot_half_width_m=plot_half_width_m,
        zoom_half_width_m=zoom_half_width_m,
        zoom_body_scale=zoom_body_scale,
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
    active.state0 = active.state0.copy()
    active.state0[4] = controller(0.0, active.state0, active)
    scenarios[active.id] = active

    active = Scenario(
        id=f"05_moonward_compression_{suffix}",
        title=f"05: Moonward Compression Stress Test ({half_span_km:.0f} km)",
        description="The craft starts at L1 with vx = 0.009 m/s moonward and no rho floor so the controller can collapse the diamond much closer to a line without immediately running away.",
        state0=base_state(vx=moonward_vx),
        t_max=t_max,
        half_span_m=half_span_m,
        plot_half_width_m=plot_half_width_m,
        zoom_half_width_m=zoom_half_width_m,
        zoom_body_scale=zoom_body_scale,
        render_duration=render_duration,
        fps=fps,
        num_samples=num_samples,
        mass_total=mass_total,
        rho_eq=rho_eq,
        rho_min=0.0,
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
    active.state0 = active.state0.copy()
    active.state0[4] = controller(0.0, active.state0, active)
    scenarios[active.id] = active

    return scenarios


def get_scenarios_from_env() -> dict[str, Scenario]:
    import os

    half_span_km = float(os.environ.get("DIAMOND_L1_HALF_SPAN_KM", "400"))
    return get_scenarios(half_span_km=half_span_km)
