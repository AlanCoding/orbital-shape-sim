"""Plotting utilities."""

from __future__ import annotations

import matplotlib.pyplot as plt

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
