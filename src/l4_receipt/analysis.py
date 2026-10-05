from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d
from scipy.optimize import brentq

from .physics import derivatives


DAY_SECONDS = 86400.0


@dataclass(frozen=True)
class OrbitCrossing:
    target_angle_rad: float
    time_s: float
    state: np.ndarray

    @property
    def target_angle_deg(self) -> float:
        return float(np.degrees(self.target_angle_rad) % 360.0)


@dataclass(frozen=True)
class PayloadTrajectory:
    catch_state: np.ndarray
    catch_velocity: np.ndarray
    trajectory_t: np.ndarray
    trajectory_states: np.ndarray
    surface_state: np.ndarray
    launch_speed_mps: float
    longitude_deg: float
    flight_time_s: float
    tangent_sign: float


@dataclass(frozen=True)
class CatchRecord:
    index: int
    time_s: float
    state_pre: np.ndarray
    state_post: np.ndarray
    station_mass_before: float
    station_mass_after: float
    payload_mass: float
    payload_velocity: np.ndarray
    surface_state: np.ndarray
    longitude_deg: float
    flight_time_s: float


@dataclass(frozen=True)
class CatchChain:
    segments_t: list[np.ndarray]
    segments_states: list[np.ndarray]
    records: list[CatchRecord]
    target_angle_rad: float
    final_station_mass: float
    total_delivered_mass: float


def integrate_orbit(scenario, state0: np.ndarray | None = None, days: float | None = None, samples_per_day: int | None = None):
    if state0 is None:
        state0 = scenario.orbit_state0
    if days is None:
        days = scenario.orbit_days
    if samples_per_day is None:
        samples_per_day = scenario.samples_per_day
    t_max = float(days) * DAY_SECONDS
    t_eval = np.linspace(0.0, t_max, int(days * samples_per_day) + 1)
    sol = solve_ivp(
        fun=lambda t, y: derivatives(t, y, scenario),
        t_span=(0.0, t_max),
        y0=np.asarray(state0, dtype=float),
        t_eval=t_eval,
        method="DOP853",
        rtol=1e-10,
        atol=1e-12,
    )
    return sol.t, sol.y.T


def velocity_angle_series(states: np.ndarray) -> np.ndarray:
    return np.unwrap(np.arctan2(states[:, 3], states[:, 2]))


def oriented_velocity_angle_series(states: np.ndarray) -> tuple[np.ndarray, float]:
    angle_series = velocity_angle_series(states)
    direction = 1.0 if float(angle_series[-1] - angle_series[0]) >= 0.0 else -1.0
    return direction * (angle_series - angle_series[0]), direction


def find_angle_crossings(t_eval: np.ndarray, states: np.ndarray, target_angles_rad: np.ndarray) -> list[OrbitCrossing]:
    angle_rel, _ = oriented_velocity_angle_series(states)
    angle_interp = interp1d(t_eval, angle_rel, kind="linear", fill_value="extrapolate")
    state_interp = interp1d(t_eval, states, axis=0, kind="linear", fill_value="extrapolate")

    crossings: list[OrbitCrossing] = []
    for target in target_angles_rad:
        target = float(target)
        values = angle_rel - target
        sign_changes = np.where(values[:-1] * values[1:] <= 0.0)[0]
        if len(sign_changes) == 0:
            continue
        idx = int(sign_changes[0])
        left_t = float(t_eval[idx])
        right_t = float(t_eval[idx + 1])
        left_v = float(values[idx])
        right_v = float(values[idx + 1])
        if left_v == 0.0:
            root_t = left_t
        elif left_v * right_v < 0.0:
            root_t = float(brentq(lambda t: float(angle_interp(t) - target), left_t, right_t, maxiter=100))
        else:
            continue
        crossings.append(OrbitCrossing(target_angle_rad=target, time_s=root_t, state=np.array(state_interp(root_t), dtype=float)))
    return crossings


def select_moon_side_crossing(crossings: list[OrbitCrossing], scenario) -> OrbitCrossing:
    successful: list[tuple[float, OrbitCrossing]] = []
    for crossing in crossings:
        payload = backpropagate_payload_to_surface(crossing.state, scenario, scenario.payload_speed_mps)
        if payload is not None:
            successful.append((float(crossing.state[0] - scenario.moon_pos[0]), crossing))
    if successful:
        return max(successful, key=lambda item: item[0])[1]
    return max(crossings, key=lambda item: float(item.state[0] - scenario.moon_pos[0]))


