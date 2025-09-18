from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DiamondControlCommand:
    """Controller command describing the diamond's planar deformation."""

    stretch: float = 0.0


class Diamond:
    """Rigid four-mass diamond configuration.

    Four equal masses are connected by massless tethers forming a diamond
    within the Moon's orbital plane.  The structure maintains a fixed
    diameter; controllers may later adjust the spacing by returning a scaling
    factor from :func:`action`.
    """

    def __init__(self, mass: float, diameter: float = 100e3) -> None:
        self.mass = mass
        self.diameter = float(diameter)

    def dynamics(self, t: float, y: np.ndarray, env, ctrl) -> np.ndarray:
        """Return time derivative of the state vector ``y``.

        The state comprises ``[r(3), v(3)]`` for the craft centre of mass.
        Offsets of individual masses start at half the diameter in the
        ``±x`` and ``±y`` directions and may be stretched or compressed by
        the controller via :class:`DiamondControlCommand`.
        """

        if not np.isfinite(y).all():
            raise RuntimeError("non-finite state in dynamics")

        r = y[0:3]
        v = y[3:6]

        cmd = ctrl.action(t, y, env)
        stretch = 0.0
        if isinstance(cmd, DiamondControlCommand):
            stretch = float(cmd.stretch)

        d = 0.5 * self.diameter
        dx = max(d + 0.5 * stretch, 0.0)
        dy = max(d - 0.5 * stretch, 0.0)

        offsets = np.array(
            [
                [ dx, 0.0, 0.0],
                [-dx, 0.0, 0.0],
                [0.0,  dy, 0.0],
                [0.0, -dy, 0.0],
            ]
        )

        acc = np.zeros(3)
        for off in offsets:
            ri = r + off
            acc += env.a_earth(ri) + env.a_moon_tide(ri, t)
        a_com = acc / 4.0

        return np.hstack([v, a_com])
