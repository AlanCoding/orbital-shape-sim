# Chapter 6: L4/L5 Mass Receipt Planning

## Planning

This document is temporary and will be deleted after the chapter is
implemented. It is only a working note for the first pass.

The topic is orbital stability near the Earth-Moon L4 and L5 points while the
station receives mass from a driver or launcher.

## Goal

Show whether a finite-mass station can stay near L4 or L5 while it receives
discrete mass deliveries, and how the orbit changes as the delivered mass
accumulates.

The claim we want to test is deliberately modest: a larger receiver mass may be
the solution, but that is not yet proven.

## First Scene

Start with a small tadpole orbit around `L4` first.

- Use the co-rotating Earth-Moon frame for the plots.
- Keep the orbit slightly offset so it is visible but still clearly tadpole-like.
- It does not need to be a perfect circle.
- Later we can repeat the analysis for `L5`, because the asymmetry matters.

This first scene is just the station motion before any mass delivery is added.

## Example Payload

After the tadpole orbit is established, show one example payload trajectory
arriving at the station.

- The payload should come in tangentially from the Moon side.
- The arrival direction must be obtained by root-finding on the station orbit.
- The payload trajectory should be shown as a distinct path leading into the
  catch point.

This is the visual proof that the arrival geometry is being constructed from
the station orbit rather than guessed by hand.

## Catch Model

The delivery is an instant catch.

At the catch point, combine the payload and station velocities with
conservation of momentum, then keep integrating the combined station forward.
The catch changes the station velocity immediately, but it does not pause the
simulation.

Because the catch can effectively “rewind” the velocity angle and bring the
station back into a similar direction later, the search needs a dead time.
After a catch, ignore re-crossings for about half the time it takes to circle
the triangular point again.

## Delivery Search

The search should be coarse in angle, but precise in arrival direction.

Planned structure:

- break the full `360°` orbit into roughly `20` angular bins
- for each bin, find a point on the station orbit where the velocity direction
  matches that bin
- root-find the time or phase where the velocity direction enters the chosen
  bin
- treat that station state as the catch point for incoming payload

The arrival speed is on the order of `260 m/s`.

The payload should be imagined as arriving tangentially from the Moon side of
the system.

## Mass Growth

Start with a station mass of about `100` units.

Then receive deliveries with a rapidly increasing loading sequence:

- first delivery: `1` unit
- then `2`, `4`, `8`, ...
- stay flexible and keep the growth factor below or around `2x` if that is
  enough to reveal the stability limit
- continue until the total delivered mass reaches about `10,000` units

The point is to see when the orbit stops being L4/L5-like and begins to decay
into some other orbit.

## Stability Question

The key question is whether the station remains near the triangular point or
falls off into a different orbit after repeated catches.

For this chapter, “fell off” means the station becomes a moon-relative circle:
if the station orbit begins to look like a near-circular path around the Moon
instead of a tadpole around the triangular point, the L4/L5 lock has failed.

The chapter does not need high angular fidelity at first. Coarse binning is
fine if the arrival direction is accurate.

## Implementation Notes

- Plots should stay in the co-rotating Earth-Moon frame.
- The station orbit should be integrated forward in time and sampled at the
  velocity-angle crossings.
- The payload trajectory should be back-propagated from the catch point using
  reversibility so the arrival vector is consistent.
- A dead-time window should suppress re-detection of the same segment right
  after a catch.
- After the example payload plot, run the repeated-catch simulation where the
  station receives a payload on every tadpole loop and show how the orbit
  changes over time.

## Open Questions

- Which triangular point should be implemented first, L4 or L5?
- What exact tadpole orbit family should be used for the initial scene?
- How should the payload arrival be visualized: point mass only, or with a
  short trajectory segment leading into the catch?
- How should we define “fell off” the L4/L5 point: a distance threshold, a
  phase threshold, or a qualitative orbit-class change?
- Should the first implementation focus on one point only and then copy the
  method to the other, or should both be built in parallel?
