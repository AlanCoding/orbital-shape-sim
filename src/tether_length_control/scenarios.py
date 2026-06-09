"""
Scenario definitions for tether-length control experiments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .controllers import (
    make_fixed_length_law,
    make_perigee_apogee_length_law,
    make_quadrant_length_law,
)
from .physics import inertia_from_length


LengthLaw = Callable[[float, Any, Any], float]


@dataclass
class Scenario:
    id: str
    title: str
    m1: float
    m2: float
    state0: np.ndarray
    t_max: float
    description: str
    length_law: LengthLaw
    mu: float = 3.986004418e14
    show_velocity_arrows: bool = False
    short_length: float = 0.0
    long_length: float = 0.0
    switch_function: Callable[[float, np.ndarray, "Scenario"], float] | None = None
    branch_nudge: Callable[[np.ndarray, np.ndarray, "Scenario"], np.ndarray] | None = None
    integration_dt: float | None = None
    render_duration: float = 3.0


def circular_state_from_local_angle(
    mu: float,
    r0: float,
    psi: float,
    omega: float,
    length0: float,
    m1: float,
    m2: float,
) -> np.ndarray:
    """
    Build a circular-orbit initial condition using a target angular momentum.
    """
    theta = 0.0
    thetadot = np.sqrt(mu / r0**3)

    x = r0
    y = 0.0
    vx = 0.0
    vy = np.sqrt(mu / r0)

    phi = theta + psi
    I0 = inertia_from_length(m1, m2, length0)
    H = I0 * omega
    return np.array([x, y, vx, vy, phi, H], dtype=float)


def eccentric_state_from_perigee(
    mu: float,
    rp: float,
    e: float,
    psi: float,
    omega: float,
    length0: float,
    m1: float,
    m2: float,
) -> np.ndarray:
    vp = np.sqrt(mu * (1.0 + e) / rp)
    theta = 0.0
    x = rp
    y = 0.0
    vx = 0.0
    vy = vp
    phi = theta + psi
    I0 = inertia_from_length(m1, m2, length0)
    H = I0 * omega
    return np.array([x, y, vx, vy, phi, H], dtype=float)


def get_scenarios(mu: float = 3.986004418e14) -> dict[str, Scenario]:
    """
    Return the first-pass tether-length control scenarios.
    """
    scenarios: dict[str, Scenario] = {}

    r0 = 1.2e7
    rp = 1.05e7
    e = 0.45
    thetadot = np.sqrt(mu / r0**3)
    thetadot_p = np.sqrt(mu * (1.0 + e) / rp**3)

    short_length = 8.0e5
    long_length = 3.0e6
    mid_length = 1.2e6
    m1 = 1000.0
    m2 = 1000.0

    quadrant_phase_offset = 0.0
    quadrant_forward = make_quadrant_length_law(short_length, long_length, phase_offset=quadrant_phase_offset, reverse=False)
    quadrant_reverse = make_quadrant_length_law(short_length, long_length, phase_offset=quadrant_phase_offset, reverse=True)
    apsis_forward = make_perigee_apogee_length_law(short_length, long_length, reverse=False)
    apsis_reverse = make_perigee_apogee_length_law(short_length, long_length, reverse=True)
    fixed_mid = make_fixed_length_law(mid_length)

    def quadrant_switch(t: float, state: np.ndarray, scenario: Scenario) -> float:
        x, y, vx, vy, phi, H = state
        theta = np.arctan2(y, x)
        psi = (phi - theta - quadrant_phase_offset + np.pi) % (2.0 * np.pi) - np.pi
        return np.sin(2.0 * psi)

    def apsis_switch(t: float, state: np.ndarray, scenario: Scenario) -> float:
        x, y, vx, vy, phi, H = state
        r = np.hypot(x, y)
        return 0.0 if r == 0.0 else (x * vx + y * vy) / r

    def quadrant_nudge(state: np.ndarray, deriv: np.ndarray, scenario: Scenario) -> np.ndarray:
        y = np.array(state, dtype=float)
        x, pos_y, vx, vy, phi, H = y
        r2 = x * x + pos_y * pos_y
        theta_dot = 0.0 if r2 == 0.0 else (x * vy - pos_y * vx) / r2
        omega = float(deriv[4])
        psi_dot = omega - theta_dot
        delta = 1.0e-6 if psi_dot >= 0.0 else -1.0e-6
        y[4] = phi + delta
        return y

    def apsis_nudge(state: np.ndarray, deriv: np.ndarray, scenario: Scenario) -> np.ndarray:
        y = np.array(state, dtype=float)
        x, pos_y, vx, vy, phi, H = y
        r = np.hypot(x, pos_y)
        if r == 0.0:
            return y
        theta_dot = (x * vy - pos_y * vx) / (r * r)
        delta = 1.0e-6 if theta_dot >= 0.0 else -1.0e-6
        c = np.cos(delta)
        s = np.sin(delta)
        y[0] = c * x - s * pos_y
        y[1] = s * x + c * pos_y
        return y

    state_fixed = circular_state_from_local_angle(
        mu,
        r0,
        psi=np.radians(20.0),
        omega=1.4 * thetadot,
        length0=mid_length,
        m1=m1,
        m2=m2,
    )
    scenarios["01_fixed_length"] = Scenario(
        id="01_fixed_length",
        title="01: Fixed-Length Baseline",
        m1=m1,
        m2=m2,
        state0=state_fixed,
        t_max=2.4 * (2.0 * np.pi * np.sqrt(r0**3 / mu)),
        description="Circular-orbit reference with a constant tether length.",
        length_law=fixed_mid,
        short_length=mid_length,
        long_length=mid_length,
    )

    state_quadrant = circular_state_from_local_angle(
        mu,
        r0,
        psi=np.radians(25.0),
        omega=6.0 * thetadot,
        length0=long_length,
        m1=m1,
        m2=m2,
    )
    scenarios["02_quadrant_forward"] = Scenario(
        id="02_quadrant_forward",
        title="02: Quadrant Length Pumping (High-Spin Start)",
        m1=m1,
        m2=m2,
        state0=state_quadrant,
        t_max=2.4 * (2.0 * np.pi * np.sqrt(r0**3 / mu)),
        description="State-feedback length control that alternates extension and retraction across the four attitude quadrants, starting from a fast-spin state so the spin-down direction is visually clear.",
        length_law=quadrant_forward,
        short_length=short_length,
        long_length=long_length,
        switch_function=quadrant_switch,
        branch_nudge=quadrant_nudge,
    )

    state_quadrant_reverse = circular_state_from_local_angle(
        mu,
        r0,
        psi=np.radians(25.0),
        omega=1.8 * thetadot,
        length0=short_length,
        m1=m1,
        m2=m2,
    )
    scenarios["03_quadrant_reverse"] = Scenario(
        id="03_quadrant_reverse",
        title="03: Reversed Quadrant Pumping",
        m1=m1,
        m2=m2,
        state0=state_quadrant_reverse,
        t_max=2.4 * (2.0 * np.pi * np.sqrt(r0**3 / mu)),
        description="Same four-quadrant law with the long/short sign convention reversed.",
        length_law=quadrant_reverse,
        short_length=short_length,
        long_length=long_length,
        switch_function=quadrant_switch,
        branch_nudge=quadrant_nudge,
    )

    state_apsis = eccentric_state_from_perigee(
        mu,
        rp,
        e,
        psi=np.radians(20.0),
        omega=4.0 * thetadot_p,
        length0=long_length,
        m1=m1,
        m2=m2,
    )
    a = rp / (1.0 - e)
    t_orbit_e = 2.0 * np.pi * np.sqrt(a**3 / mu)
    eccentric_run = 5.0 * t_orbit_e
    eccentric_dt = (2.0 * t_orbit_e) / 1199.0
    scenarios["04_perigee_apogee_forward"] = Scenario(
        id="04_perigee_apogee_forward",
        title="04: Perigee/Apogee Pumping",
        m1=m1,
        m2=m2,
        state0=state_apsis,
        t_max=eccentric_run,
        description="Eccentric-orbit length control that changes length at the apses, run for multiple orbits so the higher-order pumping is easier to see.",
        length_law=apsis_forward,
        short_length=short_length,
        long_length=long_length,
        switch_function=apsis_switch,
        branch_nudge=apsis_nudge,
        integration_dt=eccentric_dt,
        render_duration=15.0,
    )

    state_apsis_reverse = eccentric_state_from_perigee(
        mu,
        rp,
        e,
        psi=np.radians(20.0),
        omega=8.0 * thetadot_p,
        length0=short_length,
        m1=m1,
        m2=m2,
    )
    scenarios["05_perigee_apogee_reverse"] = Scenario(
        id="05_perigee_apogee_reverse",
        title="05: Reversed Perigee/Apogee Pumping",
        m1=m1,
        m2=m2,
        state0=state_apsis_reverse,
        t_max=eccentric_run,
        description="Same eccentric-orbit schedule with the long/short phases swapped, run for multiple orbits so the higher-order pumping is easier to see.",
        length_law=apsis_reverse,
        short_length=short_length,
        long_length=long_length,
        switch_function=apsis_switch,
        branch_nudge=apsis_nudge,
        integration_dt=eccentric_dt,
        render_duration=15.0,
    )

    return scenarios
