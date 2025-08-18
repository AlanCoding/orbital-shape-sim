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
    """Simplified dual counter-rotating barbell model."""

    def __init__(self, mass: float) -> None:
        self.mass = mass
        self.q_scale = 0.0

    def update(self, q_scale: float | None) -> None:
        """Update quadrupole magnitude if a new command is provided."""
        if q_scale is not None:
            self.q_scale = q_scale

    def Q(self, r_hat: np.ndarray) -> np.ndarray:
        """Current quadrupole tensor aligned with ``r_hat``."""
        r_hat = r_hat / np.linalg.norm(r_hat)
        return self.q_scale * (3.0 * np.outer(r_hat, r_hat) - np.eye(3))

    def tension_ok(self) -> bool:
        """Placeholder tension constraint: require non-negative ``q_scale``."""
        return self.q_scale >= 0.0
