"""
Physics equations for a rigid barbell orbital simulation.
"""

import numpy as np

def gravity_accel(r, mu):
    """
    Computes central gravity acceleration: g(r) = -mu * r / |r|^3
    """
    r_mag = np.linalg.norm(r)
    if r_mag == 0:
        return np.zeros_like(r)
    return -mu * r / (r_mag ** 3)

def cross2(a, b):
    """
    2D cross product: a_x * b_y - a_y * b_x
    """
    return a[0] * b[1] - a[1] * b[0]

def barbell_derivatives(t, state, m1, m2, L, mu):
    """
    Computes derivatives of the state vector:
    state = [x, y, vx, vy, phi, phidot]
    """
    x, y, vx, vy, phi, phidot = state
    R = np.array([x, y])
    u = np.array([np.cos(phi), np.sin(phi)])

    M = m1 + m2
    a = L * m2 / M
    b = L * m1 / M

    r1 = R - a * u
    r2 = R + b * u

    g1 = gravity_accel(r1, mu)
    g2 = gravity_accel(r2, mu)

    # CM acceleration is mass-weighted
    A = (m1 * g1 + m2 * g2) / M

    # Torque about the CM
    tau = m1 * cross2(r1 - R, g1) + m2 * cross2(r2 - R, g2)

    # Moment of inertia
    I = (m1 * m2 / M) * (L ** 2)

    # Angular acceleration
    phiddot = tau / I

    return [
        vx,
        vy,
        A[0],
        A[1],
        phidot,
        phiddot,
    ]

def endpoint_positions(state, m1, m2, L):
    """
    Computes the inertial coordinates of the two endpoint masses r1, r2.
    """
    x, y, vx, vy, phi, phidot = state
    R = np.array([x, y])
    u = np.array([np.cos(phi), np.sin(phi)])
    M = m1 + m2
    a = L * m2 / M
    b = L * m1 / M
    r1 = R - a * u
    r2 = R + b * u
    return r1, r2

def endpoint_velocities(state, m1, m2, L):
    """
    Computes the inertial velocities of the two endpoint masses v1, v2.
    """
    x, y, vx, vy, phi, phidot = state
    V = np.array([vx, vy])
    u_perp = np.array([-np.sin(phi), np.cos(phi)])
    M = m1 + m2
    a = L * m2 / M
    b = L * m1 / M
    v1 = V - a * phidot * u_perp
    v2 = V + b * phidot * u_perp
    return v1, v2

def get_diagnostics(state):
    """
    Returns diagnostics such as radius, orbital angle, and local orientation angle.
    """
    x, y, vx, vy, phi, phidot = state
    r = np.sqrt(x ** 2 + y ** 2)
    theta = np.arctan2(y, x)
    psi = phi - theta
    # Wrap psi to [-pi, pi] for plotting/libration checks
    psi_wrapped = (psi + np.pi) % (2 * np.pi) - np.pi
    return {
        'r': r,
        'theta': theta,
        'psi': psi,
        'psi_wrapped': psi_wrapped
    }
