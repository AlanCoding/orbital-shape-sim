"""System definitions and normalized-unit conversions."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SystemParameters:
    """A normalized circular primary-secondary system.

    Length, angular rate, and total gravitational parameter are one.  The
    coordinates used by :mod:`aerocycler` are centered on the primary and
    rotate with the secondary; the secondary is therefore fixed at (1, 0, 0).
    """

    mu: float
    rho1: float
    rho2: float
    separation_km: float | None = None
    period_days: float | None = None
    primary_rotation_ratio: float | None = None
    name: str = "normalized"

    @property
    def mu1(self) -> float:
        return 1.0 - self.mu

    @property
    def time_unit_days(self) -> float | None:
        return None if self.period_days is None else self.period_days / (2.0 * math.pi)

    @property
    def velocity_unit_km_s(self) -> float | None:
        if self.separation_km is None or self.period_days is None:
            return None
        return self.separation_km / (self.time_unit_days * 86400.0)


def earth_moon_system() -> SystemParameters:
    """Return reproducible mean Earth-Moon parameters.

    Values use the conventional CR3BP mass parameter and mean separation.
    The sidereal Earth rotation ratio is the lunar sidereal period divided by
    Earth's sidereal day.
    """

    separation_km = 384_400.0
    lunar_sidereal_days = 27.321661
    earth_sidereal_days = 0.99726968
    return SystemParameters(
        mu=0.012150585609624,
        rho1=6378.1363 / separation_km,
        rho2=1737.4 / separation_km,
        separation_km=separation_km,
        period_days=lunar_sidereal_days,
        primary_rotation_ratio=lunar_sidereal_days / earth_sidereal_days,
        name="Earth-Moon",
    )
