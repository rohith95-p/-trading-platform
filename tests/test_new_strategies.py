"""Smoke / causality tests for the research-only new_* strategies."""
import os

import numpy as np
import pytest

from src.strategies.base_strategy import Signal
from src.strategies.new_asia_vol_breakout import AsiaVolBreakout
from src.strategies.new_daily_open_momentum import DailyOpenMomentum
from src.strategies.new_london_open_drive import LondonOpenDrive

DATA = os.path.join(os.path.dirname(__file__), "..", "research", "data", "XAUUSDm_M15.npy")
DTYPE = [("time", "<i8"), ("open", "<f8"), ("high", "<f8"), ("low", "<f8"),
         ("close", "<f8"), ("tick_volume", "<u8"), ("spread", "<i4"), ("real_volume", "<u8")]
T0 = 1704067200  # Monday 2024-01-01 00:00 UTC
STRATS = [AsiaVolBreakout, LondonOpenDrive, DailyOpenMomentum]


def _make(n, drift=0.0, sigma=0.3, seed=1, t0=T0):
    rng = np.random.default_rng(seed)
    close = 2000.0 + np.cumsum(drift + sigma * rng.standard_normal(n))
    r = np.zeros(n, dtype=DTYPE)
    r["time"] = t0 + 900 * np.arange(n)
    r["close"] = close
    r["open"] = np.concatenate([[2000.0], close[:-1]])
    r["high"] = np.maximum(r["open"], r["close"]) + 0.1
    r["low"] = np.minimum(r["open"], r["close"]) - 0.1
    r["tick_volume"] = 100
    return r


def _key(sig):
    return None if sig is None else sig.is_buy


@pytest.fixture(scope="module")
def real():
    if not os.path.exists(DATA):
        pytest.skip("real M15 data not available")
    return np.load(DATA)


@pytest.mark.parametrize("cls", STRATS)
def test_attributes_and_short_input(cls):
    s = cls()
    assert 7200 <= s.magic <= 7299
    assert s.execute_immediately is True
    assert s.sl_atr_mult == 1.5 and s.tp_atr_mult == 3.0
    assert s.name and len(s.session) == 2
    need = s._min_bars
    full = _make(need + 50)
    assert s.evaluate(None) is None
    for n in (0, 1, 5, need - 1):
        assert s.evaluate(full[:n]) is None
    assert s.evaluate(full[:need]) in (None,) or isinstance(s.evaluate(full[:need]), Signal)


@pytest.mark.parametrize("cls", STRATS)
def test_synthetic_never_raises(cls):
    s = cls()
    for seed, drift in ((1, 0.0), (2, 0.05), (3, -0.05)):
        r = _make(1500, drift=drift, seed=seed)
        for end in range(s._min_bars, len(r), 7):
            out = s.evaluate(r[max(0, end - 600):end])
            assert out is None or isinstance(out, Signal)


def _alter_forming(w):
    a = w.copy()
    a["open"][-1] += 37.0
    a["high"][-1] += 91.0
    a["low"][-1] -= 83.0
    a["close"][-1] += 55.0
    return a


@pytest.mark.parametrize("cls", STRATS)
def test_real_sliding_and_lookahead(cls, real):
    s = cls()
    ends = range(len(real) - 12000, len(real), 4)      # ~3000 window positions
    n_sig = 0
    for e in ends:
        w = real[e - 600:e]
        out = s.evaluate(w)
        assert out is None or isinstance(out, Signal)
        alt = s.evaluate(_alter_forming(w))
        assert _key(out) == _key(alt), f"lookahead at end={e}"
        if out is not None:
            n_sig += 1
            assert out.magic == s.magic and out.strategy_name == s.name
            assert out.direction in (0, 1)
    if cls is not LondonOpenDrive:   # London fires on one 13:15 IST bar/day; stride 4 can miss it
        assert n_sig >= 1


def test_london_stride1_lookahead(real):
    s = LondonOpenDrive()
    n = 0
    for e in range(len(real) - 30000, len(real)):
        w = real[e - 300:e]
        out = s.evaluate(w)
        if out is not None:
            n += 1
            assert _key(out) == _key(s.evaluate(_alter_forming(w)))
    assert n >= 1


def test_london_synthetic_trigger():
    s = LondonOpenDrive()
    r = _make(700, sigma=0.2)
    # pick a 07:45 UTC bar (13:15 IST) with room before it
    idx = [i for i in range(300, 650) if int(r["time"][i]) % 86400 == 27900][-1]
    for k, j in enumerate(range(idx - 3, idx + 1)):      # four rising bars 07:00..07:45
        base = 2000.0 + 1.5 * k
        r["open"][j], r["close"][j] = base, base + 1.5
        r["high"][j], r["low"][j] = base + 1.6, base - 0.1
    w = r[:idx + 2]                                      # bar idx is the last closed bar
    sig = s.evaluate(w)
    assert sig is not None and sig.is_buy
    assert s.evaluate(r[:idx + 3]) is None               # next bar: not the 13:15 bar
    # mirror
    m = r.copy()
    for k, j in enumerate(range(idx - 3, idx + 1)):
        base = 2000.0 - 1.5 * k
        m["open"][j], m["close"][j] = base, base - 1.5
        m["high"][j], m["low"][j] = base + 0.1, base - 1.6
    sig = s.evaluate(m[:idx + 2])
    assert sig is not None and not sig.is_buy


def test_asia_synthetic_first_break_only():
    s = AsiaVolBreakout()
    r = _make(700, sigma=0.15)
    ist = ((r["time"] % 86400) + 19800) % 86400
    day_key = (r["time"] + 19800) // 86400
    d = day_key[500]
    cand = np.flatnonzero((day_key == d) & (ist == 41400))   # 11:30 IST bar
    b = int(cand[0])
    hi = float(r["high"][np.flatnonzero((day_key == d) & (ist >= 9000) & (ist < 41400))].max())
    r["open"][b], r["close"][b] = hi, hi + 6.0
    r["high"][b], r["low"][b] = hi + 6.2, hi - 0.1
    r["open"][b + 1], r["close"][b + 1] = hi + 6.0, hi + 7.0   # second break, same day
    r["high"][b + 1], r["low"][b + 1] = hi + 7.1, hi + 5.9
    first = s.evaluate(r[:b + 2])
    assert first is not None and first.is_buy
    assert s.evaluate(r[:b + 3]) is None                     # later break ignored


def test_daily_open_synthetic_once_per_day():
    s = DailyOpenMomentum()
    r = _make(1500, drift=0.04, sigma=0.3, seed=5)
    day = r["time"] // 86400
    sigs = {}
    for end in range(450, len(r)):
        out = s.evaluate(r[end - 420:end])
        if out is not None:
            assert out.is_buy
            sigs.setdefault(int(day[end - 2]), []).append(end)
    assert len(sigs) >= 1
    assert all(len(v) == 1 for v in sigs.values())
