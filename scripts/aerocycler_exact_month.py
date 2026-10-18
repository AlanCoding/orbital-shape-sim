#!/usr/bin/env python3
"""Explore exact monthly 3/1 roots with an inertially fixed tilted spin.

Exploratory output includes failed correctors and surface-intersecting roots.
A low bank L/D in this file is NOT an accepted aerocycler. See the report's
rejected-leads section; only aerocycler_revisit.py validates retained returns.
"""
from dataclasses import replace
import json
import math
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from aerocycler import Family, earth_moon_system
from aerocycler.aerodynamics import bank_path, tangent_basis
from aerocycler_bank_search import evaluate

base=earth_moon_system()
family=Family(3,1)
x=np.array([2.04142911,.09843128,5.26051368,.18330856])
previous_radius=4*base.rho1
records=[]
for factor in [4,3.5,3,2.5,2,1.8,1.6,1.5,1.4,1.3,1.2,1.1,1]:
    system=replace(base,rho1=factor*base.rho1)
    x[2]=math.sqrt(x[2]**2+2*base.mu1*(1/system.rho1-1/previous_radius))
    previous_radius=system.rho1
    def fun(x):
        _,r=evaluate(x[:3],system,family,x[3],tight=True)
        return np.r_[(r.final_state[:3]-r.initial_state[:3])/system.rho1,r.period-2*np.pi] if r.success else np.ones(4)*100
    op=least_squares(fun,x,diff_step=1e-6,x_scale=[1,.1,.1,.1],max_nfev=60,ftol=1e-12,xtol=1e-12,gtol=1e-12)
    x=op.x
    _,r=evaluate(x[:3],system,family,x[3],tight=True,dense=True)
    t=np.linspace(0,r.period,20001)
    y=np.empty((len(t),6))
    for arc in r.arcs:
        for sol in arc.solutions:
            m=(t>=sol.t[0])&(t<=sol.t[-1])
            if np.any(m): y[m]=sol.sol(t[m]).T
    q=y[:,:3]
    rad=np.linalg.norm(q,axis=1)
    lat=np.degrees(np.arcsin(np.clip(abs(q[:,2])/rad,0,1)))
    h=np.cross(q,y[:,3:]+np.cross([0,0,1],q))
    inc=np.degrees(np.arccos(np.clip(h[:,2]/np.linalg.norm(h,axis=1),-1,1)))
    e1,e2=tangent_basis(r.final_state[:3])
    theta=math.atan2(r.initial_state[3:]@e2,r.initial_state[3:]@e1)
    spin_cases={}
    for tilt in [18.28,23.44,28.58]:
        alpha=math.radians(tilt)
        axis=-math.sin(alpha)*e1+math.cos(alpha)*np.array([0,0,1])
        bank=bank_path(r.final_state,theta,system.primary_rotation_ratio,time=r.period,spin_axis_inertial=axis)
        spin_cases[str(tilt)]={k:v for k,v in bank.items() if k not in ['angles_deg','local_ld']}
    rec=dict(radius_factor=factor,x=x.tolist(),residual=fun(x).tolist(),position_closure=r.position_residual,
             period=r.period,periapsis_radii=r.periapsis_radii,max_inclination=float(max(inc)),
             max_position_latitude=float(max(lat)),fraction_time_within_5deg=float(np.mean(lat<=5)),
             fraction_time_within_10deg=float(np.mean(lat<=10)),outer_max_position_latitude=float(max(lat[rad>.5])),
             min_moon_distance=float(min(np.linalg.norm(q-[1,0,0],axis=1))),spin_cases=spin_cases,
             initial_state=r.initial_state.tolist(),pre_state=r.final_state.tolist())
    records.append(rec)
    print(json.dumps({k:v for k,v in rec.items() if k not in ['initial_state','pre_state']}),flush=True)
Path('results/aerocycler/exact_month_radius_continuation.json').write_text(json.dumps(records,indent=2)+'\n')
