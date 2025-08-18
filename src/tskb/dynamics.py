"""State derivative for the barbell spacecraft."""

from __future__ import annotations

import numpy as np

from .utils import contract_Q_J3


def f_state(t: float, y: np.ndarray, env, craft, ctrl) -> np.ndarray:
    """Return time derivative of the state vector."""
    r = y[0:3]
    v = y[3:6]
    nu = np.arctan2(r[1], r[0])
    q_cmd = ctrl.select_q(nu)
    craft.update(q_cmd)
    r_hat = r / np.linalg.norm(r)
    a = env.a_earth(r) + env.a_moon_tide(r, t)
    Q = craft.Q(r_hat)
    J3 = env.tidal_jet_third_deriv(r, t)
    a_Q = contract_Q_J3(Q, J3)
    return np.hstack([v, a + a_Q])
