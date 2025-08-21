"""Plotting utilities."""

from __future__ import annotations

import subprocess

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, FFMpegWriter

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


def animate_barbell(log: dict, path: str, fps: int = 15) -> None:
    """Animate barbell COM trajectory and save as a video file.

    Parameters
    ----------
    log : dict
        Simulation log with position history ``r`` shaped ``(N, 3)``.
    path : str
        Destination filename for the animation.
    fps : int, optional
        Frames per second for the output video.  Defaults to ``15``.
    """

    r = np.asarray(log["r"])  # (N, 3) array of COM positions
    x = r[:, 0]
    y = r[:, 1]

    fig, ax = plt.subplots()
    line, = ax.plot([], [], "-", lw=2)
    ax.set_aspect("equal", "box")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_xlim(float(np.min(x)), float(np.max(x)))
    ax.set_ylim(float(np.min(y)), float(np.max(y)))

    def update(i: int):
        line.set_data(x[: i + 1], y[: i + 1])
        return (line,)

    ani = FuncAnimation(fig, update, frames=len(r), blit=True)

    try:
        writer = FFMpegWriter(fps=fps)
        ani.save(path, writer=writer)
    except subprocess.CalledProcessError as exc:
        msg = (
            "FFmpeg failed while writing the animation. Verify your ffmpeg installation "
            "or use a Pillow/ImageMagick writer instead."
        )
        raise RuntimeError(msg) from exc
    finally:
        plt.close(fig)
