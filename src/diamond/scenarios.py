from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np


AlphaLaw = Callable[[float, Any, "Scenario"], float]
RhoLaw = Callable[[float, Any, "Scenario"], float]


@dataclass
class Scenario:
    id: str
    title: str
    description: str
    state0: np.ndarray
    t_max: float
    mass: float
    R0: float
    mu: float
    rho_min: float
    rho_max: float
    rho_tau: float
    alpha_fixed: float
    alpha_offset: float
    alpha_law: AlphaLaw
    rho_law: RhoLaw
    primary_radius: float = 6.371e6
    show_primary_body: bool = True
    render_duration: float = 4.0
    fps: int = 80
    num_samples: int = 1600


def smoothstep(x: float) -> float:
    x = float(np.clip(x, 0.0, 1.0))
    return x * x * (3.0 - 2.0 * x)


def wrap_to_pi(angle: float) -> float:
    return float((angle + np.pi) % (2.0 * np.pi) - np.pi)


def circular_state(mu: float, r0: float, phi0: float, omega0: float, rho0: float) -> np.ndarray:
    v0 = np.sqrt(mu / r0) if mu > 0.0 else 0.0
    return np.array([r0, 0.0, 0.0, v0, phi0, omega0, rho0], dtype=float)


def perigee_state(mu: float, rp: float, e: float, phi0: float, omega0: float, rho0: float) -> np.ndarray:
    vp = np.sqrt(mu * (1.0 + e) / rp)
    return np.array([rp, 0.0, 0.0, vp, phi0, omega0, rho0], dtype=float)


