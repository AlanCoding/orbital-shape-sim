"""Plotting utilities."""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation

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


def animate_barbell(log: dict, path: str, interval: int = 200) -> None:
    """Animate barbell motion about Earth.

    Parameters
    ----------
    log : dict
        Output dictionary from :func:`run_simulation`.
    path : str
        Output filename for the GIF animation.
    interval : int
        Delay between frames in milliseconds.
    """

    r = log["r"]
    theta = log["theta"]
    length = log["length"]

    u = np.vstack([np.cos(theta), np.sin(theta), np.zeros_like(theta)]).T
    r1 = r + 0.5 * length[:, None] * u
    r2 = r - 0.5 * length[:, None] * u

    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    # Earth represented as a translucent sphere
    R_EARTH = 6378e3
    u_s = np.linspace(0, 2 * np.pi, 30)
    v_s = np.linspace(0, np.pi, 15)
    x = R_EARTH * np.outer(np.cos(u_s), np.sin(v_s))
    y = R_EARTH * np.outer(np.sin(u_s), np.sin(v_s))
    z = R_EARTH * np.outer(np.ones_like(u_s), np.cos(v_s))
    ax.plot_surface(x, y, z, color="b", alpha=0.3, linewidth=0)
    ax.scatter([0], [0], [0], color="k", s=10)

    mass1, = ax.plot([], [], [], "ro")
    mass2, = ax.plot([], [], [], "ro")
    connector, = ax.plot([], [], [], "k-", lw=1)

    all_pos = np.vstack([r1, r2])
    limit = np.max(np.abs(all_pos))
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_zlim(-limit, limit)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_zlabel("z [m]")

    def update(i: int):
        p1 = r1[i]
        p2 = r2[i]
        mass1.set_data([p1[0]], [p1[1]])
        mass1.set_3d_properties([p1[2]])
        mass2.set_data([p2[0]], [p2[1]])
        mass2.set_3d_properties([p2[2]])
        connector.set_data([p1[0], p2[0]], [p1[1], p2[1]])
        connector.set_3d_properties([p1[2], p2[2]])
        return mass1, mass2, connector

    ani = animation.FuncAnimation(fig, update, frames=len(log["t"]), interval=interval, blit=False)
    writer = animation.PillowWriter(fps=max(1, int(1000 / interval)))
    ani.save(path, writer=writer)
    plt.close(fig)
