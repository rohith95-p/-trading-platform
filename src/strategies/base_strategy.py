"""
BaseStrategy — Abstract base class for all pluggable strategies.

Every strategy must implement `evaluate()` which returns a Signal or None.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import numpy as np
import MetaTrader5 as _mt5
from typing import Any

mt5: Any = _mt5


@dataclass
class Signal:
    """A trade signal emitted by a strategy."""
    direction: int          # mt5.ORDER_TYPE_BUY or mt5.ORDER_TYPE_SELL
    strategy_name: str
    magic: int
    is_buy: bool

    @property
    def direction_str(self) -> str:
        return "BUY" if self.is_buy else "SELL"


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    name: str = "BaseStrategy"
    magic: int = 0

    @abstractmethod
    def evaluate(self, rates: np.ndarray) -> Optional[Signal]:
        """Evaluate the strategy on the given rate data.

        Args:
            rates: Numpy structured array from MT5 (with open, high, low, close,
                   tick_volume fields).

        Returns:
            A Signal if a valid entry is detected, otherwise None.
        """
        ...

    # ------------------------------------------------------------------
    # Shared indicator helpers (used by multiple strategies)
    # ------------------------------------------------------------------

    @staticmethod
    def ema(prices: np.ndarray, period: int) -> np.ndarray:
        """Exponential Moving Average."""
        prices = np.asarray(prices, dtype=float)
        result = np.full_like(prices, np.nan)
        if len(prices) < period:
            return result
        result[period - 1] = np.mean(prices[:period])
        mult = 2.0 / (period + 1)
        for i in range(period, len(prices)):
            result[i] = prices[i] * mult + result[i - 1] * (1 - mult)
        return result

    @staticmethod
    def rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Relative Strength Index."""
        prices = np.asarray(prices, dtype=float)
        result = np.full_like(prices, np.nan)
        if len(prices) < period + 1:
            return result
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        if avg_loss == 0:
            result[period] = 100.0
        else:
            result[period] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                result[i + 1] = 100.0
            else:
                result[i + 1] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
        return result

    @staticmethod
    def macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
        """MACD line and signal line."""
        e_fast = BaseStrategy.ema(prices, fast)
        e_slow = BaseStrategy.ema(prices, slow)
        macd_line = e_fast - e_slow
        valid_macd = macd_line[~np.isnan(macd_line)]
        sig_line = BaseStrategy.ema(valid_macd, signal)
        full_sig = np.full_like(macd_line, np.nan)
        start_idx = slow - 1 + signal - 1
        if start_idx < len(full_sig) and len(sig_line) > 0:
            valid_sig = sig_line[~np.isnan(sig_line)]
            end_idx = min(start_idx + len(valid_sig), len(full_sig))
            full_sig[start_idx:end_idx] = valid_sig[: end_idx - start_idx]
        return macd_line, full_sig