def get_scenarios(mu: float = 3.986004418e14) -> dict[str, Scenario]:
    scenarios: dict[str, Scenario] = {}

    mass = 1000.0
    R0 = 4.0e5
    rho_min = 0.08
    rho_max = 1.92
    alpha_offset = np.deg2rad(22.5)
    phi0 = np.deg2rad(18.0)

    def orbital_alpha(t: float, state: np.ndarray, scenario: Scenario) -> float:
        x, y, vx, vy, phi, omega, rho_act = state
        theta = float(np.arctan2(y, x))
        return wrap_to_pi(theta - phi + scenario.alpha_offset)

    def fixed_alpha(t: float, state: np.ndarray, scenario: Scenario) -> float:
        return float(scenario.alpha_fixed)

    def fixed_rho(value: float) -> RhoLaw:
        def _law(t: float, state: np.ndarray, scenario: Scenario) -> float:
            return float(value)

        return _law

    def apsis_rho(low: float, high: float, reverse: bool = False, transition_width: float = 50.0) -> RhoLaw:
        def _law(t: float, state: np.ndarray, scenario: Scenario) -> float:
            x, y, vx, vy, phi, omega, rho_act = state
            r = float(np.hypot(x, y))
            drdt = 0.0 if r == 0.0 else float((x * vx + y * vy) / r)
            signal = -drdt if reverse else drdt
            blend = float(0.5 * (1.0 + np.tanh(signal / transition_width)))
            return float(low + (high - low) * blend)

        return _law

    def ramp_rho(start: float, end: float, t_max: float) -> RhoLaw:
        def _law(t: float, state: np.ndarray, scenario: Scenario) -> float:
            s = smoothstep(t / t_max)
            return float(start + (end - start) * s)

        return _law

    # 1. Orbital control baseline.
    r0 = 8.5e6
    n_orbit = np.sqrt(mu / r0**3)
    omega0 = 1.0 * n_orbit
    state_ref = circular_state(mu, r0, phi0, omega0, 1.0)
    scenarios["01_orbital_control_reference"] = Scenario(
        id="01_orbital_control_reference",
        title="01: Orbital Control Reference",
        description="Circular-orbit baseline with the undeformed square, used to show the final control stack in its simplest orbital configuration.",
        state0=state_ref,
        t_max=2.4 * 2.0 * np.pi / n_orbit,
        mass=mass,
        R0=R0,
        mu=mu,
        rho_min=rho_min,
        rho_max=rho_max,
        rho_tau=180.0,
        alpha_fixed=0.0,
        alpha_offset=0.0,
        alpha_law=orbital_alpha,
        rho_law=fixed_rho(1.0),
        render_duration=4.0,
        num_samples=1600,
    )

    omega0 = 1.25 * n_orbit
    state_low = circular_state(mu, r0, phi0, omega0, 0.2)
    scenarios["02_low_tidal_loading"] = Scenario(
        id="02_low_tidal_loading",
        title="02: Near-Circular Orbit, Low Tidal Loading",
        description="A circular reference orbit with a low rho target that keeps the shape pinched toward the action axis.",
        state0=state_low,
        t_max=2.4 * 2.0 * np.pi / n_orbit,
        mass=mass,
        R0=R0,
        mu=mu,
        rho_min=rho_min,
        rho_max=rho_max,
        rho_tau=180.0,
        alpha_fixed=0.0,
        alpha_offset=alpha_offset,
        alpha_law=orbital_alpha,
        rho_law=fixed_rho(0.2),
        render_duration=4.0,
        num_samples=1600,
    )

    state_high = circular_state(mu, r0, phi0, omega0, 1.5)
    scenarios["03_high_tidal_loading"] = Scenario(
        id="03_high_tidal_loading",
        title="03: Near-Circular Orbit, High Tidal Loading",
        description="The same circular orbit as the low-loading case, but with rho pushed upward so the spin and tidal response differ visibly.",
        state0=state_high,
        t_max=2.4 * 2.0 * np.pi / n_orbit,
        mass=mass,
        R0=R0,
        mu=mu,
        rho_min=rho_min,
        rho_max=rho_max,
        rho_tau=180.0,
        alpha_fixed=0.0,
        alpha_offset=alpha_offset,
        alpha_law=orbital_alpha,
        rho_law=fixed_rho(1.5),
        render_duration=4.0,
        num_samples=1600,
    )

    rp = 7.0e6
    e = 0.28
    n_perigee = np.sqrt(mu * (1.0 + e) / rp**3)
    omega0 = 1.4 * n_perigee
    pump_t_max = 5.0 * 2.0 * np.pi * np.sqrt((rp / (1.0 - e))**3 / mu)
    state_up = perigee_state(mu, rp, e, phi0, omega0, 0.2)
    scenarios["04_orbital_pumping_up"] = Scenario(
        id="04_orbital_pumping_up",
        title="04: Orbital Pumping Up",
        description="The rho schedule ramps from low to high while the craft flies an eccentric orbit, producing a smoother time-driven pumping pattern.",
        state0=state_up,
        t_max=pump_t_max,
        mass=mass,
        R0=R0,
        mu=mu,
        rho_min=rho_min,
        rho_max=rho_max,
        rho_tau=240.0,
        alpha_fixed=0.0,
        alpha_offset=alpha_offset,
        alpha_law=orbital_alpha,
        rho_law=ramp_rho(0.2, 1.5, pump_t_max),
        render_duration=8.0,
        num_samples=2200,
    )

    state_down = perigee_state(mu, rp, e, phi0, omega0, 1.5)
    scenarios["05_orbital_pumping_down"] = Scenario(
        id="05_orbital_pumping_down",
        title="05: Orbital Pumping Down",
        description="The same eccentric orbit and the opposite rho schedule, showing the time-reversed orbital pumping case.",
        state0=state_down,
        t_max=pump_t_max,
        mass=mass,
        R0=R0,
        mu=mu,
        rho_min=rho_min,
        rho_max=rho_max,
        rho_tau=240.0,
        alpha_fixed=0.0,
        alpha_offset=alpha_offset,
        alpha_law=orbital_alpha,
        rho_law=ramp_rho(1.5, 0.2, pump_t_max),
        render_duration=8.0,
        num_samples=2200,
    )

    eccentric_up_state = perigee_state(mu, rp, e, phi0, omega0, 0.2)
    scenarios["06_eccentricity_pumping_down"] = Scenario(
        id="06_eccentricity_pumping_down",
        title="06: Eccentricity Pumping Down",
        description="Aperigee-to-perigee pumping that switches the rho target on the sign of radial velocity, so the control changes across the outbound and inbound halves of each orbit.",
        state0=eccentric_up_state,
        t_max=pump_t_max,
        mass=mass,
        R0=R0,
        mu=mu,
        rho_min=rho_min,
        rho_max=rho_max,
        rho_tau=180.0,
        alpha_fixed=0.0,
        alpha_offset=alpha_offset,
        alpha_law=orbital_alpha,
        rho_law=apsis_rho(0.2, 1.5, reverse=False),
        render_duration=8.0,
        num_samples=2200,
    )

    eccentric_down_state = perigee_state(mu, rp, e, phi0, omega0, 1.5)
    scenarios["07_eccentricity_pumping_up"] = Scenario(
        id="07_eccentricity_pumping_up",
        title="07: Eccentricity Pumping Up",
        description="The sign-reversed partner to the previous case. It uses the same apsis switch but flips which branch is active on the outbound and inbound legs.",
        state0=eccentric_down_state,
        t_max=pump_t_max,
        mass=mass,
        R0=R0,
        mu=mu,
        rho_min=rho_min,
        rho_max=rho_max,
        rho_tau=180.0,
        alpha_fixed=0.0,
        alpha_offset=alpha_offset,
        alpha_law=orbital_alpha,
        rho_law=apsis_rho(0.2, 1.5, reverse=True),
        render_duration=8.0,
        num_samples=2200,
    )

    return scenarios
