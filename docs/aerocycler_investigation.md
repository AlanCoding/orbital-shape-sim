# Idealized orbital aerocycler: first numerical investigation

> **Current polar results, 2026-10-17:** see the [explicitly polar closure investigation](aerocycler_polar_results.md), which verifies nine near-polar checkpoints and compares resonance and primary radius. The historical L/D values and branch failures below do not bound those newer constructions.

> **Reviewed and corrected, 2026-10-14.** The new [orbital-mechanics review and monthly bank search](aerocycler_revisit.md) supersedes the aerodynamic conclusions below. The retained 4/2 orbit is almost **polar relative to the lunar plane**. Its quoted 7° compares plane normals in rotating coordinates and includes coordinate rotation; the zero-cross-track baseline's actual fixed-inertial-plane angles are about 1–3°. The original incoming-velocity impulse projection omitted quadratic work. Exact finite-work accounting rejects the nonzero-cross-track checkpoint as passive aerodynamics. A separately validated synthetic monthly return now requires maximum local L/D below 38 under the intended impulsive model.

## Bottom line

This investigation found and independently repropagated a closed 4/2 Earth–Moon CR3BP orbit with four identical primary impulses.  It also continued that root to a nonzero cross-track impulse, `J_E = 0.002`.  The latter closes to

- position norm: `7.43e-11` normalized length (`2.85e-5 km`),
- velocity norm: `6.81e-8` normalized velocity (about `7e-5 m/s`),
- period: `12.5118369601` normalized time (`54.4061891 days`).

It is a useful numerical root, but it is **not yet a physically valid cislunar aerocycler under a literal solid-surface interpretation**.  Its negative radial impulse produces a minimum primary distance about 10 m below the specified Earth radius.  More importantly, continuation toward larger plane changes loses the equal-radius/closure conditions before reaching 5° or 10°.  The simple constant-identical-impulse formulation is therefore characterized here as unsuccessful for the requested 5° and 10° physical cases, not silently repaired with pass-dependent controls.

The complete machine-readable results are in [`results/aerocycler`](../results/aerocycler), and all figures are in [`docs/assets/aerocycler`](assets/aerocycler).

## Variable closure

The prompt's variable count is subtly different from a naive six-state shooting problem.

At fixed `J_E`, the initial pre-impulse periapsis state has four coordinates:

1. two position angles on the prescribed primary-radius sphere,
2. two tangential inertial-velocity components.

Together with `J_D` and `J_R`, this appears to give six variables for six state-closure equations.  But an event-to-event map ends on a periapsis section, so one velocity closure equation is dependent.  Numerically, the nominal 6×6 Jacobian had singular values spanning approximately `1.9e3` to `1e-9`.  The correct formulation is five independent closure equations in six variables: a one-parameter family at fixed `J_E`.

The implementation uses:

- all three position residuals, scaled by `rho1`,
- the two tangential velocity residuals,
- the remaining family freedom for branch selection or an additional physical-radius condition.

The omitted radial residual is always checked in the independent six-state repropagation.

Requiring every one of `N` periapses independently to equal exactly `rho1` would add `N-1` constraints and overdetermine the original single-shooting variables.  The 4/2 branch has a symmetry that leaves only one alternating-radius condition, which was used during the physical continuation attempt.

## Equations and event convention

The code uses primary-centered coordinates rotating with the secondary.  The secondary is fixed at `(1, 0, 0)`.  With `q` measured from the primary,

```text
q_ddot = -2 zhat × q_dot + (q_x, q_y, 0)
         - (1-mu) q / |q|^3
         - lambda mu [ (q-e_x)/|q-e_x|^3 + e_x ].
```

Scaling both the direct secondary acceleration and the indirect primary-origin term makes `lambda=0` an exact Kepler problem represented in rotating axes.  This was regression-tested: the analytical 3/2 seed closes after `4 pi` with errors below `2e-8`.

The initial state is genuinely post-impulse.  The pre-impulse state is tangential at the prescribed radius, then the same `(J_D,J_E,J_R)` used at subsequent events is applied.  Each loop is integrated through an apogee event and then a periapsis event, which prevents the event detector from accepting the initial root.

## Retained Earth–Moon roots

Parameters:

```text
mu   = 0.012150585609624
rho1 = 6378.1363 / 384400 = 0.0165924461498439
rho2 = 1737.4 / 384400    = 0.00451977107180021
Earth rotation sigma = 27.396...
```

### Nonzero-cross-track 4/2 checkpoint

Shooting variables:

```text
longitude = -1.6321001629818868
latitude  =  0.0015249271317237549
v_lon     =  0.0060410850298954592
v_lat     = 10.841066498894092
J_D       =  0.00011336886523449427
J_E       =  0.002
J_R       = -0.048869101199811631
```

Initial rotating post-impulse state:

```text
[-0.0010165424171873416,
 -0.01656125812084008,
  0.000025302261509234897,
 -0.008521023785709958,
  0.0660468159477547,
 10.840867117948529]
```

Key outputs:

| quantity | value |
|---|---:|
| cycle period | 12.5118369601 (54.4061891 d) |
| encounter radii | 0.01659244615, 0.01659245629, 0.01659243559, 0.01659244622 |
| minimum primary distance | 0.01659242041 |
| minimum secondary distance | 0.2373408563 |
| lunar altitude at closest approach | 89,496.4 km |
| sampled secondary turning angle | 9.35545° |
| maximum encounter-plane departure | 7.16494° |
| position closure norm | 7.43e-11 |
| velocity closure norm | 6.81e-8 |

