"""Low-order returns with a passive, Jacobi-neutral periapsis bank.

Coast through N periapses, applying a bank only at the last one.  Unlike the
original identical-impulse problem, intermediate periapses can be higher
than the atmosphere.  Surface clearance is checked at ALL of them.
"""
from __future__ import annotations

import math
import numpy as np

from .aerodynamics import bank_path, bank_to_angle, impulse_work, tangent_basis
from .dynamics import jacobi
from .model import SystemParameters
from .shooting import Family, Shot, ShotResult, propagate_cycle


def return_flight(x: np.ndarray, system: SystemParameters, family: Family,
                  inclination: float, *, rtol: float = 2e-12, atol: float = 2e-14,
                  dense_output: bool = False, max_step: float = 0.03) -> tuple[Shot, ShotResult]:
    """x = longitude, latitude, inertial tangential speed.

    Inclination here is the local velocity angle above east, NOT necessarily
    the osculating orbital inclination.  The latter also depends on latitude.
    All angles are in radians.
    """
    longitude, latitude, speed = x
    shot = Shot(longitude, latitude, speed*math.cos(inclination), speed*math.sin(inclination))
    return shot, propagate_cycle(system, family, shot, rtol=rtol, atol=atol,
                                  max_step=max_step, dense_output=dense_output)


def uniform_history(result: ShotResult, count: int = 30001) -> tuple[np.ndarray, np.ndarray]:
    """Uniform time samples: percentages must not overweight adaptive steps."""
    times = np.linspace(0, result.period, count)
    states = np.full((count,6), np.nan)
    for arc in result.arcs:
        for solution in arc.solutions:
            mask = (times >= solution.t[0]) & (times <= solution.t[-1])
            if np.any(mask):
                if solution.sol is None:
                    raise ValueError("uniform history requires dense output")
                states[mask] = solution.sol(times[mask]).T
    if not np.all(np.isfinite(states)):
        raise ValueError("incomplete flight history")
    return times, states


