"""Independent diagnostics and aerodynamic interpretation of closed shots."""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np

from .dynamics import EZ, SECONDARY, inertial_relative_velocity, jacobi
from .model import SystemParameters
from .shooting import Shot, ShotResult
from .aerodynamics import impulse_work


def osculating_elements(state: np.ndarray, mu_primary: float) -> dict[str, float]:
    q = state[:3]
    w = inertial_relative_velocity(state)
    radius = float(np.linalg.norm(q))
    speed2 = float(np.dot(w, w))
    hvec = np.cross(q, w)
    h = float(np.linalg.norm(hvec))
    energy = 0.5 * speed2 - mu_primary / radius
    evec = np.cross(w, hvec) / mu_primary - q / radius
    eccentricity = float(np.linalg.norm(evec))
    semimajor = math.inf if abs(energy) < 1e-15 else -mu_primary / (2.0 * energy)
    inclination = math.acos(np.clip(hvec[2] / h, -1.0, 1.0))
    node = np.cross(EZ, hvec)
    node_norm = float(np.linalg.norm(node))
    raan = 0.0 if node_norm < 1e-15 else math.atan2(node[1], node[0])
    if node_norm < 1e-15 or eccentricity < 1e-15:
        arg_periapsis = 0.0
    else:
        arg_periapsis = math.atan2(
            np.dot(np.cross(node, evec), hvec) / (node_norm * eccentricity * h),
            np.dot(node, evec) / (node_norm * eccentricity),
        )
    return {
        "semimajor_axis": float(semimajor),
        "eccentricity": eccentricity,
        "inclination_deg": math.degrees(inclination),
        "raan_deg": math.degrees(raan),
        "argument_of_periapsis_deg": math.degrees(arg_periapsis),
        "specific_energy": energy,
        "angular_momentum": h,
    }


def sample_result(result: ShotResult, points_per_time: float = 350.0) -> tuple[np.ndarray, np.ndarray]:
    times: list[np.ndarray] = []
    states: list[np.ndarray] = []
    for arc in result.arcs:
        for solution in arc.solutions:
            count = max(3, int((solution.t[-1] - solution.t[0]) * points_per_time) + 2)
            t = np.linspace(solution.t[0], solution.t[-1], count)
            if solution.sol is None:
                y = np.vstack([np.interp(t, solution.t, row) for row in solution.y]).T
            else:
                y = solution.sol(t).T
            times.append(t)
            states.append(y)
    return np.concatenate(times), np.vstack(states)


def inertial_history(times: np.ndarray, rotating_states: np.ndarray, mu: float) -> np.ndarray:
    """Convert primary-centered rotating states to barycentric inertial states."""

    result = np.empty_like(rotating_states)
    for index, (time, state) in enumerate(zip(times, rotating_states, strict=True)):
        c, s = math.cos(time), math.sin(time)
        rotation = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        q = state[:3]
        w = inertial_relative_velocity(state)
        result[index, :3] = rotation @ (q - np.array([mu, 0.0, 0.0]))
        result[index, 3:] = rotation @ (w + np.array([0.0, -mu, 0.0]))
    return result


def encounter_plane_excursions(
    result: ShotResult, shot: Shot, rho1: float, *, reference_frame: str = "rotating"
) -> list[float]:
    """Plane-normal angles against the initial pre-impulse plane.

    The legacy default compares normals in lunar ROTATING coordinates at
    different times. It includes coordinate rotation and is not drift from
    a fixed inertial plane. Use ``reference_frame='inertial'`` for that.
    Plane orientation is unoriented here (h and -h describe the same plane);
    lunar-plane inclination elsewhere retains prograde/retrograde sense.
    """
    if reference_frame not in {"rotating", "inertial"}:
        raise ValueError("reference_frame must be rotating or inertial")
    pre_initial = Shot(
        shot.longitude, shot.latitude, shot.v_lon, shot.v_lat, 0.0, 0.0, 0.0
    ).state(rho1)
    h0 = np.cross(pre_initial[:3], inertial_relative_velocity(pre_initial))
    h0 /= np.linalg.norm(h0)
    excursions = []
    states = [result.initial_state, *[arc.post_state for arc in result.arcs]]
    times = [0.0, *[arc.t1 for arc in result.arcs]]
    for time, state in zip(times, states, strict=True):
        h = np.cross(state[:3], inertial_relative_velocity(state))
        h /= np.linalg.norm(h)
        if reference_frame == "inertial":
            c, s = math.cos(time), math.sin(time)
            h = np.array([c*h[0]-s*h[1], s*h[0]+c*h[1], h[2]])
        excursions.append(math.degrees(math.acos(np.clip(abs(float(np.dot(h, h0))), -1.0, 1.0))))
    return excursions


