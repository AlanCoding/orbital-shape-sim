from __future__ import annotations

import os
import time

from .analysis import (
    backpropagate_payload_to_surface,
    find_angle_crossings,
    integrate_orbit,
    select_moon_side_crossing,
    select_catch_schedule,
    simulate_catch_chain,
)
from .render import render_catch_chain, render_final_orbit, render_payload_example, render_reference_orbit, render_tadpole_orbit
from .scenario import get_scenario


def main():
    scenario = get_scenario()
    output_dir = os.path.join("docs", "assets", "l4_receipt")
    os.makedirs(output_dir, exist_ok=True)

    print("Running L4 tadpole orbit...", flush=True)
    start = time.time()
    t_eval, states = integrate_orbit(scenario)
    crossings = find_angle_crossings(t_eval, states, scenario.launch_angles_rad)
    pickup_crossing = select_moon_side_crossing(crossings, scenario)
    print(f"  Integration finished in {time.time() - start:.2f} s", flush=True)

    reference_path = os.path.join(output_dir, "01_l4_tadpole_orbit.png")
    start = time.time()
    render_tadpole_orbit(scenario, t_eval, states, reference_path)
    print(f"  Wrote {reference_path} in {time.time() - start:.2f} s", flush=True)

    print("Running example payload catch...", flush=True)
    start = time.time()
    payload = backpropagate_payload_to_surface(pickup_crossing.state, scenario, scenario.payload_speed_mps)
    if payload is None:
        raise RuntimeError("failed to back-propagate payload to the lunar surface")
    print(f"  Back-propagation finished in {time.time() - start:.2f} s", flush=True)

    payload_path = os.path.join(output_dir, "02_l4_payload_path.png")
    start = time.time()
    render_payload_example(scenario, t_eval, states, pickup_crossing, payload, payload_path)
    print(f"  Wrote {payload_path} in {time.time() - start:.2f} s", flush=True)

    print("Running repeated-catch mass receipt chain...", flush=True)
    start = time.time()
    catch_schedule = select_catch_schedule(crossings, 0.0)
    chain = simulate_catch_chain(scenario, catch_schedule)
    print(f"  Mass receipt finished in {time.time() - start:.2f} s", flush=True)

    chain_path = os.path.join(output_dir, "03_l4_catch_chain.png")
    start = time.time()
    render_catch_chain(scenario, chain, chain_path)
    print(f"  Wrote {chain_path} in {time.time() - start:.2f} s", flush=True)

    if chain.records:
        final_state = chain.records[-1].state_post
    elif chain.segments_states:
        final_state = chain.segments_states[-1][-1]
    else:
        final_state = scenario.orbit_state0

    print("Running one-month post-catch orbit...", flush=True)
    orbit_path = os.path.join(output_dir, "04_l4_final_orbit.png")
    start = time.time()
    render_final_orbit(scenario, final_state, 30.0, orbit_path)
    print(f"  Wrote {orbit_path} in {time.time() - start:.2f} s", flush=True)


if __name__ == "__main__":
    main()
