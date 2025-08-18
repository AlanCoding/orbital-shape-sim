"""Integration helpers."""

from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp

from .dynamics import f_state
from .utils import contract_Q_J3


def run_simulation(env, craft, ctrl, cfg: dict) -> dict:
    """Run a simulation and return a log dictionary."""
    t_final = cfg["integrator"]["t_final"]
    dt = cfg["integrator"]["dt_output"]
    mass = cfg["mass"]
    alt = cfg["altitude_m"]
    r0_mag = 6378e3 + alt
    v0_mag = np.sqrt(env.mu_earth / r0_mag)
    y0 = np.hstack([
        np.array([r0_mag, 0.0, 0.0]),
        np.array([0.0, v0_mag, 0.0]),
    ])

    t_eval = np.arange(0.0, t_final + dt, dt)
    sol = solve_ivp(
        lambda t, y: f_state(t, y, env, craft, ctrl),
        (0.0, t_final),
        y0,
        method="DOP853",
        rtol=1e-9,
        atol=1e-9,
        t_eval=t_eval,
    )

    r = sol.y[0:3, :].T
    v = sol.y[3:6, :].T
    power_tide = np.zeros_like(sol.t)
    q_scale = 0.0
    for i, (t, ri, vi) in enumerate(zip(sol.t, r, v)):
        nu = np.arctan2(ri[1], ri[0])
        q_cmd = ctrl.select_q(nu)
        if q_cmd is not None:
            q_scale = q_cmd
        r_hat = ri / np.linalg.norm(ri)
        Q = q_scale * (3 * np.outer(r_hat, r_hat) - np.eye(3))
        Rm = env.moon_position(t)
        J_moon = env._third_deriv_point_mass(ri - Rm, env.mu_moon)
        a_Q_moon = contract_Q_J3(Q, J_moon)
        power_tide[i] = np.dot(vi, a_Q_moon)

    return {"t": sol.t, "r": r, "v": v, "power_tide": power_tide}
