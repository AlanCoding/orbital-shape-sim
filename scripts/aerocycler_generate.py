#!/usr/bin/env python3
"""Repropagate the retained Earth-Moon shots and regenerate data/figures."""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from aerocycler import Family, Shot, earth_moon_system, propagate_cycle
from aerocycler.diagnostics import inertial_history, summarize


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "aerocycler"
FIGURES = ROOT / "docs" / "assets" / "aerocycler"


RETAINED = {
    "earth_moon_4_2_baseline": Shot.from_fixed_je(
        np.array(
            [
                -1.6333172555942024,
                0.0017041852717482289,
                0.0014867402810952914,
                10.841069151675804,
                1.1013466011515201e-4,
                -0.048866463459400086,
            ]
        ),
        0.0,
    ),
    "earth_moon_4_2_je_0p002": Shot.from_fixed_je(
        np.array(
            [
                -1.6321001629818868,
                0.0015249271317237549,
                0.0060410850298954592,
                10.841066498894092,
                1.1336886523449427e-4,
                -0.048869101199811631,
            ]
        ),
        0.002,
    ),
}


# Continuation checkpoints include rejected points.  They are intentionally
# retained so a failed physical branch cannot be mistaken for missing work.
CONTINUATION = [
    {"je": 0.0, "excursion_deg": 7.16391, "jd": 1.10135e-4, "jr": -0.0488665, "period": 12.511852, "min_r": 0.016592431, "status": "verified"},
    {"je": 0.002, "excursion_deg": 7.16508, "jd": 1.13371e-4, "jr": -0.0488694, "period": 12.511836, "min_r": 0.016592420, "status": "verified"},
    {"je": 0.01, "excursion_deg": 7.18181, "jd": 1.27207e-4, "jr": -0.0488706, "period": 12.5118, "min_r": 0.01659112, "status": "radius/closure failure"},
    {"je": 0.05, "excursion_deg": 7.27558, "jd": 2.84953e-4, "jr": -0.0489293, "period": 12.5118, "min_r": 0.01658455, "status": "radius/closure failure"},
    {"je": 0.10, "excursion_deg": 7.40009, "jd": 6.90213e-4, "jr": -0.0490804, "period": 12.5118, "min_r": 0.01657665, "status": "radius/closure failure"},
    {"je": 0.15, "excursion_deg": 7.72867, "jd": 1.31544e-3, "jr": -0.0492675, "period": 12.5118, "min_r": 0.01656380, "status": "radius/closure failure"},
    {"je": 0.20, "excursion_deg": 7.83801, "jd": 2.18155e-3, "jr": -0.0495902, "period": 12.5118, "min_r": 0.01655538, "status": "radius/closure failure"},
]


