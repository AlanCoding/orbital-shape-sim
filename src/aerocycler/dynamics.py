"""Primary-centered rotating CR3BP equations and encounter geometry."""

from __future__ import annotations

import numpy as np


EZ = np.array([0.0, 0.0, 1.0])
SECONDARY = np.array([1.0, 0.0, 0.0])


def rhs(_t: float, state: np.ndarray, mu: float, secondary_scale: float = 1.0) -> np.ndarray:
    """Primary-centered rotating equations with a secondary-gravity homotopy.

    Scaling both the direct secondary acceleration and the indirect origin
    acceleration makes ``secondary_scale=0`` an exact Kepler problem viewed
    in axes rotating at unit angular rate.
    """

    q = state[:3]
    v = state[3:]
    r1 = np.linalg.norm(q)
    d2v = q - SECONDARY
    r2 = np.linalg.norm(d2v)
    mu1 = 1.0 - mu
    # Component form avoids allocating cross-product arrays at every ODE call.
    a1 = -mu1 / r1**3
    a2 = -secondary_scale * mu / r2**3
    return np.array([
        v[0], v[1], v[2],
        2.0 * v[1] + q[0] + a1 * q[0] + a2 * d2v[0] - secondary_scale * mu,
        -2.0 * v[0] + q[1] + a1 * q[1] + a2 * d2v[1],
        a1 * q[2] + a2 * d2v[2],
    ])


def inertial_relative_velocity(state: np.ndarray) -> np.ndarray:
    """Primary-relative inertial velocity expressed in rotating axes."""

    return state[3:] + np.cross(EZ, state[:3])


def rotating_velocity(q: np.ndarray, inertial_relative_v: np.ndarray) -> np.ndarray:
    return inertial_relative_v - np.cross(EZ, q)


def encounter_basis(state: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return radial, prograde tangential, and cross-track unit vectors."""

    q = state[:3]
    w = inertial_relative_velocity(state)
    rhat = q / np.linalg.norm(q)
    transverse = w - np.dot(w, rhat) * rhat
    speed = np.linalg.norm(transverse)
    if speed < 1e-12:
        raise ValueError("undefined encounter basis for radial motion")
    that = transverse / speed
    chat = np.cross(rhat, that)
    chat /= np.linalg.norm(chat)
    return rhat, that, chat


def impulse_vector(state: np.ndarray, jd: float, je: float, jr: float) -> np.ndarray:
    rhat, that, chat = encounter_basis(state)
    return -jd * that + je * chat + jr * rhat


def apply_impulse(state: np.ndarray, jd: float, je: float, jr: float) -> tuple[np.ndarray, np.ndarray]:
    dv = impulse_vector(state, jd, je, jr)
    result = state.copy()
    # An instantaneous vector is identical in rotating and inertial velocity.
    result[3:] += dv
    return result, dv


def jacobi(state: np.ndarray, mu: float) -> float:
    """Jacobi integral of the full CR3BP in primary-centered coordinates."""

    q = state[:3]
    v = state[3:]
    r1 = np.linalg.norm(q)
    r2 = np.linalg.norm(q - SECONDARY)
    # Barycentric x is q_x-mu; adding an irrelevant constant is avoided by
    # evaluating the conventional expression directly.
    x_b = q[0] - mu
    omega = 0.5 * (x_b * x_b + q[1] * q[1]) + (1.0 - mu) / r1 + mu / r2
    return float(2.0 * omega - np.dot(v, v))
