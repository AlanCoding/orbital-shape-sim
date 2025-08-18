# tidal-station-keeping-barbell

Prototype for tidal station-keeping using a counter-rotating double barbell spacecraft.

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
