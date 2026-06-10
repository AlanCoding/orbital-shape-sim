# Chapter 4: Diamond L1

Run the chapter with:

```bash
PYTHONPATH=src MPLCONFIGDIR=/tmp .env/bin/python -m diamond_l1
```

The GIFs are written to `docs/assets/diamond_l1/`.

This chapter moves the diamond craft into the Earth-Moon rotating frame and
focuses on the L1 saddle point. The Earth and Moon are fixed in that frame, the
state is kept Cartesian internally, and the renderer shows a narrow L1-centered
window with a small Earth-Moon overview strip below it.

The published asset set uses a 400 km half-span for the diamond. A first pass
comparison against 200 km showed that the larger structure reads better at the
chosen plot scale, so 400 km became the default chapter version.

The control law is deliberately simple:

- one scalar `rho` shape command
- proportional plus damping feedback along the Earth-Moon line
- constant total moment of inertia
- no skew mode and no spin command

The point of the chapter is not perfect station keeping. It is to show how the
diamond responds near the unstable L1 axis and how the control surface can
moderate that response without turning the chapter into a full guidance system.

## Model

The state is:

- `x, y`: spacecraft center-of-mass position in the rotating Earth-Moon frame
- `vx, vy`: velocity in the rotating frame
- `rho_act`: filtered realized diamond shape

The body geometry is a four-mass diamond with one pair of masses on the
Earth-Moon line and one pair on the perpendicular axis. The scalar `rho`
continuously trades length between those two axes while keeping the planar
moment of inertia constant.

The controller watches the displacement from L1 and the velocity along the
Earth-Moon line. That is enough for the first pass:

- Earthward motion should be countered by stretching the diamond
- Moonward drift should be countered by compressing it
- the tangential case is mainly a diagnostic for side motion, not the primary
  stabilization target

## Geometry

The reference diamond uses a one-parameter family:

```text
a = half_span * sqrt(rho)
b = half_span * sqrt(2 - rho)
```

with masses placed at:

```text
(+a, 0), (-a, 0), (0, +b), (0, -b)
```

This keeps the total planar inertia constant and avoids any skewed shapes.

## Scenarios

### 01. L1 No-Op Baseline

![L1 no-op baseline](assets/diamond_l1/01_noop_400km.gif)

The craft starts exactly at the nominal L1 point with zero velocity. The control
law is active but commands the neutral shape, so this is the reference case for
the chapter.

### 02. Earthward Perturbation

![Earthward perturbation](assets/diamond_l1/02_earthward_400km.gif)

The craft starts at L1 with a small Earthward velocity. This probes the
unstable axis of the saddle point and shows how much the shape feedback can
moderate the drift.

### 03. Tangential Perturbation

![Tangential perturbation](assets/diamond_l1/03_tangential_400km.gif)

The craft starts at L1 with a tangential velocity. This is a sideways response
case, not the main instability axis, but it helps show how the local motion
unfolds in the rotating frame.

### 04. Offset Position, Zero Velocity

![Offset position, zero velocity](assets/diamond_l1/04_offset_400km.gif)

The craft starts slightly displaced from L1 with no initial velocity. This is
the most direct “can the control pull it back gently?” case in the first batch.

## Notes

- The 400 km half-span is the published chapter configuration.
- The 200 km comparison run is retained only as a development reference.
- The main plot is L1-centered; the lower strip shows the Earth-Moon line and
  the local window position.
- The controller is intentionally simple so the chapter can be tuned iteratively
  after the first renders.

