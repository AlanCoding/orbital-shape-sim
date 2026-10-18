"""Kepler initialization and periapsis-to-periapsis shooting maps."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp

from .dynamics import apply_impulse, rhs, rotating_velocity
from .model import SystemParameters


@dataclass(frozen=True)
class Family:
    loops: int
    secondary_periods: int

    @property
    def label(self) -> str:
        return f"{self.loops}/{self.secondary_periods}"

    @property
    def kepler_period(self) -> float:
        return 2.0 * math.pi * self.secondary_periods / self.loops


@dataclass(frozen=True)
class Shot:
    """Compact shooting variables at the initial post-impulse periapsis."""

    longitude: float
    latitude: float
    v_lon: float
    v_lat: float
    jd: float = 0.0
    je: float = 0.0
    jr: float = 0.0

    def state(self, rho1: float) -> np.ndarray:
        """Return the initial post-impulse state.

        The four geometric variables describe the pre-impulse periapsis.  The
        common encounter impulse is then applied, including any radial term.
        """

        clat, slat = math.cos(self.latitude), math.sin(self.latitude)
        clon, slon = math.cos(self.longitude), math.sin(self.longitude)
        rhat = np.array([clat * clon, clat * slon, slat])
        elon = np.array([-slon, clon, 0.0])
        elat = np.array([-slat * clon, -slat * slon, clat])
        q = rho1 * rhat
        w = self.v_lon * elon + self.v_lat * elat
        pre = np.concatenate((q, rotating_velocity(q, w)))
        return apply_impulse(pre, self.jd, self.je, self.jr)[0]

    def vector_fixed_je(self) -> np.ndarray:
        return np.array([self.longitude, self.latitude, self.v_lon, self.v_lat, self.jd, self.jr])

    @classmethod
    def from_fixed_je(cls, x: np.ndarray, je: float) -> "Shot":
        return cls(x[0], x[1], x[2], x[3], x[4], je, x[5])


@dataclass
class Arc:
    t0: float
    t1: float
    pre_state: np.ndarray
    post_state: np.ndarray
    impulse: np.ndarray
    solutions: tuple[object, ...]


@dataclass
class ShotResult:
    initial_state: np.ndarray
    final_state: np.ndarray
    arcs: list[Arc]
    success: bool
    message: str

    @property
    def period(self) -> float:
        return self.arcs[-1].t1 if self.arcs else math.nan

    @property
    def closure(self) -> np.ndarray:
        return self.final_state - self.initial_state

    @property
    def position_residual(self) -> float:
        return float(np.linalg.norm(self.closure[:3]))

    @property
    def velocity_residual(self) -> float:
        return float(np.linalg.norm(self.closure[3:]))

    @property
    def periapsis_radii(self) -> list[float]:
        return [float(np.linalg.norm(a.pre_state[:3])) for a in self.arcs]


def kepler_seed(system: SystemParameters, family: Family) -> Shot:
    """Analytical polar ellipse phased to put first apogee at the secondary."""

    period = family.kepler_period
    semimajor = (system.mu1 * (period / (2.0 * math.pi)) ** 2) ** (1.0 / 3.0)
    if 2.0 * semimajor <= system.rho1:
        raise ValueError("resonance period is too short for the prescribed periapsis")
    speed = math.sqrt(system.mu1 * (2.0 / system.rho1 - 1.0 / semimajor))
    longitude = 0.5 * period - math.pi
    return Shot(longitude=longitude, latitude=0.0, v_lon=0.0, v_lat=speed)


def _radial_turn_event(direction: float) -> Callable[[float, np.ndarray], float]:
    def event(_t: float, state: np.ndarray, *_args: object) -> float:
        return float(np.dot(state[:3], state[3:]))

    event.direction = direction
    event.terminal = True
    return event


def propagate_cycle(
    system: SystemParameters,
    family: Family,
    shot: Shot,
    *,
    secondary_scale: float = 1.0,
    rtol: float = 2e-11,
    atol: float = 2e-13,
    dense_output: bool = False,
    max_step: float = 0.03,
    periapsis_control: Callable[[int, np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
) -> ShotResult:
    """Propagate through exactly ``family.loops`` subsequent periapses."""

    initial = shot.state(system.rho1)
    state = initial.copy()
    arcs: list[Arc] = []
    time = 0.0
    expected = family.kepler_period
    for _ in range(family.loops):
        # Splitting at apogee avoids the event detector immediately accepting
        # the initial periapsis root.  The first event is outward-to-inward,
        # the second is the desired inward-to-outward periapsis.
        departure_time = time + max(1e-8, expected * 1e-7)
        departure = solve_ivp(
            rhs,
            (time, departure_time),
            state,
            args=(system.mu, secondary_scale),
            rtol=rtol,
            atol=atol,
            max_step=max_step,
            dense_output=dense_output,
            method="DOP853",
        )
        apo = solve_ivp(
            rhs,
            (departure_time, time + 1.25 * expected),
            departure.y[:, -1],
            args=(system.mu, secondary_scale),
            events=_radial_turn_event(-1.0),
            rtol=rtol,
            atol=atol,
            max_step=max_step,
            dense_output=dense_output,
            method="DOP853",
        )
        if not apo.success or len(apo.t_events[0]) != 1:
            return ShotResult(initial, state, arcs, False, apo.message or "apogee not found")
        peri = solve_ivp(
            rhs,
            (float(apo.t_events[0][0]), time + 2.5 * expected),
            apo.y_events[0][0],
            args=(system.mu, secondary_scale),
            events=_radial_turn_event(1.0),
            rtol=rtol,
            atol=atol,
            max_step=max_step,
            dense_output=dense_output,
            method="DOP853",
        )
        if not peri.success or len(peri.t_events[0]) != 1:
            return ShotResult(initial, state, arcs, False, peri.message or "periapsis not found")
        time = float(peri.t_events[0][0])
        pre = peri.y_events[0][0]
        try:
            post, dv = (apply_impulse(pre, shot.jd, shot.je, shot.jr)
                        if periapsis_control is None else periapsis_control(len(arcs), pre))
        except ValueError as exc:
            return ShotResult(initial, pre, arcs, False, str(exc))
        arcs.append(Arc(float(departure.t[0]), time, pre, post, dv, (departure, apo, peri)))
        state = post
    return ShotResult(initial, state, arcs, True, "ok")


def closure_residual(
    x: np.ndarray,
    *,
    system: SystemParameters,
    family: Family,
    je: float,
    secondary_scale: float,
    failure_value: float = 1e3,
) -> np.ndarray:
    shot = Shot.from_fixed_je(x, je)
    result = propagate_cycle(
        system,
        family,
        shot,
        secondary_scale=secondary_scale,
        rtol=2e-9,
        atol=2e-11,
        max_step=0.08,
    )
    if not result.success or not np.all(np.isfinite(result.closure)):
        return np.full(6, failure_value)
    # Position and velocity are similar O(1) scales away from the primary,
    # despite q0 itself being small, so leave the physical residual unscaled.
    return result.closure


def reduced_closure_residual(
    z: np.ndarray,
    *,
    longitude: float,
    system: SystemParameters,
    family: Family,
    je: float,
    secondary_scale: float,
) -> np.ndarray:
    """Five independent closure equations at fixed initial longitude.

    Both endpoints lie on a periapsis section before receiving the identical
    impulse.  Once position and the two tangential velocity components close,
    radial velocity closure is dependent.  Keeping all six equations in a
    square solver produces a numerically singular Jacobian and premature
    convergence; the omitted component is always checked afterward.
    """

    shot = Shot(longitude, z[0], z[1], z[2], z[3], je, z[4])
    result = propagate_cycle(
        system,
        family,
        shot,
        secondary_scale=secondary_scale,
        rtol=2e-9,
        atol=2e-11,
        max_step=0.08,
    )
    if not result.success or not np.all(np.isfinite(result.closure)):
        return np.full(5, 1e3)
    dq = result.closure[:3]
    dv = result.closure[3:]
    slon, clon = math.sin(longitude), math.cos(longitude)
    slat, clat = math.sin(z[0]), math.cos(z[0])
    elon = np.array([-slon, clon, 0.0])
    elat = np.array([-slat * clon, -slat * slon, clat])
    return np.concatenate((dq / system.rho1, [np.dot(dv, elon) / 10.0, np.dot(dv, elat) / 10.0]))


def family_closure_residual(
    x: np.ndarray,
    *,
    system: SystemParameters,
    family: Family,
    je: float,
    secondary_scale: float,
    rtol: float = 2e-10,
    atol: float = 2e-12,
    max_step: float = 0.04,
) -> np.ndarray:
    """Five independent closure equations with longitude left free.

    ``x`` is ``[longitude, latitude, v_lon, v_lat, J_D, J_R]``.  This is the
    numerically honest formulation: at fixed ``J_E`` the periodic roots form
    (generically) a one-dimensional family rather than an isolated 6x6 root.
    """

    shot = Shot(x[0], x[1], x[2], x[3], x[4], je, x[5])
    result = propagate_cycle(
        system,
        family,
        shot,
        secondary_scale=secondary_scale,
        rtol=rtol,
        atol=atol,
        max_step=max_step,
    )
    if not result.success or not np.all(np.isfinite(result.closure)):
        return np.full(5, 1e3)
    longitude, latitude = x[:2]
    slon, clon = math.sin(longitude), math.cos(longitude)
    slat, clat = math.sin(latitude), math.cos(latitude)
    elon = np.array([-slon, clon, 0.0])
    elat = np.array([-slat * clon, -slat * slon, clat])
    dq = result.closure[:3] / system.rho1
    dv = result.closure[3:]
    return np.concatenate((dq, [np.dot(dv, elon) / 10.0, np.dot(dv, elat) / 10.0]))
