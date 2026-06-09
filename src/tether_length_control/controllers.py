"""
State-feedback tether length laws.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np


LengthLaw = Callable[[float, Any, Any], float]


class ScenarioLike:
    short_length: float
    long_length: float


def wrap_to_pi(angle: float) -> float:
    return (angle + np.pi) % (2.0 * np.pi) - np.pi


def _smooth_gate(signal: float, width: float) -> float:
    if width <= 0.0:
        return 1.0 if signal >= 0.0 else 0.0
    return float(0.5 * (1.0 + np.tanh(signal / width)))


def make_fixed_length_law(length: float) -> LengthLaw:
    """
    Return a constant tether length law.
    """

    def length_law(t: float, state: np.ndarray, scenario: ScenarioLike) -> float:
        return float(length)

    return length_law


def make_quadrant_length_law(
    short_length: float,
    long_length: float,
    phase_offset: float = 0.0,
    reverse: bool = False,
    transition_width: float = 0.05,
) -> LengthLaw:
    """
    Return a four-quadrant length law driven by the local attitude phase.

    The phase is the tether angle relative to the local radial direction.
    Two opposite quadrants map to the long state and the other two map to
    the short state. Reversing swaps the sign convention.
    """

    def length_law(t: float, state: np.ndarray, scenario: ScenarioLike) -> float:
        x, y, vx, vy, phi, H = state
        theta = np.arctan2(y, x)
        psi = wrap_to_pi(phi - theta - phase_offset)
        signal = np.sin(2.0 * psi)
        if reverse:
            signal = -signal
        blend = _smooth_gate(signal, transition_width)
        return float(short_length + (long_length - short_length) * blend)

    return length_law


def make_perigee_apogee_length_law(
    short_length: float,
    long_length: float,
    reverse: bool = False,
    transition_width: float = 50.0,
) -> LengthLaw:
    """
    Return a two-phase length law for eccentric-orbit pumping.

    The switch is keyed to radial velocity so the length changes at the
    apses rather than during approach.
    """

    def length_law(t: float, state: np.ndarray, scenario: ScenarioLike) -> float:
        x, y, vx, vy, phi, H = state
        r = np.hypot(x, y)
        drdt = 0.0 if r == 0.0 else (x * vx + y * vy) / r
        signal = drdt
        if reverse:
            signal = -signal
        blend = _smooth_gate(signal, transition_width)
        return float(short_length + (long_length - short_length) * blend)

    return length_law
