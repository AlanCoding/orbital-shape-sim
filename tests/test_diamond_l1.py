from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp

from diamond_l1.controllers import controller
from diamond_l1.geometry import moment_of_inertia, solve_geometry
from diamond_l1.physics import derivatives
from diamond_l1.scenarios import get_scenarios


def test_l1_position_sits_between_earth_and_moon():
    scenario = get_scenarios(200.0)["01_noop_200km"]
    earth_x = scenario.earth_pos[0]
    moon_x = scenario.moon_pos[0]
    assert earth_x < scenario.l1_x < moon_x


def test_geometry_keeps_moment_of_inertia_constant():
    scenario = get_scenarios(200.0)["01_noop_200km"]
    body_a = solve_geometry(0.2, scenario)
    body_b = solve_geometry(1.8, scenario)
    mass_per_corner = scenario.mass_total / 4.0
    inertia_a = moment_of_inertia(body_a, mass_per_corner)
    inertia_b = moment_of_inertia(body_b, mass_per_corner)
    assert np.isclose(inertia_a, inertia_b, rtol=1e-12, atol=1e-6)


def test_controller_reacts_to_earthward_motion():
    scenario = get_scenarios(200.0)["02_earthward_200km"]
    state = np.array([scenario.l1_x, 0.0, -5.0, 0.0, 1.0], dtype=float)
    rho_cmd = controller(0.0, state, scenario)
    assert rho_cmd > 1.0


def test_rho_moves_local_ax_toward_the_moon_at_l1():
    scenario = get_scenarios(200.0)["01_noop_200km"]
    state_low = np.array([scenario.l1_x, 0.0, 0.0, 0.0, 0.5], dtype=float)
    state_high = np.array([scenario.l1_x, 0.0, 0.0, 0.0, 1.5], dtype=float)
    ax_low = derivatives(0.0, state_low, scenario)[2]
    ax_high = derivatives(0.0, state_high, scenario)[2]
    assert ax_high > ax_low


def test_short_l1_simulation_runs():
    scenario = get_scenarios(200.0)["04_offset_200km"]
    sol = solve_ivp(
        fun=lambda t, y: derivatives(t, y, scenario),
        t_span=(0.0, 12.0 * 3600.0),
        y0=scenario.state0,
        t_eval=np.linspace(0.0, 12.0 * 3600.0, 40),
        method="DOP853",
        rtol=1e-10,
        atol=1e-12,
    )
    assert sol.status == 0
    assert sol.y.shape[0] == 5
    assert np.isfinite(sol.y).all()


def test_active_control_beats_open_loop_on_earthward_perturbation():
    scenarios = get_scenarios(400.0)
    controlled = scenarios["02_earthward_400km"]
    open_loop = get_scenarios(400.0)["01_noop_400km"]
    open_loop.state0 = controlled.state0.copy()

    def run(scenario):
        sol = solve_ivp(
            fun=lambda t, y: derivatives(t, y, scenario),
            t_span=(0.0, 3.0 * 24.0 * 3600.0),
            y0=scenario.state0,
            t_eval=np.linspace(0.0, 3.0 * 24.0 * 3600.0, 50),
            method="DOP853",
            rtol=1e-10,
            atol=1e-12,
        )
        return np.abs(sol.y[0] - scenario.l1_x).max()

    controlled_max = run(controlled)
    open_loop_max = run(open_loop)

    assert controlled_max < open_loop_max
