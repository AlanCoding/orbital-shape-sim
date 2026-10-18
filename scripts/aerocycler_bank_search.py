#!/usr/bin/env python3
"""Exploratory same-position returns; no radial closure impulse is allowed.

Run with PYTHONPATH=src .env/bin/python scripts/aerocycler_bank_search.py.
This initial search writes candidates, including rejected roots, to a separate
file so it cannot overwrite the original investigation.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.optimize import least_squares

from aerocycler import Family, earth_moon_system
from aerocycler.banking import describe_return, return_flight


def evaluate(x, system, family, inclination, *, tight=False, dense=False):
    return return_flight(x, system, family, inclination,rtol=2e-12 if tight else 2e-9,
                         atol=2e-14 if tight else 2e-11,
                         max_step=.03 if tight else .12,dense_output=dense)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--radius-factor', type=float, default=1.0)
    parser.add_argument('--months', type=int, choices=(1, 2), default=1)
    parser.add_argument('--loops', type=int, default=1)
    parser.add_argument('--inclination', type=float, default=5.0)
    parser.add_argument('--starts', type=int, default=12)
    parser.add_argument('--interface-altitude-km',type=float,default=100.0)
    parser.add_argument('--initial-latitude',type=float,default=0.0,
                        help='Initial latitude guess in degrees; -4 is useful on the passive monthly branch.')
    args = parser.parse_args()
    system = earth_moon_system()
    if args.radius_factor <= 0 or args.loops < 1 or args.starts < 1 or args.interface_altitude_km < 0:
        parser.error('radius, loops, and starts must be positive; interface altitude must be nonnegative')
    solid_radius=system.rho1*args.radius_factor
    system = replace(system, rho1=solid_radius+args.interface_altitude_km/system.separation_km)
    family = Family(args.loops, args.months)
    inclination = math.radians(args.inclination)
    a = (system.mu1 * (args.months/args.loops)**2)**(1/3)
    speed = math.sqrt(system.mu1 * (2/system.rho1 - 1/a))
    records = []
    def fun(x):
        _, result = evaluate(x, system, family, inclination)
        return ((result.final_state[:3] - result.initial_state[:3]) / system.rho1
                if result.success else np.full(3, 100.0))
    for longitude in np.linspace(-math.pi, math.pi, args.starts, endpoint=False):
        start = time.monotonic()
        opt = least_squares(fun, [longitude, math.radians(args.initial_latitude), speed], diff_step=2e-5,
                            x_scale=[1, .1, .1], max_nfev=100,
                            bounds=([-10, -.3, speed-.15], [10, .3, speed+.15]),
                            ftol=1e-10, xtol=1e-10, gtol=1e-10)
        if np.linalg.norm(fun(opt.x)) < 1e-6:
            def tight_fun(x):
                _, result = evaluate(x, system, family, inclination, tight=True)
                return ((result.final_state[:3] - result.initial_state[:3]) / system.rho1
                        if result.success else np.full(3, 100.0))
            opt = least_squares(tight_fun, opt.x, diff_step=1e-6, x_scale=[1, .1, .1],
                                max_nfev=30, ftol=1e-12, xtol=1e-12, gtol=1e-12)
        shot, result = evaluate(opt.x, system, family, inclination, tight=True, dense=True)
        record = dict(start_longitude=float(longitude), x=opt.x.tolist(),
                      residual=float(np.linalg.norm(fun(opt.x))),
                      tight_position_residual=result.position_residual,
                      period=result.period if result.success else None,
                      integration_success=result.success, nfev=opt.nfev,
                      runtime_seconds=time.monotonic()-start)
        if result.success:
            audit=describe_return(system,family,shot,result,solid_radius=solid_radius)
            record.update({key:audit[key] for key in ['accepted_idealized_return','rejection_reasons',
                'period_days','position_closure_norm','velocity_closure_norm','periapsis_radii',
                'minimum_primary_clearance_km','minimum_secondary_altitude_km',
                'maximum_osculating_inclination_deg','fraction_time_within_5deg_of_lunar_plane',
                'fraction_time_within_10deg_of_lunar_plane']})
            record['bank']={k:v for k,v in audit['bank'].items() if k not in ['angles_deg','local_ld']}
            record['finite_impulse_work']=audit['finite_impulse_work']
        else:
            record.update(accepted_idealized_return=False,rejection_reasons=[result.message])
        records.append(record)
        print(json.dumps(record,allow_nan=False), flush=True)
    path = Path(__file__).resolve().parents[1]/'results/aerocycler'/f'bank_search_r{args.radius_factor:g}_{args.loops}_{args.months}m_i{args.inclination:g}_h{args.interface_altitude_km:g}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(dict(arguments=vars(args), candidates=records), indent=2,allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
