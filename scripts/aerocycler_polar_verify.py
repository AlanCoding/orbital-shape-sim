#!/usr/bin/env python3
"""Fixed-input verification of explicitly polar return checkpoints.

Default: repropagate stored inputs twice; no optimizer. --refine is an
explicit research step that first corrects the exploratory inputs at high
accuracy and writes checkpoints.json. The complete search logs are separate.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares, minimize_scalar

from aerocycler import Family, earth_moon_system, propagate_cycle
from aerocycler.aerodynamics import bank_path, bank_to_angle, tangent_basis
from aerocycler.diagnostics import osculating_elements
from aerocycler.polar import audit_polar_return, flight, system_at_radius

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/aerocycler/polar'
FIGURES=ROOT/'docs/assets/aerocycler/polar'
INPUTS=OUT/'checkpoints.json'

# x = longitude, latitude, primary-relative Kepler energy, heading-90 deg.
# The last coordinate is radians, as are both position angles.
SEEDS={
 'earth_1_1': dict(radius=1.,family=[1,1],x=[-.3203099489174665,.3341623423392879,-.48798070391187176,-.022689280275926284]),
 'toy2_1_1': dict(radius=2.,family=[1,1],x=[-.39550586416155464,.4329350860212344,-.4869321955866154,-.022689280275926284]),
 'toy4_1_1': dict(radius=4.,family=[1,1],x=[-.5335970572344115,.5863050957778327,-.4850877146571089,-.022689280275926284]),
 'toy3_1_2': dict(radius=3.,family=[1,2],x=[-1.8651200575855198,.14533761709877624,-.27257253076145327,-.06370451769779303]),
 'toy4_1_2': dict(radius=4.,family=[1,2],x=[-1.818082295979565,.14195027155095796,-.27470451920048,-.06370451769779303]),
 'toy35_3_2': dict(radius=3.5,family=[3,2],x=[-3.227495506559405,-.009895728025704462,-.634273267860979,-.018468725078753596]),
 'toy4_3_2': dict(radius=4.,family=[3,2],x=[-3.2950361276864433,-.01216542981337289,-.6321015592527246,-.018468725078753596]),
 'toy3_1_4': dict(radius=3.,family=[1,4],x=[-1.784925696549553,.0969102253365203,-.1590441241826919,-.05632432314256492]),
 'toy4_1_4': dict(radius=4.,family=[1,4],x=[-1.7656155379923,.0864438943875525,-.1607405886710392,-.05632432314256492]),
}


def write(path, value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def refine(x,system,family):
    x=np.array(x)
    deviation=x[3]
    def residual(z):
        _,r=flight(np.r_[z,deviation],system,family,rtol=3e-14,atol=3e-16,max_step=.008)
        return r.closure[:3]/system.rho1 if r.success else np.full(3,100.)
    fit=least_squares(residual,x[:3],x_scale=[1,.1,.3],diff_step=1e-6,
                      ftol=5e-14,xtol=5e-14,gtol=5e-14,max_nfev=20)
    if np.linalg.norm(residual(fit.x))>1e-8:
        raise RuntimeError(f'input refinement failed: {residual(fit.x)}')
    return np.r_[fit.x,deviation].tolist()


def refined_moon_minimum(result):
    """Refine all local candidates on the adaptive dense trajectory."""
    best=(math.inf,None)
    for arc in result.arcs:
        for sol in arc.solutions:
            d=np.linalg.norm(sol.y[:3].T-[1,0,0],axis=1)
            if min(d)<best[0]:
                k=int(np.argmin(d))
                best=(float(d[k]),float(sol.t[k]))
            candidates=np.flatnonzero((d[1:-1]<=d[:-2])&(d[1:-1]<=d[2:]))+1
            for k in candidates:
                opt=minimize_scalar(lambda t:np.linalg.norm(sol.sol(t)[:3]-[1,0,0]),
                                    bounds=(sol.t[k-1],sol.t[k+1]),method='bounded',options={'xatol':1e-12})
                if opt.fun<best[0]: best=(float(opt.fun),float(opt.x))
    return best


def verify(name,record,base):
    factor=record['radius']
    family=Family(*record['family'])
    system=system_at_radius(base,factor)
    reports=[]
    for rtol,atol,step in [(2e-13,2e-15,.006),(3e-14,3e-16,.004)]:
        shot,result=flight(record['x'],system,family,rtol=rtol,atol=atol,max_step=step,dense=True)
        report=audit_polar_return(system,family,shot,result,solid_radius=factor*base.rho1)
        if not report['accepted_idealized_return']:
            raise RuntimeError(f'{name} failed independent audit: {report["rejection_reasons"]}')
        report['integration_tolerances']=dict(rtol=rtol,atol=atol,max_step=step)
        reports.append(report)
    report,check=reports
    minimum,closest_time=refined_moon_minimum(result)
    report['minimum_secondary_distance']=minimum
    report['minimum_secondary_altitude_km']=(minimum-base.rho2)*base.separation_km
    report['closest_secondary_time']=closest_time
    report['minimum_secondary_distance_method']='dense-output local minimization, checked against adaptive nodes'
    apo=max(np.linalg.norm(arc.solutions[1].y[:3,-1]) for arc in result.arcs)
    report['maximum_primary_distance_km']=float(apo*base.separation_km)
    report['system']['solid_radius_factor_vs_earth']=factor
    report['system']['solid_radius_km']=factor*base.rho1*base.separation_km
    report['system']['atmospheric_interface_altitude_km']=100.
    report['input_parameters']=record['x']
    report['initial_periapsis_latitude_deg']=math.degrees(shot.latitude)
    report['initial_osculating_elements']=osculating_elements(result.initial_state,base.mu1)
    pre=np.array(report['pre_bank_state'])
    post=np.array(report['post_bank_state'])
    for label,state in [('pre',pre),('post',post)]:
        elements=osculating_elements(state,base.mu1)
        report[f'{label}_bank_osculating_elements']=elements
    unit2=base.velocity_unit_km_s**2*1e6
    work=report['finite_impulse_work']
    de=(report['post_bank_osculating_elements']['specific_energy']-
         report['pre_bank_osculating_elements']['specific_energy'])*unit2
    report['energy_budget_J_kg']={
        'orbital_energy_gain_at_bank':de,
        'orbital_energy_change_over_coast':(report['pre_bank_osculating_elements']['specific_energy']-
                                           report['initial_osculating_elements']['specific_energy'])*unit2,
        'atmosphere_relative_dissipation':-work['atmosphere_relative_work']*unit2,
        'primary_rotation_work':base.primary_rotation_ratio*work['angular_momentum_z_change']*unit2,
    }
    report['tolerance_check']={k:check[k] for k in ['period_days','position_closure_norm','velocity_closure_norm',
        'maximum_primary_pass_departure_from_polar_deg','maximum_coast_jacobi_drift','bank_jacobi_jump']}
    report['tolerance_check']['maximum_local_ld']=check['bank']['maximum_local_ld']
    # Keep a portable plot history while deriving percentages from 30,001
    # uniform samples, not from this compacted array or adaptive ODE steps.
    for key in ['time','state_rotating']:
        report['history'][key]=report['history'][key][::3]
    report['history']['geometry_sample_count']=30001
    report['history']['stored_sample_count']=10001
    write(OUT/f'{name}.json',report)
    summary={k:report[k] for k in ['period_days','period_in_lunar_months','earth_orbits_per_return',
        'atmospheric_banks_per_return','primary_pass_inclinations_deg',
        'maximum_primary_pass_departure_from_polar_deg','minimum_primary_clearance_km',
        'minimum_secondary_altitude_km','maximum_primary_distance_km','initial_periapsis_latitude_deg',
        'impulse_local_components_m_s','position_closure_norm','velocity_closure_norm','energy_budget_J_kg']}
    summary.update(name=name,radius_factor=factor,nominal_resonance=f'{family.loops}:{family.secondary_periods}',
                   max_local_ld=report['bank']['maximum_local_ld'])
    return summary,report


def verify_repetition(record,base):
    """Two controlled repetitions of primitive 1:4: a nonprimitive 2:8."""
    system=system_at_radius(base,record['radius'])
    shot,_=flight(record['x'],system,Family(1,4))
    initial=shot.state(system.rho1)
    east,north=tangent_basis(initial[:3])
    angle=math.atan2(initial[3:]@north,initial[3:]@east)
    banks=[]
    def control(index,pre):
        post=bank_to_angle(pre,angle)
        bank=bank_path(pre,angle,base.primary_rotation_ratio)
        banks.append({k:v for k,v in bank.items() if k not in ['angles_deg','local_ld']})
        return post,post[3:]-pre[3:]
    result=propagate_cycle(system,Family(2,8),shot,periapsis_control=control,
                           rtol=3e-14,atol=3e-16,max_step=.004)
    record=dict(primitive_nominal_resonance='1:4',repeated_nominal_resonance='2:8',repetitions=2,
        independent_primitive_family=False,primary_passes=2,atmospheric_banks=2,
        period_days=result.period*base.time_unit_days,position_closure_norm=result.position_residual,
        velocity_closure_norm=result.velocity_residual,periapsis_radii=result.periapsis_radii,banks=banks)
    if not result.success or result.position_residual>1e-8 or result.velocity_residual>1e-7 or not all(b['all_segments_passive'] for b in banks):
        raise RuntimeError(f'repeated cycle failed: {record}')
    write(OUT/'repeated_2_8.json',record)
    return record


def plots(summaries,reports,base):
    FIGURES.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(1,2,figsize=(11,4.6))
    for family in ['1:1','1:2','3:2','1:4']:
        rows=sorted([r for r in summaries if r['nominal_resonance']==family],key=lambda r:r['radius_factor'])
        axes[0].plot([r['radius_factor'] for r in rows],[r['max_local_ld'] for r in rows],'o-',label=family)
        axes[1].plot([r['radius_factor'] for r in rows],[r['maximum_primary_pass_departure_from_polar_deg'] for r in rows],'o-',label=family)
    axes[0].set(yscale='log',ylabel='Maximum local L/D',xlabel='Solid radius / Earth radius',title='Verified polar branches')
    axes[0].axhline(50,color='grey',ls=':')
    axes[1].set(ylabel='Worst primary-pass departure from polar (deg)',xlabel='Solid radius / Earth radius',title='All passes checked; 0° is exactly polar')
    axes[1].axhline(5,color='grey',ls=':',label='5° acceptance criterion')
    for ax in axes:
        ax.grid(alpha=.3,which='both')
        ax.legend(title='Nominal primary:secondary')
    fig.tight_layout()
    fig.savefig(FIGURES/'01_radius_and_polarity.png',dpi=180)
    plt.close(fig)

    fig=plt.figure(figsize=(11,5))
    for k,name in enumerate(['earth_1_1','toy4_3_2']):
        report=reports[name]
        t=np.array(report['history']['time'])
        q=np.array(report['history']['state_rotating'])[:,:3]
        inertial=q.copy()
        inertial[:,0]=np.cos(t)*q[:,0]-np.sin(t)*q[:,1]
        inertial[:,1]=np.sin(t)*q[:,0]+np.cos(t)*q[:,1]
        ax=fig.add_subplot(1,2,k+1,projection='3d')
        ax.plot(*inertial.T,lw=.8,label='Vehicle')
        phase=np.linspace(0,2*np.pi,300)
        ax.plot(np.cos(phase),np.sin(phase),np.zeros_like(phase),'--',color='grey',label='Lunar orbit / equatorial plane')
        ax.scatter(0,0,0,color='tab:blue',s=45,label='Primary')
        ax.scatter(*inertial[0],color='red',marker='^',s=30,label='Atmospheric bank')
        extent=max(abs(inertial).max(),1.)*1.05
        # Show the actual orbital plane: an eccentric polar ellipse can have
        # a nearly equatorial major axis and look deceptively flat by itself.
        initial=np.array(report['initial_state'])
        rhat=initial[:3]/np.linalg.norm(initial[:3])
        w=initial[3:]+np.cross([0,0,1],initial[:3])
        tangent=w/np.linalg.norm(w)
        u,v=np.meshgrid(np.linspace(-.85,.85,2),np.linspace(-.85,.85,2))
        plane=extent*(u[:,:,None]*rhat+v[:,:,None]*tangent)
        ax.plot_surface(plane[:,:,0],plane[:,:,1],plane[:,:,2],color='tab:blue',alpha=.07,shade=False)
        ax.set(xlim=(-extent,extent),ylim=(-extent,extent),zlim=(-extent,extent),
               xlabel='x / lunar distance',ylabel='y / lunar distance',zlabel='z / lunar distance',
               title=f"{report['seed_family']} seed; R={report['system']['solid_radius_factor_vs_earth']:g} R_E; {report['period_days']:.3f} d")
        ax.set_box_aspect((1,1,1))
        ax.view_init(elev=12,azim=72)
        if k==0: ax.legend(fontsize=7)
    fig.suptitle('Primary-centered inertial views: blue sheet is the initial near-polar orbital plane')
    fig.tight_layout()
    fig.savefig(FIGURES/'02_polar_trajectories.png',dpi=180)
    plt.close(fig)

    report=reports['earth_1_1']
    b=report['bank']
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    axes[0].plot(b['angles_deg'],b['local_ld'])
    axes[0].set(xlabel='Local rotating velocity heading from east (deg)',ylabel='Local L/D',title='Earth-radius polar bank')
    rows=[r for r in summaries if r['name'] in ['earth_1_1','toy4_3_2','toy4_1_4']]
    labels=[r['name'] for r in rows]
    axes[1].bar(np.arange(len(rows))-.15,[r['impulse_local_components_m_s']['east'] for r in rows],width=.3,label='East')
    axes[1].bar(np.arange(len(rows))+.15,[r['impulse_local_components_m_s']['north'] for r in rows],width=.3,label='North')
    axes[1].set(xticks=np.arange(len(rows)),xticklabels=labels,ylabel='Net impulse component (m/s)',title='Eastward impulse dominates; radial component is zero')
    axes[1].legend()
    for ax in axes: ax.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(FIGURES/'03_polar_impulses.png',dpi=180)
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refine',action='store_true')
    parser.add_argument('--compact-exploratory',action='store_true',
                        help='Thin only generated candidate/follow plot histories to 1,001 samples; retain all input/audit fields.')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    base=earth_moon_system()
    if args.compact_exploratory:
        for pattern in ['candidate_*.json','follow_*.json']:
            for path in OUT.glob(pattern):
                data=json.loads(path.read_text())
                history=data.get('history',{})
                count=len(history.get('time',[]))
                if count!=30001: continue
                for key in ['time','state_rotating']:
                    history[key]=history[key][::30]
                history['geometry_sample_count']=30001
                history['stored_sample_count']=1001
                history['note']='Exploratory plotting history; repropagate recorded shot for full resolution. Audit percentages used the original uniform sampling.'
                write(path,data)
    inputs=json.loads(INPUTS.read_text()) if INPUTS.exists() else SEEDS
    if args.refine:
        for name,record in inputs.items():
            record['x']=refine(record['x'],system_at_radius(base,record['radius']),Family(*record['family']))
            print(json.dumps(dict(refined=name,**record)),flush=True)
        write(INPUTS,inputs)
    elif not INPUTS.exists():
        raise SystemExit('Run once with --refine to create the fixed-input checkpoints.')
    summaries=[]
    reports={}
    for name,record in inputs.items():
        summary,report=verify(name,record,base)
        summaries.append(summary)
        reports[name]=report
        print(json.dumps(summary),flush=True)
    repetition=verify_repetition(inputs['toy4_1_4'],base)
    write(OUT/'summary.json',dict(verified_returns=summaries,repeated_cycle=repetition))
    plots(summaries,reports,base)


if __name__=='__main__':
    main()
