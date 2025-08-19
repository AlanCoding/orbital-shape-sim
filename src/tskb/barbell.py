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
    """Physical dual barbell model with variable tether length.

    The class currently stores only bulk properties required by the
    dynamics and exposes a simple length-limits check used by tests or
    higher level code.  Mass is the total mass of both endpoint masses
    combined.
    """

    def __init__(
        self,
        mass: float,
        min_length: float = 0.0,
        max_length: float | None = None,
    ) -> None:
        self.mass = mass
        self.min_length = float(min_length)
        self.max_length = None if max_length is None else float(max_length)

    def tension_ok(self, length: float) -> bool:
        """Return ``True`` if ``length`` lies within allowed limits."""

        if length < self.min_length:
            return False
        if self.max_length is not None and length > self.max_length:
            return False
        return True
