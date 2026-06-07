# Repository: `tidal-station-keeping-barbell`

A simulation + control prototype for **tidal station‑keeping / orbital raising** using **internal mass shifting** on a **counter‑rotating double‑barbell** spacecraft. The system exploits **third‑body (lunar/solar) tidal gradients** with an **optimal quadrupole schedule** to produce secular **orbital energy gain** without propellant.

---

## 0) Goals & Acceptance Criteria

**Primary goal (Phase 1 demo):** Show **net increase in orbital energy** ($\Delta a>0$) of the spacecraft over $N$ orbits in LEO **with the Moon tide enabled**, using only internal actuation (barbell extension/retraction and spin control), while keeping total spacecraft linear momentum and external torque‐free aside from gravity.

**Acceptance test (baseline):** With parameters in `configs/leo_100km.yaml` and the **bang‑bang peri/apo schedule** for quadrupole $q(t)$, the integrator should report

* $\Delta a/a \ge 1\times10^{-4}$ ($~700\,\text{m}$ semimajor‑axis increase) over **30 days** of simulation, and
* **positive mean power** $\langle \dot E\rangle>0$ attributable to the lunar tide term (diagnostic decomposition), and
* **bounded attitude error** and **non‑slack tethers** throughout.

**Secondary goals:**

* Verify scaling $\propto (\ell/a)^2$ of effect size by sweeping boom extent $\ell$ (10–150 km).
* Demonstrate that a **single barbell** suffers secular spin bleed (spin‑orbit coupling) while **dual counter‑rotating barbells** preserve net spin and improve control authority.

---

## 1) Repository Tree

```
 tidal-station-keeping-barbell/
 ├─ README.md
 ├─ LICENSE
 ├─ CITATION.cff
 ├─ pyproject.toml
 ├─ requirements.txt
 ├─ Makefile
 ├─ .gitignore
 ├─ .pre-commit-config.yaml
 ├─ configs/
 │   ├─ leo_100km.yaml
 │   ├─ leo_50km.yaml
 │   ├─ leo_10km.yaml
 │   └─ integrator.yaml
 ├─ src/
 │   └─ tskb/
 │       ├─ __init__.py
 │       ├─ env.py            # gravity model (Earth central + lunar tidal), frames, ephemeris
 │       ├─ point.py          # single-mass dynamics
 │       ├─ barbell.py        # geometry → quadrupole Q, tension checks, spin kinematics
 │       ├─ kite.py           # placeholder four-point structure
 │       ├─ controller.py     # peri/apo bang‑bang, phase‑locked schedules, feedback wrappers
 │       ├─ integrate.py      # solve_ivp wrapper, event handling
 │       ├─ diagnostics.py    # energy partition, power from each term, osculating elements
 │       ├─ plotting.py       # quicklook plots
 │       └─ utils.py
 ├─ sims/
 │   ├─ run_leo_100km.py
 │   ├─ run_point_mass.py
 │   ├─ run_sweep_extent.py
 │   └─ run_single_vs_double_barbell.py
 ├─ tests/
 │   ├─ test_quadrupole_mapping.py
 │   ├─ test_tidal_forcing_switch.py
 │   ├─ test_energy_growth_baseline.py
 │   └─ test_tension_constraints.py
 ├─ docs/
 │   ├─ control_law.md
 │   ├─ physics_model.md
 │   ├─ numerics.md
 │   └─ roadmap.md
 └─ TODO.md
```

---

## 2) Physics Model (executive summary)

We integrate the spacecraft COM motion in an Earth–Moon 3‑body **tidal** setting and inject **extended‑body** effects via a **time‑varying quadrupole** $Q(t)$ derived from the barbell geometry.

**Gravitational potential:**

$$
\Phi(\mathbf r, t) = -\frac{\mu_E}{r}\; +\; \Phi_{\text{Moon}}(\mathbf r,t)\,.
$$

For the Moon we keep **full point‑mass** acceleration (not just the quadrupole) so the tide is exact:

