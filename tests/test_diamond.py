from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp

from diamond.geometry import inertia_from_body_points, solve_geometry
from diamond.physics import derivatives
from diamond.scenarios import get_scenarios


def test_geometry_keeps_inertia_constant():
    scenarios = get_scenarios()
    scenario = scenarios["03_high_tidal_loading"]
    body_a = solve_geometry(0.0, 0.2, scenario)
    body_b = solve_geometry(np.deg2rad(33.0), 1.5, scenario)
    mass_per_corner = scenario.mass / 4.0
    inertia_a = inertia_from_body_points(body_a, mass_per_corner)
    inertia_b = inertia_from_body_points(body_b, mass_per_corner)
    assert np.isclose(inertia_a, inertia_b, rtol=1e-12, atol=1e-9)


def test_short_diamond_simulation_runs():
    scenario = get_scenarios()["02_low_tidal_loading"]
    sol = solve_ivp(
        fun=lambda t, y: derivatives(t, y, scenario),
        t_span=(0.0, 60.0),
        y0=scenario.state0,
        t_eval=np.linspace(0.0, 60.0, 50),
        method="DOP853",
        rtol=1e-10,
        atol=1e-12,
    )
    assert sol.status == 0
    assert np.isfinite(sol.y).all()
    assert sol.y.shape[0] == 7


def test_eccentricity_pumping_switches_on_radial_velocity():
    scenarios = get_scenarios()
    scenario = scenarios["06_eccentricity_pumping_up"]
    state_outbound = np.array([7.0e6, 0.0, 1.0e3, 0.0, 0.0, 0.0, 0.2], dtype=float)
    state_inbound = np.array([7.0e6, 0.0, -1.0e3, 0.0, 0.0, 0.0, 0.2], dtype=float)

    outbound_cmd = scenario.rho_law(0.0, state_outbound, scenario)
    inbound_cmd = scenario.rho_law(0.0, state_inbound, scenario)

    assert outbound_cmd != inbound_cmd
    assert outbound_cmd > inbound_cmd
