# Passive diamond craft animation

This guide explains how to generate a lightweight animation of the passive
Earth–Moon L1 diamond craft configuration. The animation shows the four masses
as red dots connected by line segments, overlays the Earth–Moon line with a
dotted guide, and marks the approximate L2 location with a dotted circle.

## Prerequisites

Create the virtual environment and install the project dependencies if you
have not already done so:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Generate the animation

Run the helper script from the repository root. The command below keeps the
default simulation settings and writes `outputs/diamond_passive.gif`:

```bash
python sims/make_diamond_animation.py
```

The script prints the absolute path to the GIF when it finishes. To experiment
with different cadences or durations, use the optional CLI flags:

- `--t-final-days`: total simulated time in days (default: `7`).
- `--dt-output-hours`: integrator output cadence in hours (default: `0.5`).
- `--downsample-hours`: maximum spacing between animation frames in hours
  after down-sampling (default: `1`).
- `--circle-radius-km`: radius in kilometres for the dotted circle centred on
  L2 (default: `5000`).
- `--output`: custom output path for the generated GIF.

Example with a shorter run and a tighter circle around L2:

```bash
python sims/make_diamond_animation.py \
    --t-final-days 3 \
    --downsample-hours 1.5 \
    --circle-radius-km 3000 \
    --output outputs/diamond_passive_short.gif
```

The axes are plotted in the frame co-rotating with the Moon so that the
spacecraft remains near the centre of the view. Each frame uses only one
sample per simulated hour by default, keeping the file size manageable while
preserving the overall motion.
