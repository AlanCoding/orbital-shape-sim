# tidal-station-keeping-barbell

Prototype for tidal station-keeping using a counter-rotating double barbell spacecraft.

## Example orbit evolution

![Semimajor axis growth over time](docs/semimajor_axis_demo.png)

The plot above shows how the simulated barbell slowly raises its orbit.  The
semimajor axis—the average size of the orbit—grows as the counter-rotating
booms exchange angular momentum with the surrounding gravitational field.

This capability hints at practical value for a future space economy.  If a
spacecraft can adjust its orbit using tidal effects instead of propellant, it
reduces resupply needs and extends operational lifetimes.  Long-lived platforms
that can maneuver economically are better suited for activities such as
resource transport, on-orbit servicing, and manufacturing, all of which are
expected to be cornerstones of sustained economic activity beyond Earth.

## Running simulations

1. Install dependencies:
   ```bash
   python -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   ```
   or `make setup`.
2. Run the baseline case:
   ```bash
   python sims/run_leo_100km.py --config configs/leo_100km.yaml
   ```
   The script writes `outputs/leo_100km.csv` and a quicklook plot `outputs/leo_100km.png`.
3. Additional simulations:
   ```bash
   python sims/run_sweep_extent.py
   ```
   produces a sweep over boom length. Use `plotting.quicklook` or custom analysis on the CSV logs for other plots.

For a detailed project overview and development roadmap see `docs/overview.md` and `docs/roadmap.md`.

# Repository: `tidal-station-keeping-barbell`

A simulation + control prototype for **tidal station‑keeping / orbital raising** using **internal mass shifting** on a **counter‑rotating double‑barbell** spacecraft. The system exploits **third‑body (lunar/solar) tidal gradients** with an **optimal quadrupole schedule** to produce secular **orbital energy gain** without propellant.

---

## Goals & Acceptance Criteria

**Primary goal (Phase 1 demo):** Show **net increase in orbital energy** ($\Delta a>0$) of the spacecraft over $N$ orbits in LEO **with the Moon tide enabled**, using only internal actuation (barbell extension/retraction and spin control), while keeping total spacecraft linear momentum and external torque‐free aside from gravity.

**Acceptance test (baseline):** With parameters in `configs/leo_100km.yaml` and the **bang‑bang peri/apo schedule** for quadrupole $q(t)$, the integrator should report

* $\Delta a/a \ge 1\times10^{-4}$ ($~700\,\text{m}$ semimajor‑axis increase) over **30 days** of simulation, and
* **positive mean power** $\langle \dot E\rangle>0$ attributable to the lunar tide term (diagnostic decomposition), and
* **bounded attitude error** and **non‑slack tethers** throughout.

**Secondary goals:**

* Verify scaling $\propto (\ell/a)^2$ of effect size by sweeping boom extent $\ell$ (10–150 km).
* Demonstrate that a **single barbell** suffers secular spin bleed (spin‑orbit coupling) while **dual counter‑rotating barbells** preserve net spin and improve control authority.

## Academic Literature

This project builds on and extends a line of research into **extended‑body effects** and **tether/orbital mechanics**. Key references include:

* **Harte & Gaffney (2021), *Extended‑body effects and rocket‑free orbital maneuvering*.**

  * Showed how cyclic shape changes (quadrupole cycling) can alter **eccentricity** and **apsidal orientation** in a central (spherically symmetric) gravitational field.
  * Crucially: they proved that in a pure central field, **orbital energy and semimajor axis cannot change** — you only re‑shape the ellipse.
  * Difference: our present work adds a **third‑body tidal gradient** (Moon/Sun), breaking spherical symmetry and enabling **net energy transfer**.

* **Wisdom (2003), “Swimming in Spacetime”** and **Gueron et al. (2005), “Swimming vs. swinging in spacetime.”**

  * Conceptual/theoretical treatments showing that cyclic deformations in a curved field can alter trajectories. Distinguish relativistic “swimming” vs Newtonian “swinging.”
  * They gave the foundation for why internal motion *can* matter when the background potential has curvature/gradients.
  * Difference: our present work uses this insight *practically* for orbit raising in the Earth–Moon system, not just as a theoretical curiosity.

* **Murakami (1981), “On orbit control using gravity gradient effects.”**

  * Studied how **gravity‑gradient torques** on extended bodies couple attitude and orbital motion.
  * Showed that re‑shaping satellites can change how they interact with the field.
  * Difference: his work focused on **attitude control**, whereas our scheme deliberately harvests energy via the **tidal gradient** to change semimajor axis.

* **Tether studies (Carroll, NASA *Tethers in Space Handbook*, 1986).**

  * Explored **tether reeling** and gravity‑gradient effects to alter eccentricity or semimajor axis, sometimes invoking third‑body perturbations.
  * Difference: those schemes typically require **deployment/retrieval with respect to Earth’s central gradient** or use atmosphere drag (“electrodynamic” or “aerodynamic” tethers). Our work uses **lunar tidal forces**, avoiding drag/propellant.

* **Barbell/Dumbbell control literature (e.g. Pilipchuk, Shaw, Chalhoub, 2022).**

  * Studied using moving masses in a dumbbell satellite to alter eccentricity or orbital orientation.
  * Difference: again, these assumed only Earth’s central field, so **no energy gain**. Our dual‑barbell scheme extends this by leveraging the **third‑body tide**.

### Summary

All prior work shows that *internal actuation matters*, but in a central field it only redistributes orbital geometry, not energy. The novelty here is:

1. Explicitly adding the **lunar tidal gradient** to the force model.
2. Demonstrating with a **counter‑rotating dual‑barbell** that you can get **positive secular energy growth** (semimajor axis increase) without propellant.
