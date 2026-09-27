"""TrendSniperSAR -- research candidate, NOT approved for live trading.

Status: RESEARCH ONLY. Not imported by `main_loop` and must not be until it has
cleared the remaining gates in docs/research/RESEARCH_LEDGER.md.

The setup is a confluence of 7 conditions, all of which must be true simultaneously
to generate a signal. This extreme selectivity (prior audit noted 0 signals in a
full backtest) is intentional — the hypothesis is that when all seven align, the
signal quality is so high it outweighs the rarity of occurrence.

Entry (LONG): EMA7 > EMA21 > EMA200, price > EMA7, Parabolic SAR flipped bullish,
ADX(14) > 25 (strong trend), change of character (break of prior 5-bar low), and
M5 tick volume > 20-bar average (buying interest).

Entry (SHORT): Mirror conditions.

Why 7 conditions? Each is measurable and has independent predictive value per the
audit (docs/research/MASTER_WEEKEND_AUDIT_AUG28.md:367-368). The original project
used 7 because a simpler version would have produced false breakouts in chop.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from src.strategies.base_strategy import BaseStrategy, Signal, mt5


class TrendSniperSAR(BaseStrategy):
    """7-condition trend confirmation with Parabolic SAR flip gate."""

    name = "TREND_SNIPER_SAR"
    magic = 3002

    def __init__(self):
        self._pending_signal: Optional[Signal] = None
        self._pending_candle_time: Optional[int] = None

    def evaluate(self, m15_rates: np.ndarray,
                 m5_rates: Optional[np.ndarray] = None) -> Optional[Signal]:
        # Require enough history for EMA(200) + SAR + ADX
        need = 200 + 50  # EMA200 convergence buffer + overhead
        if m15_rates is None or len(m15_rates) < need:
            return None

        closes = m15_rates["close"].astype(float)
        highs = m15_rates["high"].astype(float)
        lows = m15_rates["low"].astype(float)

        # --- Compute indicators on M15 ---
        e7 = self.ema(closes, 7)
        e21 = self.ema(closes, 21)
        e200 = self.ema(closes, 200)
        adx_vals = self._adx(highs, lows, closes, 14)
        sar = self._parabolic_sar(highs, lows, 0.02, 0.02, 0.2)

        # Use the last *completed* candle (index -2).
        c = closes[-2]
        h = highs[-2]
        l = lows[-2]
        e7_val = e7[-2]
        e21_val = e21[-2]
        e200_val = e200[-2]
        adx_val = adx_vals[-2]
        sar_val = sar[-2]

        # --- Check NaN ---
        if (np.isnan(e7_val) or np.isnan(e21_val) or np.isnan(e200_val) or
            np.isnan(adx_val) or np.isnan(sar_val)):
            return None

        # --- Condition 1: EMA stack aligned (LONG: 7 > 21 > 200, SHORT: inverted) ---
        long_aligned = e7_val > e21_val > e200_val
        short_aligned = e7_val < e21_val < e200_val
        if not (long_aligned or short_aligned):
            return None

        # --- Condition 2: Price on correct side of EMA7 (LONG: c > e7, SHORT: c < e7) ---
        if long_aligned and c <= e7_val:
            return None
        if short_aligned and c >= e7_val:
            return None

        # --- Condition 3: SAR flip in trend direction (LONG: price > sar, SHORT: price < sar) ---
        if long_aligned and c <= sar_val:
            return None
        if short_aligned and c >= sar_val:
            return None

        # --- Condition 4: ADX > 25 (strong trend, not chop) ---
        if adx_val <= 25.0:
            return None

        # --- Condition 5: Change of character (swing-extreme break) ---
        if len(closes) < 6:
            return None
        swing_bars = 5
        swing_high = np.max(highs[-swing_bars - 1:-1])
        swing_low = np.min(lows[-swing_bars - 1:-1])

        if long_aligned and l >= swing_low:
            # Bullish ChoCh requires a break below the prior low
            return None
        if short_aligned and h <= swing_high:
            # Bearish ChoCh requires a break above the prior high
            return None

        # --- Condition 6: Volume confirmation (M5 preferred, M15 fallback) ---
        if m5_rates is not None and len(m5_rates) >= 21:
            volumes = m5_rates["tick_volume"].astype(float)
            curr_vol = volumes[-2]
            avg_vol = np.mean(volumes[-21:-1])
            volume_ok = curr_vol > avg_vol
        else:
            volumes = m15_rates["tick_volume"].astype(float)
            curr_vol = volumes[-2]
            avg_vol = np.mean(volumes[-21:-1])
            volume_ok = curr_vol > avg_vol

        if not volume_ok:
            return None

        # --- All 7 conditions passed ---
        if long_aligned:
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name,
                          magic=self.magic, is_buy=True)
        else:
            return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name,
                          magic=self.magic, is_buy=False)

    def check_pending_confirmation(self, m15_rates: np.ndarray) -> Optional[Signal]:
        return None

    def set_pending(self, signal: Signal, candle_time: int) -> None:
        self._pending_signal = signal
        self._pending_candle_time = candle_time

    # --- Indicator helpers (copied from live code to stay self-contained) ---

    def _adx(self, high: np.ndarray, low: np.ndarray, close: np.ndarray,
             period: int = 14) -> np.ndarray:
        """ADX using Wilder's smoothing, matching live implementation."""
        n = len(high)
        out = np.full(n, np.nan)
        if n < period + 1:
            return out

        tr = np.empty(n)
        tr[0] = high[0] - low[0]
        tr[1:] = np.maximum(high[1:] - low[1:],
                             np.maximum(np.abs(high[1:] - close[:-1]),
                                        np.abs(low[1:] - close[:-1])))

        du = np.where(high[1:] - high[:-1] > 0, high[1:] - high[:-1], 0.0)
        dd = np.where(low[:-1] - low[1:] > 0, low[:-1] - low[1:], 0.0)

        atr_sum = tr[:period].sum()
        du_sum = du[:period].sum()
        dd_sum = dd[:period].sum()

        for i in range(period, n):
            atr_sum += tr[i] - tr[i - period]
            du_sum += du[i - 1] - du[i - 1 - period]
            dd_sum += dd[i - 1] - dd[i - 1 - period]

            di_plus = 100.0 * du_sum / atr_sum if atr_sum > 0 else 0.0
            di_minus = 100.0 * dd_sum / atr_sum if atr_sum > 0 else 0.0
            di_diff = abs(di_plus - di_minus)
            di_sum = di_plus + di_minus
            dx = 100.0 * di_diff / di_sum if di_sum > 0 else 0.0

            if i == period:
                adx_sum = dx * period
                out[i] = adx_sum / period
            else:
                adx_sum = (adx_sum * (period - 1) + dx) / period
                out[i] = adx_sum

        return out

    def _parabolic_sar(self, h: np.ndarray, l: np.ndarray,
                       step: float = 0.02, increment: float = 0.02,
                       max_step: float = 0.2) -> np.ndarray:
        """Parabolic SAR following the standard algorithm."""
        n = len(h)
        sar = np.full(n, np.nan, dtype=float)
        if n < 2:
            return sar

        long = True
        af = step
        hp = h[0]
        lp = l[0]
        sar[0] = l[0]

        for i in range(1, n):
            if long:
                sar[i] = sar[i - 1] + af * (hp - sar[i - 1])
                sar[i] = min(sar[i], l[i], l[i - 1] if i > 0 else l[i])
                if h[i] > hp:
                    hp = h[i]
                    af = min(af + increment, max_step)
                if l[i] < sar[i]:
                    long = False
                    sar[i] = hp
                    lp = l[i]
                    af = step
            else:
                sar[i] = sar[i - 1] - af * (sar[i - 1] - lp)
                sar[i] = max(sar[i], h[i], h[i - 1] if i > 0 else h[i])
                if l[i] < lp:
                    lp = l[i]
                    af = min(af + increment, max_step)
                if h[i] > sar[i]:
                    long = True
                    sar[i] = lp
                    hp = h[i]
                    af = step

        return sar
