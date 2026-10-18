# Technical record: the 27.4413-day polar aerocycler

2026-10-17. **One fixed numerical return in an explicitly defined reduced
model.** The intended use is repeated atmospheric collection, not lunar
rendezvous. No collected-mass yield or physical vehicle design is claimed.

## 1. What exactly repeats?

Start immediately **after** an idealized aerodynamic bank at primary
periapsis. Coast under circular restricted Earth-Moon gravity through **one
apogee and one subsequent Earth periapsis**, then apply the specified bank.
The post-bank six-state vector returns numerically to its initial value in
**primary-centered axes rotating with the Moon**.

| Quantity | Value |
|---|---:|
| Coast / return period | 27.4413356378 days |
| Lunar sidereal periods per return | 1.00438021092 |
| Nominal resonance | Near 1:1, not an exact integer-month period |
| Subsequent Earth periapses per cycle | 1 |
| Aerodynamic banks per cycle | 1, at the return periapsis |
| Earth solid radius | 6,378.1363 km |
| Atmospheric interface altitude | 100 km |
| Periapsis center distance | 6,478.1363 km |
| Actual maximum Earth-center distance | 770,237.3132 km |
| Time of that maximum distance | 13.6468466304 days after departure |
| Incoming / outgoing inclination at bank | 91.13431852° / 88.77192035° |
| Worst primary-pass departure from polar | 1.22807965° |
| Instantaneous inclination during coast | Approximately 81.527°–91.158° |
| Periapsis latitude | 19.14609189° north |
| Required local L/D along prescribed bank | 25.64109431–25.68543101 |

The inertial orientation advances **361.57687593°** per return, or
**1.57687593° beyond one revolution**. The final position is not the initial
position in non-rotating axes. The bank changes velocity, not position.

The atmosphere is axisymmetric and its spin is aligned with the Moon's
orbital normal. It therefore presents the same velocity field at each
rotating-frame return even though the Earth's geographical longitude need
not repeat. The model does not require a particular patch of solid surface
to recur beneath the pass.

## 2. Model, constants, and normalization

The primary and secondary move on circular orbits. The spacecraft has
negligible mass for the gravity calculation. The primary is spherical, with
a prescribed atmosphere rotating rigidly about +z. There is no Sun, J2,
lunar eccentricity, spin-axis tilt, finite atmospheric coast, or captured
mass in this model.

These are the **actual constants of the computation**:

| Symbol | Definition | Value |
|---|---|---:|
| μ | Secondary fraction of total gravitational parameter | 0.012150585609624 |
| L | Earth–Moon separation / length unit | 384,400 km |
| P | Lunar sidereal period | 27.321661 days |
| τ = P/(2π) | Time unit | 375,699.8075009233 s |
| U = L/τ | Velocity unit | 1,023.1572982614725 m/s |
| Primary sidereal day | Prescribed rotation period | 0.99726968 days |
| σ = Ω/n | Primary rotation rate in normalized units | 27.39646210842387 |
| Primary solid radius / L | Dimensionless surface | 0.016592446149843912 |
| Interface radius / L | Surface plus 100 km | 0.0168525918314256 |
| Secondary radius | Moon exclusion sphere | 1,737.4 km |

Normalized lunar angular rate and total GM are both one. Consequently the
dimensional total GM is **402,409.4694253092 km³/s²** and primary GM is
**397,519.9587169337 km³/s²**. These are derived from the specified mean
separation/period and μ; **do not substitute an independently tabulated Earth
GM and expect the same root**. "Earth-radius" refers to the radius in this
mean circular, aligned-spin model, not a full Earth ephemeris.

## 3. Equations and coordinate systems

Let **q = (x,y,z)** be primary-relative position, in units L, in the rotating
frame. Earth is at 0, Moon at **eₓ = (1,0,0)**. +z is primary spin north and
the lunar orbital normal. Time t is in units τ. **v = dq/dt** is the
rotating-frame velocity, not the inertial velocity.

Define r = |q| and d = |q − eₓ|. Then

```text
q_dot = v

v_dot = -(1-μ) q/r³ - μ (q-eₓ)/d³ - μ eₓ
        - 2 e_z × v - e_z × (e_z × q).
```

The `−μ eₓ` term accounts for the acceleration of the primary-centered
origin. Its omission changes the problem.

Component form, to remove any sign ambiguity:

