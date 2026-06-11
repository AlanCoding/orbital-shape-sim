from __future__ import annotations

import numpy as np

from diamond_l1_reachability.scenarios import get_launch_cases, get_scenario


def test_reachability_launch_grid_covers_24_cases():
    scenario = get_scenario()
    launch_cases = get_launch_cases(scenario)
    assert len(launch_cases) == 24

    speeds = sorted({round(case[1], 6) for case in launch_cases})
    angles = sorted({round(case[3], 6) for case in launch_cases})

    assert np.isclose(speeds[0], 0.05)
    assert np.isclose(speeds[1], 50.0)
    assert len(angles) == 12
    assert np.isclose(angles[1] - angles[0], np.pi / 6.0)


def test_l1_is_between_earth_and_moon_in_plot_coordinates():
    scenario = get_scenario()
    assert np.isclose(scenario.earth_centered_l1_x, scenario.l1_x - scenario.earth_pos[0])
    assert np.isclose(scenario.earth_centered_moon_x, scenario.distance)
