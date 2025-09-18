"""Controller interfaces and simple implementations."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass

from .env import Environment
from .barbell import DualBarbell
from .diamond import Diamond, DiamondControlCommand
from .cr3bp import l1_unstable_mode


class Controller:
    """Abstract controller interface."""

    def action(self, t: float, state: np.ndarray, env: Environment) -> float:
        """Return control acceleration for the current state."""

        raise NotImplementedError

    def initial_state(self, env: Environment, craft, cfg: dict) -> np.ndarray:
        """Return initial state vector for ``craft``.

        Controllers own the initial conditions; the configuration ``cfg`` may
        supply helper fields such as ``altitude_m`` or spin modes.  Subclasses
        must implement this method.
        """

        raise NotImplementedError


@dataclass
class ControllerState:
    p_lp: float = 0.0
    last_switch_t: float = -np.inf
    q_cmd: float = 0.0
    delta_phase: float = 0.0
    last_p_t: float = 0.0


class BarbellControllerBase(Controller):
    """Base class for controllers operating on ``DualBarbell`` craft."""

    def initial_state(self, env: Environment, craft, cfg: dict) -> np.ndarray:  # noqa: D401
        ctrl_cfg = cfg.get("controller", {})
        init_cfg = ctrl_cfg.get("initial", {})
        alt = init_cfg.get("altitude_m", 0.0)
        r0_mag = env.r_earth + alt
        v0_mag = np.sqrt(env.mu_earth / r0_mag)
        n0 = np.sqrt(env.mu_earth / r0_mag**3)
        n_syn = n0 - env.n_moon
        theta0 = init_cfg.get("theta0", 0.0)
        omega_cfg = init_cfg.get("omega0", "tidally_locked")
        if isinstance(omega_cfg, str):
            modes = {
                "tidally_locked": n0,
                "no_rotation": 0.0,
                "prograde": n0 + n_syn,
                "retrograde": n0 - n_syn,
                "fast_prograde": 5.0 * (n0 + n_syn),
            }
            if omega_cfg not in modes:
                raise ValueError(f"unknown omega0 mode: {omega_cfg}")
            omega0 = modes[omega_cfg]
        else:
            omega0 = float(omega_cfg)
        L0 = init_cfg.get("length0", 1000.0)
        Ldot0 = init_cfg.get("length_rate0", 0.0)
        return np.hstack(
            [
                np.array([r0_mag, 0.0, 0.0]),
                np.array([0.0, v0_mag, 0.0]),
                np.array([theta0, omega0, L0, Ldot0]),
            ]
        )


class BangBangController(BarbellControllerBase):
    """Adaptive bang-bang controller maximizing tidal power."""

    def __init__(self, cfg: dict) -> None:
        # Acceleration bounds for length control
        self.extend_accel = float(cfg.get("extend_accel", 1.0))
        self.retract_accel = float(cfg.get("retract_accel", 1.0))

        # q scaling (defaults ±1)
        self.q_plus_scale = float(cfg.get("q_plus_scale", 1.0))
        self.q_minus_scale = float(cfg.get("q_minus_scale", -1.0))

        # Power LPF and hysteresis settings
        self.power_tau = float(cfg.get("power_tau_s", 30.0))
        self.power_deadband = float(cfg.get("power_deadband", 1e-10))
        self.min_dwell = float(cfg.get("min_dwell_s", 120.0))

        # Phase adaptation
        self.enable_adapt = bool(cfg.get("adapt_phase", True))
        delta_phase = np.deg2rad(cfg.get("delta_phase_deg", 0.0))
        self.adapt_gain = float(cfg.get("adapt_gain", 1e-5))

        self.state = ControllerState(delta_phase=delta_phase)

    @staticmethod
    def _rotate_in_plane(vec: np.ndarray, axis_rhat: np.ndarray, delta: float) -> np.ndarray:
        """Rotate ``vec`` within the plane orthogonal to ``axis_rhat``."""
        rhat = axis_rhat / (np.linalg.norm(axis_rhat) + 1e-15)
        v_rad = np.dot(vec, rhat) * rhat
        v_tan = vec - v_rad
        tmp = np.array([1.0, 0.0, 0.0]) if abs(rhat[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        t1 = np.cross(rhat, tmp)
        t1 /= (np.linalg.norm(t1) + 1e-15)
        t2 = np.cross(rhat, t1)
        c1 = np.dot(v_tan, t1)
        c2 = np.dot(v_tan, t2)
        cd1 = np.cos(delta) * c1 - np.sin(delta) * c2
        cd2 = np.sin(delta) * c1 + np.cos(delta) * c2
        return v_rad + cd1 * t1 + cd2 * t2

    def step(self, t: float, r: np.ndarray, v: np.ndarray, aQ_unit: np.ndarray, rhat: np.ndarray) -> float:
        """Return commanded ``q`` scale based on instantaneous tidal power."""
        aQ_biased = self._rotate_in_plane(aQ_unit, rhat, self.state.delta_phase)
        p = float(np.dot(v, aQ_biased))

        # initialize low-pass filter on first call
        if self.state.last_p_t == 0.0 and self.state.p_lp == 0.0:
            self.state.p_lp = p
            self.state.last_p_t = t

        dt = t - self.state.last_p_t
        if not np.isfinite(dt) or dt <= 0.0:
            alpha = 0.0
        else:
            alpha = -np.expm1(-dt / max(self.power_tau, 1e-9))
        self.state.p_lp = (1.0 - alpha) * self.state.p_lp + alpha * p
        self.state.last_p_t = t

        if self.state.p_lp > self.power_deadband:
            q_des = self.q_plus_scale
        elif self.state.p_lp < -self.power_deadband:
            q_des = self.q_minus_scale
        else:
            q_des = self.state.q_cmd

        if (t - self.state.last_switch_t) < self.min_dwell:
            q_cmd = self.state.q_cmd
        else:
            if q_des != self.state.q_cmd:
                self.state.q_cmd = q_des
                self.state.last_switch_t = t
            q_cmd = self.state.q_cmd

        if self.enable_adapt and (t - self.state.last_switch_t) > self.min_dwell:
            eps = 1e-3
            aQ_eps = self._rotate_in_plane(aQ_unit, rhat, self.state.delta_phase + eps)
            p_eps = float(np.dot(v, aQ_eps))
            grad = (p_eps - p) / eps
            self.state.delta_phase += self.adapt_gain * grad
            self.state.delta_phase = np.clip(self.state.delta_phase, -0.35, 0.35)

        return q_cmd

    def action(self, t: float, state: np.ndarray, env: Environment) -> float:
        """Return commanded tether acceleration ``L_ddot``."""
        r = state[0:3]
        v = state[3:6]
        rhat = r / (np.linalg.norm(r) + 1e-15)

        u_rad = rhat
        r1 = r + 0.5 * u_rad
        r2 = r - 0.5 * u_rad
        a1 = env.a_earth(r1) + env.a_moon_tide(r1, t)
        a2 = env.a_earth(r2) + env.a_moon_tide(r2, t)
        aQ_unit = a1 - a2

        q_cmd = self.step(t, r, v, aQ_unit, rhat)
        if q_cmd > 0.0:
            return self.extend_accel
        if q_cmd < 0.0:
            return -self.retract_accel
        return 0.0


class PassiveController(Controller):
    """Controller that commands no acceleration and provides initial state."""

    def action(self, t: float, state: np.ndarray, env: Environment) -> float:
        return 0.0

    def initial_state(self, env: Environment, craft, cfg: dict) -> np.ndarray:  # noqa: D401
        ctrl_cfg = cfg.get("controller", {})
        init_cfg = ctrl_cfg.get("initial", {})
        alt = init_cfg.get("altitude_m", 0.0)
        r0_mag = env.r_earth + alt
        v0_mag = np.sqrt(env.mu_earth / r0_mag)
        r = np.array([r0_mag, 0.0, 0.0])
        v = np.array([0.0, v0_mag, 0.0])
        if isinstance(craft, Diamond):
            r = env.l1_position(0.0)
            v = np.cross(np.array([0.0, 0.0, env.n_moon]), r)
            vx0 = float(init_cfg.get("vx0", 0.0))
            vy0 = float(init_cfg.get("vy0", 0.0))
            vz0 = float(init_cfg.get("vz0", 0.0))
            v = v + np.array([vx0, vy0, vz0])
        if isinstance(craft, DualBarbell):
            n0 = np.sqrt(env.mu_earth / r0_mag**3)
            n_syn = n0 - env.n_moon
            theta0 = init_cfg.get("theta0", 0.0)
            omega_cfg = init_cfg.get("omega0", "tidally_locked")
            if isinstance(omega_cfg, str):
                modes = {
                    "tidally_locked": n0,
                    "no_rotation": 0.0,
                    "prograde": n0 + n_syn,
                    "retrograde": n0 - n_syn,
                    "fast_prograde": 5.0 * (n0 + n_syn),
                }
                if omega_cfg not in modes:
                    raise ValueError(f"unknown omega0 mode: {omega_cfg}")
                omega0 = modes[omega_cfg]
            else:
                omega0 = float(omega_cfg)
            L0 = init_cfg.get("length0", 1000.0)
            Ldot0 = init_cfg.get("length_rate0", 0.0)
            return np.hstack([r, v, theta0, omega0, L0, Ldot0])
        return np.hstack([r, v])


class DiamondL1Stabilizer(Controller):
    """PD stabilizer for the diamond craft about the Earth–Moon L1 point."""

    def __init__(self, cfg: dict) -> None:
        self.kp = float(cfg.get("kp", 5.0e-2))
        self.kd = float(cfg.get("kd", 5.0e-1))
        self.ku = max(float(cfg.get("ku", 2.0e-3)), 1e-6)
        self.delta_limit = float(cfg.get("delta_limit_m", 150_000.0))
        self.delta_rate = float(cfg.get("delta_rate_limit_mps", 80.0))

        self._mode = None
        self._x_l1 = None
        self._delta = 0.0
        self._last_t: float | None = None

    @staticmethod
    def _rotation(theta: float) -> np.ndarray:
        c = float(np.cos(theta))
        s = float(np.sin(theta))
        return np.array(
            [
                [c, s, 0.0],
                [-s, c, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )

    def _ensure_mode(self, env: Environment) -> None:
        if self._mode is not None:
            return
        mu = env.mu_moon / (env.mu_earth + env.mu_moon)
        self._mode = l1_unstable_mode(mu, env.r_moon, env.n_moon)
        self._x_l1 = (self._mode.x_l1_bary + mu) * env.r_moon

    def _l1_position(self, theta: float) -> np.ndarray:
        assert self._x_l1 is not None
        x = float(self._x_l1)
        c = float(np.cos(theta))
        s = float(np.sin(theta))
        return np.array([x * c, x * s, 0.0])

    def initial_state(self, env: Environment, craft, cfg: dict) -> np.ndarray:  # noqa: D401
        self._ensure_mode(env)
        ctrl_cfg = cfg.get("controller", {})
        init_cfg = ctrl_cfg.get("initial", {})
        theta0 = float(init_cfg.get("theta0", 0.0))
        r = self._l1_position(theta0)
        omega_vec = np.array([0.0, 0.0, env.n_moon])
        v = np.cross(omega_vec, r)
        vx0 = float(init_cfg.get("vx0", 0.0))
        vy0 = float(init_cfg.get("vy0", 0.0))
        vz0 = float(init_cfg.get("vz0", 0.0))
        v = v + np.array([vx0, vy0, vz0])
        return np.hstack([r, v])

    def action(self, t: float, state: np.ndarray, env: Environment) -> DiamondControlCommand:
        self._ensure_mode(env)
        assert self._mode is not None
        assert self._x_l1 is not None

        r = state[0:3]
        v = state[3:6]

        theta = env.n_moon * t
        rot = self._rotation(theta)
        r_l1 = self._l1_position(theta)
        delta_r = rot @ (r - r_l1)

        omega_vec = np.array([0.0, 0.0, env.n_moon])
        v_rel = v - np.cross(omega_vec, r)
        delta_v = rot @ v_rel

        q = float(self._mode.pos_dir @ delta_r[0:2])
        qdot = float(self._mode.vel_dir @ delta_v[0:2])

        u = -self.kp * q - self.kd * qdot
        delta_des = np.clip(u / self.ku, -self.delta_limit, self.delta_limit)

        if self._last_t is None:
            delta = delta_des
        else:
            dt = t - self._last_t
            if dt <= 0.0:
                delta = self._delta
            else:
                max_change = self.delta_rate * dt
                delta = np.clip(delta_des, self._delta - max_change, self._delta + max_change)
        self._delta = float(np.clip(delta, -self.delta_limit, self.delta_limit))
        self._last_t = float(t)
        return DiamondControlCommand(stretch=self._delta)


class LandisController(BarbellControllerBase):
    """Perigee-retract / apogee-extend controller from Landis.

    This scheme reels the tether out while the spacecraft moves away from the
    Earth and reels it in while it falls back, converting barbell angular
    momentum into orbital energy.
    """

    def __init__(self, cfg: dict) -> None:
        self.extend_accel = float(cfg.get("extend_accel", 1.0))
        self.retract_accel = float(cfg.get("retract_accel", 1.0))
        self.deadband = float(cfg.get("deadband", 1e-9))

    def action(self, t: float, state: np.ndarray, env: Environment) -> float:  # noqa: D401
        """Return commanded tether acceleration ``L_ddot``."""
        r = state[0:3]
        v = state[3:6]
        rhat = r / (np.linalg.norm(r) + 1e-15)
        v_rad = float(np.dot(v, rhat))
        if v_rad > self.deadband:
            return self.extend_accel
        if v_rad < -self.deadband:
            return -self.retract_accel
        return 0.0


class MoonAngleController(BarbellControllerBase):
    """PID controller tracking a Moon-relative length schedule.

    This strategy was explored briefly but found to have negligible impact; it
    is retained only for reference and is no longer recommended for use.
    """

    def __init__(self, cfg: dict) -> None:
        self.max_accel = float(cfg.get("max_accel", 0.01))
        self.offset_rad = float(cfg.get("offset_rad", 0.0))
        self.extend_limit = float(cfg.get("extend_limit_m", 110_000.0))
        self.retract_limit = float(cfg.get("retract_limit_m", 80_000.0))
        self.kp = float(cfg.get("kp", 5e-5))
        self.ki = float(cfg.get("ki", 1e-8))
        self.kd = float(cfg.get("kd", 1e-1))
        self._int_err = 0.0
        self._last_t: float | None = None

    def action(self, t: float, state: np.ndarray, env: Environment) -> float:  # noqa: D401
        """Return commanded tether acceleration ``L_ddot``."""
        r = state[0:3]
        L = state[8]
        moon_r = env.moon_position(t)
        theta_r = np.arctan2(r[1], r[0])
        theta_m = np.arctan2(moon_r[1], moon_r[0])
        theta = theta_r - theta_m

        L_mid = 0.5 * (self.extend_limit + self.retract_limit)
        L_amp = 0.5 * (self.extend_limit - self.retract_limit)
        L_des = L_mid + L_amp * np.cos(2.0 * (theta - self.offset_rad))

        err = L_des - L
        if self._last_t is None:
            dt = 0.0
        else:
            dt = t - self._last_t
        self._last_t = t
        self._int_err += err * dt
        Ldot = state[9]
        accel = self.kp * err + self.ki * self._int_err - self.kd * Ldot
        accel = np.clip(accel, -self.max_accel, self.max_accel)
        if accel > 0.0 and L >= self.extend_limit:
            return 0.0
        if accel < 0.0 and L <= self.retract_limit:
            return 0.0
        return accel


class NeuralNetController(BarbellControllerBase):
    """Feedforward neural-network controller.

    The network maps the full 10-element state vector to a commanded
    tether acceleration.  Hidden layers use ``tanh`` activations and the
    final output is clipped to ``±max_accel``.  Parameters are stored as a
    flat vector to enable simple optimization strategies.
    """

    def __init__(self, cfg: dict | None = None) -> None:
        cfg = cfg or {}
        self.max_accel = float(cfg.get("max_accel", 0.01))
        self.hidden_sizes = [int(h) for h in cfg.get("hidden_sizes", [16, 16])]
        self.rng = np.random.default_rng(cfg.get("seed"))
        layer_sizes = [10] + self.hidden_sizes + [1]

        self.layers: list[tuple[np.ndarray, np.ndarray]] = []
        scale = float(cfg.get("weight_scale", 0.1))
        for in_size, out_size in zip(layer_sizes[:-1], layer_sizes[1:]):
            w = self.rng.normal(0.0, scale, size=(out_size, in_size))
            b = np.zeros(out_size)
            self.layers.append((w, b))

        if "weights" in cfg:
            weights = np.load(cfg["weights"])
            self.set_parameters(weights)

    # ------------------------------------------------------------------
    # Parameter helpers
    def get_parameters(self) -> np.ndarray:
        """Return flattened parameter vector."""

        parts = []
        for w, b in self.layers:
            parts.append(w.ravel())
            parts.append(b.ravel())
        return np.concatenate(parts)

    def set_parameters(self, flat: np.ndarray) -> None:
        """Set network parameters from a flat array."""

        idx = 0
        new_layers = []
        for w, b in self.layers:
            w_size = w.size
            b_size = b.size
            w_shape = w.shape
            b_shape = b.shape
            w = flat[idx : idx + w_size].reshape(w_shape)
            idx += w_size
            b = flat[idx : idx + b_size].reshape(b_shape)
            idx += b_size
            new_layers.append((w, b))
        self.layers = new_layers

    # ------------------------------------------------------------------
    def action(self, t: float, state: np.ndarray, env: Environment) -> float:
        x = np.asarray(state, dtype=float)
        for i, (w, b) in enumerate(self.layers):
            x = w @ x + b
            if i < len(self.layers) - 1:
                x = np.tanh(x)
        out = float(x.squeeze())
        return float(np.clip(out, -self.max_accel, self.max_accel))


def make_controller(cfg: dict) -> Controller:
    """Instantiate a controller from ``cfg``.

    Parameters
    ----------
    cfg : dict
        Controller configuration with a ``type`` key specifying
        ``"bang_bang"``, ``"passive"``, ``"landis"``, ``"neural_net"`` or ``"moon_angle"``.
    """

    ctrl_type = cfg.get("type", "bang_bang").lower()
    if ctrl_type == "bang_bang":
        return BangBangController(cfg)
    if ctrl_type == "passive":
        return PassiveController()
    if ctrl_type == "landis":
        return LandisController(cfg)
    if ctrl_type == "moon_angle":
        return MoonAngleController(cfg)
    if ctrl_type == "neural_net":
        return NeuralNetController(cfg)
    if ctrl_type == "diamond_l1_stabilizer":
        return DiamondL1Stabilizer(cfg)
    raise ValueError(f"unknown controller type: {ctrl_type}")
