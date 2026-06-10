# Diamond L1 Chapter Planning

This is the planning note for the next chapter: a diamond craft operating near
the Earth-Moon L1 region.

The goal is not to reuse the previous orbital chapters directly. This chapter is
about a craft balancing in the rotating Earth-Moon frame near the L1 saddle
point, with a very small control surface compared to the earlier orbital pumping
cases.

## Goal

Model a four-mass diamond craft near the Earth-Moon L1 point.

The intended behavior is:

- keep the Earth and Moon stationary in the chosen co-moving frame
- express the craft dynamics in a numerically stable frame, using Cartesian
  state internally and the rotating Earth-Moon frame for plots
- keep the Earth-Moon line explicit in the control law so the controller knows
  which axis it is trying to stabilize
- hold the diamond near the L1 equilibrium with a control law that only
  stretches or squishes the diagonal
- avoid skewed shapes entirely
- start from a diamond orientation with one mass pointing toward Earth and one
  toward the Moon
- study how the control behaves when the craft is perturbed away from the
  equilibrium

The reduced control surface is intentionally narrow:

- one scalar control for elongation/compression along the Earth-Moon line
- no in-plane skew degree of freedom
- no desire to spin the craft as a primary goal

The chapter should emphasize stability near the saddle point and the danger of
over-correction.

## Physical Picture

The earlier orbital chapters were driven by a single central body and ordinary
tidal gradients. This chapter is different.

Near L1, the local environment is a saddle in the effective potential of the
Earth-Moon rotating frame. The relevant restoring/unstable directions are not
the same as in the earlier Earth-only cases, and the control law will probably
need to account for that.

The intuition here is:

- the Earth-Moon line defines the primary axis
- the diamond is stretched or squeezed along that axis
- the craft remains mostly non-rotating
- the control tries to offset the saddle-point instability without injecting
  excessive oscillation

If the model is reliable enough, the motion should be readable even before the
controller is tuned aggressively.

## Coordinate Choice

The likely simulation frame is the standard rotating Earth-Moon frame:

- Earth and Moon remain fixed in the frame
- the craft evolves under the rotating-frame equations of motion
- the plotting layer should render in the Earth-Moon rotating frame so the
  fixed primaries and the craft path are easy to interpret

That is probably the cleanest way to avoid algebraic clutter while still keeping
the physics honest.

The implementation should avoid brittle symbolic derivations. Numerical
transforms are acceptable if they keep the code easier to trust.

For the first implementation, use the real Earth/Moon scale rather than a
normalized toy system. The Earth-Moon rotation rate comes from the actual lunar
orbital period, and the plot window should be narrowed in around the L1 station
so the craft and perturbations are visible at the same time.

## Control Model

The control law should be simpler than the previous chapters.

The working assumption is that the craft only has one useful shape input:

- `rho`: elongate or compress the diagonal along the Earth-Moon line

The shape should not skew.
The control should not try to rotate the diamond as a primary action.
The craft should stay oriented so that:

- one mass points toward Earth
- one mass points toward Moon
- the other two masses sit on the orthogonal diagonal

This is the “diamond” orientation in the strict sense, not the square-like
orientation.

The controller should be a low-order feedback law, most likely proportional
plus damping for the first pass, but the design should stay modest.

The goal is not precision station-keeping at the L1 point.
The goal is to show that the control can trend toward stability and avoid
obvious runaway behavior.

## Geometry

The diamond geometry should be reduced to a one-parameter family.

Planned constraints:

- only one deformation axis
- no skew family
- constant total moment of inertia, matching the earlier diamond chapter
- the diagonal toward Earth-Moon should be the controlled axis

The shape family should keep the diamond centered on its own center of mass and
deform smoothly along the Earth-Moon line.

That suggests a model where the body-frame reference is already aligned with
the Earth-Moon direction, and the only shape change is a diagonal squash/expand.

For the first scenarios, the spin should start aligned with the Earth-Moon
system and the diamond diagonal should be parallel to the Earth-Moon line.

## Scenarios

The chapter should start with a small scenario set that probes the local
stability structure around L1.

Recommended scenarios:

1. **Exact L1 with Earthward perturbation**
   - start at the nominal L1 saddle point
   - give the craft a velocity directly toward Earth
   - this probes the unstable direction
2. **Exact L1 with tangential perturbation**
   - start at the same L1 position
   - give the craft a velocity tangent to the Earth-Moon line
   - this probes the local sideways response
3. **Offset position, zero velocity**
   - start slightly displaced from L1
   - keep the velocity zero
   - this shows whether the controller can pull the craft back without
     exciting large oscillations

4. **No-op stabilization baseline**
   - keep the craft at the nominal L1 configuration with the controller active
   - use the same spatial and temporal window as the other scenarios
   - this gives a reference run for “best effort” station keeping without adding
     a new tuning branch

If a fourth scenario is useful, it should be a sign-reversal partner to one of
the first two rather than a new physical mechanism.

The nominal half-span should be tried at 200 km and 400 km in the first runs to
see which one remains readable without making the simulation too slow. The
initial simulation window can be penciled in now, then iterated after the first
renders once it is clear how much motion the perturbations produce.

## Implementation Shape

The implementation should follow the same chapter pattern as the existing code:

- `src/diamond_l1/`
  - `__init__.py`
  - `__main__.py`
  - `main.py`
  - `scenarios.py`
  - `controllers.py`
  - `geometry.py`
  - `physics.py`
  - `render.py`

The new package should keep the orchestration clean:

- `scenarios.py` defines initial conditions and metadata
- `controllers.py` defines the L1 control law
- `geometry.py` maps the scalar control target into the body-frame diamond
- `physics.py` computes the rotating-frame derivatives
- `render.py` produces the GIFs
- `main.py` only runs scenarios and writes files

## Likely Technical Risk

The biggest risk is controller over-correction near the saddle point.

Because L1 is unstable, a controller that is too aggressive may inject
oscillation or amplify the wrong mode. The chapter should probably use:

- a small gain
- explicit smoothing
- conservative initial conditions
- a short list of scenarios that are easy to interpret

The second risk is frame handling. The code should prefer numerical
transformations over manual algebra whenever that improves reliability.

## Open Questions

1. What exact Earth-Moon system parameters should we freeze for the first pass
   so the L1 location and orbital period are numerically stable and easy to
   reproduce?
2. What should the initial render-window duration be before we start iterating
   from the actual GIFs?
3. Should the first asset set include the no-op stabilization baseline in
   addition to the three probing scenarios listed above?

## Next Step

The next implementation pass should settle the coordinate choice and the exact
L1 control law, then build the minimal simulator and verify that the craft can
remain near the saddle point for at least one of the test scenarios.