def describe_return(system: SystemParameters, family: Family, shot: Shot,
                    result: ShotResult, *, solid_radius: float,
                    spin_axis_inertial: np.ndarray | None = None) -> dict:
    """Reconstruct the final bank and audit full closure, work, and clearance."""
    if not result.success:
        return {"accepted_idealized_return": False, "rejection_reasons": [result.message]}
    times, states = uniform_history(result)
    pre = result.final_state
    elon, elat = tangent_basis(result.initial_state[:3])
    target_angle = math.atan2(float(result.initial_state[3:]@elat),
                             float(result.initial_state[3:]@elon))
    post = bank_to_angle(pre, target_angle)
    closure = post-result.initial_state
    kwargs = dict(time=result.period, spin_axis_inertial=spin_axis_inertial)
    bank = bank_path(pre, target_angle, system.primary_rotation_ratio, **kwargs)
    ledger = impulse_work(pre, post, system.primary_rotation_ratio, **kwargs)
    east, north = tangent_basis(pre[:3])
    radial = pre[:3]/np.linalg.norm(pre[:3])
    local_axes = np.array([east, north, radial])
    velocity_unit_m_s = system.velocity_unit_km_s*1000
    local_delta = local_axes@(post[3:]-pre[3:])*velocity_unit_m_s
    q = states[:,:3]
    radius = np.linalg.norm(q,axis=1)
    latitudes = np.degrees(np.arcsin(np.clip(q[:,2]/radius,-1,1)))
    h = np.cross(q,states[:,3:]+np.cross([0,0,1],q))
    inclinations = np.degrees(np.arccos(np.clip(h[:,2]/np.linalg.norm(h,axis=1),-1,1)))
    lunar_distance = np.linalg.norm(q-[1,0,0],axis=1)
    # Uniform sampling misses brief periapses; exact event radii must be used.
    min_radius = float(min(radius.min(), system.rho1, *result.periapsis_radii))
    min_lunar_distance = float(lunar_distance.min())
    coast_drifts = [float(max(abs(jacobi(y, system.mu)-jacobi(sol.y[:,0],system.mu))
                             for y in sol.y.T))
                    for arc in result.arcs for sol in arc.solutions]
    reasons = []
    if np.linalg.norm(closure[:3]) > 1e-8 or np.linalg.norm(closure[3:]) > 1e-7:
        reasons.append("full state closure failed")
    if min_radius < solid_radius-1e-9:
        reasons.append("primary surface intersection")
    if any(radius < system.rho1-1e-9 for radius in result.periapsis_radii[:-1]):
        reasons.append("unmodeled intermediate atmospheric passage")
    if min_lunar_distance <= system.rho2:
        reasons.append("secondary surface intersection")
    if system.primary_rotation_ratio**2*solid_radius**3 >= system.mu1:
        reasons.append("primary rotation exceeds equatorial centrifugal breakup")
    if not bank['all_segments_passive']:
        reasons.append("bank requires nonpassive aerodynamic segments")
    if spin_axis_inertial is not None and np.linalg.norm(np.cross(spin_axis_inertial,[0,0,1])) > 1e-10:
        if abs(result.period/(2*math.pi)-round(result.period/(2*math.pi))) > 1e-8:
            reasons.append("tilted atmosphere does not repeat at the return period")
    index = int(np.argmin(lunar_distance))
    return {
        "schema": "aerocycler-bank-return-v1",
        "accepted_idealized_return": not reasons,
        "rejection_reasons": reasons,
        "seed_family": family.label,
        "actual_period_is_exact_seed_resonance": abs(result.period-2*math.pi*family.secondary_periods) < 1e-8,
        "earth_orbits_per_return": family.loops,
        "atmospheric_banks_per_return": 1,
        "system": {"mu": system.mu,"interface_radius": system.rho1,"solid_radius": solid_radius,
                   "secondary_radius": system.rho2,"separation_km": system.separation_km,
                   "lunar_period_days": system.period_days,"primary_rotation_ratio": system.primary_rotation_ratio,
                   "spin_axis_inertial": [0.,0.,1.] if spin_axis_inertial is None else spin_axis_inertial.tolist()},
        "shot": {"longitude": shot.longitude,"latitude": shot.latitude,"v_lon": shot.v_lon,"v_lat": shot.v_lat},
        "period": result.period,
        "period_days": result.period*system.time_unit_days,
        "period_in_lunar_months": result.period/(2*math.pi),
        "inertial_apsis_precession_per_return_deg": math.degrees(result.period-2*math.pi*family.secondary_periods),
        "initial_state": result.initial_state.tolist(), "pre_bank_state": pre.tolist(),
        "post_bank_state": post.tolist(), "impulse": (post[3:]-pre[3:]).tolist(),
        "impulse_local_components_m_s": {
            "east": float(local_delta[0]), "north": float(local_delta[1]),
            "radial_away_from_primary_center": float(local_delta[2]),
            "magnitude": float(np.linalg.norm(local_delta)),
        },
        "earth_pass_schedule": [
            {"pass": j+1, "time_days": arc.t1*system.time_unit_days,
             "altitude_km": (np.linalg.norm(arc.pre_state[:3])-solid_radius)*system.separation_km,
             "atmospheric_bank": j == len(result.arcs)-1}
            for j, arc in enumerate(result.arcs)
        ],
        "position_closure_norm": float(np.linalg.norm(closure[:3])),
        "velocity_closure_norm": float(np.linalg.norm(closure[3:])),
        "periapsis_radii": result.periapsis_radii,
        "minimum_primary_distance": min_radius,
        "minimum_primary_clearance_km": (min_radius-solid_radius)*system.separation_km,
        "minimum_secondary_distance": min_lunar_distance,
        "minimum_secondary_altitude_km": (min_lunar_distance-system.rho2)*system.separation_km,
        "closest_secondary_time": float(times[index]),
        "minimum_osculating_inclination_deg": float(min(inclinations)),
        "maximum_osculating_inclination_deg": float(max(inclinations)),
        "maximum_absolute_position_latitude_deg": float(max(abs(latitudes))),
        "minimum_signed_position_latitude_deg": float(min(latitudes)),
        "maximum_signed_position_latitude_deg": float(max(latitudes)),
        "time_rms_position_latitude_deg": float(np.sqrt(np.mean(latitudes**2))),
        "fraction_time_within_5deg_of_lunar_plane": float(np.mean(abs(latitudes)<=5)),
        "fraction_time_within_10deg_of_lunar_plane": float(np.mean(abs(latitudes)<=10)),
        "maximum_absolute_position_latitude_beyond_half_lunar_distance_deg": float(max(abs(latitudes[radius>.5]))),
        "maximum_coast_jacobi_drift": max(coast_drifts),
        "bank_jacobi_jump": jacobi(post,system.mu)-jacobi(pre,system.mu),
        "finite_impulse_work": ledger,
        "bank": bank,
        "history": {"time": times.tolist(),"state_rotating": states.tolist()},
        "limitations": ["Zero-duration bank at fixed position; no finite atmospheric flight is integrated.",
                        "No density, heating, structural loads, aero polar, or finite-altitude control constraints.",
                        "Circular point-mass gravity; no Sun, lunar eccentricity, primary oblateness, or orbit-stability claim.",
                        "Maximum required local L/D assumes an aerodynamic polar can supply the varying ratios along the bank."],
    }