$$
\mathbf a_{M}(\mathbf r,t) = -\mu_M\,\frac{\mathbf r-\mathbf R_M(t)}{\|\mathbf r-\mathbf R_M(t)\|^3}\; +\; \mu_M\,\frac{\mathbf R_M(t)}{\|\mathbf R_M(t)\|^3},
$$

which equals the gradient of the standard tidal potential in the spacecraft frame. (The second term removes Earth‑center acceleration.)

**Extended‑body force on COM:** (Newtonian quadrupole approximation)

$$
\mathbf F_{Q} = \frac{1}{2} Q_{jk}\,\nabla (\partial_j\partial_k \Phi) \;\equiv\; \frac{1}{2}\,Q: \nabla\nabla \nabla \Phi\,.
$$

In practice, we compute $Q(t)$ from barbell geometry (two masses per barbell, two counter‑rotating barbells) and evaluate the third derivatives of $\Phi$ **analytically** for the Moon and Earth terms; numerically, this is bundled as a single function `tidal_jet(r,t)` returning the 3rd‑order tensor $\nabla\nabla\nabla\Phi$.

**Torque‑free scheduling (default):** enforce $Q\,\hat r \parallel \hat r$ during bang‑bang segments ($\hat r = \mathbf r/\|\mathbf r\|$) to avoid pumping attitude. A fast attitude loop aligns one barbell’s principal axis to $\hat r$; the second barbell counter‑rotates to cancel net spin.

**Energy accounting:** The instantaneous **orbital power** due to tides is

$$
\dot E_{\text{tide}} = \dot{\mathbf r}\cdot \mathbf F_{Q}(t)\,.
$$

Diagnostics integrate $\int \dot E_{\text{tide}}\,dt$ and separate Moon vs. Earth contributions.

---

## 3) Control Law (bang‑bang + phase‑lock)

**State:** osculating elements $(a,e,\omega,\Omega,i)$, true anomaly $\nu$, and lunar phase angle $\phi_M$ (angle between $\hat r$ and Moon direction).

**Tether‑length schedule:** choose two tether accelerations (extension and retraction) and switch at **perigee** and **apogee** while maintaining **radial alignment** (torque‑free condition). Optionally add a small **phase lag** locked to $\phi_M$ to maximize $\langle\dot E\rangle$ from the lunar tide.

Pseudo‑spec for controller:

```
Given state (a,e,nu,phi_moon),
if near perigee window:   set L_ddot := -retract_accel
elif near apogee window:  set L_ddot := extend_accel
else:                     set L_ddot := 0
Align principal axis with r-hat (attitude loop),
command barbell spins equal/opposite (omega1 = +Ω, omega2 = -Ω) to hold net spin ≈ 0.
```

**Feedback hooks:** if diagnostics show $\langle\dot E\rangle<0$ over a window, adjust the perigee/apogee switching thresholds and $\phi_M$ lag by a bounded gradient step.

---

## 4) Key Files (initial contents)

### README.md

````markdown
# Tidal Station‑Keeping with Counter‑Rotating Barbells

This repo simulates a spacecraft that raises its orbit by cyclically changing its quadrupole moment in the **Earth–Moon tidal field**. It implements:
- Earth central gravity + exact lunar point‑mass tide,
- A double‑barbell geometry → time‑varying quadrupole \(Q(t)\),
- A peri/apo **bang‑bang** control law with lunar phase lock,
- Diagnostics to confirm **secular energy gain** (\(\Delta a>0\)).

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python sims/run_leo_100km.py --config configs/leo_100km.yaml
````

Outputs: `outputs/` contains CSV logs and plots of `a(t)`, `e(t)`, energy budget, and per‑term power.

## Physics brief

* COM dynamics under Earth + lunar tide; extended‑body force via quadrupole coupling $\mathbf F_Q = \tfrac12 Q: \nabla\nabla\nabla\Phi$.
* Control aligns $Q$ radially and switches eigenvalue at peri/apo; dual counter‑rotating barbells cancel net spin.

## Acceptance Test

Run `pytest -k energy_growth_baseline` and ensure pass criteria in README top section.

```
```

### docs/control\_law\.md