def save_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    system = earth_moon_system()
    family = Family(4, 2)
    summaries = {}
    propagated = {}
    for branch_id, shot in RETAINED.items():
        result = propagate_cycle(
            system,
            family,
            shot,
            rtol=2e-13,
            atol=2e-15,
            max_step=0.006,
            dense_output=True,
        )
        summary = summarize(system, family.label, branch_id, shot, result)
        summaries[branch_id] = summary
        propagated[branch_id] = result
        save_json(RESULTS / f"{branch_id}.json", summary)
    save_json(RESULTS / "continuation_failures.json", CONTINUATION)

    branch_id = "earth_moon_4_2_je_0p002"
    summary = summaries[branch_id]
    result = propagated[branch_id]
    time = np.asarray(summary["history"]["time"])
    state = np.asarray(summary["history"]["state_rotating"])
    q = state[:, :3]
    impulses = np.asarray([arc.pre_state[:3] for arc in result.arcs])
    closest = int(np.argmin(np.linalg.norm(q - np.array([1.0, 0.0, 0.0]), axis=1)))

    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(projection="3d")
    ax.plot(q[:, 0], q[:, 1], q[:, 2], lw=0.8)
    ax.scatter(0, 0, 0, s=80, label="Earth")
    ax.scatter(1, 0, 0, s=35, label="Moon")
    ax.scatter(impulses[:, 0], impulses[:, 1], impulses[:, 2], marker="^", s=30, label="impulses")
    ax.scatter(*q[closest], marker="x", s=60, label="closest Moon approach")
    ax.set(xlabel="x", ylabel="y", zlabel="z", title="4/2 aerocycler — Earth–Moon rotating frame")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURES / "01_rotating_trajectory.png", dpi=180)
    plt.close(fig)

    inertial = inertial_history(time, state, system.mu)
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(projection="3d")
    ax.plot(inertial[:, 0], inertial[:, 1], inertial[:, 2], lw=0.8)
    ax.set(xlabel="x", ylabel="y", zlabel="z", title="Barycentric inertial trajectory")
    fig.tight_layout()
    fig.savefig(FIGURES / "02_inertial_trajectory.png", dpi=180)
    plt.close(fig)

    distance = np.linalg.norm(q - np.array([1.0, 0.0, 0.0]), axis=1)
    mask = distance < min(0.35, 4.0 * distance[closest])
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(q[mask, 0] - 1.0, q[mask, 1], lw=1)
    moon = plt.Circle((0, 0), system.rho2, color="0.5", alpha=0.7)
    ax.add_patch(moon)
    ax.scatter(q[closest, 0] - 1.0, q[closest, 1], marker="x", color="red", label="closest approach")
    ax.set(aspect="equal", xlabel="x − x_M", ylabel="y", title="Secondary encounter (rotating frame)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "03_secondary_zoom.png", dpi=180)
    plt.close(fig)

    excursions = summary["encounter_plane_excursions_deg"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(range(len(excursions)), excursions, "o-", label="Legacy: normals in lunar rotating axes")
    inertial_excursions = summary["encounter_initial_inertial_plane_excursions_deg"]
    ax.plot(range(len(inertial_excursions)), inertial_excursions, "s-", label="Fixed initial inertial plane")
    ax.set(xlabel="encounter index (0 is initial post-impulse state)", ylabel="plane-normal angle (deg)", title="Original polar orbit: coordinate rotation versus inertial drift")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES / "04_plane_excursion.png", dpi=180)
    plt.close(fig)

    cont = CONTINUATION
    excursion = np.array([row["excursion_deg"] for row in cont])
    valid = np.array([row["status"] == "verified" for row in cont])
    fig, ax = plt.subplots(figsize=(7, 4))
    for key, label in (("jd", "$J_D$"), ("je", "$J_E$"), ("jr", "$J_R$")):
        values = np.array([row[key] for row in cont])
        ax.plot(excursion, values, "o-", label=label, alpha=0.8)
    ax.scatter(excursion[~valid], np.zeros(np.sum(~valid)), marker="x", color="red", label="rejected checkpoint")
    ax.set(xlabel="legacy rotating-coordinate normal excursion (deg)", ylabel="normalized impulse", title="Constant-impulse continuation")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES / "05_controls_vs_excursion.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(excursion, [row["min_r"] for row in cont], "o-")
    ax.axhline(system.rho1, color="black", ls="--", label="Earth radius")
    ax.set(xlabel="legacy rotating-coordinate normal excursion (deg)", ylabel="minimum primary distance", title="Primary clearance failure along continuation")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES / "06_clearance_vs_excursion.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(excursion, [row["period"] for row in cont], "o-")
    ax.set(xlabel="legacy rotating-coordinate normal excursion (deg)", ylabel="cycle period", title="Cycle period along continuation")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES / "07_period_vs_excursion.png", dpi=180)
    plt.close(fig)

    aero = summary["aerodynamic_interpretation"]
    sigma = np.asarray(aero["sigma"])
    ld = np.asarray(aero["vehicle_ld_required"], dtype=float)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.semilogy(sigma[np.isfinite(ld)], ld[np.isfinite(ld)])
    ax.axvline(system.primary_rotation_ratio, color="red", ls="--", label="Earth")
    if not np.any(np.isfinite(ld)):
        ax.text(.5,.5,'No passive finite-work impulse in this sweep',transform=ax.transAxes,ha='center')
    ax.set(xlabel=r"$\Omega_P/n$", ylabel="midpoint impulse L/D projection", title="Finite-work audit (not a continuous atmospheric flight)")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(FIGURES / "08_ld_vs_rotation.png", dpi=180)
    plt.close(fig)

    comparison = {
        "3/2": {"excursion": 65.56, "min_r": 0.01581849, "physical": False},
        "4/2": {"excursion": 7.1639, "min_r": 0.01659243, "physical": False},
        "5/2": {"excursion": 82.67, "min_r": 0.01573060, "physical": False},
    }
    fig, ax = plt.subplots(figsize=(7, 4))
    labels = list(comparison)
    values = [comparison[key]["excursion"] for key in labels]
    colors = ["tab:green" if comparison[key]["physical"] else "tab:red" for key in labels]
    ax.bar(labels, values, color=colors)
    ax.set(ylabel="legacy rotating-coordinate normal excursion (deg)", title="Original branches: all fail the physical audit")
    fig.tight_layout()
    fig.savefig(FIGURES / "09_branch_comparison.png", dpi=180)
    plt.close(fig)

    print(json.dumps({key: {"position": val["position_closure_norm"], "velocity": val["velocity_closure_norm"]} for key, val in summaries.items()}, indent=2))


if __name__ == "__main__":
    main()
