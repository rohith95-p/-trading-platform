"""
PPO Agent - Proximal Policy Optimization agent implementing DRLAgent interface.

Uses stable-baselines3 when available; falls back to a lightweight mock PPO
so the platform works without the heavy ML dependency.

Implements Requirement 7 (PPO Reinforcement Learning Agent).
"""

import logging
import os
import time
import hashlib
from typing import Any, Dict, Optional

import numpy as np

from src.core.interfaces.drl_agent import DRLAgent
from src.drl.guardrails import ConstitutionalGuardrails
from src.risk.manager import RiskManager

log = logging.getLogger(__name__)

# Try to import stable-baselines3
try:
    from stable_baselines3 import PPO as SB3_PPO
    SB3_AVAILABLE = True
    log.info("stable-baselines3 available – using real PPO")
except ImportError:
    SB3_AVAILABLE = False
    log.warning("stable-baselines3 not available – using mock PPO")

HOLD = 0
BUY = 1
SELL = 2
VALID_ACTIONS = {HOLD, BUY, SELL}
PREDICTION_TIMEOUT_MS = 500


class _MockPPO:
    """Lightweight mock that mimics the stable-baselines3 PPO API."""

    def __init__(self):
        self._weights: Optional[np.ndarray] = None
        self._trained = False

    def learn(self, total_timesteps: int, **kwargs) -> "_MockPPO":
        rng = np.random.default_rng(0)
        self._weights = rng.standard_normal(10)
        self._trained = True
        log.info("MockPPO: simulated training for %d timesteps", total_timesteps)
        return self

    def predict(self, observation: np.ndarray, deterministic: bool = True):
        obs = np.asarray(observation, dtype=np.float32).flatten()
        if self._weights is not None:
            score = float(np.dot(obs, self._weights))
        else:
            score = float(obs[0]) - 1.0

        if score > 0.1:
            action = BUY
        elif score < -0.1:
            action = SELL
        else:
            action = HOLD
        return np.array([action]), None

    def save(self, path: str) -> None:
        import json
        data = {
            "weights": self._weights.tolist() if self._weights is not None else None,
            "trained": self._trained,
        }
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        json_path = path + ".json"
        try:
            with open(json_path, "w") as f:
                json.dump(data, f)
            log.info("MockPPO saved to %s", json_path)
        except PermissionError:
            fallback_path = self._fallback_path(path)
            os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
            with open(fallback_path, "w") as f:
                json.dump(data, f)
            log.info("MockPPO saved to fallback path %s", fallback_path)

    @classmethod
    def load(cls, path: str, env=None) -> "_MockPPO":
        import json
        obj = cls()
        json_path = path + ".json"
        fallback_path = cls._fallback_path(path)
        load_path = json_path if os.path.exists(json_path) else fallback_path

        if os.path.exists(load_path):
            with open(load_path) as f:
                data = json.load(f)
            obj._weights = np.array(data["weights"]) if data["weights"] is not None else None
            obj._trained = data.get("trained", False)
            log.info("MockPPO loaded from %s", load_path)
        else:
            log.warning("MockPPO: no saved model at %s, using untrained weights", path)
        return obj

    @staticmethod
    def _fallback_path(path: str) -> str:
        digest = hashlib.sha256(os.path.abspath(path).encode("utf-8")).hexdigest()
        return os.path.join(os.getcwd(), ".ppo_model_cache", f"{digest}.json")


class PPOAgent(DRLAgent):
    """
    PPO-based trading agent with constitutional guardrails and risk management.

    Prediction contract:
    - Returns 0 (hold), 1 (buy), or 2 (sell)
    - Prediction completes in <500 ms
    - Guardrails may override the raw model output
    """

    def __init__(
        self,
        name: str = "PPOAgent",
        guardrails: Optional[ConstitutionalGuardrails] = None,
        risk_manager: Optional[RiskManager] = None,
        max_leverage: float = 10.0,
    ):
        super().__init__(name=name, algorithm="PPO")
        self.guardrails = guardrails or ConstitutionalGuardrails(max_leverage=max_leverage)
        self.risk_manager = risk_manager or RiskManager()
        self._model: Optional[Any] = None
        self._last_prediction_ms: float = 0.0

    def predict(self, state: np.ndarray) -> int:
        """Predict trading action from market state."""
        return self.predict_with_context(state, context={})

    def predict_with_context(self, state: np.ndarray, context: Dict[str, Any]) -> int:
        """Predict with optional runtime context for guardrail evaluation."""
        t0 = time.monotonic()

        obs = np.asarray(state, dtype=np.float32).flatten()

        if self._model is None:
            raw_action = HOLD
        else:
            action_arr, _ = self._model.predict(obs, deterministic=True)
            action_arr = np.asarray(action_arr).flatten()
            raw_action = int(action_arr[0]) if len(action_arr) > 0 else HOLD

        if raw_action not in VALID_ACTIONS:
            log.warning("Model returned invalid action %d, defaulting to HOLD", raw_action)
            raw_action = HOLD

        final_action = self.guardrails.check(raw_action, obs, context)

        elapsed_ms = (time.monotonic() - t0) * 1000
        self._last_prediction_ms = elapsed_ms
        if elapsed_ms > PREDICTION_TIMEOUT_MS:
            log.warning("Prediction took %.1f ms (limit %d ms)", elapsed_ms, PREDICTION_TIMEOUT_MS)

        return final_action

    def train(self, env: Any, total_timesteps: int = 10_000) -> None:
        """Train the PPO model on the given environment."""
        log.info("Training PPOAgent for %d timesteps (SB3=%s)", total_timesteps, SB3_AVAILABLE)

        if SB3_AVAILABLE:
            self._model = SB3_PPO("MlpPolicy", env, verbose=0)
            self._model.learn(total_timesteps=total_timesteps)
        else:
            self._model = _MockPPO()
            self._model.learn(total_timesteps=total_timesteps)

        log.info("Training complete")

    def save(self, path: str) -> None:
        """Persist model weights to disk."""
        if self._model is None:
            raise RuntimeError("No model to save – train the agent first")
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        self._model.save(path)
        log.info("PPOAgent saved to %s", path)

    def load(self, path: str) -> None:
        """Load model weights from disk."""
        if SB3_AVAILABLE:
            self._model = SB3_PPO.load(path)
        else:
            self._model = _MockPPO.load(path)
        log.info("PPOAgent loaded from %s", path)

    @property
    def last_prediction_ms(self) -> float:
        return self._last_prediction_ms

    def is_trained(self) -> bool:
        return self._model is not None
