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
