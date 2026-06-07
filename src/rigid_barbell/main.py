"""
Main execution script to run all scenarios and generate GIFs.
"""

import os
import time
import numpy as np
from scipy.integrate import solve_ivp

from .scenarios import get_scenarios
from .barbell_physics import barbell_derivatives
from .render import render_gif

def run_simulation(scenario):
    """
    Integrates the equations of motion for a given scenario using DOP853.
    """
    print(f"Running simulation for scenario: {scenario.id}...")
    t_start = time.time()
    
    t_span = (0.0, scenario.t_max)
    # Evaluate at a dense set of time points for high-fidelity interpolation later
    t_eval = np.linspace(0.0, scenario.t_max, 1000)
    
    sol = solve_ivp(
        fun=lambda t, y: barbell_derivatives(t, y, scenario.m1, scenario.m2, scenario.L, scenario.mu),
        t_span=t_span,
        y0=scenario.state0,
        t_eval=t_eval,
        method="DOP853",
        rtol=1e-10,
        atol=1e-12
    )
    
    t_end = time.time()
    print(f"  Simulation completed in {t_end - t_start:.2f} s. Status: {sol.status} ({sol.message})")
    return sol.t, sol.y.T

def main():
    scenarios = get_scenarios()
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    for scenario_id, scenario in scenarios.items():
        t_eval, states = run_simulation(scenario)
        
        gif_filename = f"{scenario_id}.gif"
        output_path = os.path.join(output_dir, gif_filename)
        
        print(f"  Rendering {gif_filename}...")
        t_start = time.time()
        
        # Render a 3 second GIF at 80 fps (240 frames)
        render_gif(
            scenario=scenario,
            t_eval=t_eval,
            states=states,
            output_path=output_path,
            fps=80,
            duration=3.0
        )


        
        t_end = time.time()
        print(f"  Saved GIF to {output_path} in {t_end - t_start:.2f} s.")
        print("-" * 50)

if __name__ == "__main__":
    main()
