"""Controller interfaces and simple implementations."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass

from .env import Environment


class Controller:
    """Abstract controller interface."""

    def action(self, t: float, state: np.ndarray, env: Environment) -> float:
        """Return tether length acceleration ``L_ddot``.

        Subclasses should override this method.  The returned value
        represents the commanded second derivative of the barbell length.
        """

        raise NotImplementedError


@dataclass
class ControllerState:
    p_lp: float = 0.0
    last_switch_t: float = -np.inf
    q_cmd: float = 0.0
    delta_phase: float = 0.0
    last_p_t: float = 0.0


class BangBangController(Controller):
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
    """Controller that commands no tether acceleration."""

    def action(self, t: float, state: np.ndarray, env: Environment) -> float:
        return 0.0


class LandisController(Controller):
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


class MoonAngleController(Controller):
    """Controller scheduling acceleration by Moon-relative angle."""

    def __init__(self, cfg: dict) -> None:
        self.max_accel = float(cfg.get("max_accel", 0.01))
        self.offset_rad = float(cfg.get("offset_rad", 0.0))
        self.extend_limit = float(cfg.get("extend_limit_m", 110_000.0))
        self.retract_limit = float(cfg.get("retract_limit_m", 80_000.0))

    def action(self, t: float, state: np.ndarray, env: Environment) -> float:  # noqa: D401
        """Return commanded tether acceleration ``L_ddot``."""
        r = state[0:3]
        L = state[8]
        moon_r = env.moon_position(t)
        theta_r = np.arctan2(r[1], r[0])
        theta_m = np.arctan2(moon_r[1], moon_r[0])
        theta = theta_r - theta_m
        accel = self.max_accel * np.cos(2.0 * (theta - self.offset_rad))
        if accel > 0.0 and L >= self.extend_limit:
            return 0.0
        if accel < 0.0 and L <= self.retract_limit:
            return 0.0
        return accel


class NeuralNetController(Controller):
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
    raise ValueError(f"unknown controller type: {ctrl_type}")
