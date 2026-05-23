# Refined SVG diagrams per user's preferences.
# - One figure per concept (no subplots).
# - Vector SVG output, code-defined, ready for iteration.
# - No explicit colors; rely on defaults.
# - Clear labels, arrows, and minimal text.
#
# Diagrams:
# 1) eccentricity_pumping_refined.svg
#    Shows non-spinning, radial pump as *two different radii halves*:
#    - Small-radius half near perigee (ℓ short)
#    - Big-radius half near apogee (ℓ long)
#    Impulsive actions at perigee/apogee are annotated.
#
# 2) spin_phased_length_vs_angle.svg (polar)
#    Shows ℓ(φ) as a step function vs spin angle φ in LVLH:
#    - ℓ = R_big at horizontal (φ≈0°,180°)
#    - ℓ = R_small at vertical (φ≈90°,270°)
#    Impulsive extend@horizontal / retract@vertical annotated.
#
# 3) spin_phased_local_orbit_window.svg (optional "Earth peeking")
#    A local window of the orbit (not full), with Earth circle partially visible
#    and the four 90° sectors (R_big/R_small) indicated by line styles/width.
#
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Arc
from math import cos, sin, radians

def add_earth_cartesian(ax, center=(0,0), R=1.0, label=True):
    earth = Circle(center, R, fill=False, linewidth=1.5)
    ax.add_patch(earth)
    if label:
        ax.text(center[0], center[1]-0.1*R, "Earth", ha='center', va='top', fontsize=10)

def tangent_arrow_on_circle(ax, r, theta_deg, length=0.6):
    th = np.deg2rad(theta_deg)
    x = r*np.cos(th); y = r*np.sin(th)
    dx = -np.sin(th)*length; dy = np.cos(th)*length
    ax.add_patch(FancyArrowPatch((x,y),(x+dx,y+dy),arrowstyle='->',mutation_scale=10,linewidth=1))

def draw_arc(ax, r, a0, a1, lw=2.5, ls='solid'):
    # draws arc centered at origin
    sweep = a1 - a0
    while sweep < 0:
        sweep += 360
    arc = Arc((0,0), 2*r, 2*r, theta1=a0, theta2=a0+sweep, linewidth=lw, linestyle=ls)
    ax.add_patch(arc)

def place_marker(ax, r, theta_deg, text):
    th = np.deg2rad(theta_deg)
    x = r*np.cos(th); y = r*np.sin(th)
    ax.plot([x],[y], marker='o', markersize=3)
    # shift label slightly outward
    ax.text(1.1*x, 1.1*y, text, ha='center', va='center', fontsize=9)

# 1) Eccentricity Pumping (refined: two radii halves)
def fig_eccentricity_pumping_refined():
    fig, ax = plt.subplots(figsize=(6,6))
    ax.set_aspect('equal'); ax.axis('off')
    add_earth_cartesian(ax, R=1.0)

    r_small = 3.5
    r_big   = 4.5

    # Show orbit direction arrow on apogee-side
    tangent_arrow_on_circle(ax, r_big, theta_deg=30)

    # Half-orbits: use r_small for perigee side (-90° to +90°), r_big for apogee side (90° to 270°)
    draw_arc(ax, r_small, -90,  90, lw=2.5, ls='dashed')  # perigee half (ℓ short)
    draw_arc(ax, r_big,    90, 270, lw=2.8, ls='solid')   # apogee half (ℓ long)

    # Action instants
    place_marker(ax, r_small,   0, "Perigee\n(retract Δℓ<0)")
    place_marker(ax, r_big,   180, "Apogee\n(extend Δℓ>0)")

    # Labels
    ax.text(0, r_big+0.8, "Hold ℓ = long (apogee side)", ha='center', va='center', fontsize=9)
    ax.text(0, -(r_small+0.8), "Hold ℓ = short (perigee side)", ha='center', va='center', fontsize=9)
    ax.text(0, 6.0, "Eccentricity Pumping (radial, non-spinning): impulsive actions", ha='center', va='bottom', fontsize=11)
    ax.set_xlim(-6,6); ax.set_ylim(-6,6)
    fig.savefig("./docs/eccentricity_pumping_refined.svg", format="svg", bbox_inches="tight")
    plt.close(fig)

