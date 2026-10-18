#!/usr/bin/env python3
"""Probe radius changes on the passive monthly-return branch.

Exploratory zero-altitude interfaces; not the independently verified 100 km
retained results. Surface clearance and centrifugal breakup must be checked
separately before treating a radius-sweep point as a physical candidate.
"""
from dataclasses import replace
import json
import math
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from aerocycler import Family, earth_moon_system
from aerocycler.diagnostics import sample_result
from aerocycler_bank_search import evaluate

base = earth_moon_system()
family = Family(2,1)
inc = math.radians(3)
x0 = np.array([1.5489985398832609,-.07034615960023355,5.312880971370262])
records = []
for factors in ([4,3.8,3.5,3,2.5,2,1.8,1.5,1.2,1], [4.2,4.5,5,6,7,8]):
    x = x0.copy()
    previous_radius = 4*base.rho1
    for factor in factors:
        system = replace(base,rho1=factor*base.rho1)
        x[2] = math.sqrt(x[2]**2+2*base.mu1*(1/system.rho1-1/previous_radius))
        previous_radius=system.rho1
        def fun(x):
            _,r=evaluate(x,system,family,inc,tight=True)
            return (r.final_state[:3]-r.initial_state[:3])/system.rho1 if r.success else np.ones(3)*100
        opt=least_squares(fun,x,diff_step=1e-6,x_scale=[1,.1,.1],max_nfev=60,ftol=1e-12,xtol=1e-12,gtol=1e-12)
        x=opt.x
        _,r=evaluate(x,system,family,inc,tight=True,dense=True)
        t,y=sample_result(r)
        h=np.cross(y[:,:3],y[:,3:]+np.cross([0,0,1],y[:,:3]))
        angles=np.degrees(np.arccos(np.clip(h[:,2]/np.linalg.norm(h,axis=1),-1,1)))
        lon,lat=x[:2]
        elon=np.array([-math.sin(lon),math.cos(lon),0])
        elat=np.array([-math.sin(lat)*math.cos(lon),-math.sin(lat)*math.sin(lon),math.cos(lat)])
        pre=r.final_state[3:]
        post=r.initial_state[3:]
        before=math.atan2(pre@elat,pre@elon)
        after=math.atan2(post@elat,post@elon)
        a=(system.primary_rotation_ratio-1)*system.rho1*math.cos(lat)
        ld=(np.linalg.norm(post)-a*math.cos(after))/(a*abs(math.sin(after)))
        rec=dict(radius_factor=factor,x=x.tolist(),closure=r.position_residual,period=r.period,
                 passive=bool(before>after>0),bank_before_deg=math.degrees(before),bank_after_deg=math.degrees(after),
                 local_ld_max=ld,max_inclination=float(max(angles)),
                 max_position_latitude=float(max(np.degrees(np.arcsin(abs(y[:,2])/np.linalg.norm(y[:,:3],axis=1))))),
                 min_moon_distance=float(min(np.linalg.norm(y[:,:3]-[1,0,0],axis=1))),
                 periapsis_radii=r.periapsis_radii)
        records.append(rec)
        print(json.dumps(rec),flush=True)
Path('results/aerocycler/radius_continuation_i3.json').write_text(json.dumps(records,indent=2)+'\n')
