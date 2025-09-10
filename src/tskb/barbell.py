"""Barbell geometry and quadrupole mapping."""

from __future__ import annotations

import numpy as np


def Q_of_barbell(mass: float, length: float, u: np.ndarray) -> np.ndarray:
    """Quadrupole tensor for a single barbell.

    Parameters
    ----------
    mass : float
        Total mass of the barbell (two equal masses).
    length : float
        End-to-end separation of the barbell.
    u : np.ndarray
        Unit vector along the barbell axis.
    """

    u = np.asarray(u, dtype=float)
    u = u / np.linalg.norm(u)
    factor = mass * (length ** 2) / 4.0
    return factor * (3.0 * np.outer(u, u) - np.eye(3))


class DualBarbell:
    """Physical dual barbell model with variable tether length."""

    def __init__(
        self,
        mass: float,
        min_length: float = 1.0,
        max_length: float | None = None,
    ) -> None:
        self.mass = mass
        # ``min_length`` defaults to 1 m to avoid singular inertia when the
        # tether collapses.  Simulations may override this if desired.
        self.min_length = float(min_length)
        self.max_length = None if max_length is None else float(max_length)

    def tension_ok(self, length: float) -> bool:
        """Return ``True`` if ``length`` lies within allowed limits."""

        if length < self.min_length:
            return False
        if self.max_length is not None and length > self.max_length:
            return False
        return True

    # ------------------------------------------------------------------
    def dynamics(self, t: float, y: np.ndarray, env, ctrl) -> np.ndarray:
        """Return time derivative of the state vector.

        State vector ``y`` comprises ``[r(3), v(3), theta, omega, L, Ldot]``
        where ``theta`` is the barbell orientation angle in the orbital plane,
        ``omega`` its angular rate, ``L`` the end-to-end length and ``Ldot`` its
        time derivative.
        """

        if not np.isfinite(y).all():
            raise RuntimeError("non-finite state in dynamics")

        r = y[0:3]
        v = y[3:6]
        theta = y[6]
        omega = y[7]
        L = y[8]
        Ldot = y[9]

        # Apply a floor to the tether length to avoid singular inertia.  If the
        # barbell has retracted to this minimum, stop any further contraction.
        if L <= self.min_length and Ldot <= 0.0:
            L = self.min_length
            Ldot = 0.0

        u_vec = np.array([np.cos(theta), np.sin(theta), 0.0])
        L_eff = max(L, self.min_length)

        # Positions of the endpoint masses
        r1 = r + 0.5 * L_eff * u_vec
        r2 = r - 0.5 * L_eff * u_vec

        # Gravitational accelerations at each mass
        a1 = env.a_earth(r1) + env.a_moon_tide(r1, t)
        a2 = env.a_earth(r2) + env.a_moon_tide(r2, t)

        # Control input: tether length acceleration
        L_ddot = ctrl.action(t, y, env)
        if L <= self.min_length and L_ddot < 0.0:
            L_ddot = 0.0

        # Internal accelerations to realize commanded length change
        a1 += 0.5 * L_ddot * u_vec
        a2 -= 0.5 * L_ddot * u_vec

        # Center-of-mass acceleration
        a_com = 0.5 * (a1 + a2)

        # Gravitational torque about COM (z-component)
        F1 = 0.5 * self.mass * a1
        F2 = 0.5 * self.mass * a2
        tau_vec = 0.5 * L_eff * np.cross(u_vec, F1 - F2)
        tau = tau_vec[2]

        inertia = self.mass * L_eff**2 / 4.0
        inertia_dot = self.mass * L_eff * Ldot / 2.0
        omega_dot = (tau - inertia_dot * omega) / inertia

        theta_dot = omega
        return np.hstack([v, a_com, theta_dot, omega_dot, Ldot, L_ddot])

