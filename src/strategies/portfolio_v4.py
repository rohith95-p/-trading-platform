"""Portfolio v4 -- history and current state.

ORIGINAL (2026-09-01): four session-specialist legs (squeeze_break ASIA,
ema_stack LONDON, fvg NY, range_rejection NY). Declared dead 2026-09-03
(SYSTEM_FAULTS.md): selected by screening 90+ candidates and kept because they
scored best on their own selection window; a 4-year holdout gave PF 0.965
(loses money). A real bug in EMASTACK's dedup was later found and fixed
(HYP-046/047), recovering a genuine but thin edge in FVG specifically -- see
the ledger for the full history. All four original classes remain below,
unused by PORTFOLIO_V4, for reference and possible reuse.

CURRENT (2026-09-07, HYP-059/060): PORTFOLIO_V4 runs two NY-session FVG legs --
FVGNYSweepOrVoid (liquidity-filtered: a preceding sweep, or a gap exceeding
0.5x ATR200) and FVGNYTight (unfiltered, which under the engine's Highlander
one-FVG-per-candle rule trades only the gaps SweepOrVoid rejects). Same
underlying XAU-092 fair-value-gap detector throughout.

FVGNYSweep and FVGNYVoid were REMOVED from the list 2026-09-08: each is a
strict subset of FVGNYSweepOrVoid and always loses the Highlander ranking to
it (rank 5 > 4 > 3), so both took exactly zero trades in every backtest window
(1-month, 3-month, 1-year). Classes kept below for reference only. Dropping
them does not change any result -- the 4-leg and 2-leg runs are identical.

Combined backtest, live config, 2025-01-01 -> 2026-05-20 holdout: see
docs/research/RESEARCH_LEDGER.md HYP-061 for the exact numbers.

Each class carries its own sl_atr_mult / tp_atr_mult, read by main_loop.py
and passed through to RiskManager.calculate_atr_stops() via the new
tp_multiplier parameter -- these do NOT match the live system's hardcoded
session multipliers (1.5 London/NY, 2.0 Asia), which is exactly why a
per-strategy override was needed rather than relying on session auto-detect.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from src.strategies.base_strategy import BaseStrategy, Signal, mt5
from src.research.candidates import build_library
from src.research.market_study import build_features, session_mask

_LIB = {c.id: c for c in build_library()}


class _SessionSpecialist(BaseStrategy):
    """Shared plumbing for the 4 portfolio_v4 legs."""

    candidate_id: str
    session: tuple
    sl_atr_mult: float
    tp_atr_mult: float
    # main_loop.py fetches exactly 250 M15 bars (its documented live history
    # window) -- 260 (copied from EMAStack's own EMA200-convergence margin)
    # silently blocked every evaluate() call forever. Found live: all 4
    # strategies returned None on every check with no error, no log line,
    # nothing to indicate why. Fixed 2026-09-02, see ledger HYP-045.
    _min_bars = 250
    # CRITICAL: the backtest engine that validated every number in this file
    # executes a signal immediately on the bar after it fires -- it has no
    # "queue and confirm next candle" concept. main_loop.py's default path for
    # non-London sessions DOES queue, and check_pending_confirmation() below
    # always returns None, so a queued signal would be silently dropped
    # forever. This flag routes these strategies through the same
    # execute-immediately path London already had, matching what was actually
    # tested. Found by tracing real account history, not by inspection --
    # see docs/research/RESEARCH_LEDGER.md HYP-042.
    execute_immediately = True
    # Edge-trigger: only act the bar this direction first turns on, instead
    # of every bar a persisting signal state remains true. Only XAU-005
    # ema_stack needs this -- it is a STATE test (ema20>ema50>ema200 and
    # close>ema20), true for as long as the ribbon stays aligned, not just
    # the bar it starts. main_loop's only dedup is "not the same candle
    # already acted on" (last_fired_candle), which doesn't cover "this is
    # the same persisting state as my last trade." Found 2026-09-05
    # replaying the two rest days: EMASTACK_LONDON_TIGHT fired 5
    # near-identical BUYs into one afternoon chop because the ribbon stayed
    # stacked the whole time -- 5 fresh $6 stops on one failing thesis, not
    # 5 independent setups. Tried applying this to all 4 legs first: it also
    # cut FVG's and SqueezeBreak's consecutive-bar signals during genuine
    # continuation moves, including the single biggest winner of the window
    # (a chained FVG sequence that ran to +5R) -- net result got WORSE
    # ($17.98 -> -$22.19). Those two rules' repeats are event chains during
    # a real move, not a stuck state, so this flag is opt-in per-leg, not
    # blanket plumbing. See docs/research/RESEARCH_LEDGER.md HYP-046.
    edge_trigger = False

    def evaluate(self, m15_rates: np.ndarray, m5_rates: Optional[np.ndarray] = None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None
        f = build_features(m15_rates)
        raw = _LIB[self.candidate_id].rule(f)
        mask = session_mask(f["ist_hour"], self.session)
        sig = np.where(mask, raw, 0)
        s = sig[-2]
        if s == 0 or (isinstance(s, float) and np.isnan(s)):
            return None
        if self.edge_trigger and sig[-3] == s:
            return None
        if s > 0:
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name,
                          magic=self.magic, is_buy=True)
        return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name,
                      magic=self.magic, is_buy=False)

    def check_pending_confirmation(self, m15_rates):
        return None

    def set_pending(self, signal, candle_time):
        pass


class SqueezeBreakAsia(_SessionSpecialist):
    """Squeeze breakout, ASIA session (02:30-11:30 IST). Isolated PF 1.741."""
    name = "SQUEEZE_ASIA"
    magic = 3011
    candidate_id = "XAU-062"
    session = (2.5, 11.5)
    sl_atr_mult = 2.0
    tp_atr_mult = 4.0


class EMAStackLondonTight(_SessionSpecialist):
    """EMA ribbon, LONDON session (11:30-15:30 IST), tight-risk variant
    (~$6 avg risk, ~$26 avg win). Isolated PF 1.286.

    edge_trigger=True: XAU-005 is a persisting-alignment state, not a
    one-off event -- see HYP-046. Without this, one choppy afternoon fires
    a new $6-stop entry every 15 min for as long as the ribbon stays
    stacked, which is what happened 2026-09-03 (5 near-identical BUYs, all
    stopped by the same grind)."""
    name = "EMASTACK_LONDON_TIGHT"
    magic = 3012
    candidate_id = "XAU-005"
    session = (11.5, 15.5)
    sl_atr_mult = 2.0
    tp_atr_mult = 3.0
    edge_trigger = True


class FVGNYTight(_SessionSpecialist):
    """Fair value gap, NY session (17:30-21:30 IST), tight-risk variant
    (~$5 avg risk, ~$26 avg win). Isolated PF 1.661 -- the strongest single
    leg in the portfolio."""
    name = "FVG_NY_TIGHT"
    magic = 3013
    candidate_id = "XAU-092"
    session = (17.5, 21.5)
    sl_atr_mult = 0.5
    tp_atr_mult = 2.5


class RangeRejectionNYTight(_SessionSpecialist):
    """Range rejection wick, NY session (17:30-21:30 IST), tight-risk
    variant (~$7 avg risk, ~$22 avg win). Isolated PF 1.726, smaller
    sample (n=26) than the other three legs."""
    name = "RANGEREJECTION_NY_TIGHT"
    magic = 3014
    candidate_id = "XAU-049"
    session = (17.5, 21.5)
    sl_atr_mult = 0.75
    tp_atr_mult = 2.25


class _LiquidityFilteredFVG(BaseStrategy):
    """FVG (XAU-092), restricted to the subset of gaps with a liquidity-context
    story behind them -- validated 2026-09-07, HYP-059/060.

    NOT a new entry rule: the underlying gap detector is identical to
    FVGNYTight. `mode` narrows WHICH gaps qualify:
      "sweep"          -- only gaps forming within 12 bars of a clustered
                          liquidity level (3+ pivots within atr/margin) being
                          breached. Idea: a gap right after a sweep is real
                          forced flow (stops run), not drift.
      "void"           -- only gaps exceeding `void_mult` x ATR200, the
                          script's own literal "liquidity void" definition --
                          a size floor set by the market's own long-run vol,
                          not an arbitrary % of price.
      "sweep_or_void"  -- either condition. On the 2025-2026 holdout this beat
                          plain FVG on drawdown and ruin probability in every
                          session tested (Asia/London/NY/all-day), not just
                          NY -- see docs/research/RESEARCH_LEDGER.md HYP-059.

    IMPORTANT: sweep and void are each SUBSETS of the unfiltered FVG signal,
    and sweep_or_void is a superset of both. Do not run more than one
    liquidity variant on the same session concurrently with each other or
    with the unfiltered leg -- they would fire on the same underlying gap and
    multiply exposure on one event, not diversify. Exactly one FVG-family
    strategy per session, chosen for its best measured risk profile.
    """
    candidate_id = "XAU-092"
    session: tuple
    sl_atr_mult = 0.5
    tp_atr_mult = 2.5
    execute_immediately = True
    edge_trigger = False
    _min_bars = 250
    mode: str
    void_mult = 0.5

    def evaluate(self, m15_rates: np.ndarray, m5_rates: Optional[np.ndarray] = None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < self._min_bars:
            return None
        f = build_features(m15_rates)
        i = -2
        if not bool(session_mask(f["ist_hour"], self.session)[i]):
            return None

        hi = np.asarray(f["high"], dtype=float)
        lo = np.asarray(f["low"], dtype=float)
        cl = np.asarray(f["close"], dtype=float)
        h2, l2 = hi[i - 2], lo[i - 2]
        bull = h2 < lo[i]
        bear = l2 > hi[i]
        if not (bull or bear):
            return None

        from src.research.liquidity import liquidity_state, is_liquidity_void
        from src.research.market_study import atr as _atr_struct

        if self.mode == "baseline":
            pass  # unfiltered -- any 3-bar gap qualifies, same as FVGNYTight
        elif self.mode == "void":
            a200 = _atr_struct(m15_rates, 200)[i]
            bull_v, bear_v = is_liquidity_void(h2, l2, hi[i], lo[i], cl[i - 1], a200, self.void_mult)
            if (bull and not bull_v) or (bear and not bear_v):
                return None
        elif self.mode == "sweep":
            bs, ss = liquidity_state(hi, lo, cl)
            if (bull and not bs[i]) or (bear and not ss[i]):
                return None
        elif self.mode == "sweep_or_void":
            a200 = _atr_struct(m15_rates, 200)[i]
            bull_v, bear_v = is_liquidity_void(h2, l2, hi[i], lo[i], cl[i - 1], a200, self.void_mult)
            bs, ss = liquidity_state(hi, lo, cl)
            if bull and not (bull_v or bs[i]):
                return None
            if bear and not (bear_v or ss[i]):
                return None

        if bull:
            return Signal(direction=mt5.ORDER_TYPE_BUY, strategy_name=self.name,
                          magic=self.magic, is_buy=True)
        return Signal(direction=mt5.ORDER_TYPE_SELL, strategy_name=self.name,
                      magic=self.magic, is_buy=False)

    def check_pending_confirmation(self, m15_rates):
        return None

    def set_pending(self, signal, candle_time):
        pass


class FVGAsiaSweep(_LiquidityFilteredFVG):
    """FVG, ASIA session (02:30-11:30 IST), liquidity-sweep filtered.
    Holdout (2025-01-01 -> 2026-05-20): n=548, PF 1.279, net +$393,
    min balance $102.45 (never dipped below start), maxDD 42.5%,
    P(ruin) 17.4%. See HYP-059.

    BENCHED 2026-09-07, NOT deleted -- kept exactly as validated so this
    research isn't lost. Its session (02:30-11:30 IST) sits entirely outside
    the owner's 11:30-21:30 "no night trades" trading window
    (src/core/market_hours.py) -- the two don't overlap at all, so this leg
    would be silently blocked on every single signal if left in
    PORTFOLIO_V4 live (the exact silent-failure shape as HYP-042/045).
    Excluded from PORTFOLIO_V4 below for that reason, not because the
    strategy itself is bad -- it passed I.1 on its own. To reactivate: either
    widen the trading window to cover 02:30-11:30, or run this leg on a
    separate schedule/instance that isn't gated by market_hours.py, then
    re-validate the combined config before going live. See HYP-063."""
    name = "FVG_ASIA_SWEEP"
    magic = 3021
    session = (2.5, 11.5)
    mode = "sweep"


class FVGNYSweep(_LiquidityFilteredFVG):
    """FVG, NY session, liquidity-sweep filtered only.
    Holdout: n=397, PF 1.611, net +$704, min balance $114.40, maxDD 36.3%,
    P(ruin) 5.1%."""
    name = "FVG_NY_SWEEP"
    magic = 3023
    session = (17.5, 21.5)
    mode = "sweep"


class FVGNYVoid(_LiquidityFilteredFVG):
    """FVG, NY session, void (>0.5x ATR200) filtered only.
    Holdout: n=413, PF 1.480, net +$588, min balance $102.54, maxDD 38.0%,
    P(ruin) 8.6%."""
    name = "FVG_NY_VOID"
    magic = 3024
    session = (17.5, 21.5)
    mode = "void"
    void_mult = 0.5


class FVGNYSweepOrVoid(_LiquidityFilteredFVG):
    """FVG, NY session (17:30-21:30 IST), sweep-or-void filtered -- the best
    single result of the 2026-09-07 sweep. Holdout: n=609, PF 1.593,
    net +$1,046, min balance $104.20 (never dipped below start), maxDD 31.2%
    (vs 35.7% unfiltered), P(ruin) 5.6% (vs 8.6% unfiltered).

    NOTE: sweep_or_void is a strict superset of FVG_NY_SWEEP and FVG_NY_VOID,
    and FVG_NY_TIGHT (unfiltered) is a superset of all three -- the same
    underlying gap can fire under several of these legs at once. Kept as
    separate legs 2026-09-07 per explicit owner instruction, run through the
    real engine and caps rather than assumed; see HYP-060 for the measured
    combined effect before treating this as the live configuration."""
    name = "FVG_NY_SWEEP_OR_VOID"
    magic = 3022
    session = (17.5, 21.5)
    mode = "sweep_or_void"
    void_mult = 0.5


# Live set, trimmed 2026-09-08 to the legs that actually trade. FVGNYSweep
# and FVGNYVoid are strict subsets of FVGNYSweepOrVoid and always lose the
# engine's Highlander one-FVG-per-candle ranking to it -- both took zero
# trades in every backtest window (1-month, 3-month, 1-year), so they are
# removed. FVGNYTight (unfiltered) still trades: on a candle where only it
# qualifies (a 3-bar gap with no sweep/void story) it wins the ranking.
#
# FVGAsiaSweep excluded (HYP-063): net-negative over 1- and 3-month windows
# (its morning stop-outs burn the shared 6% daily breaker and starve the NY
# legs) even though it helps over a full year. Off until the $100-account
# early-months risk is past. See its own docstring to reactivate.
PORTFOLIO_V4 = [EMAStackLondonTight, FVGNYTight, FVGNYSweepOrVoid]
