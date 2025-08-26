# Torque and Tangential Acceleration Samples

This page accompanies [`torque_accel_table.py`](./torque_accel_table.py), a standalone
script that sweeps two angles without running an integrator:

- **`phi`** – the angle between the Moon and the barbell center of mass as
  measured from Earth.
- **`theta`** – the barbell's own orientation angle in the orbital plane.

For each angle pair the script evaluates the state-derivative function
[`f_state`](../src/tskb/dynamics.py) to get the instantaneous
gravitational acceleration on each mass and then computes

- the net torque about +z on the barbell, and
- the component of the center‑of‑mass acceleration along the tangential
  (prograde) direction of the orbit.

The craft is placed in a 100 km altitude circular orbit with a 1 km barbell
length; only lunar tidal effects introduce asymmetry.  The controller is
passive (no extension or retraction).

## Running

From the repository root:

```bash
python docs/torque_accel_table.py
```

This prints a table of torque and tangential acceleration values.  The
current output is embedded below.

```
phi_deg theta_deg    torque_Nm   tan_acc_mps2
    0.0       0.0    0.000e+00      0.000e+00
    0.0      90.0   -2.245e-14      0.000e+00
    0.0     180.0    1.347e-13     -2.079e-23
    0.0     270.0   -6.734e-14      0.000e+00
   60.0       0.0    2.825e-05      5.822e-05
   60.0      90.0   -2.825e-05      5.822e-05
   60.0     180.0    2.825e-05      5.822e-05
   60.0     270.0   -2.825e-05      5.822e-05
  120.0       0.0   -2.778e-05      5.677e-05
  120.0      90.0    2.778e-05      5.677e-05
  120.0     180.0   -2.778e-05      5.677e-05
  120.0     270.0    2.778e-05      5.677e-05
  180.0       0.0   -7.419e-21      7.931e-21
  180.0      90.0   -2.245e-14      0.000e+00
  180.0     180.0    1.347e-13      7.911e-21
  180.0     270.0   -6.734e-14      0.000e+00
  240.0       0.0    2.778e-05     -5.677e-05
  240.0      90.0   -2.778e-05     -5.677e-05
  240.0     180.0    2.778e-05     -5.677e-05
  240.0     270.0   -2.778e-05     -5.677e-05
  300.0       0.0   -2.825e-05     -5.822e-05
  300.0      90.0    2.825e-05     -5.822e-05
  300.0     180.0   -2.825e-05     -5.822e-05
  300.0     270.0    2.825e-05     -5.822e-05
```

These samples help reason about control strategies that use barbell
orientation and orbital phase to gain or shed orbital energy.
