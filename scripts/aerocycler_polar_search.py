#!/usr/bin/env python3
"""Search explicitly near-polar primary passes, preserving rejected trials.

Resonance N:M means N primary orbits in M secondary periods as a Kepler
seed. Actual return periods are reported separately; --exact-period also
enforces M secondary periods instead of treating that timing as a seed.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

import numpy as np

from aerocycler import Family, earth_moon_system
from aerocycler.polar import audit_polar_return, correct_return, flight, seed_energy, system_at_radius


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--families', nargs='+', default=['1:1','2:1','3:2'])
    parser.add_argument('--radii', nargs='+', type=float, default=[1.,2.,4.])
    parser.add_argument('--starts', type=int, default=8)
    parser.add_argument('--deviation-limit', type=float, default=5.)
    parser.add_argument('--max-nfev', type=int, default=60)
    parser.add_argument('--exact-period', action='store_true')
    parser.add_argument('--tag', default='initial')
    args = parser.parse_args()
    base = earth_moon_system()
    out = Path(__file__).resolve().parents[1]/'results/aerocycler/polar'
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for label in args.families:
        family = Family(*map(int,label.split(':')))
        for factor in args.radii:
            system = system_at_radius(base, factor)
            for j, longitude in enumerate(np.linspace(-math.pi,math.pi,args.starts,endpoint=False)):
                start = time.monotonic()
                x0 = [longitude, 0., seed_energy(system,family), math.radians((-1,1)[j%2])]
                fit, residual = correct_return(x0,system,family,deviation_limit_deg=args.deviation_limit,
                                               exact_period=args.exact_period,max_nfev=args.max_nfev)
                shot, result = flight(fit.x,system,family,tight=True,dense=True)
                record = dict(family=label,radius_factor=factor,start_longitude=float(longitude),
                              x=fit.x.tolist(),residual=residual.tolist(),nfev=fit.nfev,
                              runtime_seconds=time.monotonic()-start)
                if result.success:
                    audit = audit_polar_return(system,family,shot,result,solid_radius=factor*base.rho1,
                                              deviation_limit_deg=args.deviation_limit,exact_period=args.exact_period)
                    record.update({key:audit[key] for key in ['accepted_idealized_return','rejection_reasons',
                        'period_days','period_in_lunar_months','position_closure_norm','velocity_closure_norm',
                        'primary_pass_inclinations_deg','maximum_primary_pass_departure_from_polar_deg',
                        'periapsis_radii','minimum_primary_clearance_km','minimum_secondary_altitude_km',
                        'impulse_local_components_m_s']})
                    record['maximum_local_ld'] = audit['bank']['maximum_local_ld']
                    record['bank_angle_change_deg'] = audit['bank']['final_angle_deg']-audit['bank']['initial_angle_deg']
                    if audit['accepted_idealized_return']:
                        name = f"candidate_{label.replace(':','_')}_r{factor:g}_{args.tag}_{j}.json"
                        (out/name).write_text(json.dumps(audit,indent=2,allow_nan=False)+'\n')
                        record['validated_candidate_file'] = name
                else:
                    record.update(accepted_idealized_return=False,rejection_reasons=[result.message])
                records.append(record)
                print(json.dumps(record,allow_nan=False),flush=True)
                (out/f'search_{args.tag}.json').write_text(json.dumps(dict(arguments=vars(args),trials=records),indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    main()
