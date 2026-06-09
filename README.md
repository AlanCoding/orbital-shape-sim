# Orbital Shape Sim

A simulator for multi-mass systems and tethers in orbit.

## Rigid Barbell Simulation

This project simulates a rigid barbell in a 2D central gravity field around Earth. It generates educational GIFs illustrating:
1. **Radial gravity-gradient libration** (Scenario 1)
2. **Tumbling through the gravity gradient** (Scenario 2)
3. **Unequal-mass barbell dynamics** (Scenario 3)
4. **Elliptical-orbit forcing** (Scenario 4)
5. **Long-tether nonlinear gradient effects** (Scenario 5)
6. **Chaotic tumbling in eccentric orbits** (Scenario 6)
7. **Spin-stabilized orbit-attitude coupling / CM wobble** (Scenario 7)
8. **Spin-stabilized elliptical orbit** (Scenario 8)

All scenarios share a unified physical scaling ($L/r_0 = 1/3$) based on Scenario 5, and the simulations are run twice as long to clearly show long-term orbital and attitude evolution. Each simulation is rendered at 80 frames per second for a 3-second playback duration (240 frames total) for a 4x visual speedup and ultra-smooth motion.

### Running the Simulation

To run the simulation and generate the educational GIFs:

1. Ensure the virtual environment is set up and dependencies are installed:
   ```bash
   python3 -m venv .env
   source .env/bin/activate
   pip install -e .
   ```
   *(Note: The active python environment can also be found in `.env/`)*

2. Run the main script:
   ```bash
   python main.py
   ```

3. The outputs will be saved in `outputs/`:
   - `outputs/01_radial_libration.gif`
   - `outputs/02_tumbling.gif`
   - `outputs/03_unequal_masses.gif`
   - `outputs/04_elliptical_forcing.gif`
   - `outputs/05_long_tether_nonlinear.gif`
   - `outputs/06_chaotic_tumbling.gif`
   - `outputs/07_orbit_attitude_coupling.gif`
   - `outputs/08_fast_rotating_elliptical.gif`

---

## Tether Length Control Experiments

This repository also includes a separate state-feedback tether-length-control
experiment in `src/tether_length_control/`. The controller chooses the tether
length from the current state, while the tidal torque term evolves the angular
momentum and the changing inertia maps that angular momentum into spin rate.

Run the first-pass scenarios with:

```bash
python -m tether_length_control
```

The outputs are written to:

- `outputs/tether_length_control/01_fixed_length.gif`
- `outputs/tether_length_control/02_quadrant_forward.gif`
- `outputs/tether_length_control/03_quadrant_reverse.gif`
- `outputs/tether_length_control/04_perigee_apogee_forward.gif`
- `outputs/tether_length_control/05_perigee_apogee_reverse.gif`

## Failed Ideas Archive

### Moon Tidal Station-Keeping (Tidal Station Keeping Barbell - TSKB)
The codebase and literature regarding propellantless orbital-raising using third-body lunar gravity gradients on counter-rotating barbells has been archived under [failed_ideas/moon_tidal_tether/](file:///home/arominge/repos/orbital-shape-sim/failed_ideas/moon_tidal_tether/). 

**Why it failed:** 
Through detailed simulation, it was determined that the magnitude of the third-body lunar gravitational gradient effect is too small to produce practical orbit-raising or station-keeping benefits compared to the atmospheric drag and other perturbations in LEO.
