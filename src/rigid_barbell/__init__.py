"""
Rigid barbell orbital simulation package.
"""

from .barbell_physics import (
    gravity_accel,
    cross2,
    barbell_derivatives,
    endpoint_positions,
    endpoint_velocities,
    get_diagnostics
)
from .scenarios import Scenario, get_scenarios
from .render import render_gif

__all__ = [
    "gravity_accel",
    "cross2",
    "barbell_derivatives",
    "endpoint_positions",
    "endpoint_velocities",
    "get_diagnostics",
    "Scenario",
    "get_scenarios",
    "render_gif",
]
