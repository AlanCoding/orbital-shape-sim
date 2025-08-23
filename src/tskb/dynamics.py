"""State derivative for a barbell with variable tether length."""

from __future__ import annotations

import numpy as np


def f_state(t: float, y: np.ndarray, env, craft, ctrl) -> np.ndarray:
    """Return time derivative of the state vector.

    State vector ``y`` comprises

    ``[r(3), v(3), theta, omega, L, Ldot]`` where ``theta`` is the barbell
    orientation angle in the orbital plane (about ``+z``), ``omega`` is its
    angular rate, ``L`` the end-to-end length and ``Ldot`` its time
    derivative.
    """

    r = y[0:3]
    v = y[3:6]
    theta = y[6]
    omega = y[7]
    L = y[8]
    Ldot = y[9]

    # Apply a floor to the tether length to avoid singular inertia.  If the
    # barbell has retracted to this minimum, stop any further contraction.
    if L <= craft.min_length and Ldot <= 0.0:
        L = craft.min_length
        Ldot = 0.0

    u_vec = np.array([np.cos(theta), np.sin(theta), 0.0])
    L_eff = max(L, craft.min_length)

    # Positions of the endpoint masses
    r1 = r + 0.5 * L_eff * u_vec
    r2 = r - 0.5 * L_eff * u_vec

    # Gravitational accelerations at each mass
    a1 = env.a_earth(r1) + env.a_moon_tide(r1, t)
    a2 = env.a_earth(r2) + env.a_moon_tide(r2, t)

    # Control input: tether length acceleration (clipped by craft limits)
    L_ddot_cmd = ctrl.action(t, y)
    L_ddot = craft.clip_accel(L_ddot_cmd)
    if L <= craft.min_length and L_ddot < 0.0:
        L_ddot = 0.0

    # Internal accelerations to realize commanded length change
    a1 += 0.5 * L_ddot * u_vec
    a2 -= 0.5 * L_ddot * u_vec

    # Center-of-mass acceleration
    a_com = 0.5 * (a1 + a2)

    # Gravitational torque about COM (z-component)
    F1 = 0.5 * craft.mass * a1
    F2 = 0.5 * craft.mass * a2
    tau_vec = 0.5 * L_eff * np.cross(u_vec, F1 - F2)
    tau = tau_vec[2]

    inertia = craft.mass * L_eff**2 / 4.0
    inertia_dot = craft.mass * L_eff * Ldot / 2.0
    omega_dot = (tau - inertia_dot * omega) / inertia

    theta_dot = omega
    return np.hstack([v, a_com, theta_dot, omega_dot, Ldot, L_ddot])
