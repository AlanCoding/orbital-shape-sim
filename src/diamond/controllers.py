from __future__ import annotations

import numpy as np


def wrap_to_pi(angle: float) -> float:
    return float((angle + np.pi) % (2.0 * np.pi) - np.pi)


def controller(t: float, state: np.ndarray, scenario) -> tuple[float, float]:
    """Return the commanded action angle and rho target."""
    x, y, vx, vy, phi, omega, rho_act = state
    if scenario.mu > 0.0:
        theta = float(np.arctan2(y, x))
        alpha_cmd = wrap_to_pi(theta - phi + scenario.alpha_offset)
    else:
        alpha_cmd = float(scenario.alpha_fixed)
    rho_cmd = float(scenario.rho_law(t, state, scenario))
    return alpha_cmd, rho_cmd

