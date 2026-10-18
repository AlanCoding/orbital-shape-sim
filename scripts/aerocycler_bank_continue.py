#!/usr/bin/env python3
"""Continue a same-position return with a Jacobi-neutral bank maneuver.

Exploratory zero-altitude interface; the separately verified retained result
adds an explicit 100 km interface. Every trial prints full position/radius
diagnostics, and passive here refers only to the bank's force directions.
"""
from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from aerocycler import Family, earth_moon_system
from aerocycler.diagnostics import sample_result
from aerocycler_bank_search import evaluate


def main():
    system = earth_moon_system()
    system = replace(system, rho1=4*system.rho1)
    family = Family(2, 1)
    x = np.array([1.5308601230468288, -0.06399392502396124, 5.313027772689652])
    records = []
    for degrees in [5, 4, 3, 2.5, 2, 1.5, 1, .5]:
        inclination = math.radians(degrees)
        def fun(x):
            _, result = evaluate(x, system, family, inclination, tight=True)
            return ((result.final_state[:3] - result.initial_state[:3]) / system.rho1
                    if result.success else np.full(3, 100.0))
        opt = least_squares(fun, x, diff_step=1e-6, x_scale=[1,.1,.1],
                            ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=50)
        x = opt.x
        shot, result = evaluate(x, system, family, inclination, tight=True, dense=True)
        times, history = sample_result(result)
        h = np.cross(history[:,:3], history[:,3:]+np.cross([0,0,1],history[:,:3]))
        incl = np.degrees(np.arccos(np.clip(h[:,2]/np.linalg.norm(h,axis=1),-1,1)))
        q = result.initial_state[:3]
        lon, lat = x[:2]
        elon = np.array([-math.sin(lon), math.cos(lon),0])
        elat = np.array([-math.sin(lat)*math.cos(lon),-math.sin(lat)*math.sin(lon),math.cos(lat)])
        pre = result.final_state[3:]
        post = result.initial_state[3:]
        before = math.atan2(pre@elat,pre@elon)
        after = math.atan2(post@elat,post@elon)
        v = np.linalg.norm(post)
        a = (system.primary_rotation_ratio-1)*system.rho1*math.cos(lat)
        angles = np.linspace(before, after, 1001)
        ld = (v-a*np.cos(angles))/(a*np.abs(np.sin(angles)))
        record = dict(degrees=degrees, x=x.tolist(), position_closure=result.position_residual,
                      period=result.period, periapsis_radii=result.periapsis_radii,
                      min_primary_distance=float(np.min(np.linalg.norm(history[:,:3],axis=1))),
                      min_moon_distance=float(np.min(np.linalg.norm(history[:,:3]-[1,0,0],axis=1))),
                      max_inclination=float(np.max(incl)),
                      max_position_latitude=float(np.max(np.abs(np.degrees(np.arcsin(history[:,2]/np.linalg.norm(history[:,:3],axis=1)))))),
                      bank_before_deg=math.degrees(before),bank_after_deg=math.degrees(after),
                      local_ld_max=float(np.max(ld)),
                      passive=bool(before > after > 0),
                      initial_state=result.initial_state.tolist(), pre_state=result.final_state.tolist())
        records.append(record)
        print(json.dumps(record), flush=True)
    Path('results/aerocycler/bank_continuation_r4.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__ == '__main__':
    main()
