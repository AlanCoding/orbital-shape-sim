"""Plotting utilities."""

from __future__ import annotations

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np

from .diagnostics import semimajor_axis


def quicklook(log: dict, path: str) -> None:
    """Plot semimajor axis history."""
    a = [semimajor_axis(log, i) for i in range(len(log["t"]))]
    plt.figure()
    plt.plot(log["t"], a)
    plt.xlabel("Time [s]")
    plt.ylabel("Semimajor axis [m]")
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
