import numpy as np
from tskb import Environment

def test_moonless_environment_has_no_tide():
    env = Environment(include_moon=False)
    r = np.array([env.r_earth + 1000.0, 0.0, 0.0])
    a_moon = env.a_moon_tide(r, 0.0)
    assert np.allclose(a_moon, np.zeros(3))
    assert env.n_moon == 0.0
