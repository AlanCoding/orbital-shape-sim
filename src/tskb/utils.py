"""Utility helpers for tensor operations."""

import numpy as np


def contract_Q_J3(Q: np.ndarray, J3: np.ndarray) -> np.ndarray:
    """Contract a quadrupole tensor with a third-derivative tensor.

    Parameters
    ----------
    Q : np.ndarray
        Quadrupole tensor (3x3).
    J3 : np.ndarray
        Third derivative tensor of potential (3x3x3).

    Returns
    -------
    np.ndarray
        Resulting acceleration contribution (3-vector).
    """

    return 0.5 * np.einsum("jk,ijk->i", Q, J3)
