"""Checks that the default 100 km setup is dynamically balanced."""

import numpy as np

from tskb.dynamics import f_state
from tskb.env import Environment
from tskb.barbell import DualBarbell


class _ZeroCtrl:
    def action(self, t, y):  # pragma: no cover - simple stub
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

    dy = f_state(0.0, y0, env, craft, ctrl)

    expected_accel = env.a_earth(y0[0:3]) + env.a_moon_tide(y0[0:3], 0.0)
    assert np.allclose(dy[3:6], expected_accel)

    assert np.isclose(dy[6], n0)
    assert np.isclose(dy[7], 0.0)
    assert np.isclose(dy[8], 0.0)
    assert np.isclose(dy[9], 0.0)


def test_accel_clipping():
    env = Environment()
    craft = DualBarbell(1000.0, max_accel=0.01)

    class _Ctrl:
        def action(self, t, y):
            return 0.02

    y = np.zeros(10)
    y[0] = env.r_earth + 1.0
    y[8] = 1.0
    dy = f_state(0.0, y, env, craft, _Ctrl())
    assert dy[9] == 0.01

