from __future__ import annotations

from dataclasses import replace

import numpy as np
from scipy.integrate import solve_ivp

from diamond_l1.controllers import controller
from diamond_l1.geometry import moment_of_inertia, solve_geometry
from diamond_l1.physics import derivatives
from diamond_l1.render import visible_frame_limit
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


def test_active_scenario_starts_on_the_commanded_shape():
    scenario = get_scenarios(400.0)["02_earthward_400km"]
    rho_cmd = controller(0.0, scenario.state0, scenario)
    assert np.isclose(scenario.state0[4], rho_cmd)


def test_noop_baseline_uses_same_control_law():
    scenarios = get_scenarios(400.0)
    noop = scenarios["01_noop_400km"]
    active = scenarios["02_earthward_400km"]
    assert noop.rho_kp == active.rho_kp
    assert noop.rho_kd == active.rho_kd
    assert np.isclose(noop.state0[4], controller(0.0, noop.state0, noop))


def test_rho_moves_local_ax_toward_the_moon_at_l1():
    scenario = get_scenarios(200.0)["01_noop_200km"]
    state_low = np.array([scenario.l1_x, 0.0, 0.0, 0.0, 0.5], dtype=float)
    state_high = np.array([scenario.l1_x, 0.0, 0.0, 0.0, 1.5], dtype=float)
    ax_low = derivatives(0.0, state_low, scenario)[2]
    ax_high = derivatives(0.0, state_high, scenario)[2]
    assert ax_high > ax_low


def test_control_overpowers_100m_l1_restoring_acceleration():
    active = get_scenarios(400.0)["02_earthward_400km"]
    natural = get_scenarios(400.0)["01_noop_400km"]
    state = np.array([active.l1_x + 100.0, 0.0, -0.006, 0.0, 1.0], dtype=float)
    ax_natural = derivatives(0.0, state.copy(), natural)[2]
    rho_cmd = controller(0.0, state.copy(), active)
    controlled_state = state.copy()
    controlled_state[4] = rho_cmd
    ax_controlled = derivatives(0.0, controlled_state, active)[2]
    assert ax_natural > 0.0
    assert rho_cmd < 0.7
    assert ax_controlled < 0.0


def test_offset_recovery_is_pure_position_offset():
    scenario = get_scenarios(400.0)["04_offset_400km"]
    assert np.isclose(scenario.state0[0] - scenario.l1_x, 500.0)
    assert np.isclose(scenario.state0[2], 0.0)


def test_moonward_compression_case_unclamps_rho():
    scenario = get_scenarios(400.0)["05_moonward_compression_400km"]
    assert np.isclose(scenario.rho_min, 0.0)
    assert np.isclose(scenario.state0[2], 0.009)
    assert scenario.state0[4] <= 1.0


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
    open_loop = replace(
        controlled,
        rho_kp=0.0,
        rho_kd=0.0,
        state0=controlled.state0.copy(),
    )

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


def test_visible_frame_limit_stops_on_first_offscreen_frame():
    scenario = get_scenarios(400.0)["01_noop_400km"]
    states = np.array(
        [
            [scenario.l1_x, 0.0, 0.0, 0.0, 1.0],
            [scenario.l1_x + 1.0e6, 0.0, 0.0, 0.0, 1.0],
            [scenario.l1_x + 6.0e6, 0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    assert visible_frame_limit(states, scenario) == 2
