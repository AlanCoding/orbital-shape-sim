from __future__ import annotations

import numpy as np


def solve_geometry(rho: float, scenario) -> np.ndarray:
    """Return body-frame corner positions for the four-mass diamond.

    The diamond is constrained to the Earth-Moon line: two masses lie on the
    line of centers and two lie on the perpendicular axis. The scalar rho
    continuously trades distance between those two axes while keeping the
    planar moment of inertia constant by construction.
    """

    rho_clipped = float(np.clip(rho, scenario.rho_min, scenario.rho_max))
    a = scenario.half_span_m * np.sqrt(rho_clipped)
    b = scenario.half_span_m * np.sqrt(2.0 - rho_clipped)
    return np.array(
        [
            [a, 0.0],
            [-a, 0.0],
            [0.0, b],
            [0.0, -b],
        ],
        dtype=float,
    )


def moment_of_inertia(body_points: np.ndarray, mass_per_corner: float) -> float:
    return float(mass_per_corner * np.sum(np.sum(body_points**2, axis=1)))

