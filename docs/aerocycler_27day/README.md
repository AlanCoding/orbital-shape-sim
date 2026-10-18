# The 27.4413-day polar aerocycler

This folder describes **one fixed Earth-radius solution**, not a search or a
comparison of families. The application is repeated atmospheric collection;
no close lunar encounter is required.

## Open the interactive page

Open **[index.html](index.html)** in a desktop browser. It is an offline,
buildless WebGL page: no CDN, installation, server, account, or internet
connection is required. Keep the folder together so its local assets resolve.
If a browser or website policy restricts local scripts, use the optional
server below instead.

- **Orbit mode:** drag to rotate, wheel to zoom, right-drag or Shift-drag to pan.
- **Fly mode:** click the scene, drag to look, W/S forward/back, A/D strafe,
  Q/E down/up. Hold Shift to move faster. Choose "Near Earth" for close work.
- **Top XY / Side XZ / Initial plane:** fixed camera directions, not changes to
  the physical trajectory. **Earth pass** pauses at the return and shows
  incoming/outgoing velocities and a magnified net-impulse arrow.
- **Incoming / Outgoing:** inspect the two sides of the instantaneous return
  bank. Its position does not jump; its velocity does.
- **Coordinate selector:** lunar-co-moving, Earth-centered non-rotating, or
  barycentric inertial. Only the first has periodic state closure.

The animation plays **one** coast and stops; it does not silently reset the
non-rotating trajectory and imply inertial closure. Body radii and positions
use one common scale. Spacecraft/point markers are symbols. Net Δv arrows
are explicitly magnified ×20 relative to the velocity arrows.

Optional local server, run from the **repository root**:

```bash
.env/bin/python -m http.server 8000 --bind 127.0.0.1 --directory docs/aerocycler_27day
```

Then open <http://127.0.0.1:8000/>. Stop the server with Ctrl-C.

## Technical record

- [TECHNICAL.md](TECHNICAL.md): equations, constants, precise initial state,
  frame transformations, event detection, maneuver construction, lift/drag
  decomposition, work accounting, and verification residuals.
- [data/initial_conditions.json](data/initial_conditions.json): fixed input.
- [data/verification.json](data/verification.json): generated numerical ledger.
- [data/trajectory.csv](data/trajectory.csv): full-precision coast in three frames.
- [data/bank.csv](data/bank.csv): velocity-space maneuver and local L/D.
- [figures/](figures/): five landscape figures, each PNG and editable SVG.
- [data/sha256.json](data/sha256.json): fingerprints of the generated data bundle.

The original checkpoint is preserved in repository commit `9753f73`, at
`results/aerocycler/polar/earth_1_1.json`. This folder repropagates that exact
six-state initial condition without optimization.

## Reproduce with a Python venv

Using the existing repository environment, from the repository root:

```bash
MPLCONFIGDIR=/tmp/mplconfig .env/bin/python docs/aerocycler_27day/reproduce.py --verify-only
```

Omit `--verify-only` to regenerate JSON, CSV, viewer samples, hashes, and all
figures. The script imports only NumPy, SciPy, and Matplotlib, not the
repository's aerocycler implementation. It detects apogee and the following
periapsis, applies the stated bank, and asserts closure and positive drag.

For a separate environment:

```bash
python3 -m venv .venv-aerocycler
.venv-aerocycler/bin/python -m pip install numpy scipy matplotlib
MPLCONFIGDIR=/tmp/mplconfig .venv-aerocycler/bin/python docs/aerocycler_27day/reproduce.py --verify-only
```

The generated ledger records the package versions used. Last reproduced:
Python 3.14.7, NumPy 2.4.6, SciPy 1.17.1, Matplotlib 3.10.9. Last few digits
of residuals can depend on platform and solver implementation.

## Put it on a website

Copy **this folder** to a static website directory, for example
`/aerocycler/`, and link to its `index.html`. Paths are relative. No build,
API, backend, cookies, remote fonts, analytics, or third-party scripts are
used. No deployment has been made by this work.

The interactive page needs `index.html`, `style.css`, `viewer.js`, and
`orbit-data.js`. Include `figures/`, `data/`, `README.md`, `TECHNICAL.md`, and
`reproduce.py` as well to preserve the evidence/download links. A Markdown
renderer is optional; the standalone HTML page is already readable without
one. The WebGL code is contained in `viewer.js` and uses no third-party engine.
