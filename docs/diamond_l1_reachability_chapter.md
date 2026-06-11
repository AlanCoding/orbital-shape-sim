# Chapter 5: L1 Reachability Map

Run the chapter with:

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp .env/bin/python -m diamond_l1_reachability
```

The images are written to:

- `docs/assets/diamond_l1_reachability/reachability_global.png`
- `docs/assets/diamond_l1_reachability/reachability_l1.png`

This chapter follows [docs/diamond_l1_chapter.md](diamond_l1_chapter.md) and
uses the same Earth-Moon model, but instead of a control law it asks a simpler
question: from the L1 point, where can a small delta-v send the craft?

The state is integrated in the Cartesian Earth-Moon rotating frame. For the
figure, that rotating frame is shifted so the Earth sits at the origin and the
Moon stays fixed on the positive x-axis. The Moon's full orbital radius is
drawn as a circular guide, and the launch point is marked at L1. Because the
equations are time reversible, the same map describes departures from L1 and
returns toward it.

The figure set shows 24 trajectories total:

- 12 launch directions, spaced every `pi/6`
- 2 launch speeds: a smaller `0.05 m/s` case and a larger `50 m/s` case

The launch directions are sampled as polar angles about L1, but the figure is
rendered as a Cartesian projection of the co-rotating Earth-Moon frame.

Each trajectory carries a dot for every day that passes. The colors cycle by
launch direction, and both launch-speed families appear on both images.

### Co-rotating Earth-Moon Frame

![Global reachability map](assets/diamond_l1_reachability/reachability_global.png)

This image shows the full co-rotating Earth-Moon frame, with both the
`0.05 m/s` and `50 m/s` launch families overlaid together.

### L1 Neighborhood

![L1 neighborhood reachability map](assets/diamond_l1_reachability/reachability_l1.png)

This image is the L1-centered neighborhood view, also with both launch-speed
families overlaid. The map runs for 60 days so the longer launches have room to
unfold before the picture ends.

This is deliberately a reachability map, not a station-keeping result. It is
meant to show the first-order families reachable from L1 under small delta-v,
and to make the reversible geometry visually obvious.
