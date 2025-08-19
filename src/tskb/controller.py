"""Controller interfaces and simple implementations."""

from __future__ import annotations

import numpy as np


class Controller:
    """Abstract controller interface."""

    def action(self, t: float, state: np.ndarray) -> float:
        """Return tether length acceleration ``L_ddot``.

        Subclasses should override this method.  The returned value
        represents the commanded second derivative of the barbell length.
        """

        raise NotImplementedError


class BangBangController(Controller):
    """Periapsis/apapsis bang-bang tether controller."""

    def __init__(self, cfg: dict) -> None:
        # Values may come in as strings from YAML; cast explicitly.
        self.extend_accel = float(cfg["extend_accel"])
        self.retract_accel = float(cfg["retract_accel"])
        self.delta_phase = np.deg2rad(cfg.get("delta_phase_deg", 0.0))
        self.nu_window = np.deg2rad(cfg.get("nu_window_deg", 10.0))

    def action(self, t: float, state: np.ndarray) -> float:
        """Return commanded tether acceleration ``L_ddot``."""
        def angdiff(a: float, b: float) -> float:
            d = a - b
            return (d + np.pi) % (2 * np.pi) - np.pi

        r = state[0:3]
        nu = np.arctan2(r[1], r[0])
        nu = np.arctan2(np.sin(nu + self.delta_phase), np.cos(nu + self.delta_phase))

        if abs(angdiff(nu, np.pi)) < self.nu_window:
            return self.extend_accel
        if abs(angdiff(nu, 0.0)) < self.nu_window:
            return -self.retract_accel
        return 0.0
