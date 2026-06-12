from __future__ import annotations

from diamond_l1_reachability.mass_driver import analyze_bounded_grazing_releases, analyze_grazing_releases
from diamond_l1_reachability.mass_driver import analyze_release_scan
from diamond_l1_reachability.scenarios import get_scenario


def test_mass_driver_grazing_scan_finds_two_surface_contacts():
    scenario = get_scenario()
    analysis = analyze_grazing_releases(scenario)

    assert analysis.speed_mps == 100.0
    assert len(analysis.grazing_cases) >= 2

    angles = sorted(case.angle_deg for case in analysis.grazing_cases[:2])
    assert 299.0 < angles[0] < 300.0
    assert 303.0 < angles[1] < 304.0

    for case in analysis.grazing_cases[:2]:
        assert abs(case.min_distance_m - scenario.moon_radius_m) < 2_000.0
        assert -180.0 <= case.longitude_deg <= 180.0


def test_mass_driver_low_speed_scan_stays_above_surface():
    scenario = get_scenario()
    analysis = analyze_grazing_releases(scenario, speed_mps=0.05)

    assert analysis.speed_mps == 0.05
    assert len(analysis.grazing_cases) == 0
    assert analysis.scan_min_distances_m.min() > scenario.moon_radius_m
    assert 5_000_000.0 < analysis.scan_min_distances_m.min() < 6_000_000.0


def test_release_scan_densifies_the_interesting_band():
    scenario = get_scenario()
    scan = analyze_release_scan(scenario, speed_mps=102.0, dense_band_deg=(50.0, 120.0), dense_factor=4)

    angles_deg = scan.scan_angles_rad * 180.0 / 3.141592653589793
    dense_count = sum(50.0 <= angle < 120.0 for angle in angles_deg)

    assert len(scan.scan_angles_rad) > 70
    assert dense_count >= 50


def test_bounded_grazing_search_finds_two_roots_in_window():
    scenario = get_scenario()
    analysis = analyze_bounded_grazing_releases(scenario, speed_mps=102.0, angle_min_deg=70.0, angle_max_deg=100.0)

    assert analysis.speed_mps == 102.0
    assert len(analysis.grazing_cases) == 2

    angles = [case.angle_deg for case in analysis.grazing_cases]
    assert 96.0 < angles[0] < 96.2
    assert 97.8 < angles[1] < 98.0

    for case in analysis.grazing_cases:
        assert abs(case.min_distance_m - scenario.moon_radius_m) < 1_000.0
        assert -180.0 <= case.longitude_deg <= 180.0


def test_bounded_grazing_search_finds_one_root_in_wider_window():
    scenario = get_scenario()
    analysis = analyze_bounded_grazing_releases(scenario, speed_mps=120.0, angle_min_deg=50.0, angle_max_deg=100.0)

    assert analysis.speed_mps == 120.0
    assert len(analysis.grazing_cases) == 1

    case = analysis.grazing_cases[0]
    assert 64.8 < case.angle_deg < 65.1
    assert abs(case.min_distance_m - scenario.moon_radius_m) < 1_000.0
    assert -180.0 <= case.longitude_deg <= 180.0


def test_capped_release_scan_uses_short_window():
    scenario = get_scenario()
    scan = analyze_release_scan(scenario, speed_mps=130.0, max_days=8.4)

    assert scan.speed_mps == 130.0
    assert scan.max_days == 8.4
    assert 1_400_000.0 < scan.scan_min_distances_m.min() < 1_600_000.0


def test_bounded_capped_130_scan_finds_two_roots():
    scenario = get_scenario()
    analysis = analyze_bounded_grazing_releases(
        scenario,
        speed_mps=130.0,
        angle_min_deg=50.0,
        angle_max_deg=100.0,
        max_days=8.4,
    )

    assert analysis.speed_mps == 130.0
    assert len(analysis.grazing_cases) == 2

    angles = [case.angle_deg for case in analysis.grazing_cases]
    assert 55.9 < angles[0] < 56.0
    assert 71.2 < angles[1] < 71.4

    for case in analysis.grazing_cases:
        assert abs(case.min_distance_m - scenario.moon_radius_m) < 1_000.0
        assert -180.0 <= case.longitude_deg <= 180.0