```text
x_ddot =  2 y_dot + x - (1-μ)x/r³ - μ(x-1)/d³ - μ
y_ddot = -2 x_dot + y - (1-μ)y/r³ - μy/d³
z_ddot =                  -(1-μ)z/r³ - μz/d³.
```

Let Rz(t) be a right-handed rotation about +z, with Rz(0) = identity. The
three coordinate conventions in the data/viewer are:

```text
Lunar-co-moving, primary centered:
    q_R = q                         v_R = v
    Earth_R = 0                     Moon_R = eₓ

Earth-centered, non-rotating axes:
    q_I = Rz(t) q
    v_I = Rz(t) [v + e_z × q]
    Earth_I = 0                     Moon_I = Rz(t) eₓ

Barycentric inertial:
    q_B = Rz(t) [q - μ eₓ]
    v_B = Rz(t) [v + e_z × (q - μ eₓ)]
    Earth_B = Rz(t) [-μ eₓ]          Moon_B = Rz(t) [(1-μ)eₓ].
```

Multiply positions by L and velocities by U for dimensional values. The
Earth-centered non-rotating axes have an accelerating origin; they should
not be mistaken for globally inertial barycentric coordinates. The label
"stationary" here means non-rotating axes, not a stationary Moon.

## 4. Full-precision initial condition

Epoch **t = 0** is immediately after the departure bank. The lunar line at
this arbitrary model epoch is +x. No calendar date or real lunar phase is
implied. Use this vector, not rounded orbital elements:

```text
q_R / L = [ 0.015110651764613217,
           -0.005012708307188879,
            0.005527278725762243 ]

v_R / U = [-3.2836195551417013,
            1.3302433736936474,
           10.18326674440602 ]
```

For orientation, the same initial position in km is

```text
[5808.534538317321, -1926.885073283405, 2124.6859421830063].
```

The initial primary-relative **non-rotating** velocity, in m/s and expressed
in axes coincident with rotating axes at t = 0, is

```text
[-3354.5305234687653, 1376.5087898930701, 10419.083689682364].
```

The initial two-body osculating elements provide context, not a replacement
for three-body propagation: semimajor axis **389,082.305797 km**,
eccentricity **0.983350216128**, inclination **88.77192035°**. Their values
vary during the coast; the trajectory is not one unchanging Kepler ellipse.

## 5. Event detection and coast verification

`reproduce.py` uses SciPy `solve_ivp(method="DOP853")` with
`rtol=3e-14`, `atol=3e-16`, `max_step=0.004` in normalized time. Dense output
is retained. It performs no fitting or optimization.

1. Integrate from t = 0 until q·v = 0 crosses **positive to negative**
   (apogee). The opposite event direction excludes the initial periapsis.
2. From that state integrate until q·v = 0 crosses **negative to positive**
   (the subsequent periapsis).
3. Construct the bank below at that event position. Compare the resulting
   post-bank state with the initial six-state vector.

The event time is approximately **6.310706984069389 τ**, rather than a
prescribed 2π. This distinction is why this return is near, not exactly,
1:1. Numerical residuals are reported in Section 8.

The first apogee is the maximum primary distance, not a closest-Moon event.
The Moon is distant throughout this coast; no lunar flyby targeting is part
of the construction.

## 6. Exact definition of the instantaneous bank

At the return periapsis q*, define local longitude λ and latitude φ, then

```text
e_E = [-sin λ, cos λ, 0]
e_N = [-sin φ cos λ, -sin φ sin λ, cos φ]
e_R = q*/|q*|.
```

The pre-bank radial velocity is zero to numerical event accuracy. Set
**s = |v_R,pre|**. Compute the target angle from the initial state using the
same local-basis construction at q₀:

```text
θ_target = atan2(v_R,0 · e_N,0, v_R,0 · e_E,0).
```

The heading is measured **from local east toward local north**. This is the
rotating-velocity heading; it differs from the inertial-velocity heading.
Construct a continuous path in velocity space, at fixed position:

```text
v_R(θ) = s [cos θ e_E + sin θ e_N]
θ: θ_pre → θ_target, monotonically decreasing
θ_pre ≈ 91.2853293953°
θ_target ≈ 88.7845799133°.
```

