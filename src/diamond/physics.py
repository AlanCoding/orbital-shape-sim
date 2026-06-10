from __future__ import annotations

import numpy as np

from .controllers import controller, wrap_to_pi
from .geometry import body_to_inertial, inertia_from_body_points, solve_geometry


def gravity_accel(r: np.ndarray, mu: float) -> np.ndarray:
    r_mag = float(np.linalg.norm(r))
    if r_mag == 0.0 or mu == 0.0:
        return np.zeros_like(r)
    return -mu * r / (r_mag**3)


def cross2(a: np.ndarray, b: np.ndarray) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


def _body_and_inertial_points(t: float, state: np.ndarray, scenario, body_points=None):
    alpha_cmd, rho_cmd = controller(t, state, scenario)
    rho_act = float(state[6])
    if body_points is None:
        body_points = solve_geometry(alpha_cmd, rho_act, scenario)
    center = np.array(state[0:2], dtype=float)
    inertial_points = body_to_inertial(body_points, float(state[4]), center)
    return alpha_cmd, rho_cmd, body_points, inertial_points


def derivatives(t: float, state: np.ndarray, scenario, body_points=None) -> np.ndarray:
    x, y, vx, vy, phi, omega, rho_act = state
    alpha_cmd, rho_cmd, body_points, inertial_points = _body_and_inertial_points(
        t, state, scenario, body_points=body_points
    )
    center = np.array([x, y], dtype=float)
    velocities = np.array([vx, vy], dtype=float)

    masses = np.full(4, scenario.mass / 4.0, dtype=float)
    g_all = np.array([gravity_accel(pt, scenario.mu) for pt in inertial_points], dtype=float)
    acc_cm = np.sum(g_all * masses[:, None], axis=0) / scenario.mass
    torques = np.array([cross2(pt - center, g) for pt, g in zip(inertial_points, g_all)], dtype=float)
    tau = float(np.sum(torques * masses))

    inertia = inertia_from_body_points(body_points, scenario.mass / 4.0)
    drho = (rho_cmd - rho_act) / scenario.rho_tau

    return np.array(
        [
            velocities[0],
            velocities[1],
            acc_cm[0],
            acc_cm[1],
            omega,
            tau / inertia,
            drho,
        ],
        dtype=float,
    )


def diagnostics(t: float, state: np.ndarray, scenario, body_points=None) -> dict[str, float]:
    x, y, vx, vy, phi, omega, rho_act = state
    alpha_cmd, rho_cmd, body_points, inertial_points = _body_and_inertial_points(
        t, state, scenario, body_points=body_points
    )
    masses = np.full(4, scenario.mass / 4.0, dtype=float)
    inertia = inertia_from_body_points(body_points, scenario.mass / 4.0)

    center = np.array([x, y], dtype=float)
    r = float(np.linalg.norm(center))
    theta = float(np.arctan2(y, x)) if r > 0.0 else 0.0
    psi = wrap_to_pi(phi - theta)
    rho_geom = float("nan")
    tidal_angle = float("nan")
    if scenario.mu > 0.0 and r > 0.0:
        g_hat = -center / r
        d = np.array([(pt - center) @ g_hat for pt in inertial_points], dtype=float)
        i_tidal = float(np.sum(masses * d**2))
        i_ref = scenario.mass * (scenario.R0**2)
        rho_geom = i_tidal / i_ref
        tidal_angle = float(np.arctan2(g_hat[1], g_hat[0]))

    tau = 0.0
    if scenario.mu > 0.0:
        g_all = np.array([gravity_accel(pt, scenario.mu) for pt in inertial_points], dtype=float)
        tau = float(np.sum(masses * np.array([cross2(pt - center, g) for pt, g in zip(inertial_points, g_all)])))

    return {
        "r": r,
        "theta": theta,
        "psi": psi,
        "omega": float(omega),
        "rho_act": float(rho_act),
        "rho_cmd": float(rho_cmd),
        "rho_geom": rho_geom,
        "alpha_cmd": float(alpha_cmd),
        "inertia": inertia,
        "tau": tau,
        "tidal_angle": tidal_angle,
    }