def select_catch_schedule(crossings: list[OrbitCrossing], dead_time_s: float) -> list[OrbitCrossing]:
    if dead_time_s <= 0.0:
        return list(crossings)
    schedule: list[OrbitCrossing] = []
    last_time = -1e99
    for crossing in crossings:
        if crossing.time_s < dead_time_s:
            continue
        if crossing.time_s - last_time >= dead_time_s:
            schedule.append(crossing)
            last_time = crossing.time_s
    return schedule


def backpropagate_payload_to_surface(
    catch_state: np.ndarray,
    scenario,
    payload_speed_mps: float,
    max_days: float = 20.0,
) -> PayloadTrajectory | None:
    catch_pos = np.asarray(catch_state[:2], dtype=float)
    rel = catch_pos - np.asarray(scenario.moon_pos, dtype=float)
    rel_norm = float(np.linalg.norm(rel))
    if rel_norm == 0.0:
        return None

    radial_hat = rel / rel_norm
    tangent_hats = [
        np.array([-radial_hat[1], radial_hat[0]], dtype=float),
        np.array([radial_hat[1], -radial_hat[0]], dtype=float),
    ]

    t_span = (0.0, -max_days * DAY_SECONDS)
    for sign_idx, tangent_hat in enumerate(tangent_hats):
        payload_velocity = float(payload_speed_mps) * tangent_hat
        y0 = np.array([catch_pos[0], catch_pos[1], payload_velocity[0], payload_velocity[1]], dtype=float)

        def surface_event(t, y):
            pos = np.array(y[:2], dtype=float)
            return float(np.linalg.norm(pos - scenario.moon_pos) - scenario.moon_radius_m)

        surface_event.terminal = True
        surface_event.direction = 0.0
        sol = solve_ivp(
            fun=lambda t, y: derivatives(t, y, scenario),
            t_span=t_span,
            y0=y0,
            events=surface_event,
            dense_output=True,
            max_step=DAY_SECONDS / 4.0,
            method="DOP853",
            rtol=1e-10,
            atol=1e-12,
        )
        if len(sol.t_events[0]) == 0:
            continue

        t_hit = float(sol.t_events[0][0])
        sample_t = np.linspace(t_hit, 0.0, 300)
        sample_states = sol.sol(sample_t).T
        surface_state = np.array(sample_states[0], dtype=float)
        surface_rel = surface_state[:2] - np.asarray(scenario.moon_pos, dtype=float)
        longitude_deg = float(np.degrees(np.arctan2(surface_rel[1], surface_rel[0])))
        return PayloadTrajectory(
            catch_state=np.asarray(catch_state, dtype=float),
            catch_velocity=payload_velocity,
            trajectory_t=sample_t,
            trajectory_states=sample_states,
            surface_state=surface_state,
            launch_speed_mps=float(np.linalg.norm(surface_state[2:4])),
            longitude_deg=longitude_deg,
            flight_time_s=float(abs(t_hit)),
            tangent_sign=float(1.0 if sign_idx == 0 else -1.0),
        )

    return None


def _find_next_crossing_after(
    t_eval: np.ndarray,
    states: np.ndarray,
    target_angle_rad: float,
    t_min_s: float,
) -> tuple[float, np.ndarray] | None:
    angle_rel, _ = oriented_velocity_angle_series(states)
    mask = t_eval >= t_min_s
    if not np.any(mask):
        return None
    t_local = np.asarray(t_eval[mask], dtype=float)
    angle_local = np.asarray(angle_rel[mask], dtype=float)
    state_local = np.asarray(states[mask], dtype=float)
    if len(t_local) < 2:
        return None

    base_target = float(target_angle_rad)
    span_min = float(np.min(angle_local))
    span_max = float(np.max(angle_local))
    k_min = int(np.floor((span_min - base_target) / (2.0 * np.pi))) - 1
    k_max = int(np.ceil((span_max - base_target) / (2.0 * np.pi))) + 1

    angle_interp = interp1d(t_local, angle_local, kind="linear", fill_value="extrapolate")
    state_interp = interp1d(t_local, state_local, axis=0, kind="linear", fill_value="extrapolate")

    best: tuple[float, np.ndarray] | None = None
    for k in range(k_min, k_max + 1):
        target = base_target + 2.0 * np.pi * k
        values = angle_local - target
        sign_changes = np.where(values[:-1] * values[1:] <= 0.0)[0]
        for idx in sign_changes:
            left_t = float(t_local[idx])
            right_t = float(t_local[idx + 1])
            left_v = float(values[idx])
            right_v = float(values[idx + 1])
            if left_v == 0.0:
                root_t = left_t
            elif left_v * right_v < 0.0:
                root_t = float(brentq(lambda t: float(angle_interp(t) - target), left_t, right_t, maxiter=100))
            else:
                continue
            if root_t >= t_min_s:
                state = np.array(state_interp(root_t), dtype=float)
                if best is None or root_t < best[0]:
                    best = (root_t, state)
                break
    return best


