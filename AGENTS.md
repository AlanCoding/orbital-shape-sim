# Agents

This document describes the **agents** (controllers and scenario runners) used in **orbital-shape-sim**.  
Agents are modular strategies for controlling or evolving orbital tether systems within the simulator.  
They can be swapped in and out when running scenarios to compare performance.

---

## Controllers

### Bang–Bang Controller
- **File**: `src/tskb/controller.py`
- **Description**: Adaptive bang-bang controller that chooses tether extension or retraction to maximize instantaneous tidal power using a filtered power-sign heuristic with dwell-time and optional phase adaptation.
- **Use Case**: Baseline active control strategy for energy gain.

### Passive Controller

* **File**: `src/tskb/controller.py`
* **Description**: No active control; the system evolves only under natural dynamics.
* **Use Case**: Baseline for comparison against active controllers. An active controller may not be needed.

### Landis Controller

* **File**: `src/tskb/controller.py`
* **Description**: Implements the Landis perigee-retract / apogee-extend scheme that
  trades barbell angular momentum for orbital energy.
* **Use Case**: Simple propellantless orbit-raising controller.

### Moon Angle Controller

* **File**: `src/tskb/controller.py`
* **Description**: Commands tether acceleration using ``max_accel * cos(2*(\theta - offset))`` where ``\theta`` is the angle between the Moon and barbell center of mass. A phase offset ``offset_rad`` allows sweeping different schedules.
* **Use Case**: Explore angle-based acceleration schedules.
* **Run Example**:

```bash
  python sims/run_fom_scenarios.py --controller moon_angle \
    --omega0 fast_prograde --override theta0=0 \
    --override controller.offset_rad=0,1.57,3.14,4.71,6.28
```

### Neural Net Controller

* **File**: `src/tskb/controller.py`
* **Description**: Feedforward neural-network policy that maps the full state
  vector to a tether acceleration command. Parameters are optimized to maximize
  the semimajor-axis FOM.
* **Training Script**: `sims/train_nn_controller.py`
* **Use Case**: Learned control strategies and experimentation with optimized
  policies.

## Scenario Runners

### FOM Scenarios

* **File**: `sims/run_fom_scenarios.py`
* **Description**: Sweeps multiple initial conditions (e.g., rotation state, controller type) and reports the **Figure of Merit (FOM)**.
- **Run Example**:

```bash
  python sims/run_fom_scenarios.py --controller passive
```

- **Multiple Controllers**: Provide a comma-separated list.

```bash
  python sims/run_fom_scenarios.py --controller bang_bang,passive
```

- **Other Config Overrides**: Use `--override key=value1,value2` (dot notation for nested keys) to sweep additional
  configuration options.

```bash
  python sims/run_fom_scenarios.py --override mass=500,1000 --override controller.extend_accel=0.02,0.05
```

- **Single Spin Mode**: Use `--omega0` to run one initial rotation state. The `fast_prograde`
  option spins five times faster than the nominal prograde rate.

```bash
  python sims/run_fom_scenarios.py --controller moon_angle --omega0 fast_prograde --override theta0=0
```

* **Sample Output**:

```
  theta0(rad) omega0         controller     FOM (m)
  0.000       tidally_locked bang_bang   -218404.337
  0.000       tidally_locked passive       -753.637
  ...
```

### LEO 100 km

* **File**: `sims/run_leo_100km.py`
* **Config**: `configs/leo_100km.yaml`
* **Description**: Runs a detailed simulation of a tether system in low Earth orbit at 100 km altitude. Produces time-series artifacts for deeper analysis and automatically downsamples outputs to one point every two minutes to match plots and animations. In addition to the state history (`leo_100km.csv`), a derived-metrics file (`leo_100km_derived.csv`) records altitude, rotation rate, angle, tether length, control acceleration, eccentricity, and semimajor axis at the same cadence.
* **Run Example**:

```bash
  python sims/run_leo_100km.py --config configs/leo_100km.yaml
```

### Landis Demo

* **File**: `sims/landis_demo.py`
* **Description**: Minimal reproduction of the Landis orbit-raising maneuver.
  Runs with built-in parameters, disables lunar gravity, and writes a
  semimajor-axis plot.
* **Run Example**:

```bash
  python sims/landis_demo.py
```

## Roadmap

Planned or potential future work:

* **Fix negative FOM** – We are not getting the gains in semi-major axis expected, cause unknown.
* **Collision Constraint** - If Earth impact detected, end simulation, FOM is effectively negative infinity
* **Drag** - due to interaction with atmosphere, energy is lost
* **Atmospheric Scoop and Apature control** - collect propellant from atmosphere, integrate collection area into control system

## Contributing

To add a new controller:

1. Implement it in `controllers/` as a Python class or module.
2. Integrate with the scenario runner (`sims/`).
3. Add documentation here in `AGENTS.md` with usage examples.
