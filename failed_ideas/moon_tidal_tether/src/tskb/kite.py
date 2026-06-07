from __future__ import annotations

import numpy as np


class Kite:
    """Placeholder four-point connected structure."""

    def __init__(self, mass: float) -> None:
        self.mass = mass

    def dynamics(self, t: float, y: np.ndarray, env, ctrl) -> np.ndarray:
        """State derivative for the kite structure.

        The implementation is pending; this stub allows controllers and the
        integrator to recognize the type.
        """

        raise NotImplementedError("Kite dynamics not yet implemented")
