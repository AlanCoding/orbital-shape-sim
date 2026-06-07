"""
Scenario definitions for the rigid barbell orbital simulation.
"""

from dataclasses import dataclass
import numpy as np

@dataclass
class Scenario:
    id: str
    title: str
    m1: float
    m2: float
    L: float
    state0: np.ndarray
    t_max: float
    description: str
    mu: float = 3.986004418e14
    show_velocity_arrows: bool = False

def circular_state_from_local_angle(mu, r0, psi, psidot):
    """
    Computes initial state for a circular orbit at radius r0 with local
    orientation angle psi and relative angular rate psidot.
    """
    theta = 0.0
    thetadot = np.sqrt(mu / r0**3)

    x = r0
    y = 0.0
    vx = 0.0
    vy = np.sqrt(mu / r0)

    phi = theta + psi
    phidot = thetadot + psidot

    return np.array([x, y, vx, vy, phi, phidot])

def get_scenarios(mu=3.986004418e14):
    """
    Returns a dictionary of the eight named simulation scenarios.
    """
    scenarios = {}

    # Unified physical ratios based on revised Scenario 5
    r0 = 9.0e6            # 9000 km orbit radius of CM
    L = 3.0e6             # 3000 km tether length (L/r0 = 1/3)
    T_orbit = 2.0 * np.pi * np.sqrt(r0**3 / mu)
    thetadot = np.sqrt(mu / r0**3)

    # 1. Radial gravity-gradient libration
    psi_1 = np.radians(10.0)
    state_1 = circular_state_from_local_angle(mu, r0, psi_1, 0.0)
    scenarios["01_radial_libration"] = Scenario(
        id="01_radial_libration",
        title="01: Radial Gravity-Gradient Libration",
        m1=1000.0,
        m2=1000.0,
        L=L,
        state0=state_1,
        t_max=2.4 * T_orbit,
        description="Equal mass barbell in circular orbit starting with a 10 deg offset, showing gravity-gradient libration over 2.4 orbits."
    )

    # 2. Tumbling through the gravity gradient
    psi_2 = np.radians(30.0)
    psidot_2 = 1.6 * thetadot  # Spin rate high enough to tumble
    state_2 = circular_state_from_local_angle(mu, r0, psi_2, psidot_2)
    scenarios["02_tumbling"] = Scenario(
        id="02_tumbling",
        title="02: Tumbling through Gravity Gradient",
        m1=1000.0,
        m2=1000.0,
        L=L,
        state0=state_2,
        t_max=2.4 * T_orbit,
        description="Equal mass barbell starting with enough spin to overcome the gravity gradient and tumble continuously."
    )

    # 3. Unequal-mass barbell
    psi_3 = np.radians(20.0)
    state_3 = circular_state_from_local_angle(mu, r0, psi_3, 0.0)
    scenarios["03_unequal_masses"] = Scenario(
        id="03_unequal_masses",
        title="03: Unequal-Mass Barbell Dynamics",
        m1=200.0,      # light mass
        m2=1800.0,     # heavy mass
        L=L,
        state0=state_3,
        t_max=2.4 * T_orbit,
        description="Asymmetric barbell (m2 = 9*m1) showing the center of mass shifted closer to the heavier endpoint."
    )

    # 4. Elliptical-orbit forcing
    rp = 9.0e6         # perigee radius
    e = 0.3            # highly eccentric
    vp = np.sqrt(mu * (1.0 + e) / rp)
    thetadot_p = vp / rp
    psi_4 = np.radians(30.0)
    state_4 = np.array([rp, 0.0, 0.0, vp, psi_4, thetadot_p])
    a_semi = rp / (1.0 - e)
    T_orbit_elliptical = 2.0 * np.pi * np.sqrt(a_semi**3 / mu)
    scenarios["04_elliptical_forcing"] = Scenario(
        id="04_elliptical_forcing",
        title="04: Elliptical-Orbit Libration Forcing",
        m1=1000.0,
        m2=1000.0,
        L=L,
        state0=state_4,
        t_max=2.0 * T_orbit_elliptical,
        description="Equal mass barbell in eccentric orbit (e=0.3), showing stronger gravity-gradient torque near perigee over 2.0 orbits."
    )

    # 5. Long-tether nonlinear gradient
    psi_5 = np.radians(45.0)
    psidot_5 = 0.8 * thetadot
    state_5 = circular_state_from_local_angle(mu, r0, psi_5, psidot_5)
    scenarios["05_long_tether_nonlinear"] = Scenario(
        id="05_long_tether_nonlinear",
        title="05: Long-Tether Nonlinear Gradient",
        m1=1000.0,
        m2=1000.0,
        L=L,
        state0=state_5,
        t_max=2.4 * T_orbit,
        description="Extremely long tether (3000 km) in a 9000 km radius orbit showing non-Keplerian endpoint paths due to nonlinear gravity-gradient."
    )

    # 6. Chaotic Tumbling in an Eccentric Orbit
    e_6 = 0.35
    vp_6 = np.sqrt(mu * (1.0 + e_6) / rp)
    thetadot_p6 = vp_6 / rp
    psi_6 = np.radians(45.0)
    psidot_6 = 1.5 * thetadot_p6
    state_6 = np.array([rp, 0.0, 0.0, vp_6, psi_6, psidot_6])
    a_semi_6 = rp / (1.0 - e_6)
    T_orbit_elliptical_6 = 2.0 * np.pi * np.sqrt(a_semi_6**3 / mu)
    scenarios["06_chaotic_tumbling"] = Scenario(
        id="06_chaotic_tumbling",
        title="06: Chaotic Tumbling in Eccentric Orbit",
        m1=1000.0,
        m2=1000.0,
        L=L,
        state0=state_6,
        t_max=2.0 * T_orbit_elliptical_6,
        description="Barbell in eccentric orbit (e=0.35) starting in a chaotic attitude state, showing unpredictable capture/tumbling transitions."
    )

    # 7. Orbit-Attitude Coupling (Renamed / Clarified)
    psi_7 = 0.0
    psidot_7 = 8.0 * thetadot  # Very fast spin rate
    state_7 = circular_state_from_local_angle(mu, r0, psi_7, psidot_7)
    scenarios["07_orbit_attitude_coupling"] = Scenario(
        id="07_orbit_attitude_coupling",
        title="07: Spin-Stabilized Orbit-Attitude Coupling",
        m1=1000.0,
        m2=1000.0,
        L=L,
        state0=state_7,
        t_max=2.4 * T_orbit,
        description="Fast-rotating barbell in circular orbit showing gyroscopic stabilization and high-frequency center-of-mass radial wobble."
    )

    # 8. Spin-Stabilized Elliptical Orbit (New Scenario 8)
    e_8 = 0.3
    vp_8 = np.sqrt(mu * (1.0 + e_8) / rp)
    thetadot_p8 = vp_8 / rp
    psi_8 = 0.0
    psidot_8 = 8.0 * thetadot_p8  # Fast spin rate
    state_8 = np.array([rp, 0.0, 0.0, vp_8, psi_8, psidot_8])
    a_semi_8 = rp / (1.0 - e_8)
    T_orbit_elliptical_8 = 2.0 * np.pi * np.sqrt(a_semi_8**3 / mu)
    scenarios["08_fast_rotating_elliptical"] = Scenario(
        id="08_fast_rotating_elliptical",
        title="08: Spin-Stabilized Elliptical Orbit",
        m1=1000.0,
        m2=1000.0,
        L=L,
        state0=state_8,
        t_max=2.0 * T_orbit_elliptical_8,
        description="Fast-rotating barbell in eccentric orbit (e=0.3) demonstrating gyroscopic stability that resists elliptical gravity-gradient torque."
    )

    return scenarios