def atmosphere_ld(shot: Shot, result: ShotResult, sigmas: Iterable[float]) -> dict:
    """Finite-work midpoint projection; necessary but not sufficient for flight.

    The incoming-only projection used in v1 dropped quadratic impulse work.
    Neither projection substitutes for a continuous aerodynamic trajectory.
    """
    sigmas = list(sigmas)
    encounters = [arc.pre_state for arc in result.arcs]
    impulses = [arc.impulse for arc in result.arcs]
    required: list[float] = []
    passive: list[bool] = []
    per_encounter: list[list[float | None]] = []
    for sigma in sigmas:
        ratios: list[float | None] = []
        valid = True
        for state, dv in zip(encounters, impulses, strict=True):
            atmosphere = sigma * np.cross(EZ, state[:3])
            post = state.copy()
            post[3:] += dv
            relative = inertial_relative_velocity(state) + 0.5*dv - atmosphere
            uhat = relative / np.linalg.norm(relative)
            drag = -float(np.dot(dv, uhat))
            lift = dv + drag * uhat
            if drag <= 0.0:
                valid = False
                ratios.append(None)
            else:
                ratios.append(float(np.linalg.norm(lift) / drag))
        passive.append(valid)
        per_encounter.append(ratios)
        required.append(max(r for r in ratios if r is not None) if valid else None)
    return {
        "convention": "finite-impulse midpoint work; necessary passivity only",
        "sigma": [float(value) for value in sigmas],
        "vehicle_ld_required": required,
        "all_encounters_passive": passive,
        "per_encounter_ld": per_encounter,
    }


