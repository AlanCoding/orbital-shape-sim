"""Checks that the default 100 km setup is dynamically balanced."""

import numpy as np

from tskb.env import Environment
from tskb.barbell import DualBarbell


class _ZeroCtrl:
    def action(self, t, y, env):  # pragma: no cover - simple stub
        return 0.0


def test_leo_100km_initial_balance():
    env = Environment()
    craft = DualBarbell(1000.0)
    ctrl = _ZeroCtrl()

    alt = 100_000.0
    r0 = 6378e3 + alt
    v0 = np.sqrt(env.mu_earth / r0)
    n0 = np.sqrt(env.mu_earth / r0**3)

    # state: r, v, theta, omega, L, Ldot
    y0 = np.array([
        r0,
        0.0,
        0.0,
        0.0,
        v0,
        0.0,
        0.0,
        n0,
        1000.0,
        0.0,
    ])

    dy = craft.dynamics(0.0, y0, env, ctrl)

    expected_accel = env.a_earth(y0[0:3]) + env.a_moon_tide(y0[0:3], 0.0)
    assert np.allclose(dy[3:6], expected_accel)

    assert np.isclose(dy[6], n0)
    assert np.isclose(dy[7], 0.0)
    assert np.isclose(dy[8], 0.0)
    assert np.isclose(dy[9], 0.0)

