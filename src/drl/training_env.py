"""
Trading Environment - gym-compatible environment for DRL training.

Implements Requirement 7 (PPO Reinforcement Learning Agent) - training environment.
"""

import numpy as np
from typing import Tuple, Dict, Any, Optional

# Try gymnasium first (preferred by stable-baselines3 >= 2.0), then legacy gym
try:
    import gymnasium as gym
    from gymnasium import spaces
    GYM_AVAILABLE = True
    GYM_MODULE = "gymnasium"
except ImportError:
    try:
        import gym
        from gym import spaces
        GYM_AVAILABLE = True
        GYM_MODULE = "gym"
    except ImportError:
        GYM_AVAILABLE = False
        GYM_MODULE = None

# Number of features in the observation vector:
# [price, volume, ema_fast, ema_slow, rsi, macd, signal, atr, bb_upper, bb_lower]
N_FEATURES = 10
N_ACTIONS = 3  # 0=hold, 1=buy, 2=sell

TRANSACTION_COST = 0.001  # 0.1% per trade


def _make_env_base():
    """Return the correct base class depending on what is installed."""
    if GYM_AVAILABLE:
        return gym.Env
    return object


class TradingEnvironment(_make_env_base()):
    """
    Gym/Gymnasium-compatible trading environment for PPO training.

    Observation space: Box(10,) - price, volume, and 8 technical indicators.
    Action space: Discrete(3) - 0=hold, 1=buy, 2=sell.
    Reward: portfolio return minus transaction cost.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        price_data: Optional[np.ndarray] = None,
        initial_balance: float = 10_000.0,
        transaction_cost: float = TRANSACTION_COST,
    ):
        super().__init__()

        self.initial_balance = initial_balance
        self.transaction_cost = transaction_cost

        # Generate synthetic price data if none provided
        if price_data is not None:
            self._prices = np.asarray(price_data, dtype=np.float32)
        else:
            rng = np.random.default_rng(42)
            n = 252  # one trading year
            returns = rng.normal(0.0005, 0.02, n)
            self._prices = np.cumprod(1 + returns) * 100.0

        # Observation / action spaces
        if GYM_AVAILABLE:
            self.observation_space = spaces.Box(
                low=-np.inf,
                high=np.inf,
                shape=(N_FEATURES,),
                dtype=np.float32,
            )
            self.action_space = spaces.Discrete(N_ACTIONS)
        else:
            self.observation_space = _BoxSpace(N_FEATURES)
            self.action_space = _DiscreteSpace(N_ACTIONS)

        self._step_idx: int = 0
        self._balance: float = initial_balance
        self._position: float = 0.0
        self._entry_price: float = 0.0

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        """Reset environment to initial state and return first observation."""
        if GYM_MODULE == "gymnasium":
            super().reset(seed=seed)
        if seed is not None:
            np.random.seed(seed)
        self._step_idx = 0
        self._balance = self.initial_balance
        self._position = 0.0
        self._entry_price = 0.0
        obs = self._get_obs()
        if GYM_MODULE == "gymnasium":
            return obs, {}
        return obs

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """Execute one step."""
        price = float(self._prices[self._step_idx])
        reward = 0.0
        cost = 0.0

        if action == 1 and self._position == 0.0:  # buy
            units = self._balance / price
            cost = self._balance * self.transaction_cost
            self._position = units
            self._balance = 0.0
            self._entry_price = price
            reward = -cost

        elif action == 2 and self._position > 0.0:  # sell
            proceeds = self._position * price
            cost = proceeds * self.transaction_cost
            net = proceeds - cost
            reward = (net - self._position * self._entry_price) / (
                self._position * self._entry_price + 1e-8
            )
            self._balance = net
            self._position = 0.0
            self._entry_price = 0.0

        else:  # hold
            if self._position > 0.0:
                reward = (price - self._entry_price) / (self._entry_price + 1e-8) * 0.001

        self._step_idx += 1
        done = self._step_idx >= len(self._prices) - 1

        obs = self._get_obs()
        info = {
            "balance": self._balance,
            "position": self._position,
            "price": price,
            "portfolio_value": self._portfolio_value(price),
        }

        if GYM_MODULE == "gymnasium":
            return obs, float(reward), done, False, info

        return obs, float(reward), done, info

    def render(self, mode: str = "human") -> None:
        """Minimal render (no-op)."""

    def _get_obs(self) -> np.ndarray:
        """Build a 10-feature observation vector from current state."""
        idx = min(self._step_idx, len(self._prices) - 1)
        price = float(self._prices[idx])

        window = self._prices[max(0, idx - 14): idx + 1]

        ema_fast = float(np.mean(window[-5:])) if len(window) >= 5 else price
        ema_slow = float(np.mean(window)) if len(window) > 0 else price

        if len(window) > 1:
            deltas = np.diff(window)
            gains = np.where(deltas > 0, deltas, 0.0)
            losses = np.where(deltas < 0, -deltas, 0.0)
            avg_gain = np.mean(gains) if len(gains) > 0 else 0.0
            avg_loss = np.mean(losses) if len(losses) > 0 else 1e-8
            rs = avg_gain / (avg_loss + 1e-8)
            rsi = 100.0 - 100.0 / (1.0 + rs)
        else:
            rsi = 50.0

        macd = ema_fast - ema_slow
        signal = macd * 0.9
        atr = float(np.std(window)) if len(window) > 1 else 0.0
        std = atr if atr > 0 else 1.0
        bb_upper = ema_slow + 2 * std
        bb_lower = ema_slow - 2 * std

        norm_price = price / (self._prices[0] + 1e-8)
        volume = 1.0

        obs = np.array(
            [norm_price, volume, ema_fast / price, ema_slow / price,
             rsi / 100.0, macd / price, signal / price,
             atr / price, bb_upper / price, bb_lower / price],
            dtype=np.float32,
        )
        return obs

    def _portfolio_value(self, price: float) -> float:
        return self._balance + self._position * price


class _BoxSpace:
    def __init__(self, n: int):
        self.shape = (n,)
        self.low = np.full(n, -np.inf, dtype=np.float32)
        self.high = np.full(n, np.inf, dtype=np.float32)

    def sample(self) -> np.ndarray:
        return np.random.randn(self.shape[0]).astype(np.float32)


class _DiscreteSpace:
    def __init__(self, n: int):
        self.n = n

    def sample(self) -> int:
        return int(np.random.randint(0, self.n))
