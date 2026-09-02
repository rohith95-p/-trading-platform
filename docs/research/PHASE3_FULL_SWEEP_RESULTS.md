# Phase 3 — Full Session Sweep Results (2026-09-01)

Comprehensive tier-2 M1-fidelity sweep across all 4 IST sessions (Asia,
London, NY, Late), 8 entry-rule families, multiple stop/target combinations.
297 total configurations tested (some duplicated across relaunches after a
network interruption — see `all_results.txt` for the raw deduplicated data).

**Window**: 2026-05-21 → 2026-08-29 (~100 days), the only period with true
M1 sub-bar fidelity data. All numbers below are real backtest results using
the actual `RiskManager`, real spread costs, the real 6% daily-loss breaker,
starting from $105.74 at fixed 0.01 lots.

Raw data: `research/runs/20260901_phase3_full_sweep/all_results.txt`

---

## Best single-strategy result per session

| Session | Strategy | Config | Trades | WR | PF | Net$ | MinBal | Notes |
|---|---|---|---:|---:|---:|---:|---:|---|
| **ASIA** | squeeze_break | SL4.0/TP8.0 (~$29 risk) | 38 | 50.0% | 1.722 | **$432** | $80 | Best net$ in Asia; avg win $54 |
| **ASIA** | squeeze_break | SL2.0/TP4.0 (~$15 risk) | 49 | 46.9% | 1.741 | $285 | $106 | Safer, never dipped below start |
| **LONDON** | ema_stack | SL2.0/TP3.0 | 50 | 50.0% | 1.48 | $197 | $106 | Best sample+safety combo |
| **LONDON** | ema_stack | SL0.75/TP3.0 (~$6 risk) | 70 | 22.9% | 1.286 | $93 | $95 | Fits ≤$7-risk criterion, avg win $26 |
| **NY** | fvg | SL0.5/TP2.5 (~$5 risk) | 110 | 23.6% | **1.661** | **$269** | $106 | Best NY result; avg win $26, never dipped below start |
| **NY** | range_rejection | SL0.75/TP2.25 (~$7 risk) | 26 | 34.6% | 1.726 | $83 | $84 | Fits tight-risk criterion, smaller sample |
| **LATE** | hhll_structure | SL0.75/TP3.0 (~$7 risk) | 57 | 26.3% | 1.467 | $141 | $85 | 4.11:1 reward:risk, avg win $29.51 |

---

## Best combined portfolio (real, verified)

Four configurations tested combining independently-validated strategies onto
ONE shared account with the real daily-loss breaker, replayed chronologically
(not a naive sum of isolated runs):

| Version | Legs | Net$ | MinBal | MaxDD | PF | Breaches |
|---|---|---:|---:|---:|---:|---:|
| v1 (original) | squeeze_ASIA($15) + emastack_LONDON + fvg_NY | $569 | $106 | 22.1% | 1.437 | 9/64 days |
| v2 (bigger Asia risk) | squeeze_ASIA($29) + emastack_LONDON + fvg_NY | $524 | $83 | 30.3% | 1.400 | 22/64 days |
| v3 (tight-risk only, no Asia) | emastack_LONDON(tight) + fvg_NY(tight) + rangerejection_NY(tight) | $383 | $105 | 29.1% | 1.455 | 9/66 days |
| **v4 (full, tight London/NY + Asia)** | squeeze_ASIA($15) + emastack_LONDON(tight) + fvg_NY(tight) + rangerejection_NY(tight) | **$703** | **$106** | 35.0% | **1.512** | 11/69 days |

**v4 is the best validated result of the entire research effort**: ≈**$7.03/day**,
never dropped below starting balance, highest PF of any combined test. Still
short of the $20/day goal by roughly 2.85×.

### Key lesson from the portfolio tests (HYP-036/037/038 in the ledger)

1. Bigger risk in one leg doesn't help the combined portfolio even when it
   helps that leg alone — it trips the *shared* daily-loss breaker more
   often, blocking otherwise-good trades in other legs (v2's 22 breach days
   vs v1's 9, despite the isolated leg being "better").
2. Two legs in the *same* session (v3's two NY strategies) reduce
   diversification even if each looks fine alone — Asia's independence from
   London/NY's day-to-day variance is what made v1 and v4 stronger than v3.
3. A naive single-shared-config multi-strategy backtest run (one TP/SL
   forced onto every leg) materially understates a real portfolio — `ema_stack`
   LONDON *lost* money under a forced compromise config despite being
   profitable at its own real parameters. Use the chronological-replay method
   (`scripts/portfolio_merge_honest.py` and variants) instead.

---

## Trailing stop — reconfirmed harmful, 3-for-3

Direct A/B tests (trailing on vs off) on three different session/rule
combinations, all at today's tighter stop distances (not the old wide-stop
system HYP-005/018 originally tested):

| Strategy | No Trail PF | No Trail Net$ | Trail PF | Trail Net$ |
|---|---:|---:|---:|---:|
| squeeze_break ASIA | 1.741 | +$285 | 0.664 | **-$87** |
| ema_stack LONDON | 1.396 | +$159 | 1.019 | +$6 |
| fvg ASIA | 1.287 | +$201 | 0.957 | **-$21** |

Trailing consistently raises win rate (more "wins," each tiny) while
collapsing average captured profit toward zero or negative — it exits real
winners on the pullback before the move completes. **Confirmed, not a
one-off** (ledger HYP-034).

---

## Time-of-day ATR correction — hypothesis rejected as originally stated

Wired `use_time_of_day_atr` into the engine (opt-in, doesn't touch
`src/core/risk_manager.py`). Tested expecting it to *narrow* stops in
LATE/Asia per Phase 2's "flat ATR overstates" claim — it did the opposite
(widened the stop, $14.02→$17.10 avg on `fvg` LATE). Root cause: Phase 2's
comparison mixed two different statistics (backward ATR vs forward realized
MAE). Marginal PF improvement observed (1.002→1.059) but for the
already-known "wider stop = fewer shakeouts" reason, not the claimed one.
See ledger HYP-033.

---

## What's still open

1. **v4 portfolio needs holdout validation** — it's built entirely on the
   single ~100-day M1-covered window. No out-of-sample check exists yet.
2. **Gap to $20/day**: v4 gets to ~$7.03/day. Closing the remaining ~2.85×
   gap needs either bigger account/position size (structural, not a strategy
   question) or a materially better edge than anything found so far.
3. **3 candidates in the v2 (`candidates_v2.py`) library still produce zero
   trades** despite valid underlying signals — root cause not fully
   identified (ruled out: spread gate correlation, `atr_pct` NaN handling).
   Does not block anything found tonight; parked as a known open item.
4. **Engine doesn't support per-strategy TP/SL in one `run()` call** — the
   chronological-replay workaround (`portfolio_merge_*.py`) works but a real
   fix (`Dict[str, EngineConfig]` keyed by strategy) would let this be tested
   natively instead of via a manual replay script.

---

*Compiled 2026-09-01. All figures cite either `research/runs/` directories
or the specific ad hoc script named alongside them. Ledger entries: HYP-025
through HYP-038.*
