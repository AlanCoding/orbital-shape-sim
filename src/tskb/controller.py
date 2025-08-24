"""Controller interfaces and simple implementations."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass

from .env import Environment


class Controller:
    """Abstract controller interface."""

    def action(self, t: float, state: np.ndarray) -> float:
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


class BangBangController(Controller):
    """Adaptive bang-bang controller maximizing tidal power."""

    def __init__(self, cfg: dict) -> None:
        # Acceleration bounds for length control
        self.extend_accel = float(cfg.get("extend_accel", 1.0))
        self.retract_accel = float(cfg.get("retract_accel", 1.0))

        # Power LPF and hysteresis settings
        self.power_tau = float(cfg.get("power_tau_s", 30.0))
        self.power_deadband = float(cfg.get("power_deadband", 1e-10))
        self.min_dwell = float(cfg.get("min_dwell_s", 120.0))

        # Phase adaptation
        self.enable_adapt = bool(cfg.get("adapt_phase", True))
        delta_phase = np.deg2rad(cfg.get("delta_phase_deg", 0.0))
        self.adapt_gain = float(cfg.get("adapt_gain", 1e-5))

        self.state = ControllerState(delta_phase=delta_phase)
        self.env = Environment()

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
        """Return commanded ``q`` sign based on instantaneous tidal power."""
        aQ_biased = self._rotate_in_plane(aQ_unit, rhat, self.state.delta_phase)
        p = float(np.dot(v, aQ_biased))
        if self.state.p_lp == 0.0:
            self.state.p_lp = p
        alpha = np.clip(
            (t > 0)
            * (1.0 - np.exp(-1.0 * min(1.0, (t - self.state.last_switch_t) / max(self.power_tau, 1e-9)))),
            0.0,
            1.0,
        )
        self.state.p_lp = (1.0 - alpha) * self.state.p_lp + alpha * p

        if self.state.p_lp > self.power_deadband:
            q_des = 1.0
        elif self.state.p_lp < -self.power_deadband:
            q_des = -1.0
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

    def action(self, t: float, state: np.ndarray) -> float:
        """Return commanded tether acceleration ``L_ddot``."""
        r = state[0:3]
        v = state[3:6]
        rhat = r / (np.linalg.norm(r) + 1e-15)

        u_rad = rhat
        r1 = r + 0.5 * u_rad
        r2 = r - 0.5 * u_rad
        a1 = self.env.a_earth(r1) + self.env.a_moon_tide(r1, t)
        a2 = self.env.a_earth(r2) + self.env.a_moon_tide(r2, t)
        aQ_unit = a1 - a2

        q_cmd = self.step(t, r, v, aQ_unit, rhat)
        if q_cmd > 0.0:
            return self.extend_accel
        if q_cmd < 0.0:
            return -self.retract_accel
        return 0.0


class PassiveController(Controller):
    """Controller that commands no tether acceleration."""

    def action(self, t: float, state: np.ndarray) -> float:
        return 0.0


def make_controller(cfg: dict) -> Controller:
    """Instantiate a controller from ``cfg``.

    Parameters
    ----------
    cfg : dict
        Controller configuration with a ``type`` key specifying
        ``"bang_bang"`` or ``"passive"``.
    """

    ctrl_type = cfg.get("type", "bang_bang").lower()
    if ctrl_type == "bang_bang":
        return BangBangController(cfg)
    if ctrl_type == "passive":
        return PassiveController()
    raise ValueError(f"unknown controller type: {ctrl_type}")
