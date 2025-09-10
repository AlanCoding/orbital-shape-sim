"""Factory for spacecraft models."""

from __future__ import annotations

from .barbell import DualBarbell
from .point import PointMass
from .kite import Kite
from .diamond import Diamond


def make_craft(cfg: dict):
    """Instantiate a craft from configuration ``cfg``.

    Parameters
    ----------
    cfg : dict
        Must contain a ``type`` key of ``"barbell"``, ``"point"``, ``"kite"``
        or ``"diamond"`` and a ``mass`` value.  Additional keys are passed
        through to the specific craft constructor where applicable.
    """

    craft_type = cfg.get("type", "barbell").lower()
    mass = float(cfg.get("mass", 0.0))
    if craft_type == "barbell":
        return DualBarbell(
            mass,
            min_length=float(cfg.get("min_length", 1.0)),
            max_length=cfg.get("max_length"),
        )
    if craft_type == "point":
        return PointMass(mass)
    if craft_type == "kite":
        return Kite(mass)
    if craft_type == "diamond":
        return Diamond(mass, diameter=float(cfg.get("diameter", 100_000.0)))
    raise ValueError(f"unknown craft type: {craft_type}")

