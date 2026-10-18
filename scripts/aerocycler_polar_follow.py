#!/usr/bin/env python3
"""Follow identified polar branches in primary radius and departure heading."""
import argparse
import json
from pathlib import Path

from aerocycler import Family, earth_moon_system
from aerocycler.polar import audit_polar_return,correct_at_heading,flight,reversed_return_parameters,system_at_radius


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family',default='1:1')
    parser.add_argument('--radii',nargs='+',type=float,default=[1])
    parser.add_argument('--headings',nargs='+',type=float,default=[2,1,0,-1,-2,-3,-4])
    parser.add_argument('--seed',nargs=4,type=float,default=[-.36167433711223235,.3073382713182775,-.48726387472713606,.03424754758757808])
    parser.add_argument('--tag',default='headings')
    parser.add_argument('--deviation-limit',type=float,default=5)
    parser.add_argument('--reverse',action='store_true',help='Construct and independently propagate the reversed-coast branch.')
    args=parser.parse_args()
    base=earth_moon_system()
    family=Family(*map(int,args.family.split(':')))
    x=args.seed
    out=Path(__file__).resolve().parents[1]/'results/aerocycler/polar'
    out.mkdir(parents=True,exist_ok=True)
    records=[]
    for factor in args.radii:
        system=system_at_radius(base,factor)
        for heading in args.headings:
            x,residual=correct_at_heading(x,system,family,deviation_deg=heading)
            shot,result=flight(x,system,family,tight=True,dense=True)
            audit_x=x
            if args.reverse and result.success:
                audit_x=reversed_return_parameters(result,system)
                audit_x,residual=correct_at_heading(audit_x,system,family,deviation_deg=float(audit_x[3]*180/3.141592653589793))
                shot,result=flight(audit_x,system,family,tight=True,dense=True)
            audit=audit_polar_return(system,family,shot,result,solid_radius=factor*base.rho1,
                                     deviation_limit_deg=args.deviation_limit)
            record=dict(radius_factor=factor,heading_deviation=heading,x=audit_x.tolist(),residual=residual.tolist(),
                        accepted=audit['accepted_idealized_return'],rejections=audit['rejection_reasons'])
            if result.success:
                record.update({k:audit[k] for k in ['period_days','period_in_lunar_months',
                    'maximum_primary_pass_departure_from_polar_deg','primary_pass_inclinations_deg',
                    'minimum_secondary_altitude_km','minimum_primary_clearance_km','position_closure_norm','velocity_closure_norm',
                    'impulse_local_components_m_s']})
                record['maximum_local_ld']=audit['bank']['maximum_local_ld']
            records.append(record)
            if record['accepted']:
                path=out/f'follow_{args.tag}_r{factor:g}_d{heading:g}.json'
                path.write_text(json.dumps(audit,indent=2,allow_nan=False)+'\n')
                record['candidate_file']=path.name
            print(json.dumps(record),flush=True)
            (out/f'continuation_{args.tag}.json').write_text(json.dumps(records,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    main()
