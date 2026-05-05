"""
SOURCE: git repos/Fiduciary-Sentinel-Core - Copy/mcp/confluence_engine.py
PURPOSE: 4-pillar confluence filter for trade execution authorization.
         Prevents low-quality entries by requiring multiple confirming signals.

The 4 Pillars:
1. Sentiment (20%) — Fear & Greed index; blocks late buys in extreme greed
2. Volume/Session (20%) — Volume vs 20-MA; blocks weekend/low-volume entries
3. SMC/Liquidity Sweeps (40%) — Smart Money Concepts; requires sweep + FVG
4. Candlestick Trigger (20%) — 15m hammer/shooting star confirmation

Execution authorized only if weighted score >= 0.75.

Adaptive weights: Updated after each trade based on which pillars were
predictive of profitable outcomes (EMA weight adjustment).

Usage:
    filter = ConfluenceFilter(ticker="BTC-USD")
    authorized = filter.authorize_trade(agent_action_value=0.8, df=ohlcv_df)
    if authorized:
        place_order(...)
"""

import json
import os
from typing import Dict


class ConfluenceFilter:
    """
    Multi-pillar confluence filter for trade execution.
    Requires 75%+ weighted score across 4 pillars before authorizing.
    """

    BASE_WEIGHTS = {"sentiment": 0.20, "volume": 0.20, "smc": 0.40, "candles": 0.20}

    def __init__(self, ticker: str = "BTC-USD", weights_file: str = "data/confluence_weights.json"):
        self.ticker = ticker
        self.weights_file = weights_file
        self.weights = self._load_weights()

    def _load_weights(self) -> dict:
        if os.path.exists(self.weights_file):
            try:
                with open(self.weights_file) as f:
                    data = json.load(f)
                    if all(k in data for k in self.BASE_WEIGHTS):
                        return data
            except Exception:
                pass
        return self.BASE_WEIGHTS.copy()

    def update_weights(self, pillar_scores: dict, is_profitable: bool, alpha: float = 0.1):
        """Adapt weights based on trade outcome (EMA update)."""
        for pillar, val in pillar_scores.items():
            if val >= 0.6 and is_profitable:
                target = min(self.BASE_WEIGHTS[pillar] * 1.5, 0.6)
            elif val >= 0.6 and not is_profitable:
                target = max(self.BASE_WEIGHTS[pillar] * 0.5, 0.05)
            else:
                target = self.weights[pillar]
            self.weights[pillar] = (1 - alpha) * self.weights[pillar] + alpha * target

        total = sum(self.weights.values())
        for p in self.weights:
            self.weights[p] /= total

        os.makedirs(os.path.dirname(self.weights_file) if os.path.dirname(self.weights_file) else ".", exist_ok=True)
        with open(self.weights_file, "w") as f:
            json.dump(self.weights, f)

    def check_fear_greed(self, action: str) -> float:
        """Pillar 1: Fear & Greed index from alternative.me API."""
        try:
            import requests
            resp = requests.get("https://api.alternative.me/fng/", timeout=5)
            fng_value = int(resp.json()["data"][0]["value"])
            if fng_value >= 80 and action == "BUY":
                return 0.0  # Extreme greed — penalize late buys
            if fng_value <= 20 and action == "SELL":
                return 0.0  # Extreme fear — penalize late sells
            return 1.0
        except Exception:
            return 1.0  # Default pass if API fails

    def check_volume_session(self, df) -> float:
        """Pillar 2: Volume vs 20-MA; penalize weekends."""
        try:
            import pandas as pd
            latest_time = df.index[-1]
            if hasattr(latest_time, "weekday") and latest_time.weekday() >= 5:
                return 0.0  # Weekend penalty
            avg_volume = df["volume"].rolling(20).mean().iloc[-1]
            current_volume = df["volume"].iloc[-1]
            return 1.0 if current_volume > avg_volume else 0.0
        except Exception:
            return 0.0

    def check_liquidity_sweep_fvg(self, df, action: str) -> float:
        """Pillar 3: Smart Money Concepts — sweep + Fair Value Gap."""
        try:
            if len(df) < 10:
                return 0.0
            recent = df.tail(5)
            struct_low = df["low"].iloc[-20:-5].min()
            struct_high = df["high"].iloc[-20:-5].max()
            recent_min = df["low"].iloc[-5:].min()
            recent_max = df["high"].iloc[-5:].max()
            last_close = df["close"].iloc[-1]

            fvg_bullish = any(
                df["high"].iloc[i-2] < df["low"].iloc[i]
                for i in range(max(2, len(df)-5), len(df))
            )
            fvg_bearish = any(
                df["low"].iloc[i-2] > df["high"].iloc[i]
                for i in range(max(2, len(df)-5), len(df))
            )

            sweep_bullish = (recent_min < struct_low) and (last_close > struct_low)
            sweep_bearish = (recent_max > struct_high) and (last_close < struct_high)

            if action == "BUY":
                if sweep_bullish and fvg_bullish:
                    return 1.0  # Full score: sweep + FVG
                elif fvg_bullish:
                    return 0.5  # Partial: FVG only
            elif action == "SELL":
                if sweep_bearish and fvg_bearish:
                    return 1.0
                elif fvg_bearish:
                    return 0.5
            return 0.0
        except Exception:
            return 0.0

    def check_candlestick_trigger(self, action: str) -> float:
        """Pillar 4: 15m hammer/shooting star confirmation."""
        try:
            import yfinance as yf
            df_15m = yf.Ticker(self.ticker).history(period="1d", interval="15m")
            if len(df_15m) < 3:
                return 0.0

            def has_long_lower_wick(c):
                body = abs(c["Close"] - c["Open"])
                lower = min(c["Close"], c["Open"]) - c["Low"]
                upper = c["High"] - max(c["Close"], c["Open"])
                return lower > body * 2 and lower > upper

            def has_long_upper_wick(c):
                body = abs(c["Close"] - c["Open"])
                upper = c["High"] - max(c["Close"], c["Open"])
                lower = min(c["Close"], c["Open"]) - c["Low"]
                return upper > body * 2 and upper > lower

            c1 = df_15m.iloc[-2]
            c2 = df_15m.iloc[-3]

            if action == "BUY" and (has_long_lower_wick(c1) or has_long_lower_wick(c2)):
                return 1.0
            if action == "SELL" and (has_long_upper_wick(c1) or has_long_upper_wick(c2)):
                return 1.0
            return 0.0
        except Exception:
            return 0.0

    def authorize_trade(self, agent_action_value: float, df) -> bool:
        """
        Run all 4 pillars and authorize if weighted score >= 0.75.

        Args:
            agent_action_value: PPO output (>0 = BUY, <0 = SELL, 0 = HOLD)
            df: OHLCV DataFrame

        Returns:
            True if trade is authorized, False otherwise
        """
        if agent_action_value == 0:
            return False

        action = "BUY" if agent_action_value > 0 else "SELL"

        scores = {
            "sentiment": self.check_fear_greed(action),
            "volume": self.check_volume_session(df),
            "smc": self.check_liquidity_sweep_fvg(df, action),
            "candles": self.check_candlestick_trigger(action),
        }

        score = sum(v * self.weights[k] for k, v in scores.items())
        return score >= 0.75
