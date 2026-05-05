"""
SOURCE: git repos/Fiduciary-Sentinel-Core - Copy/mcp/fracdiff.py
PURPOSE: Fractional differentiation for time series stationarity.
         Based on de Prado "Advances in Financial ML" (2018).
         Used to preprocess price/return features for the PPO agent.

Key insight: Standard differencing (d=1) destroys memory.
Fractional differencing (d=0.3-0.6) achieves stationarity while
preserving maximum historical memory — critical for RL agents.

Usage:
    from src.reference_implementations.fractional_differentiation import frac_diff_fixed, find_min_d
    
    # Find minimum d that makes series stationary
    d = find_min_d(price_series)  # typically 0.3-0.6
    
    # Apply fractional differentiation
    stationary_series = frac_diff_fixed(price_series, d)
"""

import numpy as np
from typing import Optional


def _get_weights(d: float, size: int, threshold: float = 1e-5) -> np.ndarray:
    """Compute fractional differentiation weights (de Prado formula)."""
    weights = [1.0]
    for k in range(1, size):
        w = -weights[-1] * (d - k + 1) / k
        if abs(w) < threshold:
            break
        weights.append(w)
    return np.array(weights[::-1])


def frac_diff_fixed(series: np.ndarray, d: float, threshold: float = 1e-5) -> np.ndarray:
    """
    Apply fixed-window fractional differentiation.

    Args:
        series: 1D array (log prices or returns)
        d: Fractional order (0 < d < 1). Typical: 0.3-0.6
        threshold: Weight cutoff

    Returns:
        Fractionally-differenced series (NaN-padded at start)
    """
    weights = _get_weights(d, len(series), threshold)
    width = len(weights)
    result = np.full(len(series), np.nan)
    for i in range(width - 1, len(series)):
        result[i] = np.dot(weights, series[i - width + 1: i + 1])
    return result


def find_min_d(series: np.ndarray, p_value_threshold: float = 0.05,
               d_range: Optional[np.ndarray] = None) -> float:
    """
    Find minimum d that produces a stationary series (ADF test).

    Args:
        series: Price or log-price series
        p_value_threshold: ADF stationarity threshold (default 0.05)
        d_range: d values to test (default 0.0 to 1.0 in 0.05 steps)

    Returns:
        Minimum d achieving stationarity (fallback: 0.4)
    """
    if d_range is None:
        d_range = np.arange(0.0, 1.05, 0.05)

    try:
        from statsmodels.tsa.stattools import adfuller
    except ImportError:
        return 0.4

    for d in d_range:
        if d == 0:
            continue
        diffed = frac_diff_fixed(series, d)
        clean = diffed[~np.isnan(diffed)]
        if len(clean) < 20:
            continue
        try:
            p_value = adfuller(clean, maxlag=1, regression='c', autolag=None)[1]
            if p_value < p_value_threshold:
                return float(d)
        except Exception:
            continue
    return 1.0


def preprocess_state_returns(state_vector: np.ndarray,
                              price_history: Optional[np.ndarray] = None,
                              d: float = 0.4) -> np.ndarray:
    """
    Apply fractional differentiation to lagged return features in state vector.

    The first 5 elements (indices 0-4) are lagged returns: Ret(t)..Ret(t-4).
    Fracdiff makes them stationary while preserving memory.

    Args:
        state_vector: 21-element observation vector
        price_history: Optional longer price series for better estimation
        d: Fractional differentiation order (default 0.4)

    Returns:
        Modified state vector with fracdiffed return features
    """
    state = state_vector.copy()

    if price_history is not None and len(price_history) >= 20:
        diffed = frac_diff_fixed(price_history, d)
        clean = diffed[~np.isnan(diffed)]
        if len(clean) >= 5:
            state[0:5] = clean[-5:]
            return state

    # Fallback: apply directly to 5 return values
    returns = state[0:5]
    if np.any(returns != 0):
        padded = np.concatenate([np.zeros(10), returns])
        diffed = frac_diff_fixed(padded, d)
        clean = diffed[~np.isnan(diffed)]
        if len(clean) >= 5:
            state[0:5] = clean[-5:]

    return state