The post-bank vector is the endpoint. The bank keeps **rotating-frame
speed** constant, not atmosphere-relative speed or primary-relative
inertial speed. At a fixed position this preserves the Jacobi integral.
Six-state closure is verified after the maneuver; it is not defined by
arbitrarily overwriting the final velocity with the initial vector.

### Atmosphere-relative lift and drag

The atmospheric velocity in rotating axes is
**a = (σ−1) e_z × q***. Define relative velocity **u(θ) = v_R(θ) − a** and
unit vector **û = u/|u|**. For nonnegative path parameter
**ℓ = |θ−θ_pre|**, in radians, the required velocity derivative is

```text
g = dv_R/dℓ = -s [-sin θ e_E + cos θ e_N]
D = -g · û
g_D = -D û
g_L = g - g_D
L_aero = |g_L|
local L/D = L_aero / D.
```

Here D and L_aero are impulse magnitudes **per radian**, not physical forces
in newtons. Integrate `g_D dℓ` and `g_L dℓ` for the separate vector impulses.
`bank.csv` supplies 4,001 samples, including these per-radian magnitudes in
m/s/radian. Every sampled D is strictly positive. In fact its sign is
positive continuously on this turn: `g·v_R=0` and `g·a>0`, because g has a
positive eastward component throughout the small heading interval. Lift is
perpendicular to u by construction.

No propulsive thrust is supplied. Given a hypothetical time law ℓ(t_phys),
accelerations would be `U g_D dℓ/dt_phys` and `U g_L dℓ/dt_phys`; multiply by
vehicle mass to obtain force. The impulse model supplies **neither a duration
nor vehicle mass**, so it does not specify peak force, g-load, aerodynamic
area, heat flux, or an engine specific impulse. An atmospheric flight path
would also need gravity and altitude control during a finite maneuver.

### Velocity and impulse ledger

All entries below are **local east, north, radial** components, in m/s.
The velocities are primary-relative **inertial** velocities, expressed in
the local basis at the return. The impulse is the same physical vector in
rotating and inertial descriptions at the event.

| Quantity | East | North | Radial |
|---|---:|---:|---:|
| Incoming velocity | −231.165476 | +11,028.863682 | approximately 0 |
| Outgoing velocity | +250.286594 | +11,029.157404 | approximately 0 |
| **Net aerodynamic Δv** | **+481.452071** | **+0.293721** | **0** |
| Drag contribution | +0.741456 | −18.734453 | 0 |
| Lift contribution | +480.710615 | +19.028174 | 0 |

The northward spacecraft velocity does not reverse. Lift's favorable
northward component nearly cancels drag's southward component. Geographic
east/north components are **not** themselves lift/drag.

The integrated magnitudes are **18.750603 m/s drag** and **481.125138 m/s
lift**, ratio **25.65918**. These integrals of magnitudes are not generally
equal to the magnitudes of their vector integrals. Net Δv magnitude is about
**481.45216 m/s**. The local L/D varies slightly, and a physical vehicle
would need to realize the corresponding force directions and ratios.

## 7. Why rotational energy can close the orbit

At the pass the atmosphere moves eastward at **446.262900 m/s**. The useful
atmospheric speed relative to lunar-rotating axes is about **429.974 m/s**.
For an almost northward pass, the neutral-work bound is approximately

```text
L/D ≈ v_north / [(Ω−n) r cos φ] ≈ 11029 / 430 ≈ 25.7.
```

More exactly, for favorable lift and positive drag the local neutral
rotating-work ratio is `(v_R · u) / |v_R × u|`. The prescribed bank follows
that condition while turning v_R at constant speed. This supplies a
fundamental-mechanics explanation for the computed ratio, not a claim that
it is a global minimum across all possible trajectories.

Let **w = v_R + e_z × q*** be the primary-relative inertial velocity in the
local rotating axes. Exact work for a finite impulse uses the midpoint
velocity **w_mid = (w_pre+w_post)/2**, not just the incoming velocity:

```text
Δε_primary = U² Δv · w_mid
W_rotation = U² Δv · [σ e_z × q*]
W_air = U² Δv · [w_mid - σ e_z × q*]
Δε_primary = W_rotation + W_air.
```

| Energy per unit vehicle mass | J/kg |
|---|---:|
| Work supplied by prescribed planetary rotation | +214,854.1973 |
| Work relative to atmosphere (dissipative) | −207,011.7907 |
| **Net primary orbital-energy gain at bank** | **+7,842.4067** |
| Change of primary-relative orbital energy over coast | **−7,842.4067** |

