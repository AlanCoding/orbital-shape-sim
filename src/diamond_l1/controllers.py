from __future__ import annotations

import numpy as np


def controller(t: float, state: np.ndarray, scenario) -> float:
    """Return the commanded rho value for the L1 diamond."""
    x, y, vx, vy, rho_act = state
    x_err = x - scenario.l1_x
    rho_cmd = scenario.rho_eq
    rho_cmd += scenario.rho_kp * (-x_err / scenario.half_span_m)
    rho_cmd += scenario.rho_kd * (-vx / scenario.v_scale)
    return float(np.clip(rho_cmd, scenario.rho_min, scenario.rho_max))

