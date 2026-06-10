from __future__ import annotations

import numpy as np

from .controllers import controller
from .geometry import moment_of_inertia, solve_geometry

G = 6.67430e-11


def gravity_accel(r: np.ndarray, mu: float, center: np.ndarray) -> np.ndarray:
    rel = r - center
    rel_norm = float(np.linalg.norm(rel))
    if rel_norm == 0.0:
        return np.zeros_like(rel)
    return -mu * rel / (rel_norm**3)


def rotating_frame_terms(r: np.ndarray, v: np.ndarray, omega: float) -> np.ndarray:
    """Centrifugal plus Coriolis terms in the Earth-Moon rotating frame."""
    x, y = float(r[0]), float(r[1])
    vx, vy = float(v[0]), float(v[1])
    coriolis = np.array([2.0 * omega * vy, -2.0 * omega * vx], dtype=float)
    centrifugal = np.array([omega**2 * x, omega**2 * y], dtype=float)
    return coriolis + centrifugal


def mass_points(state: np.ndarray, body_points: np.ndarray) -> np.ndarray:
    center = np.array(state[0:2], dtype=float)
    return center + body_points


def derivatives(t: float, state: np.ndarray, scenario, body_points=None) -> np.ndarray:
    x, y, vx, vy, rho_act = state
    rho_cmd = controller(t, state, scenario)
    if body_points is None:
        body_points = solve_geometry(rho_act, scenario)

    positions = mass_points(state, body_points)
    v = np.array([vx, vy], dtype=float)
    a_all = []
    for p in positions:
        a = gravity_accel(p, scenario.mu_earth, scenario.earth_pos)
        a += gravity_accel(p, scenario.mu_moon, scenario.moon_pos)
        a += rotating_frame_terms(p, v, scenario.omega)
        a_all.append(a)
    a_cm = np.mean(np.array(a_all, dtype=float), axis=0)
    drho = (rho_cmd - rho_act) / scenario.rho_tau
    return np.array([vx, vy, a_cm[0], a_cm[1], drho], dtype=float)


def diagnostics(t: float, state: np.ndarray, scenario, body_points=None) -> dict[str, float]:
    x, y, vx, vy, rho_act = state
    rho_cmd = controller(t, state, scenario)
    if body_points is None:
        body_points = solve_geometry(rho_act, scenario)
    positions = mass_points(state, body_points)
    center = np.array([x, y], dtype=float)
    x_rel = float(x - scenario.l1_x)
    y_rel = float(y)
    r_cm = float(np.linalg.norm(center))
    r_l1 = float(np.linalg.norm(center - np.array([scenario.l1_x, 0.0], dtype=float)))
    mass_per_corner = scenario.mass_total / 4.0
    inertia = moment_of_inertia(body_points, mass_per_corner)
    a_all = []
    for p in positions:
        a = gravity_accel(p, scenario.mu_earth, scenario.earth_pos)
        a += gravity_accel(p, scenario.mu_moon, scenario.moon_pos)
        a += rotating_frame_terms(p, np.array([vx, vy], dtype=float), scenario.omega)
        a_all.append(a)
    a_cm = np.mean(np.array(a_all, dtype=float), axis=0)
    return {
        "x_rel": x_rel,
        "y_rel": y_rel,
        "r_cm": r_cm,
        "r_l1": r_l1,
        "rho_act": float(rho_act),
        "rho_cmd": float(rho_cmd),
        "vx": float(vx),
        "vy": float(vy),
        "ax": float(a_cm[0]),
        "ay": float(a_cm[1]),
        "inertia": inertia,
    }

