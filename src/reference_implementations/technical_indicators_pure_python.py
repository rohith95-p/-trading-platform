"""
SOURCE: git repos/hyperliquid-trading-agent-master - Copy/src/indicators/local_indicators.py
PURPOSE: Pure Python technical indicator computation from OHLCV candle data.
         No external dependencies (no TA-Lib, no pandas-ta).
         Useful as a fallback when NumPy/TA-Lib unavailable, or for
         lightweight environments.

Our main implementation uses NumPy vectorization in src/intelligence/indicators.py.
This pure Python version is kept as a reference and fallback.

Indicators: EMA, SMA, RSI (Wilder), MACD, ATR, Bollinger Bands,
            Stochastic RSI, ADX, OBV, VWAP

Usage:
    from src.reference_implementations.technical_indicators_pure_python import compute_all
    
    candles = [{"open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000}, ...]
    indicators = compute_all(candles)
    print(indicators["rsi14"])  # [None, None, ..., 65.3, 67.1, ...]
"""

from __future__ import annotations
import math


def _closes(candles): return [c["close"] for c in candles]
def _highs(candles): return [c["high"] for c in candles]
def _lows(candles): return [c["low"] for c in candles]
def _volumes(candles): return [c["volume"] for c in candles]


def sma(values: list, period: int) -> list:
    result = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(None)
        else:
            result.append(sum(values[i - period + 1: i + 1]) / period)
    return result


def ema(values: list, period: int) -> list:
    result = []
    k = 2.0 / (period + 1)
    prev = None
    for i, v in enumerate(values):
        if i < period - 1:
            result.append(None)
        elif i == period - 1:
            prev = sum(values[:period]) / period
            result.append(prev)
        else:
            prev = v * k + prev * (1 - k)
            result.append(prev)
    return result


def rsi(candles: list, period: int = 14) -> list:
    """RSI using Wilder's smoothing method."""
    closes = _closes(candles)
    if len(closes) < period + 1:
        return [None] * len(closes)
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    result = [None] * period
    gains = [max(d, 0) for d in deltas[:period]]
    losses = [abs(min(d, 0)) for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    result.append(100.0 if avg_loss == 0 else round(100.0 - (100.0 / (1.0 + avg_gain / avg_loss)), 4))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + max(deltas[i], 0)) / period
        avg_loss = (avg_loss * (period - 1) + abs(min(deltas[i], 0))) / period
        result.append(100.0 if avg_loss == 0 else round(100.0 - (100.0 / (1.0 + avg_gain / avg_loss)), 4))
    return result


def macd(candles: list, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    closes = _closes(candles)
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [round(f - s, 6) if f is not None and s is not None else None for f, s in zip(ema_fast, ema_slow)]
    valid_macd = [v for v in macd_line if v is not None]
    signal_raw = ema(valid_macd, signal) if len(valid_macd) >= signal else [None] * len(valid_macd)
    signal_line = [None] * (len(macd_line) - len(valid_macd)) + signal_raw
    histogram = [round(m - s, 6) if m is not None and s is not None else None for m, s in zip(macd_line, signal_line)]
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def atr(candles: list, period: int = 14) -> list:
    if len(candles) < 2:
        return [None] * len(candles)
    true_ranges = [max(candles[i]["high"] - candles[i]["low"],
                       abs(candles[i]["high"] - candles[i-1]["close"]),
                       abs(candles[i]["low"] - candles[i-1]["close"]))
                   for i in range(1, len(candles))]
    if len(true_ranges) < period:
        return [None] * len(candles)
    result = [None] * period
    avg = sum(true_ranges[:period]) / period
    result.append(round(avg, 6))
    for i in range(period, len(true_ranges)):
        avg = (avg * (period - 1) + true_ranges[i]) / period
        result.append(round(avg, 6))
    return result


def bbands(candles: list, period: int = 20, std_dev: float = 2.0) -> dict:
    closes = _closes(candles)
    middle = sma(closes, period)
    upper, lower = [], []
    for i in range(len(closes)):
        if middle[i] is None:
            upper.append(None); lower.append(None)
        else:
            window = closes[i - period + 1: i + 1]
            sd = math.sqrt(sum((x - middle[i]) ** 2 for x in window) / period)
            upper.append(round(middle[i] + std_dev * sd, 6))
            lower.append(round(middle[i] - std_dev * sd, 6))
    return {"upper": upper, "middle": middle, "lower": lower}


def obv(candles: list) -> list:
    closes = _closes(candles)
    volumes = _volumes(candles)
    result = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]: result.append(result[-1] + volumes[i])
        elif closes[i] < closes[i-1]: result.append(result[-1] - volumes[i])
        else: result.append(result[-1])
    return result


