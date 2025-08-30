"""Integration helpers."""

from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp

from .dynamics import f_state


class SimulationError(RuntimeError):
    """Exception carrying a partial log when simulation fails."""

    def __init__(self, message: str, log: dict) -> None:
        super().__init__(message)
        self.log = log


class TetherTooShortError(SimulationError):
    """Raised when the tether length drops below the safety threshold."""


class SpinReversalError(SimulationError):
    """Raised when the barbell reverses its spin direction."""


def run_simulation(env, craft, ctrl, cfg: dict) -> dict:
    """Run a simulation and return a log dictionary."""

    t_final = cfg["integrator"]["t_final"]
    dt = cfg["integrator"]["dt_output"]
    alt = cfg["altitude_m"]

    r0_mag = env.r_earth + alt
    v0_mag = np.sqrt(env.mu_earth / r0_mag)
    n0 = np.sqrt(env.mu_earth / r0_mag**3)
    n_syn = n0 - env.n_moon

    # Initial orientation/length state
    theta0 = cfg.get("theta0", 0.0)
    omega_cfg = cfg.get("omega0", "tidally_locked")
    if isinstance(omega_cfg, str):
        modes = {
            "tidally_locked": n0,
            "no_rotation": 0.0,
            "prograde": n0 + n_syn,
            "retrograde": n0 - n_syn,
            "fast_prograde": 5.0 * (n0 + n_syn),
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

    if not np.isfinite(sol.y).all():
        raise RuntimeError("non-finite state encountered during integration")

    r = sol.y[0:3, :].T
    v = sol.y[3:6, :].T
    theta = sol.y[6, :]
    omega = sol.y[7, :]
    length = sol.y[8, :]
    length_rate = sol.y[9, :]

    accel = np.zeros_like(sol.t)
    power_control = np.zeros_like(sol.t)
    for i, (t, L, Ldot) in enumerate(zip(sol.t, length, length_rate)):
        state = sol.y[:, i]
        L_ddot = ctrl.action(t, state, env)
        accel[i] = L_ddot
        power_control[i] = craft.mass * L_ddot * Ldot / 4.0

    log = {
        "t": sol.t,
        "r": r,
        "v": v,
        "theta": theta,
        "omega": omega,
        "length": length,
        "length_rate": length_rate,
        "accel": accel,
        "power_control": power_control,
    }

    r_mag = np.linalg.norm(r, axis=1)

    # Gather potential failure events
    events: list[tuple[str, float, int]] = []
    if np.min(r_mag) < env.r_earth:
        i_hit = int(np.argmin(r_mag))
        events.append(("earth", sol.t[i_hit], i_hit))

    min_length = 10_000.0
    below = np.where(length < min_length)[0]
    if length[0] > min_length and below.size:
        i_short = int(below[0])
        events.append(("short", sol.t[i_short], i_short))

    sign0 = np.sign(omega[0])
    if sign0 != 0.0:
        rev = np.where(omega[1:] * sign0 < 0.0)[0]
        if rev.size:
            i_rev = int(rev[0] + 1)
            events.append(("spin", sol.t[i_rev], i_rev))

    if events:
        kind, t_evt, idx = min(events, key=lambda e: e[1])
        for k, v_arr in log.items():
            log[k] = v_arr[: idx + 1]
        if kind == "earth":
            alt = r_mag[idx] - env.r_earth
            raise SimulationError(
                f"simulation crashed into Earth at t={t_evt:.3f}s, altitude={alt:.1f} m",
                log,
            )
        if kind == "short":
            log["length"][-1] = min_length
            log["length_rate"][-1] = 0.0
            raise TetherTooShortError(
                f"tether length dropped below 10 km at t={t_evt:.3f}s",
                log,
            )
        raise SpinReversalError(
            f"angular velocity reversed sign at t={t_evt:.3f}s",
            log,
        )

    return log