# 2) Spin-phased: length vs angle (polar step function)
def fig_spin_phased_length_vs_angle():
    # Polar plot where radius = ℓ(φ), angle = φ (LVLH spin angle)
    fig = plt.figure(figsize=(6,6))
    ax = plt.subplot(111, projection='polar')
    ax.set_theta_zero_location('E')  # 0° at +x (horizontal right)
    ax.set_theta_direction(-1)       # clockwise increases angle (to match LVLH view from above)
    # Define two levels
    R_small = 1.0
    R_big   = 1.5
    # Build step function over 0..360°: big on horizontals, small on verticals
    phis_deg = np.arange(0, 361, 1)
    r = np.empty_like(phis_deg, dtype=float)
    for i,phi in enumerate(phis_deg):
        # Long (R_big) in neighborhoods of horizontal (around 0 and 180), short elsewhere
        # Use exact quadrants to keep it crisp: [ -45..+45 ] and [ 135..225 ] => R_big
        phi_mod = (phi % 360)
        if (phi_mod <= 45) or (135 <= phi_mod <= 225) or (phi_mod >= 315):
            r[i] = R_big
        else:
            r[i] = R_small
    ax.plot(np.deg2rad(phis_deg), r, linewidth=2.5)

    # Annotate key angles
    # Horizontal: extend
    for ang in [0, 180]:
        ax.plot(np.deg2rad([ang]), [R_big], marker='o')
        ax.text(np.deg2rad(ang), R_big+0.1, "extend (Δℓ>0)\nhorizontal", ha='center', va='bottom', fontsize=9)
    # Vertical: retract
    for ang in [90, 270]:
        ax.plot(np.deg2rad([ang]), [R_small], marker='o')
        ax.text(np.deg2rad(ang), R_small+0.1, "retract (Δℓ<0)\nvertical", ha='center', va='bottom', fontsize=9)

    # Ticks and labels
    ax.set_rlabel_position(135)
    ax.set_rticks([R_small, R_big])
    ax.set_yticklabels(["R_small", "R_big"])
    ax.set_title("Spin-Phased Barbell Pumping: ℓ(φ) step function\n(extend@horizontal, retract@vertical)", va='bottom', fontsize=11)
    fig.savefig("./docs/spin_phased_length_vs_angle.svg", format="svg", bbox_inches="tight")
    plt.close(fig)

# 3) Spin-phased: local orbit window with Earth peeking
def fig_spin_phased_local_orbit_window():
    fig, ax = plt.subplots(figsize=(7,5))
    ax.set_aspect('equal'); ax.axis('off')

    # Place Earth partially visible on the left
    earth_center = (-5.0, 0.0)
    add_earth_cartesian(ax, center=earth_center, R=2.5, label=True)

    r_orbit = 6.0
    # Show only a local window on the right side of the orbit
    # We'll draw arcs from -110° to +110° to keep Earth peeking on the left
    # Quadrant segments relative to origin (LVLH): 0..90 long, 90..180 short, etc.
    # But in this cropped view, we include the crossings at ~0° and ~90° if they fall in range.
    draw_arc(ax, r_orbit,  -110,    0, lw=3.0, ls='solid')    # approaching horizontal (long)
    draw_arc(ax, r_orbit,     0,   90, lw=2.0, ls='dashed')   # after horizontal to vertical (short)
    draw_arc(ax, r_orbit,    90,  110, lw=3.0, ls='solid')    # a bit past vertical (long) for visual balance

    # Mark key instants in the window
    def marker_label(theta, text, r=r_orbit):
        th = np.deg2rad(theta)
        x = r*np.cos(th); y = r*np.sin(th)
        ax.plot([x],[y], marker='o', markersize=3)
        ax.text(x+0.6, y+0.2, text, fontsize=9)

    marker_label(0,   "horizontal\nextend")
    marker_label(90,  "vertical\nretract")

    # Tangential arrow to indicate orbit direction near theta=20°
    tangent_arrow_on_circle(ax, r_orbit, theta_deg=20)

    ax.text(0, 4.6, "Spin-Phased (local view):\nextend at horizontal, retract at vertical", ha='center', va='bottom', fontsize=11)
    ax.set_xlim(-8,8); ax.set_ylim(-4.5,4.5)
    fig.savefig("./docs/spin_phased_local_orbit_window.svg", format="svg", bbox_inches="tight")
    plt.close(fig)

fig_eccentricity_pumping_refined()
fig_spin_phased_length_vs_angle()
fig_spin_phased_local_orbit_window()

print("Generated files:")
print("- ./docs/eccentricity_pumping_refined.svg")
print("- ./docs/spin_phased_length_vs_angle.svg")
print("- ./docs/spin_phased_local_orbit_window.svg")