def vwap(candles: list) -> list:
    cum_vol = cum_tp_vol = 0.0
    result = []
    for c in candles:
        tp = (c["high"] + c["low"] + c["close"]) / 3.0
        cum_vol += c["volume"]
        cum_tp_vol += tp * c["volume"]
        result.append(round(cum_tp_vol / cum_vol, 6) if cum_vol > 0 else None)
    return result


def adx(candles: list, period: int = 14) -> list:
    if len(candles) < period + 1:
        return [None] * len(candles)
    plus_dm_list, minus_dm_list, tr_list = [], [], []
    for i in range(1, len(candles)):
        h, l = candles[i]["high"], candles[i]["low"]
        ph, pl, pc = candles[i-1]["high"], candles[i-1]["low"], candles[i-1]["close"]
        plus_dm_list.append(max(h - ph, 0) if (h - ph) > (pl - l) else 0)
        minus_dm_list.append(max(pl - l, 0) if (pl - l) > (h - ph) else 0)
        tr_list.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(tr_list) < period:
        return [None] * len(candles)
    atr_v = sum(tr_list[:period])
    pdm = sum(plus_dm_list[:period])
    mdm = sum(minus_dm_list[:period])
    dx_list = []
    pdi = (pdm / atr_v) * 100 if atr_v else 0
    mdi = (mdm / atr_v) * 100 if atr_v else 0
    s = pdi + mdi
    dx_list.append(abs(pdi - mdi) / s * 100 if s else 0)
    for i in range(period, len(tr_list)):
        atr_v = atr_v - atr_v / period + tr_list[i]
        pdm = pdm - pdm / period + plus_dm_list[i]
        mdm = mdm - mdm / period + minus_dm_list[i]
        pdi = (pdm / atr_v) * 100 if atr_v else 0
        mdi = (mdm / atr_v) * 100 if atr_v else 0
        s = pdi + mdi
        dx_list.append(abs(pdi - mdi) / s * 100 if s else 0)
    result = [None] * (period * 2)
    if len(dx_list) >= period:
        adx_v = sum(dx_list[:period]) / period
        result.append(round(adx_v, 4))
        for i in range(period, len(dx_list)):
            adx_v = (adx_v * (period - 1) + dx_list[i]) / period
            result.append(round(adx_v, 4))
    while len(result) < len(candles):
        result.insert(0, None)
    return result[:len(candles)]


def compute_all(candles: list) -> dict:
    """Compute standard indicator suite from OHLCV candles."""
    if not candles:
        return {}
    closes = _closes(candles)
    macd_data = macd(candles)
    bb_data = bbands(candles)
    return {
        "ema20": ema(closes, 20),
        "ema50": ema(closes, 50),
        "rsi7": rsi(candles, 7),
        "rsi14": rsi(candles, 14),
        "macd": macd_data["macd"],
        "macd_signal": macd_data["signal"],
        "macd_histogram": macd_data["histogram"],
        "atr3": atr(candles, 3),
        "atr14": atr(candles, 14),
        "bbands_upper": bb_data["upper"],
        "bbands_middle": bb_data["middle"],
        "bbands_lower": bb_data["lower"],
        "adx": adx(candles),
        "obv": obv(candles),
        "vwap": vwap(candles),
    }


def last_n(series: list, n: int = 10) -> list:
    return [v for v in series if v is not None][-n:]


def latest(series: list):
    for v in reversed(series):
        if v is not None:
            return v
    return None
