"""Diagnostic helpers."""

from __future__ import annotations

import numpy as np

MU_EARTH = 3.986004418e14


def semimajor_axis(log: dict, idx: int) -> float:
    r = log["r"][idx]
    v = log["v"][idx]
    mu = MU_EARTH
    rmag = np.linalg.norm(r)
    vmag2 = np.dot(v, v)
    return 1.0 / (2.0 / rmag - vmag2 / mu)


def mean_power_from_tide(log: dict) -> float:
    return float(np.mean(log["power_tide"]))


def _semimajor_axis_from_rv(r: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Return semimajor axis from position/velocity vectors.

    Parameters
    ----------
    r : np.ndarray
        Position vectors with shape (..., 3).
    v : np.ndarray
        Velocity vectors with shape (..., 3).
    """

    rmag = np.linalg.norm(r, axis=-1)
    vmag2 = np.sum(v * v, axis=-1)
    return 1.0 / (2.0 / rmag - vmag2 / MU_EARTH)


def orbit_period(log: dict, idx: int = 0) -> float:
    """Estimate orbital period from state ``idx``."""

    a0 = _semimajor_axis_from_rv(log["r"][idx], log["v"][idx])
    return 2 * np.pi * np.sqrt(a0**3 / MU_EARTH)


def orbit_averaged_semimajor_axis(
    log: dict, start_time: float, period: float
) -> float:
    """Average semimajor axis over one full orbit.

    Integrates the osculating semimajor axis between ``start_time`` and
    ``start_time + period`` using a trapezoidal rule.
    """

    t = log["t"]
    r = log["r"]
    v = log["v"]
    mask = (t >= start_time) & (t <= start_time + period)
    if np.count_nonzero(mask) < 2:
        raise ValueError("insufficient samples for orbit averaging")
    a = _semimajor_axis_from_rv(r[mask], v[mask])
    tt = t[mask]
    return float(np.trapz(a, tt) / (tt[-1] - tt[0]))


def semimajor_axis_fom(log: dict, month: float = 30 * 24 * 3600.0) -> float:
    """Figure of merit: growth in orbit-averaged semimajor axis.

    The value returned is the difference between the semimajor axis
    averaged over the first orbit and the semimajor axis averaged over
    one orbit after ``month`` seconds of simulation time.
    """

    period = orbit_period(log)
    a_start = orbit_averaged_semimajor_axis(log, 0.0, period)
    a_month = orbit_averaged_semimajor_axis(log, month, period)
    return a_month - a_start
