"""
Inertial rendering module for generating educational GIFs.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.ticker as ticker
from matplotlib.patches import Circle
from scipy.interpolate import interp1d

from .barbell_physics import endpoint_positions, endpoint_velocities, get_diagnostics

def render_gif(scenario, t_eval, states, output_path, fps=20, duration=8.0):
    """
    Renders the simulation trajectory as a high-quality GIF using a global inertial camera.
    """
    num_frames = int(fps * duration)
    
    # Interpolate states onto evenly spaced render times
    t_render = np.linspace(t_eval[0], t_eval[-1], num_frames)
    interpolator = interp1d(t_eval, states, axis=0, kind='cubic')
    states_render = interpolator(t_render)

    # Pre-calculate positions and velocities for all frames
    r1_all = []
    r2_all = []
    v1_all = []
    v2_all = []
    R_all = []

    for state in states_render:
        r1, r2 = endpoint_positions(state, scenario.m1, scenario.m2, scenario.L)
        v1, v2 = endpoint_velocities(state, scenario.m1, scenario.m2, scenario.L)
        r1_all.append(r1)
        r2_all.append(r2)
        v1_all.append(v1)
        v2_all.append(v2)
        R_all.append(state[0:2])

    r1_all = np.array(r1_all)
    r2_all = np.array(r2_all)
    v1_all = np.array(v1_all)
    v2_all = np.array(v2_all)
    R_all = np.array(R_all)

    # Constants
    earth_radius = 5.415e6  # 15% smaller than 6.371e6 to prevent endpoint visual overlap

    # Set up figure and axis (480x480 pixels)
    fig, ax = plt.subplots(figsize=(6, 6), dpi=80)
    fig.patch.set_facecolor('#0b0c10')  # Sleek dark space background
    ax.set_facecolor('#0b0c10')

    # Draw Earth
    earth = Circle((0, 0), earth_radius, color='#1f2833', ec='#45a29e', lw=2.0, zorder=1)
    ax.add_patch(earth)

    # Faint grid lines
    ax.grid(color='#1f2833', linestyle=':', linewidth=0.5, alpha=0.7)

    # Determine plot bounds to keep Earth centered and fit the entire trajectory
    max_dist = 0.0
    for i in range(len(states_render)):
        max_dist = max(max_dist, 
                       np.linalg.norm(r1_all[i]), 
                       np.linalg.norm(r2_all[i]), 
                       np.linalg.norm(R_all[i]))

    # Set symmetric limits
    plot_limit = max(max_dist * 1.05, earth_radius * 1.1)
    ax.set_xlim(-plot_limit, plot_limit)
    ax.set_ylim(-plot_limit, plot_limit)
    ax.set_aspect('equal')

    # Axis styling
    ax.set_xlabel("Inertial X (10³ km)", color='#c9d1d9', fontsize=9)
    ax.set_ylabel("Inertial Y (10³ km)", color='#c9d1d9', fontsize=9)
    ax.tick_params(colors='#c9d1d9', labelsize=8)

    # Divide by 1e6 to get units of 10^3 km for clean axis tick labels
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val/1e6:.1f}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"{val/1e6:.1f}"))

    # Title
    ax.set_title(scenario.title, color='#f0f6fc', fontsize=11, fontweight='bold', pad=10)

    # Setup plots elements
    cm_trail_line, = ax.plot([], [], color='#66fcf1', linestyle='-', linewidth=1.2, alpha=0.8, label='CM Trail', zorder=2)
    
    # Endpoint trails: use colors corresponding to endpoints with low opacity
    ep1_trail_line, = ax.plot([], [], color='#ff007f', linestyle=':', linewidth=0.8, alpha=0.4, zorder=2)
    ep2_trail_line, = ax.plot([], [], color='#00e676', linestyle=':', linewidth=0.8, alpha=0.4, zorder=2)

    # Barbell link line
    barbell_line, = ax.plot([], [], color='#e5e5e5', linestyle='-', linewidth=1.5, zorder=3)

    # Endpoint dot sizes based on mass
    max_m = max(scenario.m1, scenario.m2)
    s1 = 20 + 80 * (scenario.m1 / max_m)
    s2 = 20 + 80 * (scenario.m2 / max_m)

    ep1_dot = ax.scatter([], [], color='#ff007f', s=s1, zorder=4, label='m1 (pink)')
    ep2_dot = ax.scatter([], [], color='#00e676', s=s2, zorder=4, label='m2 (green)')
    cm_dot = ax.scatter([], [], color='#66fcf1', s=15, marker='o', zorder=4)

    # Setup legend
    ax.legend(loc='upper right', facecolor='#1f2833', edgecolor='#45a29e', labelcolor='#c9d1d9', fontsize=8)

    # Setup velocity vectors if enabled
    quiver_obj = None
    if scenario.show_velocity_arrows:
        # We'll plot 3 vectors: endpoint 1, endpoint 2, and CM
        q_x = [0.0, 0.0, 0.0]
        q_y = [0.0, 0.0, 0.0]
        q_u = [0.0, 0.0, 0.0]
        q_v = [0.0, 0.0, 0.0]
        # scale=1/120.0 means 1 m/s velocity maps to 120 meters on plot.
        # This keeps the arrows reasonably sized (7.5 km/s -> ~900 km length)
        quiver_obj = ax.quiver(q_x, q_y, q_u, q_v, color=['#ff007f', '#00e676', '#66fcf1'],
                               angles='xy', scale_units='xy', scale=1.0/120.0, zorder=5,
                               width=0.005, headwidth=4, headlength=5)

    # HUD text overlay
    hud_text = ax.text(0.03, 0.03, '', transform=ax.transAxes, color='#c9d1d9',
                       fontsize=8, fontfamily='monospace',
                       bbox=dict(facecolor='#0b0c10', edgecolor='#45a29e', alpha=0.8, boxstyle='round,pad=0.4'))

    # Calculate reference orbital period for HUD
    r0_ref = np.linalg.norm(states_render[0, 0:2])
    T_orbit_ref = 2.0 * np.pi * np.sqrt(r0_ref**3 / scenario.mu)

    def init():
        cm_trail_line.set_data([], [])
        ep1_trail_line.set_data([], [])
        ep2_trail_line.set_data([], [])
        barbell_line.set_data([], [])
        hud_text.set_text('')
        artists = [cm_trail_line, ep1_trail_line, ep2_trail_line, barbell_line, hud_text]
        if quiver_obj is not None:
            artists.append(quiver_obj)
        return artists

    def update(frame):
        state = states_render[frame]
        t = t_render[frame]

        r1 = r1_all[frame]
        r2 = r2_all[frame]
        v1 = v1_all[frame]
        v2 = v2_all[frame]
        R = R_all[frame]

        # Update trails up to current frame
        cm_trail_line.set_data(R_all[:frame+1, 0], R_all[:frame+1, 1])
        ep1_trail_line.set_data(r1_all[:frame+1, 0], r1_all[:frame+1, 1])
        ep2_trail_line.set_data(r2_all[:frame+1, 0], r2_all[:frame+1, 1])

        # Update barbell link
        barbell_line.set_data([r1[0], r2[0]], [r1[1], r2[1]])

        # Update dots
        ep1_dot.set_offsets(np.array([r1]))
        ep2_dot.set_offsets(np.array([r2]))
        cm_dot.set_offsets(np.array([R]))

        # Update velocity arrows
        if quiver_obj is not None:
            vx, vy = state[2], state[3]
            V = np.array([vx, vy])
            
            q_x = [r1[0], r2[0], R[0]]
            q_y = [r1[1], r2[1], R[1]]
            q_u = [v1[0], v2[0], V[0]]
            q_v = [v1[1], v2[1], V[1]]
            
            quiver_obj.set_offsets(np.column_stack((q_x, q_y)))
            quiver_obj.set_UVC(q_u, q_v)

        # Compute diagnostics for HUD
        diag = get_diagnostics(state)
        alt = diag['r'] - earth_radius
        psi_deg = np.degrees(diag['psi_wrapped'])
        orbit_fraction = t / T_orbit_ref

        hud_lines = [
            f"Time:      {t:6.0f} s",
            f"Orbit:     {orbit_fraction:6.2f}",
            f"Altitude:  {alt/1e3:6.1f} km",
            f"Libration: {psi_deg:6.1f}°"
        ]
        hud_text.set_text("\n".join(hud_lines))

        artists = [cm_trail_line, ep1_trail_line, ep2_trail_line, barbell_line, ep1_dot, ep2_dot, cm_dot, hud_text]
        if quiver_obj is not None:
            artists.append(quiver_obj)
        return artists

    # Create animation
    ani = animation.FuncAnimation(fig, update, init_func=init, frames=num_frames, blit=True)
    
    # Ensure parent output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save GIF
    ani.save(output_path, writer='pillow', fps=fps)
    plt.close(fig)
