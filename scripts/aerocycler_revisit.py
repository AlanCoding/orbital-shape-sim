#!/usr/bin/env python3
"""Independently verify retained monthly bank returns and regenerate the review.

PYTHONPATH=src MPLCONFIGDIR=/tmp/mplconfig .env/bin/python scripts/aerocycler_revisit.py
No optimization is performed here.  Candidate constants are fixed inputs.
"""
from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from aerocycler import Family, earth_moon_system
from aerocycler.aerodynamics import impulse_work, neutral_ld_floor
from aerocycler.banking import describe_return, return_flight

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'results/aerocycler'
FIGURES=ROOT/'docs/assets/aerocycler/revisit'

# The solver changes initial position/speed, not atmospheric work or clearance.
# These initial conditions use an explicit 100 km atmospheric interface.
RETAINED={
    'synthetic_monthly_bank': (4., [1.5490606325993435,-.0702675728528885,5.3019347756483866]),
    'earth_monthly_bank': (1., [1.542126868450618,-.07183480131803806,10.755894238580616]),
}


def save(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def main():
    RESULTS.mkdir(parents=True,exist_ok=True)
    FIGURES.mkdir(parents=True,exist_ok=True)
    base=earth_moon_system()
    family=Family(2,1)
    reports={}
    for name,(factor,x) in RETAINED.items():
        solid_radius=factor*base.rho1
        system=replace(base,rho1=solid_radius+100/base.separation_km)
        shot,result=return_flight(np.array(x),system,family,math.radians(3),
                                  rtol=2e-13,atol=2e-15,max_step=.006,dense_output=True)
        report=describe_return(system,family,shot,result,solid_radius=solid_radius)
        report['system']['solid_radius_factor_vs_earth']=factor
        report['system']['atmospheric_interface_altitude_km']=100.
        # Repeat with a tighter tolerance and a different step limit.
        shot2,result2=return_flight(np.array(x),system,family,math.radians(3),
                                    rtol=3e-14,atol=3e-16,max_step=.004,dense_output=True)
        check=describe_return(system,family,shot2,result2,solid_radius=solid_radius)
        report['tolerance_check']={key:check[key] for key in ['position_closure_norm','velocity_closure_norm',
                    'maximum_coast_jacobi_drift','bank_jacobi_jump','period_days','minimum_primary_clearance_km']}
        report['tolerance_check']['maximum_local_ld']=check['bank']['maximum_local_ld']
        report['accepted_idealized_return']=report['accepted_idealized_return'] and check['accepted_idealized_return']
        reports[name]=report
        save(RESULTS/f'{name}.json',report)
    old_audit={}
    for name in ['earth_moon_4_2_baseline','earth_moon_4_2_je_0p002']:
        old=json.loads((RESULTS/f'{name}.json').read_text())
        states=np.array(old['history']['state_rotating'])
        q=states[:,:3]
        h=np.cross(q,states[:,3:]+np.cross([0,0,1],q))
        inc=np.degrees(np.arccos(np.clip(h[:,2]/np.linalg.norm(h,axis=1),-1,1)))
        old_audit[name]={
            'minimum_lunar_plane_inclination_deg':float(min(inc)),
            'maximum_lunar_plane_inclination_deg':float(max(inc)),
            'reported_initial_plane_drift_deg':old['maximum_encounter_plane_excursion_deg'],
            'legacy_drift_reference_frame': 'lunar rotating axes; includes coordinate rotation',
            'fixed_initial_inertial_plane_excursions_deg': old.get('encounter_initial_inertial_plane_excursions_deg'),
            'finite_impulse_work':[impulse_work(np.array(e['pre_state_rotating']),np.array(e['post_state_rotating']),
                                              base.primary_rotation_ratio) for e in old['encounters']],
        }
    save(RESULTS/'previous_branch_audit.json',old_audit)

    # A necessary bound for perigee speed on the nominal 2/1 Kepler seed.
    angles=np.linspace(.1,90,1000)
    floors={}
    for factor in [1,2,3,4]:
        rp=factor*base.rho1+100/base.separation_km
        a=(base.mu1*.5**2)**(1/3)
        speed=math.sqrt(base.mu1*(2/rp-1/a))
        curve=[]
        for angle in np.radians(angles):
            state=np.array([rp,0,0,0,speed*math.cos(angle)-rp,speed*math.sin(angle)])
            curve.append(neutral_ld_floor(state,base.primary_rotation_ratio))
        floors[str(factor)]={str(deg):float(np.interp(deg,angles,curve)) for deg in [5,10,20,30,90]}
        plt.semilogy(angles,curve,label=f'Primary radius {factor}× Earth')
    plt.axhline(50,color='black',ls='--',label='L/D = 50')
    plt.ylim(1,1000)
    plt.xlabel('Velocity inclination at equatorial periapsis (deg)')
    plt.ylabel('Necessary local L/D for neutral rotating-frame work')
    plt.title('Aligned-spin bound: a geometry constraint, not a closure result')
    plt.grid(alpha=.3,which='both')
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES/'01_rotation_bound.png',dpi=180)
    plt.close()
    save(RESULTS/'rotation_floor.json',dict(interface_altitude_km=100,floors=floors))

    report=reports['synthetic_monthly_bank']
    states=np.array(report['history']['state_rotating'])
    times=np.array(report['history']['time'])
    q=states[:,:3]
    solid=report['system']['solid_radius']
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,vertical in zip(axes,[1,2],strict=True):
        ax.plot(q[:,0],q[:,vertical],lw=.9,color='tab:blue')
        ax.add_patch(plt.Circle((0,0),solid,color='tab:blue',alpha=.3,label='Synthetic primary'))
        ax.add_patch(plt.Circle((1,0),base.rho2,color='grey',label='Moon'))
        ax.scatter(*q[0,[0,vertical]],marker='^',color='red',s=35,label='Atmospheric bank')
        ax.axhline(0,color='grey',lw=.5)
        ax.set(aspect='equal',xlabel='x / lunar distance',ylabel=('y' if vertical==1 else 'z')+' / lunar distance')
    axes[0].set_title('Lunar rotating frame: view in orbital plane')
    axes[1].set_title('Side view: actual departure from lunar plane')
    axes[0].legend(fontsize=8)
    for ax in axes:
        ax.set_ylim(-.7,.7)
    fig.suptitle(f"Two primary orbits in {report['period_days']:.3f} days; local L/D ≤ {report['bank']['maximum_local_ld']:.2f}")
    fig.tight_layout()
    fig.savefig(FIGURES/'02_monthly_trajectory.png',dpi=180)
    plt.close(fig)

    radius=np.linalg.norm(q,axis=1)
    lat=np.degrees(np.arcsin(q[:,2]/radius))
    h=np.cross(q,states[:,3:]+np.cross([0,0,1],q))
    inc=np.degrees(np.arccos(np.clip(h[:,2]/np.linalg.norm(h,axis=1),-1,1)))
    days=times*base.time_unit_days
    fig,axes=plt.subplots(3,1,figsize=(9,8),sharex=True)
    axes[0].plot(days,lat,label='Position latitude')
    axes[0].plot(days,inc,label='Osculating inclination',alpha=.7)
    axes[0].set(ylabel='Lunar-plane angle (deg)')
    axes[0].axhline(10,color='black',ls=':',lw=.8)
    axes[0].axhline(-10,color='black',ls=':',lw=.8)
    axes[0].legend()
    axes[1].plot(days,(radius-solid)*base.separation_km)
    axes[1].axhline(100,color='red',ls='--',label='Atmospheric interface (100 km)')
    axes[1].set(ylabel='Primary altitude (km)',yscale='log')
    axes[1].legend()
    axes[2].plot(days,np.linalg.norm(q-[1,0,0],axis=1)*base.separation_km)
    axes[2].set(xlabel='Time (days)',ylabel='Moon distance (km)')
    for ax in axes: ax.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(FIGURES/'03_geometry_and_clearance.png',dpi=180)
    plt.close(fig)

    b=report['bank']
    plt.plot(b['angles_deg'],b['local_ld'])
    plt.axhline(50,color='black',ls='--',label='L/D = 50')
    plt.xlabel('Local rotating-frame velocity angle above east (deg)')
    plt.ylabel('Required instantaneous L/D')
    plt.title('Passive neutral bank: every segment has positive drag')
    plt.grid(alpha=.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES/'04_bank_ld.png',dpi=180)
    plt.close()
    print(json.dumps({name:{'accepted':r['accepted_idealized_return'], 'period_days':r['period_days'],
                'max_local_ld':r['bank']['maximum_local_ld'], 'position_closure':r['position_closure_norm'],
                'velocity_closure':r['velocity_closure_norm'], 'minimum_primary_clearance_km':r['minimum_primary_clearance_km'],
                'fraction_time_within_5deg':r['fraction_time_within_5deg_of_lunar_plane'],
                'fraction_time_within_10deg':r['fraction_time_within_10deg_of_lunar_plane']} for name,r in reports.items()},indent=2))
    if not all(r['accepted_idealized_return'] for r in reports.values()):
        raise SystemExit('A retained candidate failed validation; inspect its rejection reasons.')


if __name__=='__main__':
    main()
