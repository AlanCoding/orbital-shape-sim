"""Integration helpers."""

from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp

from .dynamics import f_state


def run_simulation(env, craft, ctrl, cfg: dict) -> dict:
    """Run a simulation and return a log dictionary."""

    t_final = cfg["integrator"]["t_final"]
    dt = cfg["integrator"]["dt_output"]
    alt = cfg["altitude_m"]

    r0_mag = 6378e3 + alt
    v0_mag = np.sqrt(env.mu_earth / r0_mag)
    n0 = np.sqrt(env.mu_earth / r0_mag**3)

    # Initial orientation/length state
    theta0 = cfg.get("theta0", 0.0)
    omega_cfg = cfg.get("omega0", "tidally_locked")
    if isinstance(omega_cfg, str):
        modes = {
            "tidally_locked": n0,
            "no_rotation": 0.0,
            "prograde": 2.0 * n0,
            "retrograde": -1.0 * n0,
        }
        if omega_cfg not in modes:
            raise ValueError(f"unknown omega0 mode: {omega_cfg}")
        omega0 = modes[omega_cfg]
    else:
        omega0 = float(omega_cfg)
    L0 = cfg.get("length0", 1000.0)
    Ldot0 = cfg.get("length_rate0", 0.0)

    y0 = np.hstack(
        [
            np.array([r0_mag, 0.0, 0.0]),
            np.array([0.0, v0_mag, 0.0]),
            np.array([theta0, omega0, L0, Ldot0]),
        ]
    )

    t_eval = np.arange(0.0, t_final + dt, dt)

    sol = solve_ivp(
        lambda t, y: f_state(t, y, env, craft, ctrl),
        (0.0, t_final),
        y0,
        method="DOP853",
        rtol=1e-6,
        atol=1e-6,
        t_eval=t_eval,
    )

    if not sol.success:
        raise RuntimeError(sol.message)

    r = sol.y[0:3, :].T
    v = sol.y[3:6, :].T
    theta = sol.y[6, :]
    omega = sol.y[7, :]
    length = sol.y[8, :]
    length_rate = sol.y[9, :]

    power_control = np.zeros_like(sol.t)
    for i, (t, L, Ldot) in enumerate(zip(sol.t, length, length_rate)):
        state = sol.y[:, i]
        L_ddot = craft.clip_accel(ctrl.action(t, state))
        power_control[i] = craft.mass * L_ddot * Ldot / 4.0

    return {
        "t": sol.t,
        "r": r,
        "v": v,
        "theta": theta,
        "omega": omega,
        "length": length,
        "length_rate": length_rate,
        "power_control": power_control,
    }
