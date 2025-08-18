"""Simple periapsis/apapsis bang-bang controller."""

from __future__ import annotations

import numpy as np


class BangBangController:
    """Selects quadrupole magnitude based on true anomaly."""

    def __init__(self, cfg: dict) -> None:
        # Values may come in as strings from YAML; cast explicitly.
        self.q_plus_scale = float(cfg["q_plus_scale"])
        self.q_minus_scale = float(cfg["q_minus_scale"])
        self.delta_phase = np.deg2rad(cfg.get("delta_phase_deg", 0.0))
        self.nu_window = np.deg2rad(cfg.get("nu_window_deg", 10.0))

    def select_q(self, nu: float) -> float | None:
        """Return commanded q scale or ``None`` to hold."""
        nu = np.arctan2(
            np.sin(nu + self.delta_phase), np.cos(nu + self.delta_phase)
        )
        if abs(nu - np.pi) < self.nu_window:
            return self.q_plus_scale
        if abs(nu) < self.nu_window:
            return self.q_minus_scale
        return None
