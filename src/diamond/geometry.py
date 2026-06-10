from __future__ import annotations

import numpy as np


def reference_square(R0: float) -> np.ndarray:
    return R0 * np.array(
        [
            [1.0, 1.0],
            [1.0, -1.0],
            [-1.0, -1.0],
            [-1.0, 1.0],
        ],
        dtype=float,
    )


def action_basis(alpha: float) -> tuple[np.ndarray, np.ndarray]:
    n = np.array([np.cos(alpha), np.sin(alpha)], dtype=float)
    t = np.array([-np.sin(alpha), np.cos(alpha)], dtype=float)
    return n, t


def solve_geometry(alpha_cmd: float, rho_act: float, scenario) -> np.ndarray:
    """Return body-frame corner positions for the current deformation."""
    rho = float(np.clip(rho_act, scenario.rho_min, scenario.rho_max))
    lambda_parallel = np.sqrt(rho)
    lambda_perp = np.sqrt(max(2.0 - rho, scenario.rho_min))
    n, t = action_basis(alpha_cmd)
    M = lambda_parallel * np.outer(n, n) + lambda_perp * np.outer(t, t)
    return reference_square(scenario.R0) @ M.T


def inertia_from_body_points(body_points: np.ndarray, mass_per_corner: float) -> float:
    return float(mass_per_corner * np.sum(np.sum(body_points**2, axis=1)))


def body_to_inertial(body_points: np.ndarray, phi: float, center: np.ndarray) -> np.ndarray:
    c = np.cos(phi)
    s = np.sin(phi)
    rot = np.array([[c, -s], [s, c]], dtype=float)
    return center + body_points @ rot.T