def simulate_catch_chain(
    scenario,
    scheduled_crossings: list[OrbitCrossing],
    max_catches: int = 24,
) -> CatchChain:
    t_current = 0.0
    state_current = np.asarray(scenario.orbit_state0, dtype=float).copy()
    station_mass = float(scenario.station_mass0)
    payload_mass = float(scenario.payload_mass0)
    total_delivered = 0.0
    segments_t: list[np.ndarray] = []
    segments_states: list[np.ndarray] = []
    records: list[CatchRecord] = []
    for catch_index, crossing in enumerate(scheduled_crossings[:max_catches]):
        if crossing.time_s <= t_current:
            continue
        segment_duration = float(crossing.time_s - t_current)
        t_eval = np.linspace(t_current, crossing.time_s, max(3, int(segment_duration / DAY_SECONDS * scenario.samples_per_day) + 1))
        sol = solve_ivp(
            fun=lambda t, y: derivatives(t, y, scenario),
            t_span=(t_current, crossing.time_s),
            y0=state_current,
            t_eval=t_eval,
            method="DOP853",
            rtol=1e-10,
            atol=1e-12,
        )
        t_seg = np.asarray(sol.t, dtype=float)
        states_seg = np.asarray(sol.y.T, dtype=float)
        catch_state = np.asarray(states_seg[-1], dtype=float)
        t_catch = float(t_seg[-1])
        segments_t.append(t_seg)
        segments_states.append(states_seg)

        payload = backpropagate_payload_to_surface(catch_state, scenario, scenario.payload_speed_mps)
        if payload is None:
            moon_rel = catch_state[:2] - np.asarray(scenario.moon_pos, dtype=float)
            moon_rel_norm = float(np.linalg.norm(moon_rel))
            radial_hat = moon_rel / moon_rel_norm
            tangent_hat = np.array([-radial_hat[1], radial_hat[0]], dtype=float)
            payload_velocity = float(scenario.payload_speed_mps) * tangent_hat
            payload = PayloadTrajectory(
                catch_state=np.asarray(catch_state, dtype=float),
                catch_velocity=payload_velocity,
                trajectory_t=np.array([0.0], dtype=float),
                trajectory_states=np.array([catch_state], dtype=float),
                surface_state=np.asarray(catch_state, dtype=float),
                launch_speed_mps=float(np.linalg.norm(payload_velocity)),
                longitude_deg=float(np.degrees(np.arctan2(moon_rel[1], moon_rel[0]))),
                flight_time_s=0.0,
                tangent_sign=1.0,
            )

        catch_state_post = catch_state.copy()
        payload_mass = min(payload_mass, scenario.payload_mass_cap - total_delivered)
        if payload_mass <= 0.0:
            break

        catch_velocity = np.asarray(payload.catch_velocity, dtype=float)
        station_velocity = np.asarray(catch_state[2:4], dtype=float)
        new_velocity = (station_mass * station_velocity + payload_mass * catch_velocity) / (station_mass + payload_mass)
        catch_state_post[2:4] = new_velocity

        records.append(
            CatchRecord(
                index=catch_index,
                time_s=t_catch,
                state_pre=np.asarray(catch_state, dtype=float),
                state_post=catch_state_post,
                station_mass_before=station_mass,
                station_mass_after=station_mass + payload_mass,
                payload_mass=payload_mass,
                payload_velocity=catch_velocity,
                surface_state=payload.surface_state,
                longitude_deg=payload.longitude_deg,
                flight_time_s=payload.flight_time_s,
            )
        )

        total_delivered += payload_mass
        station_mass += payload_mass
        state_current = catch_state_post
        t_current = t_catch
        payload_mass *= scenario.payload_growth
        if total_delivered >= scenario.payload_mass_cap:
            break

    return CatchChain(
        segments_t=segments_t,
        segments_states=segments_states,
        records=records,
        target_angle_rad=float(scheduled_crossings[0].target_angle_rad if scheduled_crossings else 0.0),
        final_station_mass=station_mass,
        total_delivered_mass=total_delivered,
    )
