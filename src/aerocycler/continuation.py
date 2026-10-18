"""Small, transparent continuation correctors for aerocycler branches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass
class CorrectorResult:
    x: np.ndarray
    residual: np.ndarray
    converged: bool
    iterations: int
    singular_values: np.ndarray


def minimum_norm_corrector(
    fun: Callable[[np.ndarray], np.ndarray],
    x0: np.ndarray,
    *,
    steps: np.ndarray | None = None,
    tolerance: float = 3e-9,
    max_iterations: int = 10,
) -> CorrectorResult:
    """Damped Newton correction for an underdetermined family root.

    The five-by-six closure system is solved with the minimum-norm Moore-
    Penrose step.  Explicit central differences proved much more reliable for
    the event map than generic relative-step finite differences.
    """

    x = np.asarray(x0, dtype=float).copy()
    if steps is None:
        steps = np.array([3e-6, 1e-6, 1e-6, 1e-6, 1e-7, 1e-7])
    eye = np.eye(x.size)
    singular_values = np.empty(0)
    for iteration in range(max_iterations + 1):
        residual = fun(x)
        norm = float(np.linalg.norm(residual))
        if norm <= tolerance:
            return CorrectorResult(x, residual, True, iteration, singular_values)
        if iteration == max_iterations:
            break
        jac = np.column_stack(
            [
                (fun(x + eye[j] * steps[j]) - fun(x - eye[j] * steps[j]))
                / (2.0 * steps[j])
                for j in range(x.size)
            ]
        )
        u, singular_values, vt = np.linalg.svd(jac, full_matrices=False)
        if singular_values[-1] <= 1e-13 * singular_values[0]:
            break
        delta = -vt.T @ ((u.T @ residual) / singular_values)
        best_norm = norm
        best_x = None
        for alpha in (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625):
            candidate = x + alpha * delta
            candidate_norm = float(np.linalg.norm(fun(candidate)))
            if candidate_norm < best_norm:
                best_norm = candidate_norm
                best_x = candidate
        if best_x is None:
            break
        x = best_x
    return CorrectorResult(x, fun(x), False, iteration, singular_values)
