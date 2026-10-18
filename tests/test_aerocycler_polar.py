"""Tests for the intended polar geometry and rotation-powered closure."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from aerocycler import Family, earth_moon_system
from aerocycler.banking import return_flight
from aerocycler.dynamics import inertial_relative_velocity, rhs
from aerocycler.polar import audit_polar_return, flight, system_at_radius


CHECKPOINTS=json.loads((Path(__file__).resolve().parents[1]/'results/aerocycler/polar/checkpoints.json').read_text())


@pytest.fixture(scope='module',params=['earth_1_1','toy4_3_2'])
def polar_return(request):
    base=earth_moon_system()
    data=CHECKPOINTS[request.param]
    system=system_at_radius(base,data['radius'])
    family=Family(*data['family'])
    shot,result=flight(data['x'],system,family,rtol=2e-13,atol=2e-15,max_step=.006,dense=True)
    report=audit_polar_return(system,family,shot,result,solid_radius=data['radius']*base.rho1)
    return base,system,family,shot,result,report


def test_polar_roots_close_with_eastward_aerodynamic_impulse(polar_return):
    base,system,family,shot,result,report=polar_return
    assert report['accepted_idealized_return'],report['rejection_reasons']
    assert report['position_closure_norm']<2e-11
    assert report['velocity_closure_norm']<1e-8
    assert report['maximum_primary_pass_departure_from_polar_deg']<2
    impulse=report['impulse_local_components_m_s']
    assert impulse['east']>100
    assert abs(impulse['north'])<2
    assert abs(impulse['radial_away_from_primary_center'])<1e-5
    assert report['bank']['all_segments_passive']
    assert report['bank']['maximum_local_ld']<26
    assert len(result.arcs)==family.loops
    assert all(r>=system.rho1-1e-9 for r in result.periapsis_radii)


def test_polar_bank_extracts_rotation_and_balances_orbital_energy(polar_return):
    base,system,family,shot,result,report=polar_return
    pre=np.array(report['pre_bank_state'])
    post=np.array(report['post_bank_state'])
    dv=post[3:]-pre[3:]
    wmid=(inertial_relative_velocity(pre)+inertial_relative_velocity(post))/2
    atmosphere=base.primary_rotation_ratio*np.cross([0,0,1],pre[:3])
    orbital_work=float(dv@wmid)
    dissipation=-float(dv@(wmid-atmosphere))
    rotational_work=float(dv@atmosphere)
    assert orbital_work>0
    assert dissipation>0
    assert math.isclose(rotational_work,orbital_work+dissipation,rel_tol=1e-12)
    assert abs(report['bank_jacobi_jump'])<1e-11
    assert abs(report['finite_impulse_work']['rotating_frame_work'])<1e-11


def test_nominal_resonance_is_not_mislabeled_as_exact(polar_return):
    base,system,family,shot,result,report=polar_return
    assert not report['actual_period_is_exact_seed_resonance']
    assert abs(report['seed_cycle_period_relative_error'])<.005
    exact=audit_polar_return(system,family,shot,result,solid_radius=system.rho1-100/base.separation_km,
                             exact_period=True)
    assert not exact['accepted_idealized_return']
    assert 'actual cycle period does not match the requested resonance timing' in exact['rejection_reasons']


def test_coplanar_success_is_rejected_as_a_polar_solution():
    base=earth_moon_system()
    system=system_at_radius(base,4)
    family=Family(2,1)
    shot,result=return_flight(np.array([1.5490606325993435,-.0702675728528885,5.3019347756483866]),
                              system,family,math.radians(3),dense_output=True)
    report=audit_polar_return(system,family,shot,result,solid_radius=4*base.rho1)
    assert not report['accepted_idealized_return']
    assert 'a primary pass exceeds the allowed departure from polar' in report['rejection_reasons']


def test_reversing_symmetry_matches_coast_equations():
    state=np.array([.2,-.3,.1,.4,-.5,.6])
    transform=np.array([1.,-1.,-1.,-1.,1.,1.])
    assert np.allclose(rhs(0,transform*state,.012),-transform*rhs(0,state,.012),rtol=1e-14,atol=1e-14)
