from __future__ import annotations

import numpy as np
import unittest

from tether_length_control.controllers import (
    make_fixed_length_law,
    make_perigee_apogee_length_law,
    make_quadrant_length_law,
)
from tether_length_control.physics import inertia_from_length, tether_derivatives
from tether_length_control.scenarios import Scenario


def _scenario(length_law, short_length=1.0e5, long_length=2.0e5):
    return Scenario(
        id="test",
        title="test",
        m1=1000.0,
        m2=1000.0,
        state0=np.zeros(6),
        t_max=1.0,
        description="test",
        length_law=length_law,
        short_length=short_length,
        long_length=long_length,
    )


class TetherLengthControlTests(unittest.TestCase):
    def test_quadrant_length_law_flips_by_phase(self):
        law = make_quadrant_length_law(1.0, 2.0)
        scenario = _scenario(law)

        state_long = np.array([1.0, 0.0, 0.0, 0.0, np.pi / 4.0, 0.0])
        state_short = np.array([1.0, 0.0, 0.0, 0.0, 3.0 * np.pi / 4.0, 0.0])

        self.assertAlmostEqual(law(0.0, state_long, scenario), 2.0)
        self.assertAlmostEqual(law(0.0, state_short, scenario), 1.0)

    def test_reversed_quadrant_length_law_flips_sign(self):
        law = make_quadrant_length_law(1.0, 2.0, reverse=True)
        scenario = _scenario(law)

        state_long = np.array([1.0, 0.0, 0.0, 0.0, np.pi / 4.0, 0.0])
        state_short = np.array([1.0, 0.0, 0.0, 0.0, 3.0 * np.pi / 4.0, 0.0])

        self.assertAlmostEqual(law(0.0, state_long, scenario), 1.0)
        self.assertAlmostEqual(law(0.0, state_short, scenario), 2.0)

    def test_perigee_apogee_length_law_tracks_radial_velocity(self):
        law = make_perigee_apogee_length_law(1.0, 2.0)
        scenario = _scenario(law)

        state_outbound = np.array([1.0, 0.0, 1000.0, 0.0, 0.0, 0.0])
        state_inbound = np.array([1.0, 0.0, -1000.0, 0.0, 0.0, 0.0])

        self.assertAlmostEqual(law(0.0, state_outbound, scenario), 2.0)
        self.assertAlmostEqual(law(0.0, state_inbound, scenario), 1.0)

    def test_reversed_perigee_apogee_length_law_flips_sign(self):
        law = make_perigee_apogee_length_law(1.0, 2.0, reverse=True)
        scenario = _scenario(law)

        state_outbound = np.array([1.0, 0.0, 1000.0, 0.0, 0.0, 0.0])
        state_inbound = np.array([1.0, 0.0, -1000.0, 0.0, 0.0, 0.0])

        self.assertAlmostEqual(law(0.0, state_outbound, scenario), 1.0)
        self.assertAlmostEqual(law(0.0, state_inbound, scenario), 2.0)

    def test_tether_length_change_does_not_inject_angular_momentum(self):
        short_length = 1.0e5
        long_length = 2.0e5

        short_scenario = _scenario(make_fixed_length_law(short_length), short_length, long_length)
        long_scenario = _scenario(make_fixed_length_law(long_length), short_length, long_length)

        state = np.array([1.0e7, 0.0, 0.0, 0.0, 0.0, 12.0])
        short_deriv = tether_derivatives(0.0, state, short_scenario)
        long_deriv = tether_derivatives(0.0, state, long_scenario)

        short_inertia = inertia_from_length(short_scenario.m1, short_scenario.m2, short_length)
        long_inertia = inertia_from_length(long_scenario.m1, long_scenario.m2, long_length)

        self.assertAlmostEqual(short_deriv[5], 0.0)
        self.assertAlmostEqual(long_deriv[5], 0.0)
        self.assertAlmostEqual(short_deriv[4], 12.0 / short_inertia)
        self.assertAlmostEqual(long_deriv[4], 12.0 / long_inertia)
        self.assertGreater(short_deriv[4], long_deriv[4])


if __name__ == "__main__":
    unittest.main()
