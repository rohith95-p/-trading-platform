# Ultra Core — XAUUSD Trading System

Autonomous MetaTrader 5 bot for XAUUSD (gold) on a small fixed-0.01-lot
account, plus the research pipeline that built and validates it.

## 👉 Start with [`docs/REPO_GUIDE.md`](docs/REPO_GUIDE.md)

That is the authoritative map — what runs, where everything lives, the current
live config, how the loop works, and the open issues. This README is just the
front door.

## What runs live

```
python -m src.core.main_loop
```

Runs **`PORTFOLIO_V4`** (`src/strategies/portfolio_v4.py`) — two legs:

| Leg | Magic | Session IST | SL/TP ×ATR |
|---|---|---|---|
| `NVMR_TARGET_10` | 4003 | 17:30–21:30 | 0.4 / 1.5 |
| `LARS_LONDON` | 4004 | 11:30–15:30 | 0.4 / 1.2 |

The FVG strategies have been formally paused due to market regime shifts. This 2-leg portfolio is tuned specifically for the "$10/trade" goal on small accounts.

Hard rules, enforced in code (not guidance):

- **0.02 lots per order**, always — `ExecutionHandler.send_order`
- **0.04 lots total exposure**, max **2** concurrent positions
- **6% daily loss breaker** → no new entries until 00:00 IST
- **D1 EMA20 bias gate ON** → only trades with the daily trend
- **06:00–21:30 IST** trading window, nothing held over the weekend
- No trailing stops, no pyramiding (both backtested net-negative)

## Status (2026-09-24)

Demo account only. The massive "$10/trade" search concluded and successfully locked in `NVMR_TARGET_10` as the primary driver, supplemented by `LARS` for London volume. Monte Carlo stress tests proved 0.04 lots carries a 42% risk of ruin on a sub-$200 account; therefore, the fixed lot ceiling was strictly locked to **0.02 lots**.

**Settled this session (2026-09-24):**

- **Broker price feed restored.** `research/data/` M1/M5/M15/D1 had been
  overwritten with the Kaggle 22-yr retail set (zero-spread, ends Feb 2026).
  Backed up to `research/data/kaggle_22yr/`, refetched from MT5. Terminal only
  serves M1 back to 2026-05-29, M5 to 2025-04-11 — no clean pre-2026 M1 holdout
  on the current cache.
- **Daily trend gate stays.** A/B on the 2-leg set, broker M1, live config:
  `d1_ema20` PF 1.58 / +$875 / 22.7% DD over the year — beats `h4_structure`
  (1.50), `m15_structure` (1.44, blows up in the recent 3 months) and no-gate
  (more $ over the year, 89% DD recently). Every intraday-trend gate is
  dominated. → `research/validation/intraday_trend_gate_ab.json`
- **Structural take-profit — rejected.** External claim (snap TP to swing
  pivots → FVG_NY_TIGHT PF 4.3, $100→$12k/yr) was vectorised-backtest
  lookahead. Real engine, 8/8 (leg × window) cells: win rate up ~1 pt, PF
  flat-to-down, net −2% to −40%. `structural_tp` flag added to `EngineConfig`
  (default off, engine-only A/B tool). →
  `research/validation/structural_tp_ab.json`

## Pending owner decisions

Kept in sync with REPO_GUIDE §6. Nothing here is actioned without a call.

1. **EMASTACK_LONDON_TIGHT — keep or cut?** In the live list by the 2026-09-09
   decision. Solo 1-year backtest PF 0.81 (−$153, account blown). It also
   drags the portfolio: 3-leg year PF 1.20 / 56% DD vs 2-leg PF 1.58 / 22.7%
   DD; last 3 months 3-leg −$85 / 93% DD vs 2-leg +$41 / 50%. Cutting it
   reverts `PORTFOLIO_V4` to `[FVGNYTight, FVGNYSweepOrVoid]` and needs the
   config fingerprint re-recorded.
2. **FVGNYTight — keep, or run SweepOrVoid solo?** FVGNYTight-alone produces
   the *exact* same trades as the 2-leg combo (SOV is a relabelled subset of
   the same gap detector). SOV *alone* beats the pair on the recent window —
   PF 1.31 / +$72 / 39% DD vs 1.10 / +$41 / 50%. Dropping TIGHT → a 1-leg
   portfolio. Needs a clean pre-2026 M1 holdout to confirm before acting.
3. **The operating rulebook** (REAL_MONEY_READINESS Part II) — position floor,
   early-stage loss caps tighter than 6%, paper→live promotion path. Still
   unwritten. This is the main thing blocking real money.
4. **`risk_rules.py` streak breakers — flip `ENFORCE = True`?** Wired and
   tracking real state in shadow since 2026-09-09. Enforcing needs the
   laddered-off config backtested + recorded first.
5. **Real-money go-live date.** Target was 2026-09-30; blocked by both the I.1
   drawdown failure (50.68% > 45% bar) and the unwritten rulebook. Slip the
   date, or go with tighter caps and accept the drawdown risk?
6. **Repo housekeeping** (REPO_GUIDE §7) — archive ~20 superseded
   `scripts/phase*/tier2*` runners, prune the 43 MB `research/runs/`, rmdir 7
   empty `src/` dirs, fold `reports/` into `docs/research/`. Low stakes.

## Fresh clone

```
python -m scripts.fetch_history          # download price bars (gitignored)
python -m scripts.validation.part1_suite holdout   # the OOS edge test
```