The primary-relative osculating apogee rises from approximately
**759,920.802 km** to **771,686.475 km** at the bank. The actual three-body
maximum distance during the coast is **770,237.313 km**; these are different
diagnostics.

The impulse adds axial angular momentum, moving inclination from slightly
retrograde polar to slightly prograde polar. The coast removes that increase
so the cycle can recur. A perfectly polar incoming AND outgoing state would
have h_z = 0 on both sides and no rotational work `Ω Δh_z`. The small change
of inclination is part of the mechanism, not a substitution of an equatorial
orbit.

## 8. Numerical residuals and checks

The standalone reproduction reported:

| Diagnostic | Value |
|---|---:|
| Post-bank position closure norm | 9.43 × 10⁻⁶ m |
| Post-bank velocity closure norm | 6.44 × 10⁻⁹ m/s |
| Maximum sampled coast Jacobi error | 1.37 × 10⁻¹¹ normalized |
| Bank Jacobi jump | 1.42 × 10⁻¹⁴ normalized |
| Minimum primary altitude | 100 km, within numerical precision |

These are numerical residuals, **not physical navigation accuracy**. They
depend in their final digits on the solver/platform. The earlier repository
propagation also checked this fixed input at two tolerances. Reproduction
here uses a separate small implementation of the same equations and DOP853
algorithm; it is not a different-physics validation or a stability proof.

The Jacobi diagnostic is

```text
C = (x−μ)²+y² + 2(1−μ)/r + 2μ/d − |v_R|².
```

`verification.json` contains the full pre-bank and post-bank states, closure
vector, dimensional units, software versions, work, inclination, and
osculating-element diagnostics. Use its full values for comparisons rather
than copying rounded tables from this document.

## 9. Data, figures, and website conventions

- `data/initial_conditions.json` is the fixed, human-readable input.
- `data/trajectory.csv` contains t, time in days, rotating normalized states,
  Earth-centered non-rotating km/km/s states, and barycentric inertial
  km/km/s states. The final row is **before** the bank; post-bank state is
  separately reported in `verification.json`. Samples are nonuniform, dense
  near periapsis, and include apogee, endpoint, and adaptive solver nodes.
- `data/bank.csv` is a **velocity-space path**, not a time-resolved flight
  through the atmosphere. Its heading is the rotating heading, not inertial.
- `orbit-data.js` contains the same normalized trajectory and ledger for an
  offline page. The viewer uses cubic Hermite interpolation of q and v; it
  does not re-integrate or optimize the trajectory in JavaScript.
- `data/sha256.json` fingerprints inputs and generated data. Regenerating
  on another platform may change last digits and therefore hashes.

All PNG and SVG plots are landscape with labeled axes. Spatial plots use
equal distance scales; no vertical exaggeration. The top plots show the
Earth-Moon plane projection, and side plots retain z. The Earth-pass figure
rotates the incoming final leg back by T to compare it to the initial
outgoing leg in a common encounter orientation; it does not imply inertial
position closure. The bank figure explicitly expands the northward-velocity
axis to reveal its small net change.

The 3D viewer uses true Earth and Moon radii; point markers and labels improve
visibility at large distances. In the bank-vector overlay, incoming and
outgoing inertial velocity arrows share one scale; the much smaller net Δv
arrow is magnified **×20**, explicitly labeled. That overlay is fixed at the
return event, independently of the spacecraft time slider. Geographical
grid rotation is illustrative rigid-body spin, not an ephemeris Earth map.

## 10. Reproduction command and interpretation boundary

From the repository root, in the existing Python virtual environment:

```bash
MPLCONFIGDIR=/tmp/mplconfig .env/bin/python docs/aerocycler_27day/reproduce.py --verify-only
```

Omit `--verify-only` to regenerate all data and figures. No optimizer, API,
network access, or project-package import is used. The initial condition is
from `results/aerocycler/polar/earth_1_1.json` in commit `9753f73`.

The demonstrated result is a near-polar, passive, instantaneously controlled
periodic return in the stated model. A finite-duration aerodynamic maneuver,
a physical L/D-capable collector, accumulated cargo mass, and long-term
controlled operation remain distinct questions. They are not implicitly
included in the closure residual.
