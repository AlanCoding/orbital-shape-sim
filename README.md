# tidal-station-keeping-barbell

Prototype for tidal station-keeping using a counter-rotating double barbell spacecraft.

## Example orbit evolution

![Semimajor axis growth over time](docs/semimajor_axis_demo.png)

The plot above shows how the simulated barbell slowly raises its orbit.  The
semimajor axis—the average size of the orbit—grows as the counter-rotating
booms exchange angular momentum with the surrounding gravitational field.

This capability hints at practical value for a future space economy.  If a
spacecraft can adjust its orbit using tidal effects instead of propellant, it
reduces resupply needs and extends operational lifetimes.  Long-lived platforms
that can maneuver economically are better suited for activities such as
resource transport, on-orbit servicing, and manufacturing, all of which are
expected to be cornerstones of sustained economic activity beyond Earth.

## Running simulations

1. Install dependencies:
   ```bash
   python -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   ```
   or `make setup`.
2. Run the baseline case:
   ```bash
   python sims/run_leo_100km.py --config configs/leo_100km.yaml
   ```
   The script writes `outputs/leo_100km.csv` and a quicklook plot `outputs/leo_100km.png`.
3. Additional simulations:
   ```bash
   python sims/run_sweep_extent.py
   ```
   produces a sweep over boom length. Use `plotting.quicklook` or custom analysis on the CSV logs for other plots.

For a detailed project overview and development roadmap see `docs/overview.md` and `docs/roadmap.md`.
