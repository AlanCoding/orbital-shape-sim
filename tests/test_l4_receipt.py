from __future__ import annotations

from l4_receipt.analysis import (
    backpropagate_payload_to_surface,
    find_angle_crossings,
    integrate_orbit,
    select_moon_side_crossing,
    select_catch_schedule,
    simulate_catch_chain,
)
from l4_receipt.scenario import get_scenario


def test_reference_orbit_produces_twenty_pickup_bins():
    scenario = get_scenario()
    t_eval, states = integrate_orbit(scenario)
    crossings = find_angle_crossings(t_eval, states, scenario.launch_angles_rad)

    assert len(crossings) >= 18
    assert any(abs(c.target_angle_deg - 0.0) < 1e-6 for c in crossings)


def test_moon_side_pickup_backpropagates_to_surface():
    scenario = get_scenario()
    t_eval, states = integrate_orbit(scenario)
    crossings = find_angle_crossings(t_eval, states, scenario.launch_angles_rad)
    pickup = select_moon_side_crossing(crossings, scenario)
    payload = backpropagate_payload_to_surface(pickup.state, scenario, scenario.payload_speed_mps)

    assert payload is not None
    surface_rel = payload.surface_state[:2] - scenario.moon_pos
    surface_radius = float((surface_rel[0] ** 2 + surface_rel[1] ** 2) ** 0.5)
    assert abs(surface_radius - scenario.moon_radius_m) < 2_000.0
    assert payload.launch_speed_mps > 0.0
    assert -180.0 <= payload.longitude_deg <= 180.0


def test_catch_chain_advances_mass_and_changes_orbit():
    scenario = get_scenario()
    t_eval, states = integrate_orbit(scenario)
    crossings = find_angle_crossings(t_eval, states, scenario.launch_angles_rad)
    schedule = select_catch_schedule(crossings, 0.0)
    chain = simulate_catch_chain(scenario, schedule, max_catches=24)

    assert len(chain.records) >= 18
    assert chain.final_station_mass >= 10_000.0
    assert chain.total_delivered_mass >= 9_900.0
    if len(chain.segments_states) >= 2:
        first = chain.segments_states[0][0, :2]
        last = chain.segments_states[-1][-1, :2]
        assert ((last[0] - first[0]) ** 2 + (last[1] - first[1]) ** 2) ** 0.5 > 0.0