The normalized velocity unit is about 1.02316 km/s.  The impulse magnitude is `0.0489101`, about 50.0 m/s per pass, dominated by the radial term.  This is an abstract closure impulse, not a plausible aerodynamic maneuver.

The incoming/outgoing secondary-relative vectors, every Cartesian impulse, all post-impulse osculating elements, the sampled energy/angular momentum/Jacobi histories, and the full state history are in [`earth_moon_4_2_je_0p002.json`](../results/aerocycler/earth_moon_4_2_je_0p002.json).

### Zero-cross-track baseline

The baseline is more tightly closed:

```text
period                  = 12.5118519170
position closure norm   = 4.19e-11
velocity closure norm   = 2.65e-9
minimum secondary range = 0.2373400913
maximum node excursion  = 7.16409 deg
```

Its complete state is in [`earth_moon_4_2_baseline.json`](../results/aerocycler/earth_moon_4_2_baseline.json).

## Resonance-family results

The analytical Kepler apogees of 3/2, 4/2, and 5/2 all exceed the secondary distance.  Homotopy reached full Earth–Moon gravity for one root in every family.  A modest phase-offset multistart was also performed around the 5/2 seed.

| seed family | full-gravity result | max encounter-plane departure | physical issue |
|---|---:|---:|---|
| 3/2 | closed branch | 65.56° | one periapsis `0.0158185`, ~297 km below Earth |
| 4/2 | closed branch | 7.164° | negative radial impulse; 6–10 m dip below Earth |
| 5/2 | closed branch | 82.67° | one periapsis `0.0157306`, ~331 km below Earth |

Thus 4/2 had the smallest legacy rotating-coordinate plane-normal excursion among these three polar seeds. This does not establish either fixed-inertial-plane drift or proximity to the Earth–Moon orbital plane. All three are rejected as physical aerocyclers.

## 5° and 10° continuation result

The requested targets were not reached as physically valid constant-impulse solutions.

- The retained 4/2 family has a minimum plane departure near 7.16°; varying small `J_E` does not lower it to 5°.
- With unconstrained family selection, growing `J_E` makes alternating periapses fall below the primary radius.
- Using the remaining family variable to impose the alternating encounter radius works only close to the baseline.  The best residual and radius mismatch grow together as `J_E` increases.
- At `J_E=0.1`, the attempted physical continuation had full closure error about `1.1e-4` and a minimum event radius `0.01657665`, already about 6 km below Earth.
- A separate homotopy with `J_R` fixed exactly to zero diverged from closure by `lambda≈0.003`; the residual grew proportionally with secondary gravity rather than converging to another nearby root.

These failures are recorded in [`continuation_failures.json`](../results/aerocycler/continuation_failures.json) and plotted in the clearance/control figures.  No pseudo-arclength fold was observed before physical clearance was lost; this looks like a constraint incompatibility on the examined symmetric branch, not merely a parameter-continuation reversal.

The smallest justified next relaxation is to allow two alternating impulse vectors for the 4/2 orbit.  That adds three independent controls while preserving the useful two-pass symmetry and is more targeted than immediately allowing four unrelated impulses.  A second reasonable change is to distinguish solid radius from an atmospheric interface altitude, but that must be made explicitly rather than treating a negative `J_R` surface impulse as collision-free.

## Aerodynamic interpretation

The original investigation applied rigid atmospheric corotation only after orbital closure, using the incoming-velocity projection below:

```text
u = v_inertial,primary-relative - sigma (zhat × q)
D = -Delta-v dot uhat
L = Delta-v + D uhat.
```

This produced apparent L/D values about 1,660 for the checkpoint and 444 for the baseline. **These values are withdrawn as passive vehicle requirements.** For a finite impulse, exact atmosphere-relative work is `Delta-v · (u_in + Delta-v/2)`, not `Delta-v · u_in`. The omitted `|Delta-v|²/2` is decisive here. The nonzero-cross-track checkpoint increases atmosphere-relative energy at every encounter. The baseline's relative work is essentially zero at numerical precision, rather than showing meaningful aerodynamic dissipation.

The regenerated v2 JSON uses the exact midpoint work convention, records the work ledger, and reports lunar-plane inclination separately. Its midpoint L/D projection remains only a necessary work diagnostic, not a continuous-flight feasibility test. The new bank search resolves the local force direction throughout an idealized velocity-space turn; see [the review](aerocycler_revisit.md).

## Figures

1. [Rotating-frame trajectory](assets/aerocycler/01_rotating_trajectory.png)
2. [Inertial trajectory](assets/aerocycler/02_inertial_trajectory.png)
3. [Secondary encounter zoom](assets/aerocycler/03_secondary_zoom.png)
4. [Encounter-plane excursion](assets/aerocycler/04_plane_excursion.png)
5. [Impulse components versus excursion](assets/aerocycler/05_controls_vs_excursion.png)
6. [Primary clearance versus excursion](assets/aerocycler/06_clearance_vs_excursion.png)
7. [Cycle period versus excursion](assets/aerocycler/07_period_vs_excursion.png)
8. [Required L/D versus primary rotation](assets/aerocycler/08_ld_vs_rotation.png)
9. [Seed-family comparison](assets/aerocycler/09_branch_comparison.png)

## Reproduction

From the repository root:

```bash
PYTHONPATH=src .env/bin/pytest -q tests/test_aerocycler.py
MPLCONFIGDIR=/tmp/mplconfig PYTHONPATH=src .env/bin/python scripts/aerocycler_generate.py
```

The second command repropagates the stored shots at `rtol=2e-13`, `atol=2e-15`, rewrites the JSON, and regenerates all plots.  It does not invoke an optimizer, so it is an independent fixed-input verification of the printed states and impulses.
