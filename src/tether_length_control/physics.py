"""
Physics for tether-length control experiments.
"""

from __future__ import annotations

import numpy as np


def gravity_accel(r: np.ndarray, mu: float) -> np.ndarray:
    """
    Central gravity acceleration.
    """
    r_mag = np.linalg.norm(r)
    if r_mag == 0.0:
        return np.zeros_like(r)
    return -mu * r / (r_mag**3)


def cross2(a: np.ndarray, b: np.ndarray) -> float:
    """
    2D scalar cross product.
    """
    return float(a[0] * b[1] - a[1] * b[0])


def _geometry(state: np.ndarray, m1: float, m2: float, length: float):
    x, y, vx, vy, phi, H = state
    R = np.array([x, y], dtype=float)
    u = np.array([np.cos(phi), np.sin(phi)], dtype=float)
    u_perp = np.array([-np.sin(phi), np.cos(phi)], dtype=float)
    total_mass = m1 + m2
    a = length * m2 / total_mass
    b = length * m1 / total_mass
    return R, u, u_perp, a, b, total_mass


def endpoint_positions(state: np.ndarray, m1: float, m2: float, length: float) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute inertial coordinates of the endpoint masses.
    """
    R, u, u_perp, a, b, total_mass = _geometry(state, m1, m2, length)
    r1 = R - a * u
    r2 = R + b * u
    return r1, r2


def endpoint_velocities(
    state: np.ndarray,
    m1: float,
    m2: float,
    length: float,
    omega: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute inertial velocities of the endpoint masses.
    """
    x, y, vx, vy, phi, H = state
    R = np.array([x, y], dtype=float)
    V = np.array([vx, vy], dtype=float)
    u_perp = np.array([-np.sin(phi), np.cos(phi)], dtype=float)
    total_mass = m1 + m2
    a = length * m2 / total_mass
    b = length * m1 / total_mass
    v1 = V - a * omega * u_perp
    v2 = V + b * omega * u_perp
    return v1, v2


def inertia_from_length(m1: float, m2: float, length: float) -> float:
    total_mass = m1 + m2
    return (m1 * m2 / total_mass) * (length**2)


def orbital_elements(R: np.ndarray, V: np.ndarray, mu: float) -> dict[str, float]:
    r = float(np.linalg.norm(R))
    v2 = float(np.dot(V, V))
    energy = 0.5 * v2 - mu / r
    a = np.inf if energy >= 0 else -mu / (2.0 * energy)
    e_vec = ((v2 - mu / r) * R - float(np.dot(R, V)) * V) / mu
    e = float(np.linalg.norm(e_vec))
    theta = float(np.arctan2(R[1], R[0]))
    return {
        "r": r,
        "energy": energy,
        "semi_major_axis": a,
        "eccentricity": e,
        "theta": theta,
    }


def tether_derivatives(t: float, state: np.ndarray, scenario) -> list[float]:
    """
    State derivative for tether-length control.

    State = [x, y, vx, vy, phi, H]
    where H is the scalar angular momentum about the CM.
    """
    x, y, vx, vy, phi, H = state
    length = scenario.length_law(t, state, scenario)
    R, u, u_perp, a, b, total_mass = _geometry(state, scenario.m1, scenario.m2, length)
    V = np.array([vx, vy], dtype=float)

    r1 = R - a * u
    r2 = R + b * u
    g1 = gravity_accel(r1, scenario.mu)
    g2 = gravity_accel(r2, scenario.mu)

    # CM acceleration from the endpoint gravity.
    A = (scenario.m1 * g1 + scenario.m2 * g2) / total_mass

    # External tidal torque about the CM.
    tau = scenario.m1 * cross2(r1 - R, g1) + scenario.m2 * cross2(r2 - R, g2)

    I = inertia_from_length(scenario.m1, scenario.m2, length)
    omega = H / I if I > 0.0 else 0.0

    return [
        vx,
        vy,
        float(A[0]),
        float(A[1]),
        omega,
        tau,
    ]


def get_diagnostics(t: float, state: np.ndarray, scenario) -> dict[str, float]:
    x, y, vx, vy, phi, H = state
    R = np.array([x, y], dtype=float)
    V = np.array([vx, vy], dtype=float)
    length = scenario.length_law(t, state, scenario)
    I = inertia_from_length(scenario.m1, scenario.m2, length)
    omega = H / I if I > 0.0 else 0.0
    orbit = orbital_elements(R, V, scenario.mu)
    theta = orbit["theta"]
    psi = phi - theta
    psi_wrapped = wrap_to_pi(psi)
    return {
        "r": orbit["r"],
        "theta": theta,
        "psi": psi,
        "psi_wrapped": psi_wrapped,
        "length": length,
        "omega": omega,
        "H": H,
        "energy": orbit["energy"],
        "semi_major_axis": orbit["semi_major_axis"],
        "eccentricity": orbit["eccentricity"],
    }


def wrap_to_pi(angle: float) -> float:
    return (angle + np.pi) % (2.0 * np.pi) - np.pi