```markdown
# Control Law: Peri/Apo Bang‑Bang with Lunar Phase Lock

We schedule the tether length acceleration \(L\ddot{}\) between extension and retraction values with switches near true anomalies \(\nu\in\{0,\pi\}\). The barbell is kept radially aligned (torque‑free) and a small phase offset \(\delta\) relative to the Moon direction can be used to obtain positive average power from the tidal force.

Controller parameters:
- `extend_accel`, `retract_accel` (m/s²)
- windows `Δν_peri`, `Δν_apo` in radians
- lunar phase offset `δ`
- attitude loop gain `k_att`

We expose a gradient tweak on `(Δν_peri, Δν_apo, δ)` to maximize a rolling estimate of mean power.
```

### docs/physics\_model.md

```markdown
# Physics Model

**Moon ephemeris:** circular orbit at radius \(R_M\), mean motion \(n_M\). Vector \(\mathbf R_M(t)\) in ECI.

**Tidal acceleration:** \(\mathbf a_M(\mathbf r,t) = -\mu_M\frac{\mathbf r-\mathbf R_M}{\|\mathbf r-\mathbf R_M\|^3} + \mu_M\frac{\mathbf R_M}{\|\mathbf R_M\|^3}\).

**Quadrupole force:** \(\mathbf F_Q = \tfrac12 Q: \nabla\nabla\nabla (\Phi_E+\Phi_M)\). We use analytic 3rd derivatives of point‑mass potentials.

**Barbell mapping to Q:** For a single barbell with endpoint masses \(m_b/2\) separated by length \(L\) along unit axis \(\hat u\):
\[Q = \frac{m_b L^2}{12}\,(3\,\hat u\hat u - I).\]
Two barbells, axes \(\hat u_1, \hat u_2\), spins \(\pm\Omega\), lengths \(L_{1,2}(t)\) → \(Q = Q_1+Q_2\). The controller commands \(L_{1,2}\) to realize radial eigen‑alignment and desired \(q(t)\).

**Tension constraint:** maintain tether tension \(T\ge 0\). We enforce \(T_0\) pre‑tension and limit \(\dot L\) to keep inertial loads < limit.
```

### configs/leo\_100km.yaml

```yaml
orbit:
  a_km: 7000.0
  e: 0.001
  inc_deg: 0.0
  raan_deg: 0.0
  argp_deg: 0.0
moon:
  model: circular
  R_km: 384400.0
  n_rad_s: 2.6617e-6
barbells:
  total_mass_kg: 20000.0
  boom_extent_km: 100.0   # ℓ
  pretension_N: 500.0
  spin_rad_s: 0.0         # net spin ≈ 0 via counter‑rotation
controller:
  type: bang_bang
  extend_accel: 0.001    # m/s^2
  retract_accel: 0.001   # m/s^2
  delta_phase_deg: 10.0
  nu_window_deg: 8.0
integrator:
  t_end_days: 35.0
  dt_s: 1.0
  rtol: 1e-9
  atol: 1e-9
outputs:
  save_csv: true
  save_plots: true
```

### src/tskb/env.py (stub API)

```python
import numpy as np

MU_E = 3.986004418e14
MU_M = 4.9048695e12
R_MOON = 384400e3
N_MOON = 2.6617e-6

class Env:
    def __init__(self, cfg):
        self.mu_e = MU_E
        self.mu_m = MU_M
        self.nm = N_MOON
        self.Rm = R_MOON

    def moon_pos(self, t):
        theta = self.nm * t
        return np.array([self.Rm*np.cos(theta), self.Rm*np.sin(theta), 0.0])

    def a_earth(self, r):
        return -self.mu_e * r / np.linalg.norm(r)**3

    def a_moon_tide(self, r, t):
        Rm = self.moon_pos(t)
        return -self.mu_m*( (r-Rm)/np.linalg.norm(r-Rm)**3 - Rm/np.linalg.norm(Rm)**3 )

    def tidal_jet_third_deriv(self, r, t):
        # return 3rd derivatives tensor of Φ_E + Φ_M at r
        # (implemented analytically in actual code)
        raise NotImplementedError
```

### src/tskb/barbell.py (mapping to Q)

