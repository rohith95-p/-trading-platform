"""Fast first-pass screen for candidate setups.

This is tier 1 of a two-tier design. It trades speed for fidelity so that a
hundred candidates can be screened, and it is honest about the approximations:

  - Entry fills at the next bar's open, plus half the bar's spread (the ask for
    longs, bid for shorts). No slippage beyond that; tier 2 adds it.
  - Exits are barrier hits on M15 OHLC. When a bar touches both stop and target,
    the STOP is taken. That is pessimistic, and the count of such bars is
    reported so the ambiguity is visible rather than buried.
  - No trailing, no pyramiding, no portfolio interaction, one position at a time
    per candidate.

Anything that survives tier 1 goes to `src/backtesting/` for full live-loop
simulation, where those approximations are replaced by M1 intrabar resolution
and the production risk modules.

**The screen's output is not "is this profitable" but "does this beat a matched
random control".** The market study established that gold's fat tails make wide
targets mildly profitable from random entries, so profit alone proves nothing.
Every candidate is therefore paired with random entries matched on session,
direction mix, trade count and exit geometry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.research.candidates import Candidate
from src.research.market_study import session_mask

POINT = 0.001  # XAUUSDm


@dataclass
class ScreenResult:
    candidate_id: str
    name: str
    family: str
    session: Tuple[float, float]
    tp_atr: float
    sl_atr: float

    trades: int = 0
    wins: int = 0
    win_rate: float = 0.0
    expectancy_r: float = 0.0
    total_r: float = 0.0
    profit_factor: float = 0.0
    max_dd_r: float = 0.0
    avg_bars_held: float = 0.0
    timeouts: int = 0
    ambiguous_bars: int = 0
    long_trades: int = 0
    short_trades: int = 0
    long_r: float = 0.0
    short_r: float = 0.0

    # control comparison
    control_expectancy_r: float = 0.0
    control_sd: float = 0.0
    edge_r: float = 0.0
    edge_z: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.__dict__)
        d["session"] = list(self.session)
        return d


def _session_mask(ist_hour: np.ndarray, session: Tuple[float, float]) -> np.ndarray:
    """Delegates to the canonical mask -- see `market_study.session_mask`.

    This used to be a private copy whose wraparound branch was wrong, so any
    overnight session silently screened zero bars (Phase 0 finding). Kept as a
    name so existing callers and scripts do not change.
    """
    return session_mask(ist_hour, session)


def simulate(f: Dict[str, np.ndarray], signals: np.ndarray, tp_atr: float,
             sl_atr: float, max_bars: int, cost_spread: bool = True
             ) -> Dict[str, Any]:
    """Walk signals forward to a barrier. Returns per-trade R multiples.

    R is measured against the INITIAL stop distance, so it is comparable across
    candidates with different volatility at entry.
    """
    hi, lo, op = f["high"], f["low"], f["open"]
    atr_, spr = f["atr14"], f["spread"]
    n = len(op)

    rs: List[float] = []
    sides: List[int] = []
    bars_held: List[int] = []
    timeouts = 0
    ambiguous = 0

    i = 0
    while i < n - 2:
        s = signals[i]
        if s == 0 or np.isnan(atr_[i]) or atr_[i] <= 0:
            i += 1
            continue

        a = atr_[i]
        half_spread = (spr[i + 1] * POINT) if cost_spread else 0.0
        if s > 0:
            entry = op[i + 1] + half_spread   # buy the ask
            tp, sl = entry + tp_atr * a, entry - sl_atr * a
        else:
            entry = op[i + 1]                 # sell the bid
            tp, sl = entry - tp_atr * a, entry + sl_atr * a
        risk = sl_atr * a

        exit_px = None
        j_end = min(i + 1 + max_bars, n)
        for j in range(i + 1, j_end):
            if s > 0:
                hit_sl, hit_tp = lo[j] <= sl, hi[j] >= tp
            else:
                # a short exits on the ask, so both barriers shift up by spread
                sp = spr[j] * POINT if cost_spread else 0.0
                hit_sl, hit_tp = (hi[j] + sp) >= sl, (lo[j] + sp) <= tp
            if hit_sl and hit_tp:
                ambiguous += 1
            if hit_sl:
                exit_px = sl
                break
            if hit_tp:
                exit_px = tp
                break
        else:
            j = j_end - 1
            sp = (spr[j] * POINT if (cost_spread and s < 0) else 0.0)
            exit_px = f["close"][j] + sp
            timeouts += 1

        r = ((exit_px - entry) if s > 0 else (entry - exit_px)) / risk
        rs.append(float(r))
        sides.append(int(s))
        bars_held.append(int(j - i))
        i = j + 1  # one position at a time

    if not rs:
        return {"trades": 0}

    arr = np.array(rs)
    sd = np.array(sides)
    wins = int((arr > 0).sum())
    gp = float(arr[arr > 0].sum())
    gl = float(-arr[arr < 0].sum())
    eq = np.cumsum(arr)
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))
    dd = float((peak - np.concatenate([[0.0], eq])).max())

    return {
        "trades": len(arr),
        "wins": wins,
        "win_rate": round(wins / len(arr) * 100, 2),
        "expectancy_r": round(float(arr.mean()), 5),
        "total_r": round(float(arr.sum()), 3),
        "profit_factor": round(gp / gl, 4) if gl > 0 else float("inf"),
        "max_dd_r": round(dd, 3),
        "avg_bars_held": round(float(np.mean(bars_held)), 1),
        "timeouts": timeouts,
        "ambiguous_bars": ambiguous,
        "long_trades": int((sd > 0).sum()),
        "short_trades": int((sd < 0).sum()),
        "long_r": round(float(arr[sd > 0].sum()), 3),
        "short_r": round(float(arr[sd < 0].sum()), 3),
        "r_array": arr,
    }


def random_control(f: Dict[str, np.ndarray], cand: Candidate, n_trades: int,
                   long_share: float, seed_base: int = 1000,
                   reps: int = 8) -> Tuple[float, float]:
    """Matched random control: same session, same direction mix, same trade count.

    Returns (mean expectancy R, sd across repetitions). A candidate's edge is
    its expectancy minus this mean, expressed in sd units -- which is the only
    number in the screen that says anything about skill.
    """
    sess = _session_mask(f["ist_hour"], cand.session)
    eligible = np.nonzero(sess & ~np.isnan(f["atr14"]))[0]
    eligible = eligible[(eligible > 250) & (eligible < len(f["close"]) - cand.max_bars - 2)]
    if len(eligible) < 20 or n_trades < 5:
        return (float("nan"), float("nan"))

    means = []
    for rep in range(reps):
        rng = np.random.default_rng(seed_base + rep)
        pick = rng.choice(eligible, size=min(n_trades * 2, len(eligible)), replace=False)
        sig = np.zeros(len(f["close"]), dtype=np.int8)
        dirs = np.where(rng.random(len(pick)) < long_share, 1, -1)
        sig[pick] = dirs
        r = simulate(f, sig, cand.tp_atr, cand.sl_atr, cand.max_bars)
        if r.get("trades", 0) >= 5:
            means.append(r["expectancy_r"])
    if not means:
        return (float("nan"), float("nan"))
    return (float(np.mean(means)), float(np.std(means)))


def screen(f: Dict[str, np.ndarray], cand: Candidate,
           with_control: bool = True) -> ScreenResult:
    sig = cand.rule(f).astype(np.int8)
    sig[~_session_mask(f["ist_hour"], cand.session)] = 0
    sig[:250] = 0  # indicator warm-up

    r = simulate(f, sig, cand.tp_atr, cand.sl_atr, cand.max_bars)
    res = ScreenResult(candidate_id=cand.id, name=cand.name, family=cand.family,
                       session=cand.session, tp_atr=cand.tp_atr, sl_atr=cand.sl_atr)
    if r.get("trades", 0) == 0:
        return res

    for k in ("trades", "wins", "win_rate", "expectancy_r", "total_r",
              "profit_factor", "max_dd_r", "avg_bars_held", "timeouts",
              "ambiguous_bars", "long_trades", "short_trades", "long_r", "short_r"):
        setattr(res, k, r[k])

    if with_control and res.trades >= 20:
        long_share = res.long_trades / res.trades
        cm, csd = random_control(f, cand, res.trades, long_share)
        res.control_expectancy_r = round(cm, 5) if cm == cm else 0.0
        res.control_sd = round(csd, 5) if csd == csd else 0.0
        if csd and csd > 0:
            res.edge_r = round(res.expectancy_r - cm, 5)
            res.edge_z = round(res.edge_r / csd, 3)
    return res