def summarize(
    system: SystemParameters,
    family_label: str,
    branch_id: str,
    shot: Shot,
    result: ShotResult,
) -> dict:
    times, states = sample_result(result)
    q = states[:, :3]
    w = states[:, 3:] + np.cross(EZ, q)
    d_primary = np.linalg.norm(q, axis=1)
    d_secondary = np.linalg.norm(q - SECONDARY, axis=1)
    closest_index = int(np.argmin(d_secondary))
    target = float(d_secondary[closest_index] + 0.02)
    before_candidates = np.flatnonzero(d_secondary[:closest_index] >= target)
    after_candidates = np.flatnonzero(d_secondary[closest_index:] >= target)
    before = int(before_candidates[-1]) if len(before_candidates) else max(0, closest_index - 1)
    after = (
        closest_index + int(after_candidates[0])
        if len(after_candidates)
        else min(len(times) - 1, closest_index + 1)
    )
    moon_velocity = np.cross(EZ, SECONDARY)
    incoming = w[before] - moon_velocity
    outgoing = w[after] - moon_velocity
    turning = math.degrees(
        math.acos(
            np.clip(
                float(np.dot(incoming, outgoing) / (np.linalg.norm(incoming) * np.linalg.norm(outgoing))),
                -1.0,
                1.0,
            )
        )
    )
    inertial_initial = inertial_history(np.array([0.0]), result.initial_state[None, :], system.mu)[0]
    excursions = encounter_plane_excursions(result, shot, system.rho1)
    inertial_excursions = encounter_plane_excursions(result, shot, system.rho1, reference_frame="inertial")
    h = np.cross(q, w)
    lunar_inclination = np.degrees(np.arccos(np.clip(h[:, 2]/np.linalg.norm(h, axis=1), -1, 1)))
    position_latitude = np.degrees(np.arcsin(np.clip(q[:, 2]/d_primary, -1, 1)))
    encounters = []
    for index, arc in enumerate(result.arcs, start=1):
        encounters.append(
            {
                "index": index,
                "time": arc.t1,
                "radius": float(np.linalg.norm(arc.pre_state[:3])),
                "pre_state_rotating": arc.pre_state.tolist(),
                "post_state_rotating": arc.post_state.tolist(),
                "impulse_rotating_cartesian": arc.impulse.tolist(),
                "osculating_elements_post_impulse": osculating_elements(arc.post_state, system.mu1),
                "jacobi_pre": jacobi(arc.pre_state, system.mu),
                "jacobi_post": jacobi(arc.post_state, system.mu),
                "finite_impulse_work": impulse_work(arc.pre_state, arc.post_state, system.primary_rotation_ratio or 0.0),
            }
        )
    sigmas = np.linspace(0.0, 40.0, 401)
    return {
        "schema": "aerocycler-result-v2",
        "family": family_label,
        "branch_id": branch_id,
        "system": {
            "name": system.name,
            "mu": system.mu,
            "rho1": system.rho1,
            "rho2": system.rho2,
            "separation_km": system.separation_km,
            "period_days": system.period_days,
            "velocity_unit_km_s": system.velocity_unit_km_s,
            "primary_rotation_ratio": system.primary_rotation_ratio,
        },
        "shot": {
            "longitude": shot.longitude,
            "latitude": shot.latitude,
            "v_lon": shot.v_lon,
            "v_lat": shot.v_lat,
            "J_D": shot.jd,
            "J_E": shot.je,
            "J_R": shot.jr,
            "impulse_magnitude": float(math.sqrt(shot.jd**2 + shot.je**2 + shot.jr**2)),
        },
        "initial_state_rotating_post_impulse": result.initial_state.tolist(),
        "initial_state_barycentric_inertial_post_impulse": inertial_initial.tolist(),
        "final_state_rotating_post_impulse": result.final_state.tolist(),
        "cycle_period": result.period,
        "cycle_period_days": result.period * system.time_unit_days if system.time_unit_days else None,
        "atmospheric_encounters": len(result.arcs),
        "position_closure_norm": result.position_residual,
        "velocity_closure_norm": result.velocity_residual,
        "closure_vector": result.closure.tolist(),
        "periapsis_radii": result.periapsis_radii,
        "minimum_primary_distance": float(np.min(d_primary)),
        "minimum_secondary_distance": float(np.min(d_secondary)),
        "minimum_secondary_altitude_km": (
            (float(np.min(d_secondary)) - system.rho2) * system.separation_km
            if system.separation_km
            else None
        ),
        "secondary_encounter": {
            "closest_time": float(times[closest_index]),
            "incoming_sample_time": float(times[before]),
            "outgoing_sample_time": float(times[after]),
            "sample_radius": target,
            "incoming_velocity_secondary_relative": incoming.tolist(),
            "outgoing_velocity_secondary_relative": outgoing.tolist(),
            "turning_angle_deg": turning,
        },
        "encounter_plane_excursions_deg": excursions,
        "maximum_encounter_plane_excursion_deg": max(excursions),
        "legacy_encounter_plane_excursion_reference_frame": "lunar rotating axes; includes coordinate rotation",
        "encounter_initial_inertial_plane_excursions_deg": inertial_excursions,
        "maximum_encounter_initial_inertial_plane_excursion_deg": max(inertial_excursions),
        "lunar_plane_geometry": {
            "minimum_osculating_inclination_deg": float(np.min(lunar_inclination)),
            "maximum_osculating_inclination_deg": float(np.max(lunar_inclination)),
            "maximum_absolute_position_latitude_deg": float(np.max(np.abs(position_latitude))),
            "note": "Original encounter-plane excursions measure drift from the INITIAL plane, not the lunar plane.",
        },
        "encounters": encounters,
        "aerodynamic_interpretation": atmosphere_ld(shot, result, sigmas),
        "history": {
            "time": times.tolist(),
            "state_rotating": states.tolist(),
            "specific_primary_energy": (0.5 * np.sum(w * w, axis=1) - system.mu1 / d_primary).tolist(),
            "angular_momentum_vector": np.cross(q, w).tolist(),
            "jacobi": [jacobi(state, system.mu) for state in states],
        },
    }