```python
import numpy as np

class DoubleBarbell:
    def __init__(self, mass, ell, pretension):
        self.m = mass
        self.ell = ell
        self.T0 = pretension
        # default axes; attitude loop will rotate these to align with r-hat
        self.u1 = np.array([1.0,0.0,0.0])
        self.u2 = np.array([1.0,0.0,0.0])
        self.L1 = ell
        self.L2 = ell

    @staticmethod
    def Q_of_barbell(mb, L, u):
        I = np.eye(3)
        uu = np.outer(u,u)
        return (mb*L**2/12.0)*(3*uu - I)

    def Q(self):
        mb = 0.5*self.m
        return self.Q_of_barbell(mb, self.L1, self.u1) + self.Q_of_barbell(mb, self.L2, self.u2)
```

### src/tskb/controller.py (spec skeleton)

```python
import numpy as np

class BangBangController:
    def __init__(self, cfg):
        self.extend_accel = cfg["extend_accel"]
        self.retract_accel = cfg["retract_accel"]
        self.delta_phase = np.deg2rad(cfg["delta_phase_deg"])
        self.nu_window = np.deg2rad(cfg["nu_window_deg"])

    def action(self, t, state):
        r = state[0:3]
        nu = np.arctan2(r[1], r[0])
        nu = np.arctan2(np.sin(nu + self.delta_phase), np.cos(nu + self.delta_phase))
        if abs(nu - np.pi) < self.nu_window:
            return self.extend_accel
        if abs(nu) < self.nu_window:
            return -self.retract_accel
        return 0.0
```


### tests/test\_energy\_growth\_baseline.py (outline)

```python
import numpy as np
from tskb.diagnostics import mean_power_from_tide, semimajor_axis

def test_energy_growth_baseline(run_100km_case):
    log = run_100km_case
    assert mean_power_from_tide(log) > 0.0
    a0 = semimajor_axis(log, idx=0)
    a1 = semimajor_axis(log, idx=-1)
    assert (a1 - a0) / a0 >= 1e-4
```

---

## 5) Numerics & Logging

* Integrator: `scipy.integrate.solve_ivp` (DOP853), strict `rtol=1e-9, atol=1e-9`.
* Time step hints from `integrator.yaml` but the solver is adaptive; we substep dynamics to keep the `tidal_jet` stable.
* Diagnostics every 10 s: osculating elements, energy partition, instantaneous powers (Earth central, lunar point‑mass, quadrupole coupling).
* CSV logs in `outputs/`; plots via `plotting.py`.

---

## 6) To‑Do (prioritized)

1. **Simulation proving energy gain** (this user request): implement `tidal_jet_third_deriv`, finish tensor contraction, run `sims/run_leo_100km.py` and validate acceptance test.
2. Add **attitude alignment loop** (fast inner loop) and verify torque‑free condition numerically.
3. Implement **phase‑locked controller** with gradient tweak on `(Δν_peri, Δν_apo, δ)`.
4. Sweep **extent ℓ** (10–150 km) and validate $\propto (\ell/a)^2$ scaling.
5. Add **drag, J2, SRP** toggles to test robustness.
6. Add **safety checks**: tension non‑negativity under commanded $\dot L$, structural load margins.
7. Package result plots and a short memo in `docs/`.

---

## 7) Requirements & Tooling

**Python 3.10+**

`requirements.txt`:

```
numpy
scipy
pyyaml
matplotlib
```

**Makefile** targets:

```
setup:        python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
lint:         ruff src sims tests
test:         pytest -q
run-100km:    python sims/run_leo_100km.py --config configs/leo_100km.yaml
sweep-extent: python sims/run_sweep_extent.py
```

---

## 8) Notes on Dual Counter‑Rotating Barbells

* Use equal masses and symmetric geometry so the total spin angular momentum ≈ 0.
* Attitude controller aligns one barbell’s axis to $\hat r$; the second mirrors it with opposite spin.
* The summed $Q$ achieves the commanded $q(t)$ while minimizing internal angular‑momentum exchange with the orbit.

---

## 9) CITATION & License

* Add `CITATION.cff` acknowledging foundational work on extended‑body effects and tidal station‑keeping concept notes.
* License: permissive (e.g., MIT).

---

**End of manifest.**

