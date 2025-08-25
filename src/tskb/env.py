"""Environment and gravity model for Earth-Moon system."""

from __future__ import annotations

import numpy as np

MU_EARTH = 3.986004418e14  # m^3/s^2
MU_MOON = 4.9048695e12
R_EARTH = 6378e3  # m
R_MOON = 384400e3  # m
N_MOON = 2 * np.pi / (27.321661 * 86400.0)


class Environment:
    """Gravitational environment with Earth central and lunar tide."""

    def __init__(self) -> None:
        self.mu_earth = MU_EARTH
        self.mu_moon = MU_MOON
        self.r_earth = R_EARTH
        self.r_moon = R_MOON
        self.n_moon = N_MOON

    def moon_position(self, t: float) -> np.ndarray:
        """Return Moon position in an Earth-centered inertial frame."""
        phase = self.n_moon * t
        return self.r_moon * np.array([np.cos(phase), np.sin(phase), 0.0])

    def a_earth(self, r: np.ndarray) -> np.ndarray:
        """Point-mass acceleration from Earth."""
        d = np.linalg.norm(r)
        return -self.mu_earth * r / d**3

    def a_moon_tide(self, r: np.ndarray, t: float) -> np.ndarray:
        """Tidal acceleration from the Moon."""
        Rm = self.moon_position(t)
        dr = r - Rm
        d = np.linalg.norm(dr)
        term1 = -self.mu_moon * dr / d**3
        term2 = self.mu_moon * Rm / np.linalg.norm(Rm) ** 3
        return term1 + term2

    def _third_deriv_point_mass(self, r: np.ndarray, mu: float) -> np.ndarray:
        x, y, z = r
        r2 = np.dot(r, r)
        r5 = r2 ** 2.5
        r7 = r5 * r2
        J = np.zeros((3, 3, 3))
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    delta_ij = 1.0 if i == j else 0.0
                    delta_ik = 1.0 if i == k else 0.0
                    delta_jk = 1.0 if j == k else 0.0
                    term = (
                        15 * r[i] * r[j] * r[k] / r7
                        - 3 * (
                            delta_ij * r[k]
                            + delta_ik * r[j]
                            + delta_jk * r[i]
                        )
                        / r5
                    )
                    J[i, j, k] = mu * term
        return J

    def tidal_jet_third_deriv(self, r: np.ndarray, t: float) -> np.ndarray:
        """Return ∂³Φ/∂x_i∂x_j∂x_k for Earth and Moon."""
        J_earth = self._third_deriv_point_mass(r, self.mu_earth)
        Rm = self.moon_position(t)
        dr = r - Rm
        J_moon = self._third_deriv_point_mass(dr, self.mu_moon)
        return J_earth + J_moon
