from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from diamond_l1.scenarios import earth_moon_constants


@dataclass(frozen=True)
class ReceiptScenario:
    mu_earth: float
    mu_moon: float
    earth_pos: np.ndarray
    moon_pos: np.ndarray
    distance: float
    omega: float
    earth_radius_m: float
    moon_radius_m: float
    l4_pos: np.ndarray
    l5_pos: np.ndarray
    orbit_state0: np.ndarray
    orbit_days: float
    samples_per_day: int
    launch_angles_rad: tuple[float, ...]
    station_mass0: float
    payload_mass0: float
    payload_growth: float
    payload_mass_cap: float
    payload_speed_mps: float
    catch_dead_time_days: float
    title: str


def get_scenario() -> ReceiptScenario:
    constants = earth_moon_constants()
    total_mass = 5.972168e24 + 7.342e22
    mu = constants["mu_moon"] / total_mass
    l4_pos = np.array([constants["distance"] * (0.5 - mu), constants["distance"] * np.sqrt(3.0) / 2.0], dtype=float)
    l5_pos = np.array([l4_pos[0], -l4_pos[1]], dtype=float)

    orbit_state0 = np.array(
        [
            l4_pos[0] - 10_000_000.0,
            l4_pos[1],
            0.0,
            25.0,
        ],
        dtype=float,
    )

    launch_angles_rad = tuple(np.linspace(0.0, 2.0 * np.pi, 20, endpoint=False))

    return ReceiptScenario(
        mu_earth=constants["mu_earth"],
        mu_moon=constants["mu_moon"],
        earth_pos=constants["earth_pos"],
        moon_pos=constants["moon_pos"],
        distance=constants["distance"],
        omega=constants["omega"],
        earth_radius_m=6_371_000.0,
        moon_radius_m=1_737_400.0,
        l4_pos=l4_pos,
        l5_pos=l5_pos,
        orbit_state0=orbit_state0,
        orbit_days=150.0,
        samples_per_day=240,
        launch_angles_rad=launch_angles_rad,
        station_mass0=100.0,
        payload_mass0=1.0,
        payload_growth=1.65,
        payload_mass_cap=10_000.0,
        payload_speed_mps=260.0,
        catch_dead_time_days=7.5,
        title="Chapter 6: L4 Mass Receipt",
    )
