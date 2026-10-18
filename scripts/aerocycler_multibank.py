#!/usr/bin/env python3
"""Attempt three banks with equal periapsis radii and exactly one lunar month.

This is a FAILED exploratory corrector, retained for reproducibility. Inspect
closure/radius residuals; printed local bank ratios do not establish a root.
"""
from dataclasses import replace
import json
import math
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from aerocycler import Family, Shot, earth_moon_system, propagate_cycle
from aerocycler.aerodynamics import bank_path,bank_to_angle,tangent_basis

base=earth_moon_system()
family=Family(3,1)
factor=2.5
system=replace(base,rho1=factor*base.rho1)
seed=np.array([2.016318637130952,.03293256722933689,6.746762013148184,.14428784971011283])
seedshot=Shot(seed[0],seed[1],seed[2]*math.cos(seed[3]),seed[2]*math.sin(seed[3]))
r=propagate_cycle(system,family,seedshot)
initial_angles=[]
for arc in r.arcs[:-1]:
    e1,e2=tangent_basis(arc.pre_state[:3])
    initial_angles.append(math.atan2(arc.pre_state[3:]@e2,arc.pre_state[3:]@e1))
x0=np.r_[seed,initial_angles]

def evaluate(x,tight=False,dense=False):
    shot=Shot(x[0],x[1],x[2]*math.cos(x[3]),x[2]*math.sin(x[3]))
    state=shot.state(system.rho1)
    e1,e2=tangent_basis(state[:3])
    final_angle=math.atan2(state[3:]@e2,state[3:]@e1)
    angles=[*x[4:],final_angle]
    def control(index,pre):
        post=bank_to_angle(pre,angles[index])
        return post,post[3:]-pre[3:]
    return propagate_cycle(system,family,shot,periapsis_control=control,
                           rtol=2e-12 if tight else 2e-9,atol=2e-14 if tight else 2e-11,
                           max_step=.03 if tight else .08,dense_output=dense)

def fun(x,tight=False):
    r=evaluate(x,tight)
    if not r.success: return np.ones(6)*100
    return np.r_[r.closure[:3]/system.rho1,
                 (np.array(r.periapsis_radii[:-1])/system.rho1-1),r.period-2*np.pi]

records=[]
for guess in [x0,np.r_[seed,[0,0]],np.r_[seed,[-seed[3],seed[3]]],np.r_[seed,[seed[3],-seed[3]]]]:
    op=least_squares(fun,guess,diff_step=1e-5,x_scale=[1,.1,.1,.1,.1,.1],
                     max_nfev=150,ftol=1e-11,xtol=1e-11,gtol=1e-11)
    if np.linalg.norm(fun(op.x))<1e-5:
        op=least_squares(lambda x:fun(x,True),op.x,diff_step=1e-6,x_scale=[1,.1,.1,.1,.1,.1],
                         max_nfev=30,ftol=1e-12,xtol=1e-12,gtol=1e-12)
    r=evaluate(op.x,True,True)
    e1,_=tangent_basis(r.initial_state[:3])
    alpha=math.radians(23.44)
    axis=-math.sin(alpha)*e1+math.cos(alpha)*np.array([0,0,1])
    banks=[]
    for arc in r.arcs:
        e1,e2=tangent_basis(arc.post_state[:3])
        theta=math.atan2(arc.post_state[3:]@e2,arc.post_state[3:]@e1)
        b=bank_path(arc.pre_state,theta,system.primary_rotation_ratio,time=arc.t1,spin_axis_inertial=axis)
        banks.append({k:v for k,v in b.items() if k not in ['angles_deg','local_ld']})
    rec=dict(x=op.x.tolist(),residual=fun(op.x,True).tolist(),period=r.period,
             position_closure=r.position_residual,velocity_closure=r.velocity_residual,
             periapsis_radii=r.periapsis_radii,banks=banks)
    records.append(rec)
    print(json.dumps(rec),flush=True)
Path('results/aerocycler/multibank_exact_month.json').write_text(json.dumps(records,indent=2)+'\n')
