#!/usr/bin/env python3
"""Generate torque and tangential acceleration samples.

This script sweeps over barbell orientation ``theta`` and the
Moon-phase angle ``phi`` (angle between the Moon and the barbell
center-of-mass as seen from Earth).  For each combination it computes

* the gravitational torque about ``+z`` on the barbell, and
* the center-of-mass acceleration component along the orbital direction.

The calculation uses the state derivative function without integrating
the trajectory.
"""
from __future__ import annotations

import numpy as np
from pathlib import Path
import sys

# Allow running without installing the package
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from tskb.barbell import DualBarbell
from tskb.controller import PassiveController
from tskb.env import Environment


def torque_and_tan_accel(t: float, state: np.ndarray, env: Environment, craft: DualBarbell) -> tuple[float, float]:
    """Return (torque_z, tangential_acceleration)."""
    r = state[0:3]
    theta = state[6]
    L = state[8]

    u_vec = np.array([np.cos(theta), np.sin(theta), 0.0])
    L_eff = max(L, craft.min_length)

    r1 = r + 0.5 * L_eff * u_vec
    r2 = r - 0.5 * L_eff * u_vec

    a1 = env.a_earth(r1) + env.a_moon_tide(r1, t)
    a2 = env.a_earth(r2) + env.a_moon_tide(r2, t)

    a_com = 0.5 * (a1 + a2)

    F1 = 0.5 * craft.mass * a1
    F2 = 0.5 * craft.mass * a2
    tau = 0.5 * L_eff * np.cross(u_vec, F1 - F2)[2]

    r_hat = r / np.linalg.norm(r)
    z_hat = np.array([0.0, 0.0, 1.0])
    tan_hat = np.cross(z_hat, r_hat)
    a_tan = float(np.dot(a_com, tan_hat))

    return float(tau), a_tan


def main() -> None:
    env = Environment()
    craft = DualBarbell(mass=1000.0, min_length=1.0)
    ctrl = PassiveController()

    alt = 100e3  # 100 km altitude
    r_mag = env.r_earth + alt
    r = np.array([r_mag, 0.0, 0.0])
    v_circ = np.sqrt(env.mu_earth / r_mag)
    v = np.array([0.0, v_circ, 0.0])
    omega = 0.0
    L = 1000.0
    Ldot = 0.0

    phi_vals = np.deg2rad(np.arange(0, 360, 60))
    theta_vals = np.deg2rad(np.arange(0, 360, 90))

    print(f"{'phi_deg':>7} {'theta_deg':>9} {'torque_Nm':>12} {'tan_acc_mps2':>14}")
    for phi in phi_vals:
        t = phi / env.n_moon
        for theta in theta_vals:
            state = np.hstack([r, v, theta, omega, L, Ldot])
            tau, a_tan = torque_and_tan_accel(t, state, env, craft)
            print(f"{np.rad2deg(phi):7.1f} {np.rad2deg(theta):9.1f} {tau:12.3e} {a_tan:14.3e}")


if __name__ == "__main__":
    main()
