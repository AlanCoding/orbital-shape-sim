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

3. The GIFs are written to `docs/assets/rigid_barbell/` and embedded in
   [docs/rigid_barbell_chapter.md](docs/rigid_barbell_chapter.md).

---

## Tether Length Control Experiments

This repository also includes a separate state-feedback tether-length-control
experiment in `src/tether_length_control/`. The controller chooses the tether
length from the current state, while the tidal torque term evolves the angular
momentum and the changing inertia maps that angular momentum into spin rate.

Run the first-pass scenarios with:

```bash
MPLCONFIGDIR=/tmp .env/bin/python -m tether_length_control
```

The GIFs are written to `docs/assets/tether_length_control/` and embedded in
[docs/variable_length_chapter.md](docs/variable_length_chapter.md).

## Diamond Chapter

The finalized four-mass diamond orbital-control chapter lives in
[docs/diamond_chapter.md](docs/diamond_chapter.md).

Run it with:

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp .env/bin/python -m diamond
```

## Diamond L1 Chapter

The Earth-Moon L1 stabilizer chapter lives in
[docs/diamond_l1_chapter.md](docs/diamond_l1_chapter.md).

Run it with:

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp .env/bin/python -m diamond_l1
```

## Diamond L1 Reachability Map

The static L1 reachability map chapter lives in
[docs/diamond_l1_reachability_chapter.md](docs/diamond_l1_reachability_chapter.md).

Run it with:

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp .env/bin/python -m diamond_l1_reachability
```

## L4 Mass Receipt Chapter

The L4 mass receipt chapter lives in
[docs/l4_receipt_chapter.md](docs/l4_receipt_chapter.md).

Run it with:

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp .env/bin/python -m l4_receipt
```

## Cislunar Aerocycler

For the **single Earth-radius, 27.4413-day orbit**, start with the
[orbit dossier](docs/aerocycler_27day/README.md), including a detailed
[technical record](docs/aerocycler_27day/TECHNICAL.md), PNG/SVG figures,
standalone reproduction, and an [offline interactive 3D page](docs/aerocycler_27day/index.html).
Open the HTML file locally; no build or server is required.

The current [polar aerocycler results](docs/aerocycler_polar_results.md)
verify nine explicitly near-polar returns across primary radii and nominal
1:1, 1:2, 3:2, and 1:4 resonance families. An Earth-radius checkpoint closes
in 27.4413 days with maximum local L/D 25.685 and primary passes within
1.23° of polar. A 3.5-radius toy primary closes a three-pass, 54.6892-day
cycle with L/D 3.719 and passes within 1.46° of polar. The intended
application is repeated atmospheric propellant collection, not lunar
rendezvous; a close lunar encounter is not a requirement. These results
establish reduced-model orbit closure, not yet a collection mass budget.
Reproduce the fixed-input verification with:

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp/mplconfig .env/bin/python scripts/aerocycler_polar_verify.py
PYTHONPATH=src .env/bin/pytest -q tests/test_aerocycler.py tests/test_aerocycler_banking.py tests/test_aerocycler_polar.py
```

The [earlier review](docs/aerocycler_revisit.md) documents the separate
mostly-eastward 26.724-day experiment and the diagnostic corrections. The
[first investigation](docs/aerocycler_investigation.md) remains available
with its superseded conclusions marked explicitly.

## Failed Ideas Archive

### Moon Tidal Station-Keeping (Tidal Station Keeping Barbell - TSKB)
The codebase and literature regarding propellantless orbital-raising using third-body lunar gravity gradients on counter-rotating barbells has been archived under [failed_ideas/moon_tidal_tether/](file:///home/arominge/repos/orbital-shape-sim/failed_ideas/moon_tidal_tether/). 

**Why it failed:** 
Through detailed simulation, it was determined that the magnitude of the third-body lunar gravitational gradient effect is too small to produce practical orbit-raising or station-keeping benefits compared to the atmospheric drag and other perturbations in LEO.
