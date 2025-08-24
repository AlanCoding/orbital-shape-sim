"""Plotting utilities."""

from __future__ import annotations

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np

from .diagnostics import _semimajor_axis_from_rv


def quicklook(log: dict, path: str) -> None:
    """Plot semimajor axis history.

    Time is rendered in **hours** and the semimajor axis in **kilometres**
    to avoid Matplotlib's offset/scientific-notation formatting when the
    simulation spans long durations and large orbital radii.  Only finite
    samples are plotted to guard against numerical blow-ups during long
    integrations.
    """

    t = np.asarray(log["t"], dtype=float) / 3600.0  # seconds → hours
    r = np.asarray(log["r"], dtype=float)
    v = np.asarray(log["v"], dtype=float)
    a = _semimajor_axis_from_rv(r, v) / 1000.0       # metres → kilometres

    mask = np.isfinite(a)
    plt.figure()
    plt.plot(t[mask], a[mask])
    plt.xlabel("Time [h]")
    plt.ylabel("Semimajor axis [km]")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def animate(log: dict, path: str) -> None:
    """Create a simple 2D animation of the barbell orbit."""

    r = np.asarray(log["r"])
    L = np.asarray(log["length"])
    theta = np.asarray(log["theta"])

    # Positions of endpoint masses
    u = np.column_stack(
        (np.cos(theta), np.sin(theta), np.zeros_like(theta))
    )
    r1 = r + 0.5 * L[:, None] * u
    r2 = r - 0.5 * L[:, None] * u

    fig, ax = plt.subplots()

    earth = plt.Circle((0.0, 0.0), 6378e3, color="tab:blue", alpha=0.3)
    ax.add_patch(earth)
    ax.plot(0.0, 0.0, "k.")

    m1, = ax.plot([], [], "ro", markersize=4)
    m2, = ax.plot([], [], "ro", markersize=4)
    tether, = ax.plot([], [], "r-", lw=1)

    ax.set_aspect("equal", "box")
    max_extent = np.max(np.linalg.norm(r, axis=1) + 0.6 * L)
    ax.set_xlim(-max_extent, max_extent)
    ax.set_ylim(-max_extent, max_extent)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")

    def init():  # pragma: no cover - animation boilerplate
        m1.set_data([], [])
        m2.set_data([], [])
        tether.set_data([], [])
        return m1, m2, tether

    def update(i):  # pragma: no cover - animation boilerplate
        p1 = r1[i]
        p2 = r2[i]
        m1.set_data([p1[0]], [p1[1]])
        m2.set_data([p2[0]], [p2[1]])
        tether.set_data([p1[0], p2[0]], [p1[1], p2[1]])
        return m1, m2, tether

    ani = animation.FuncAnimation(
        fig, update, frames=len(log["t"]), init_func=init, blit=True, interval=50
    )
    ani.save(path, writer=animation.PillowWriter(fps=10))
    plt.close(fig)
