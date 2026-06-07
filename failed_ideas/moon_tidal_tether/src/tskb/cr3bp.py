"""Utilities for working with the circular restricted three-body problem."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import optimize


@dataclass(frozen=True)
class L1UnstableMode:
    """Representation of the planar unstable mode about the L1 point."""

    eigenvalue: float
    right: np.ndarray
    left: np.ndarray
    pos_dir: np.ndarray
    vel_dir: np.ndarray
    pos_scale: float
    vel_scale: float
    x_l1_bary: float


def _solve_l1_barycentric(mu: float) -> float:
    """Return the barycentric ``x`` location of the L1 libration point."""

    def f(x: float) -> float:
        r1 = abs(x + mu)
        r2 = abs(x - 1.0 + mu)
        term1 = (1.0 - mu) * (x + mu) / r1**3
        term2 = mu * (x - 1.0 + mu) / r2**3
        return x - term1 - term2

    # Close-form approximation is sufficient as a starting guess.
    x0 = 1.0 - (mu / 3.0) ** (1.0 / 3.0)
    return float(optimize.newton(f, x0))


def _l1_state_matrix(x_l1: float, mu: float) -> np.ndarray:
    """Return planar CR3BP state matrix about L1 in normalized units."""

    r1 = abs(x_l1 + mu)
    r2 = abs(x_l1 - 1.0 + mu)

    omega_xx = (
        1.0
        - (1.0 - mu) / r1**3
        + 3.0 * (1.0 - mu) * (x_l1 + mu) ** 2 / r1**5
        - mu / r2**3
        + 3.0 * mu * (x_l1 - 1.0 + mu) ** 2 / r2**5
    )
    omega_yy = 1.0 - (1.0 - mu) / r1**3 - mu / r2**3

    A = np.array(
        [
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [omega_xx, 0.0, 0.0, 2.0],
            [0.0, omega_yy, -2.0, 0.0],
        ]
    )
    return A


def l1_unstable_mode(mu: float, distance: float, rotation_rate: float) -> L1UnstableMode:
    """Return the unstable eigenmode about the L1 point in physical units."""

    x_l1 = _solve_l1_barycentric(mu)
    A = _l1_state_matrix(x_l1, mu)

    eigvals, eigvecs = np.linalg.eig(A)
    idx = int(np.argmax(eigvals.real))
    eigval = float(eigvals[idx].real)
    right = np.asarray(eigvecs[:, idx].real)

    eigvals_left, eigvecs_left = np.linalg.eig(A.T)
    idx_left = int(np.argmin(np.abs(eigvals_left - eigvals[idx])))
    left = np.asarray(eigvecs_left[:, idx_left].real)

    dot = float(left @ right)
    if dot == 0.0:
        raise RuntimeError("degenerate eigenvectors for L1 linearization")
    left /= dot

    S_inv = np.diag([distance, distance, distance * rotation_rate, distance * rotation_rate])
    S = np.diag([1.0 / distance, 1.0 / distance, 1.0 / (distance * rotation_rate), 1.0 / (distance * rotation_rate)])

    right_phys = S_inv @ right
    left_phys = S @ left

    pos_vec = right_phys[:2].copy()
    vel_vec = right_phys[2:].copy()
    sign = 1.0 if pos_vec[0] >= 0.0 else -1.0
    pos_vec *= sign
    vel_vec *= sign
    pos_norm = float(np.linalg.norm(pos_vec))
    vel_norm = float(np.linalg.norm(vel_vec))
    if pos_norm == 0.0 or vel_norm == 0.0:
        raise RuntimeError("invalid eigenvector for L1 mode")
    pos_dir = pos_vec / pos_norm
    vel_dir = vel_vec / vel_norm

    return L1UnstableMode(
        eigenvalue=eigval * rotation_rate,
        right=right_phys,
        left=left_phys,
        pos_dir=pos_dir,
        vel_dir=vel_dir,
        pos_scale=pos_norm,
        vel_scale=vel_norm,
        x_l1_bary=x_l1,
    )

