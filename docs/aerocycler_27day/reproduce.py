#!/usr/bin/env python3
"""Reproduce ONE fixed polar return, its bank, plots, and offline viewer data.

Standalone: requires numpy, scipy, matplotlib; no aerocycler package imports,
no optimizer, network, or downloads. Run with the repository's Python venv.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
import scipy
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parent
BLUE, GOLD, INK, GRAY = '#007e99', '#ba7312', '#182f46', '#73879b'


def rhs(t, y, mu):
    q, v = y[:3], y[3:]
    d = q - [1, 0, 0]
    g = -(1-mu)*q/np.linalg.norm(q)**3 - mu*d/np.linalg.norm(d)**3 - [mu, 0, 0]
    return np.r_[v, g + [q[0]+2*v[1], q[1]-2*v[0], 0]]


def event(direction):
    def turning_point(t, y, mu):
        return float(y[:3] @ y[3:])
    turning_point.direction = direction
    turning_point.terminal = True
    return turning_point


def rotate(q, t):
    q = np.asarray(q)
    c, s = np.cos(t), np.sin(t)
    return np.stack((c*q[..., 0]-s*q[..., 1], s*q[..., 0]+c*q[..., 1], q[..., 2]), axis=-1)


def basis(q):
    lon, lat = math.atan2(q[1], q[0]), math.atan2(q[2], np.hypot(q[0], q[1]))
    return np.array([[-math.sin(lon), math.cos(lon), 0],
                     [-math.sin(lat)*math.cos(lon), -math.sin(lat)*math.sin(lon), math.cos(lat)],
                     q/np.linalg.norm(q)])


def inertial_velocity(y):
    return y[..., 3:] + np.cross([0, 0, 1], y[..., :3])


def jacobi(y, mu):
    q, v = y[..., :3], y[..., 3:]
    return ((q[..., 0]-mu)**2 + q[..., 1]**2 + 2*(1-mu)/np.linalg.norm(q, axis=-1)
            + 2*mu/np.linalg.norm(q-[1, 0, 0], axis=-1) - np.sum(v*v, axis=-1))


def osculating(y, mu1, length, velocity):
    q, w = y[:3], inertial_velocity(y)
    h = np.cross(q, w)
    energy = w@w/2-mu1/np.linalg.norm(q)
    a = -mu1/(2*energy)
    e = np.linalg.norm(np.cross(w, h)/mu1-q/np.linalg.norm(q))
    return dict(semimajor_axis_km=float(a*length), eccentricity=float(e),
                inclination_deg=float(np.degrees(np.arccos(h[2]/np.linalg.norm(h)))),
                osculating_apogee_center_distance_km=float(a*(1+e)*length),
                specific_energy_J_kg=float(energy*velocity**2))


def simulate(inputs):
    mu, length = inputs['mu'], inputs['separation_km']
    time_unit = inputs['lunar_sidereal_period_days']*86400/(2*np.pi)
    velocity_unit = length*1000/time_unit
    sigma = inputs['lunar_sidereal_period_days']/inputs['primary_sidereal_day_days']
    initial = np.array(inputs['initial_state_primary_centered_rotating'])
    settings = inputs['integration']
    options = dict(args=(mu,), method=settings['method'], rtol=settings['rtol'], atol=settings['atol'],
                   max_step=settings['max_step_normalized'], dense_output=True)
    # The first event must be apogee: it has the opposite crossing direction
    # to the initial periapsis root. The second integration stops at periapsis.
    apo = solve_ivp(rhs, (0, 8), initial, events=event(-1), **options)
    if not apo.success or len(apo.t_events[0]) != 1:
        raise RuntimeError('apogee event not found')
    ta = float(apo.t_events[0][0])
    peri = solve_ivp(rhs, (ta, 16), apo.y_events[0][0], events=event(1), **options)
    if not peri.success or len(peri.t_events[0]) != 1:
        raise RuntimeError('return periapsis not found')
    period = float(peri.t_events[0][0])
    pre = peri.y_events[0][0]
    axes = basis(pre[:3])
    # Define the target from the six-state input itself, not a rounded angle.
    initial_axes = basis(initial[:3])
    target = math.atan2(initial[3:]@initial_axes[1], initial[3:]@initial_axes[0])
    a0 = math.atan2(pre[3:]@axes[1], pre[3:]@axes[0])
    angles = np.linspace(a0, target, 4001)
    s = np.linalg.norm(pre[3:])
    bank_v = s*(np.cos(angles)[:, None]*axes[0]+np.sin(angles)[:, None]*axes[1])
    path = abs(angles-angles[0])
    derivative = np.sign(target-a0)*s*(-np.sin(angles)[:, None]*axes[0]+np.cos(angles)[:, None]*axes[1])
    air = (sigma-1)*np.cross([0, 0, 1], pre[:3])
    u = bank_v-air
    uhat = u/np.linalg.norm(u, axis=1)[:, None]
    drag = -np.sum(derivative*uhat, axis=1)
    drag_vec = -drag[:, None]*uhat
    lift_vec = derivative-drag_vec
    lift = np.linalg.norm(lift_vec, axis=1)
    post = np.r_[pre[:3], bank_v[-1]]
    dv = post[3:]-pre[3:]
    midpoint = (inertial_velocity(pre)+inertial_velocity(post))/2
    spin_air = sigma*np.cross([0, 0, 1], pre[:3])
    local = lambda vector: (axes@vector*velocity_unit).tolist()
    ld = lift/drag
    # Extra endpoint samples resolve the short atmospheric encounter. The
    # adaptive nodes are included as well as a uniform coast grid.
    edge = np.geomspace(1e-9, min(.12, period/10), 700)
    times = np.unique(np.r_[0, period, ta, np.linspace(0, period, 5001),
                            edge, period-edge, apo.t, peri.t])
    states = np.empty((len(times), 6))
    before = times <= ta
    states[before] = apo.sol(times[before]).T
    states[~before] = peri.sol(times[~before]).T
    q = states[:, :3]
    w = inertial_velocity(states)
    h = np.cross(q, w)
    inclination = np.degrees(np.arccos(h[:, 2]/np.linalg.norm(h, axis=1)))
    energy_change = (midpoint@dv)*velocity_unit**2
    closure = post-initial
    report = {
        'schema': 'polar-aerocycler-27day-verification-v1',
        'software': dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__, matplotlib=matplotlib.__version__),
        'units': dict(length_km=length, time_s=time_unit, velocity_m_s=velocity_unit,
                      total_GM_km3_s2=length**3/time_unit**2, primary_GM_km3_s2=(1-mu)*length**3/time_unit**2),
        'period_normalized': period, 'period_days': period*time_unit/86400,
        'period_lunar_months': period/(2*np.pi), 'apogee_time_days': ta*time_unit/86400,
        'inertial_orientation_advance_beyond_360_deg': float(np.degrees(period-2*np.pi)),
        'initial_state': initial.tolist(), 'pre_bank_state': pre.tolist(), 'post_bank_state': post.tolist(),
        'initial_position_km': (initial[:3]*length).tolist(),
        'initial_rotating_velocity_m_s': (initial[3:]*velocity_unit).tolist(),
        'initial_nonrotating_velocity_m_s': (inertial_velocity(initial)*velocity_unit).tolist(),
        'pre_bank_local_inertial_velocity_ENR_m_s': local(inertial_velocity(pre)),
        'post_bank_local_inertial_velocity_ENR_m_s': local(inertial_velocity(post)),
        'impulse_ENR_m_s': local(dv), 'impulse_rotating_xyz_m_s': (dv*velocity_unit).tolist(),
        'drag_impulse_ENR_m_s': local(np.trapezoid(drag_vec, path, axis=0)),
        'lift_impulse_ENR_m_s': local(np.trapezoid(lift_vec, path, axis=0)),
        'integral_drag_m_s': float(np.trapezoid(drag, path)*velocity_unit),
        'integral_lift_m_s': float(np.trapezoid(lift, path)*velocity_unit),
        'minimum_local_LD': float(ld.min()), 'maximum_local_LD': float(ld.max()),
        'all_bank_segments_positive_drag': bool(np.all(drag > 0)),
        'bank_heading_rotating_deg': [float(np.degrees(a0)), float(np.degrees(target))],
        'atmosphere_inertial_east_speed_m_s': float(np.linalg.norm(spin_air)*velocity_unit),
        'energy_J_kg': dict(orbital_gain=float(energy_change), rotation_work=float(spin_air@dv*velocity_unit**2),
                            atmosphere_relative_work=float((midpoint-spin_air)@dv*velocity_unit**2)),
        'closure_normalized': closure.tolist(),
        'position_closure_m': float(np.linalg.norm(closure[:3])*length*1000),
        'velocity_closure_m_s': float(np.linalg.norm(closure[3:])*velocity_unit),
        'coast_jacobi_max_error': float(np.max(abs(jacobi(states,mu)-jacobi(initial,mu)))),
        'bank_jacobi_jump': float(jacobi(post,mu)-jacobi(pre,mu)),
        'maximum_primary_center_distance_km': float(np.linalg.norm(apo.y_events[0][0][:3])*length),
        'minimum_primary_altitude_km': float(min(np.linalg.norm(initial[:3]), np.linalg.norm(pre[:3]))*length-inputs['primary_solid_radius_km']),
        'inclination_over_sampled_coast_deg': [float(inclination.min()), float(inclination.max())],
        'initial_osculating': osculating(initial,1-mu,length,velocity_unit),
        'pre_bank_osculating': osculating(pre,1-mu,length,velocity_unit),
        'post_bank_osculating': osculating(post,1-mu,length,velocity_unit),
    }
    if not report['all_bank_segments_positive_drag'] or report['position_closure_m'] > .01 or report['velocity_closure_m_s'] > 1e-5:
        raise RuntimeError('fixed-input verification failed: '+json.dumps(report))
    if abs(report['period_days']-inputs['expected_period_days']) > 1e-6:
        raise RuntimeError('unexpected return period')
    return report, times, states, dict(angles=angles, v=bank_v, drag=drag, lift=lift, path=path, axes=axes, dv=dv, ld=ld), ta


def figures(inputs, report, times, states, bank, ta):
    plt.rcParams.update({'font.size':11, 'axes.labelcolor':INK, 'text.color':INK,
                         'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    out = ROOT/'figures'
    out.mkdir(exist_ok=True)
    length = inputs['separation_km']
    q = states[:, :3]*length/1000 # axes in thousands of km
    qi = rotate(q,times)
    split = np.searchsorted(times,ta)
    tmoon = np.linspace(0,report['period_normalized'],601)
    moon = rotate(np.tile([length/1000,0,0],(len(tmoon),1)),tmoon)

    def save(fig, name, caption):
        fig.text(.07,.025,caption,fontsize=9,color=GRAY)
        fig.subplots_adjust(left=.09,right=.97,bottom=.15,top=.86)
        fig.savefig(out/(name+'.png'),dpi=160,facecolor='white')
        fig.savefig(out/(name+'.svg'),facecolor='white')
        svg_path=out/(name+'.svg')
        svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines())+'\n')
        plt.close(fig)

    def panel(ax, coords, dims=(0,1), rotating=False):
        a,b = dims
        ax.plot(coords[:split+1,a],coords[:split+1,b],color=BLUE,lw=2,label='Outbound to apogee')
        ax.plot(coords[split:,a],coords[split:,b],color=GOLD,lw=2,label='Return to Earth')
        ax.add_patch(Circle((0,0),inputs['primary_solid_radius_km']/1000,color='#42799e',zorder=5))
        ax.annotate('Earth',(0,0),xytext=(8,-16),textcoords='offset points',fontsize=10)
        if dims==(0,1):
            theta=np.linspace(0,2*np.pi,401)
            ax.plot(length/1000*np.cos(theta),length/1000*np.sin(theta),'--',color='#b3bfca',lw=1,label='Lunar orbit')
            if rotating:
                ax.add_patch(Circle((length/1000,0),inputs['secondary_radius_km']/1000,color=GRAY))
                ax.scatter([length/1000],[0],s=25,color=GRAY,zorder=4)
                ax.annotate('Moon (fixed)',(length/1000,0),xytext=(7,9),textcoords='offset points',fontsize=10)
            else:
                ax.plot(moon[:,0],moon[:,1],color=GRAY,lw=1)
                for idx,label in [(0,'Moon: t = 0'),(-1,'Moon: t = T')]:
                    ax.scatter(moon[idx,0],moon[idx,1],s=24,color=GRAY)
                    ax.annotate(label,moon[idx,:2],xytext=(7,12 if idx==0 else -20),textcoords='offset points',fontsize=9)
        ax.scatter(coords[split,a],coords[split,b],s=35,color=INK,zorder=5)
        on_right=coords[split,a]>(coords[:,a].min()+coords[:,a].max())/2
        ax.annotate('Apogee',coords[split,[a,b]],xytext=(-8 if on_right else 8,8),
                    ha='right' if on_right else 'left',textcoords='offset points',fontsize=10)
        ax.set(xlabel=f'{"xyz"[a]} (10³ km)',ylabel=f'{"xyz"[b]} (10³ km)')
        ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.18)

    for rotating,coords,name,title in [
        (True,q,'01_lunar_frame_top','Lunar-co-moving frame · top view'),
        (False,qi,'02_nonrotating_top','Earth-centered non-rotating axes · top view')]:
        fig,ax=plt.subplots(figsize=(12,7.5));panel(ax,coords,rotating=rotating)
        fig.suptitle(title,fontsize=18,x=.09,ha='left')
        ax.legend(loc='best',frameon=False)
        save(fig,name,'One 27.4413-day coast. Equal distance scale on both axes; Earth/Moon dots aid visibility. No vertical exaggeration.')

    fig,axes=plt.subplots(1,2,figsize=(12,7.5))
    for ax,coords,title in zip(axes,[q,qi],['Lunar-co-moving axes','Earth-centered non-rotating axes']):
        panel(ax,coords,(0,2));ax.set_title(title);ax.axhline(0,color=GRAY,lw=.7,alpha=.5)
    fig.suptitle('Out of the Earth–Moon plane · side views',fontsize=18,x=.09,ha='left')
    axes[0].legend(loc='best',frameon=False,fontsize=9)
    save(fig,'03_side_views','z = 0 is the lunar/equatorial plane. Equal axis scales: a polar orbit need not have a vertical major axis.')

    # Two Earth-local coast legs, expressed in the SAME non-rotating axes
    # with the final leg rotated back by T to compare the encounter geometry.
    near = .02
    early=times<near;late=times>report['period_normalized']-near
    local_q=rotate(states[:,:3],times)
    local_q[late]=rotate(local_q[late],-report['period_normalized'])
    axlocal=bank['axes']
    en=(local_q@axlocal.T)*length
    # Project onto east/north; radial coordinate shown separately in 3-D view.
    fig,axes=plt.subplots(1,2,figsize=(12,7.5))
    axes[0].plot(en[late,0],en[late,1],color=GOLD,label='Incoming (final encounter)')
    axes[0].plot(en[early,0],en[early,1],color=BLUE,label='Outgoing (initial encounter)')
    axes[0].scatter([en[0,0]],[en[0,1]],color=INK,s=30)
    axes[0].annotate('Periapsis',en[0,:2],xytext=(8,8),textcoords='offset points',fontsize=10)
    axes[0].set(xlabel='Local east coordinate (km)',ylabel='Local north coordinate (km)',title='Encounter-centered tangent projection')
    axes[0].set_aspect('equal',adjustable='datalim');axes[0].legend(fontsize=9,frameon=False)
    for mask,color,label in [(early,BLUE,'After departure'),(late,GOLD,'Before return')]:
        x=times[mask]*report['units']['time_s']/60
        if label=='Before return':x=x-report['period_normalized']*report['units']['time_s']/60
        alt=np.linalg.norm(states[mask,:3],axis=1)*length-inputs['primary_solid_radius_km']
        axes[1].plot(x,alt,color=color,label=label)
    axes[1].axhline(100,color=GRAY,ls='--',lw=1)
    axes[1].set(xlim=(-20,20),ylim=(0,2000),xlabel='Minutes relative to periapsis',ylabel='Altitude (km)',title='Short encounter, long coast')
    for ax in axes:ax.grid(alpha=.18)
    fig.suptitle('The nearly polar Earth passage',fontsize=18,x=.09,ha='left')
    save(fig,'04_earth_pass','Incoming leg rotated back by T for comparison. The bank is instantaneous at 100 km; no finite atmospheric flight is modeled.')

    vlocal=bank['v']@bank['axes'].T*report['units']['velocity_m_s']
    vlocal[:,0]+=np.linalg.norm(np.cross([0,0,1],np.array(report['pre_bank_state'])[:3]))*report['units']['velocity_m_s']
    fig,axes=plt.subplots(1,2,figsize=(12,7.5))
    axes[0].plot(vlocal[:,0],vlocal[:,1],color=BLUE,lw=2)
    axes[0].scatter(vlocal[[0,-1],0],vlocal[[0,-1],1],color=[GOLD,BLUE],s=40)
    for idx,label in [(0,'Incoming'),(-1,'Outgoing')]:
        axes[0].annotate(label,vlocal[idx,:2],xytext=(6 if idx==0 else -8,9),
                         ha='left' if idx==0 else 'right',textcoords='offset points')
    axes[0].set(xlabel='Eastward inertial velocity (m/s)',ylabel='Northward inertial velocity (m/s)',title='Velocity-space bank (expanded vertical scale)')
    axes[0].ticklabel_format(useOffset=False,axis='y')
    axes[1].plot(np.degrees(bank['path']),bank['ld'],color=BLUE,lw=2)
    axes[1].set(xlabel='Accumulated turn angle (degrees)',ylabel='Local lift / drag',title='Positive drag throughout the turn')
    for ax in axes:ax.grid(alpha=.18)
    fig.suptitle('Aerodynamic impulse · not a propulsive burn',fontsize=18,x=.09,ha='left')
    save(fig,'05_aerodynamic_bank','Geographic components are not lift/drag: Δv east = +481.45 m/s; Δv north = +0.294 m/s; max local L/D = 25.6854.')


def export(inputs,report,times,states,bank,ta):
    data=ROOT/'data';data.mkdir(exist_ok=True)
    write=lambda p,obj:p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
    write(data/'verification.json',report)
    length=inputs['separation_km'];unit=report['units']['velocity_m_s']/1000
    qi=rotate(states[:,:3],times)*length
    vi=rotate(inertial_velocity(states),times)*unit
    qb=states[:,:3]-[inputs['mu'],0,0]
    rb=rotate(qb,times)*length
    vb=rotate(states[:,3:]+np.cross([0,0,1],qb),times)*unit
    days=times*report['units']['time_s']/86400
    with (data/'trajectory.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n')
        writer.writerow(['t_normalized','time_days']+[f'{c}_rotating_normalized' for c in ['x','y','z','vx','vy','vz']]
                        +[f'{c}_earth_nonrotating_{"km_s" if c.startswith("v") else "km"}' for c in ['x','y','z','vx','vy','vz']]
                        +[f'{c}_barycentric_inertial_{"km_s" if c.startswith("v") else "km"}' for c in ['x','y','z','vx','vy','vz']])
        writer.writerows(np.column_stack([times,days,states,qi,vi,rb,vb]))
    with (data/'bank.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n')
        writer.writerow(['path_angle_rad','heading_rotating_deg','v_east_rotating_m_s','v_north_rotating_m_s',
                         'drag_per_radian_m_s','lift_per_radian_m_s','local_LD'])
        vl=bank['v']@bank['axes'].T*report['units']['velocity_m_s']
        writer.writerows(np.column_stack([bank['path'],np.degrees(bank['angles']),vl[:,:2],
                                          bank['drag']*report['units']['velocity_m_s'],bank['lift']*report['units']['velocity_m_s'],bank['ld']]))
    # Classic JS data (not fetch/ES modules) works from file:// without a server.
    payload=dict(inputs=inputs,verification=report,apogee_time=ta,
                 samples=np.column_stack([times,states]).tolist())
    (ROOT/'orbit-data.js').write_text('// Generated by reproduce.py. Full precision samples; no browser-side integration.\nwindow.ORBIT_DATA = '+json.dumps(payload,separators=(',',':'),allow_nan=False)+';\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only',action='store_true',help='Print the verification; do not overwrite any artifacts.')
    args=parser.parse_args()
    inputs=json.loads((ROOT/'data/initial_conditions.json').read_text())
    report,times,states,bank,ta=simulate(inputs)
    if not args.verify_only:
        export(inputs,report,times,states,bank,ta)
        figures(inputs,report,times,states,bank,ta)
        paths=[ROOT/'data'/n for n in ['initial_conditions.json','verification.json','trajectory.csv','bank.csv']]+[ROOT/'orbit-data.js']
        manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        (ROOT/'data/sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['period_days','position_closure_m','velocity_closure_m_s','maximum_local_LD','impulse_ENR_m_s','all_bank_segments_positive_drag']},indent=2))


if __name__=='__main__':
    main()
