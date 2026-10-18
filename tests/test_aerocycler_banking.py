"""Physics checks: finite work, lunar-plane geometry, and passive bank closure."""
from dataclasses import replace
import math

import numpy as np

from aerocycler import Family, earth_moon_system
from aerocycler.aerodynamics import (
    atmospheric_velocity, bank_path, bank_to_angle, impulse_work,
    neutral_ld_floor, tangent_basis,
)
from aerocycler.banking import return_flight
from aerocycler.dynamics import jacobi, rhs


def test_rhs_component_form_matches_vector_equations():
    q=np.array([.2,-.3,.1])
    v=np.array([.5,.2,-.4])
    mu=.012
    scale=.7
    secondary=np.array([1.,0.,0.])
    expected=(-2*np.cross([0,0,1],v)+[q[0],q[1],0]
              -(1-mu)*q/np.linalg.norm(q)**3
              -scale*mu*((q-secondary)/np.linalg.norm(q-secondary)**3+secondary))
    assert np.allclose(rhs(0,np.r_[q,v],mu,scale),np.r_[v,expected],rtol=1e-14)


def test_incoming_projection_can_falsely_label_finite_turn_dissipative():
    pre=np.array([.02,0,0,0,10,0.])
    post=pre.copy()
    # Increase speed slightly while turning: incoming projection is negative,
    # but exact atmosphere-relative kinetic energy increases.
    angle=.1
    post[3:]=[0,10.001*math.cos(angle),10.001*math.sin(angle)]
    ledger=impulse_work(pre,post,0)
    assert ledger['incoming_projection_work']<0
    assert ledger['atmosphere_relative_work']>0
    assert abs(ledger['atmosphere_relative_work']-(np.dot(post[3:]+[0,.02,0],post[3:]+[0,.02,0])
                   -np.dot(pre[3:]+[0,.02,0],pre[3:]+[0,.02,0]))/2)<1e-12
    assert abs(ledger['atmosphere_relative_work']-ledger['incoming_projection_work']
               -ledger['omitted_quadratic_work'])<1e-12


def test_local_floor_has_correct_rotation_and_inclination_dependence():
    s=earth_moon_system()
    v=10.8
    for degrees in [5,10,30,90]:
        theta=math.radians(degrees)
        state=np.array([s.rho1,0,0,0,v*math.cos(theta),v*math.sin(theta)])
        a=(s.primary_rotation_ratio-1)*s.rho1
        expected=(v-a*math.cos(theta))/(a*math.sin(theta))
        assert math.isclose(neutral_ld_floor(state,s.primary_rotation_ratio),expected,rel_tol=1e-13)
    assert math.isinf(neutral_ld_floor(np.array([s.rho1,0,0,0,v,0]),s.primary_rotation_ratio))


def test_tilted_axis_rotates_in_synodic_coordinates_and_repeats_monthly():
    state=np.array([.02,.01,.003,0,10,0])
    axis=np.array([.2,.3,1.])
    a0=atmospheric_velocity(state,27,time=0,spin_axis_inertial=axis)
    a1=atmospheric_velocity(state,27,time=2*math.pi,spin_axis_inertial=axis)
    assert np.allclose(a0,a1,atol=1e-15)
    assert not np.allclose(a0,atmospheric_velocity(state,27,time=math.pi,spin_axis_inertial=axis))


def test_neutral_bank_is_passive_only_when_cranking_toward_aligned_plane():
    s=earth_moon_system()
    pre=np.array([s.rho1,0,0,0,10*math.cos(.2),10*math.sin(.2)])
    post=bank_to_angle(pre,.1)
    assert abs(jacobi(post,s.mu)-jacobi(pre,s.mu))<1e-12
    assert impulse_work(pre,post,s.primary_rotation_ratio)['atmosphere_relative_work']<0
    path=bank_path(pre,.1,s.primary_rotation_ratio)
    assert path['all_segments_passive']
    assert math.isclose(path['maximum_local_ld'],neutral_ld_floor(post,s.primary_rotation_ratio),rel_tol=1e-12)
    assert not bank_path(post,.2,s.primary_rotation_ratio)['all_segments_passive']
    assert not bank_path(pre,-.1,s.primary_rotation_ratio)['all_segments_passive']


def test_synthetic_monthly_return_closes_after_passive_bank_and_clears_surface():
    base=earth_moon_system()
    system=replace(base,rho1=4*base.rho1+100/base.separation_km)
    x=np.array([1.5490606325993435,-.0702675728528885,5.3019347756483866])
    _,flight=return_flight(x,system,Family(2,1),math.radians(3),rtol=2e-13,atol=2e-15,max_step=.006)
    assert flight.success
    elon,elat=tangent_basis(flight.initial_state[:3])
    angle=math.atan2(flight.initial_state[3:]@elat,flight.initial_state[3:]@elon)
    post=bank_to_angle(flight.final_state,angle)
    assert np.linalg.norm(post[:3]-flight.initial_state[:3])<2e-9
    assert np.linalg.norm(post[3:]-flight.initial_state[3:])<2e-7
    assert min(flight.periapsis_radii)>=system.rho1-2e-9
    path=bank_path(flight.final_state,angle,system.primary_rotation_ratio)
    assert path['all_segments_passive']
    assert path['maximum_local_ld']<38
    assert 26<flight.period*system.time_unit_days<28
