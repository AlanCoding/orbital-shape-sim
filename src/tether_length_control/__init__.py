"""
State-feedback tether length control experiments.
"""

from .controllers import (
    make_fixed_length_law,
    make_perigee_apogee_length_law,
    make_quadrant_length_law,
)
from .physics import (
    gravity_accel,
    cross2,
    tether_derivatives,
    endpoint_positions,
    endpoint_velocities,
    get_diagnostics,
)
from .scenarios import Scenario, get_scenarios

__all__ = [
    "make_fixed_length_law",
    "make_perigee_apogee_length_law",
    "make_quadrant_length_law",
    "gravity_accel",
    "cross2",
    "tether_derivatives",
    "endpoint_positions",
    "endpoint_velocities",
    "get_diagnostics",
    "Scenario",
    "get_scenarios",
]
