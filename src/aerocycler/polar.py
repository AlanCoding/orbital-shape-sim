"""Near-polar, rotation-powered periapsis return search.

Angles are measured explicitly relative to the primary spin axis (aligned
with the secondary orbital normal). A bounded initial heading prevents the
optimizer from substituting an eastward/coplanar orbit. Incoming inclinations
at EVERY primary pass are independently checked after propagation.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
from scipy.optimize import least_squares

from .aerodynamics import tangent_basis
from .banking import describe_return
from .dynamics import inertial_relative_velocity
from .model import SystemParameters
from .shooting import Family, Shot, propagate_cycle


def system_at_radius(base: SystemParameters, factor: float, altitude_km: float = 100.) -> SystemParameters:
    return replace(base, rho1=factor*base.rho1+altitude_km/base.separation_km)


def seed_energy(system: SystemParameters, family: Family) -> float:
    a = (system.mu1*(family.secondary_periods/family.loops)**2)**(1/3)
    return -system.mu1/(2*a)


def shot_from_parameters(x: np.ndarray, system: SystemParameters) -> Shot:
    longitude, latitude, energy, deviation = x
    speed2 = 2*(system.mu1/system.rho1+energy)
    if speed2 <= 0:
        raise ValueError('nonpositive initial tangential speed')
    speed = math.sqrt(speed2)
    return Shot(longitude, latitude, -speed*math.sin(deviation), speed*math.cos(deviation))


def flight(x, system, family, *, tight=False, dense=False, rtol=None, atol=None, max_step=None):
    shot = shot_from_parameters(np.asarray(x), system)
    result = propagate_cycle(system, family, shot,
        rtol=rtol if rtol is not None else (2e-12 if tight else 2e-9),
        atol=atol if atol is not None else (2e-14 if tight else 2e-11),
        max_step=max_step if max_step is not None else (.03 if tight else .12), dense_output=dense)
    return shot, result


def correct_return(x0, system, family, *, deviation_limit_deg=5., exact_period=False, max_nfev=60):
    """Correct position return with a hard near-polar departure bound.

    Energy is used instead of periapsis speed to improve scaling across
    primary radii. The final tangent bank preserves Jacobi; final speed
    closure therefore follows from position closure, and is verified later.
    """
    energy0 = seed_energy(system, family)
    spread = max(.4, abs(energy0)*.8)
    limit = math.radians(deviation_limit_deg)
    bounds = ([-4*math.pi, -.6, energy0-spread, -limit],
              [4*math.pi, .6, min(-.005, energy0+spread), limit])
    x0 = np.clip(np.asarray(x0), np.array(bounds[0])+1e-9, np.array(bounds[1])-1e-9)

    def residual(x, tight=False):
        _, result = flight(x, system, family, tight=tight)
        if not result.success:
            return np.full(4 if exact_period else 3, 100.)
        value = result.closure[:3]/system.rho1
        if exact_period:
            value = np.r_[value, result.period/(2*math.pi*family.secondary_periods)-1]
        return value

    options = dict(bounds=bounds, x_scale=[1., .1, .3, .05], diff_step=2e-5,
                   ftol=1e-10, xtol=1e-10, gtol=1e-10, max_nfev=max_nfev)
    fit = least_squares(residual, x0, **options)
    if np.linalg.norm(residual(fit.x)) < 2e-5:
        options.update(diff_step=2e-6, ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=25)
        fit = least_squares(lambda x: residual(x, True), fit.x, **options)
    return fit, residual(fit.x, True)


def inclination(state):
    h = np.cross(state[:3], inertial_relative_velocity(state))
    return math.degrees(math.acos(np.clip(h[2]/np.linalg.norm(h), -1, 1)))


def correct_at_heading(x0, system, family, *, deviation_deg, max_nfev=50):
    """Follow an existing return branch with fixed departure heading."""
    deviation = math.radians(deviation_deg)

    def residual(z, tight=False):
        _, result = flight(np.r_[z,deviation],system,family,tight=tight)
        return result.closure[:3]/system.rho1 if result.success else np.full(3,100.)

    options = dict(x_scale=[1.,.1,.3],diff_step=2e-5,max_nfev=max_nfev,
                   bounds=([-4*math.pi,-.8,-3.],[4*math.pi,.8,-.005]),
                   ftol=1e-10,xtol=1e-10,gtol=1e-10)
    fit = least_squares(residual,np.asarray(x0)[:3],**options)
    if np.linalg.norm(residual(fit.x))<2e-5:
        options.update(diff_step=1e-6,max_nfev=25,ftol=1e-12,xtol=1e-12,gtol=1e-12)
        fit = least_squares(lambda z:residual(z,True),fit.x,**options)
    return np.r_[fit.x,deviation], residual(fit.x,True)


def reversed_return_parameters(result, system):
    """Reverse a coast to seed the opposite aerodynamic-work branch.

    The aligned CR3BP is reversible under q'=(x,-y,-z), v'=(-vx,vy,vz).
    Begin at the transformed final PRE-bank state, so a westward/nonpassive
    closure maneuver becomes eastward/passive after reversing the cycle.
    This is a new orbit/impulse construction, not an assertion that physical
    drag itself is time-reversible. Full propagation and passivity are checked.
    """
    reflection = np.array([1.,-1.,-1.])
    old = result.final_state
    q = reflection*old[:3]
    v = -reflection*old[3:]
    state = np.r_[q,v]
    w = inertial_relative_velocity(state)
    east, north = tangent_basis(q)
    longitude = math.atan2(q[1],q[0])
    latitude = math.atan2(q[2],math.hypot(q[0],q[1]))
    energy = .5*np.dot(w,w)-system.mu1/system.rho1
    deviation = math.atan2(-float(w@east),float(w@north))
    return np.array([longitude,latitude,energy,deviation])


def audit_polar_return(system, family, shot, result, *, solid_radius, deviation_limit_deg=5.,
                       exact_period=False, period_relative_tolerance=.03):
    audit = describe_return(system, family, shot, result, solid_radius=solid_radius)
    if not result.success:
        return audit
    states = [result.initial_state, *[arc.pre_state for arc in result.arcs], np.array(audit['post_bank_state'])]
    inclinations = [inclination(state) for state in states]
    departures = [abs(i-90) for i in inclinations]
    if max(departures) > deviation_limit_deg+1e-6:
        audit['rejection_reasons'].append('a primary pass exceeds the allowed departure from polar')
    timing_error = result.period/(2*math.pi*family.secondary_periods)-1
    if abs(timing_error) > (1e-8 if exact_period else period_relative_tolerance):
        audit['rejection_reasons'].append('actual cycle period does not match the requested resonance timing')
    audit['accepted_idealized_return'] = not audit['rejection_reasons']
    audit['primary_pass_inclinations_deg'] = inclinations
    audit['maximum_primary_pass_departure_from_polar_deg'] = max(departures)
    audit['departure_limit_deg'] = deviation_limit_deg
    if audit['impulse_local_components_m_s']['magnitude'] < .001:
        audit['rejection_reasons'].append('impulse is too small to distinguish aerodynamic closure from integration error')
        audit['accepted_idealized_return'] = False
    audit['requested_exact_cycle_period'] = exact_period
    audit['seed_cycle_period_relative_error'] = timing_error
    east, north = tangent_basis(result.final_state[:3])
    pre = inertial_relative_velocity(result.final_state)
    audit['incoming_atmospheric_heading_deg_from_east'] = math.degrees(math.atan2(pre@north, pre@east))
    post = inertial_relative_velocity(np.array(audit['post_bank_state']))
    audit['outgoing_atmospheric_heading_deg_from_east'] = math.degrees(math.atan2(post@north, post@east))
    return audit
