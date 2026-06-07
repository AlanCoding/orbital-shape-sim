from __future__ import annotations

import numpy as np

class PointMass:
    """Single-point mass spacecraft model."""

    def __init__(self, mass: float) -> None:
        self.mass = mass

    def dynamics(self, t: float, y: np.ndarray, env, ctrl) -> np.ndarray:
        """Return time derivative of the state vector ``y``.

        The state is ``[r(3), v(3)]`` and evolves under Earth gravity plus the
        lunar tidal acceleration. Controllers may still act on other craft
        types, but for a point mass the control input is ignored.
        """

        if not np.isfinite(y).all():
            raise RuntimeError("non-finite state in dynamics")

        r = y[0:3]
        v = y[3:6]
        a = env.a_earth(r) + env.a_moon_tide(r, t)
        return np.hstack([v, a])
