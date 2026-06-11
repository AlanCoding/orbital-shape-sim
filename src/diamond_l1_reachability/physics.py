from __future__ import annotations

import numpy as np

from diamond_l1.physics import G, gravity_accel, rotating_frame_terms


def derivatives(t: float, state: np.ndarray, scenario) -> np.ndarray:
    x, y, vx, vy = state
    r = np.array([x, y], dtype=float)
    v = np.array([vx, vy], dtype=float)
    a = gravity_accel(r, scenario.mu_earth, scenario.earth_pos)
    a += gravity_accel(r, scenario.mu_moon, scenario.moon_pos)
    a += rotating_frame_terms(r, v, scenario.omega)
    return np.array([vx, vy, a[0], a[1]], dtype=float)

