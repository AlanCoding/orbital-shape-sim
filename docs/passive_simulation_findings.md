# Passive Simulation Drift after One Month

Using the `configs/leo_100km.yaml` configuration with the controller set to `passive`, we simulated a dual-barbell system in a 200 km circular Earth orbit for one month (`t_final = 2,592,000 s`). The barbell angle relative to the Moon was sampled when the craft's center of mass passed directly beneath the Moon near the end of the run.

- **Prograde initial spin** (`controller.initial.omega0 = prograde`): when crossing occurred at `t ≈ 2,591,050 s`, the barbell lagged the lunar vertical by about **+34°**.
- **Retrograde initial spin** (`controller.initial.omega0 = retrograde`): when crossing occurred at `t ≈ 2,590,155 s`, the barbell led the lunar vertical by about **–32°**.

These ∼30° offsets develop over a single month under passive dynamics, indicating that active control is required to maintain alignment with the Moon over longer durations.

To reproduce these measurements locally, run:

```bash
PYTHONPATH=src python docs/passive_drift_repro.py
```

which performs the month-long passive simulations for both spin modes and prints the barbell's angle relative to the Moon at the final crossing.

