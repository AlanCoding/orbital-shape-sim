from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from diamond_l1.scenarios import earth_moon_constants, l1_x_position


@dataclass(frozen=True)
class ReachabilityScenario:
    mu_earth: float
    mu_moon: float
    earth_pos: np.ndarray
    moon_pos: np.ndarray
    distance: float
    omega: float
    l1_x: float
    launch_angles_rad: tuple[float, ...]
    small_speed_mps: float
    large_speed_mps: float
    t_max_days: float
    samples_per_day: int
    earth_radius_m: float
    moon_radius_m: float
    title: str

    @property
    def earth_centered_l1_x(self) -> float:
        return float(self.l1_x - self.earth_pos[0])

    @property
    def earth_centered_moon_x(self) -> float:
        return float(self.moon_pos[0] - self.earth_pos[0])


def get_scenario() -> ReachabilityScenario:
    constants = earth_moon_constants()
    l1_x = l1_x_position(constants)
    launch_angles_rad = tuple(np.arange(12, dtype=float) * (np.pi / 6.0))
    return ReachabilityScenario(
        mu_earth=constants["mu_earth"],
        mu_moon=constants["mu_moon"],
        earth_pos=constants["earth_pos"],
        moon_pos=constants["moon_pos"],
        distance=constants["distance"],
        omega=constants["omega"],
        l1_x=l1_x,
        launch_angles_rad=launch_angles_rad,
        small_speed_mps=0.05,
        large_speed_mps=50.0,
        t_max_days=60.0,
        samples_per_day=96,
        earth_radius_m=6_371_000.0,
        moon_radius_m=1_737_400.0,
        title="Chapter 5: L1 Reachability Map",
    )


def get_launch_cases(scenario: ReachabilityScenario) -> list[tuple[str, float, float, float]]:
    cases = []
    for speed_label, speed in (("small", scenario.small_speed_mps), ("large", scenario.large_speed_mps)):
        for angle_idx, angle in enumerate(scenario.launch_angles_rad):
            cases.append((speed_label, speed, angle_idx, angle))
    return cases
