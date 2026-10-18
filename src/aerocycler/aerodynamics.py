"""Rotation-powered aerodynamic feasibility, independent of orbit closure.

The lunar rotating-frame energy is -C/2.  A passive atmosphere can restore
that energy only if lift does enough work in this frame to offset drag.
All velocities below use normalized primary-centered rotating coordinates.
"""
from __future__ import annotations

import math
import numpy as np

from .dynamics import EZ


def atmospheric_velocity(state: np.ndarray, sigma: float, *, time: float = 0.0,
                         spin_axis_inertial: np.ndarray | None = None) -> np.ndarray:
    """Atmospheric velocity in the lunar rotating frame.

    A tilted spin axis is fixed INERTIALLY, not in the lunar rotating frame.
    The default is aligned spin, as in the original investigation.
    """
    axis = EZ if spin_axis_inertial is None else np.asarray(spin_axis_inertial, dtype=float)
    axis = axis / np.linalg.norm(axis)
    c, s = math.cos(time), math.sin(time)
    rotating_axis = np.array([c*axis[0]+s*axis[1], -s*axis[0]+c*axis[1], axis[2]])
    return np.cross(sigma*rotating_axis-EZ, state[:3])


def neutral_ld_floor(state: np.ndarray, sigma: float, **kwargs) -> float:
    """Minimum local L/D permitting nonnegative rotating-frame aero work.

    This is a necessary bound, not an orbit-existence guarantee.  If every
    drag-producing atmospheric segment has a higher floor than vehicle L/D,
    a periodically closed orbit in the circular model is impossible.
    """
    v = state[3:]
    u = v-atmospheric_velocity(state, sigma, **kwargs)
    numerator = float(np.dot(v, u))
    denominator = float(np.linalg.norm(np.cross(v, u)))
    if numerator <= 0:
        return 0.0
    return math.inf if denominator <= 1e-15*np.linalg.norm(v)*np.linalg.norm(u) else numerator/denominator


def impulse_work(pre: np.ndarray, post: np.ndarray, sigma: float, **kwargs) -> dict[str, float]:
    """Exact work of a finite velocity change at fixed position.

    The midpoint identity, dv dot (v_before+v_after)/2, is exact.  Projecting
    dv against ONLY the incoming velocity instead drops |dv|^2/2 and can
    mistakenly declare an atmosphere-energy-increasing impulse passive.
    Negative relative work is necessary for passive aerodynamic realization;
    it does not by itself establish an admissible continuous force history.
    """
    if not np.allclose(pre[:3], post[:3], rtol=0, atol=1e-10):
        raise ValueError("finite-impulse work requires the same position")
    dv = post[3:]-pre[3:]
    midpoint = (pre[3:]+post[3:])/2
    atmosphere = atmospheric_velocity(pre, sigma, **kwargs)
    relative_midpoint = midpoint-atmosphere
    relative_work = float(np.dot(dv, relative_midpoint))
    return {
        "rotating_frame_work": float(np.dot(dv, midpoint)),
        "atmosphere_relative_work": relative_work,
        "incoming_projection_work": float(np.dot(dv, pre[3:]-atmosphere)),
        "omitted_quadratic_work": float(np.dot(dv, dv)/2),
        "angular_momentum_z_change": float(np.cross(pre[:3], dv)[2]),
    }


def tangent_basis(position: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    longitude = math.atan2(position[1], position[0])
    latitude = math.atan2(position[2], math.hypot(position[0], position[1]))
    elon = np.array([-math.sin(longitude), math.cos(longitude), 0.0])
    elat = np.array([-math.sin(latitude)*math.cos(longitude),
                     -math.sin(latitude)*math.sin(longitude), math.cos(latitude)])
    return elon, elat


def bank_to_angle(pre: np.ndarray, target_angle: float) -> np.ndarray:
    """Turn tangent rotating velocity at fixed speed; preserve Jacobi exactly.

    This is an idealized zero-duration periapsis maneuver.  Its continuous
    velocity-space path is analyzed separately; a finite atmospheric flight
    with density, heating, and altitude dynamics is not modeled here.
    """
    radial = float(np.dot(pre[:3], pre[3:])/np.linalg.norm(pre[:3]))
    if abs(radial) > 1e-7:
        raise ValueError("bank maneuver must start at a periapsis")
    elon, elat = tangent_basis(pre[:3])
    post = pre.copy()
    post[3:] = np.linalg.norm(pre[3:])*(math.cos(target_angle)*elon+math.sin(target_angle)*elat)
    return post


def bank_path(pre: np.ndarray, target_angle: float, sigma: float, samples: int = 2001, **kwargs) -> dict:
    """Resolve drag/lift at EVERY point along a Jacobi-neutral tangent turn."""
    elon, elat = tangent_basis(pre[:3])
    initial_angle = math.atan2(float(pre[3:]@elat), float(pre[3:]@elon))
    angles = np.linspace(initial_angle, target_angle, samples)
    direction = np.sign(target_angle-initial_angle)
    speed = float(np.linalg.norm(pre[3:]))
    velocities = speed*(np.cos(angles)[:,None]*elon+np.sin(angles)[:,None]*elat)
    derivatives = direction*speed*(-np.sin(angles)[:,None]*elon+np.cos(angles)[:,None]*elat)
    u = velocities-atmospheric_velocity(pre, sigma, **kwargs)
    uhat = u/np.linalg.norm(u,axis=1)[:,None]
    drag = -np.sum(derivatives*uhat,axis=1)
    lift = np.linalg.norm(derivatives+drag[:,None]*uhat,axis=1)
    valid = bool(np.all(drag > 1e-13))
    path_length = abs(angles-initial_angle)
    integrated_drag = float(np.trapezoid(drag,path_length))
    integrated_lift = float(np.trapezoid(lift,path_length))
    return {
        "model": "zero-duration fixed-position continuous velocity-space bank",
        "initial_angle_deg": math.degrees(initial_angle),
        "final_angle_deg": math.degrees(target_angle),
        "all_segments_passive": valid,
        "maximum_local_ld": float(np.max(lift/drag)) if valid else None,
        "minimum_local_ld": float(np.min(lift/drag)) if valid else None,
        "integrated_lift_over_drag": integrated_lift/integrated_drag if valid else None,
        "integrated_drag": integrated_drag,
        "integrated_lift": integrated_lift,
        "angles_deg": np.degrees(angles).tolist(),
        "local_ld": (lift/drag).tolist() if valid else None,
    }
