# Ultra Core — XAUUSD Trading System

Autonomous MetaTrader 5 bot for XAUUSD (gold), plus the research pipeline that
built and validates it. Target: a survivable system for a ~$100 account at fixed
0.01-lot sizing.

## What runs live

`python -m src.core.main_loop` — the bot. It runs **portfolio_v4**: four
session-specialist strategies sharing one account.

| Leg | Session (IST) | SL / TP (×ATR) |
|---|---|---|
| SQUEEZE_ASIA | 02:30–11:30 | 2.0 / 4.0 |
| EMASTACK_LONDON_TIGHT | 11:30–15:30 | 0.75 / 3.0 |
| FVG_NY_TIGHT | 17:30–21:30 | 0.5 / 2.5 |
| RANGEREJECTION_NY_TIGHT | 17:30–21:30 | 0.75 / 2.25 |

Hard rules, enforced in code (`ExecutionHandler.send_order`), not guidance:
- **0.01 lots per order**, always
- **0.02 lots total exposure**, max 2 concurrent positions
- **6% daily loss breaker** → halts new entries until midnight IST
- **D1 EMA20 bias gate** → only trades in the direction of the daily trend
- No trailing stops, no pyramiding (both backtested net-negative — see
  `docs/plans/DAILY_BATTLE_PLAN.md`)

## Layout

```
src/
  core/          main_loop, data_fetcher, execution_handler, risk_manager  ← live
  strategies/    portfolio_v4 (live) + base_strategy; others are RESEARCH ONLY
    archive/     strategies that scored below the random-entry control
  research/      candidate library, market study, feature engineering
  backtesting/   execution-realistic backtest engine + data loader

scripts/         research + backtest runners (run as `python -m scripts.<name>`)
  oneoff/        superseded one-shot utilities, kept for reference

research/
  data/          MT5 price bars as .npy (gitignored — regenerate with
                 `python -m scripts.fetch_history`)
  runs/          backtest run outputs (manifests/summaries tracked; per-trade
                 dumps gitignored)
  candidates/, market/, screen/   research artifacts

docs/
  plans/         DAILY_MARKET_ANALYSIS.md, DAILY_BATTLE_PLAN.md, DAILY_GOALS.md
  research/      RESEARCH_LEDGER.md (hypotheses), STRATEGY_REGISTRY.md,
                 PHASE3_FULL_SWEEP_RESULTS.md, and the audit trail
  trade_logs/    LIVE_TRADE_HISTORY.md (closed deals pulled from MT5)

reports/         longer-form analysis write-ups
.agents/         AI skills (macro prep, trade auditor) and rules
config/          versioned runtime policy + production validation profile
```

## Key documents

- **`docs/plans/DAILY_BATTLE_PLAN.md`** — current market read, live config, and
  the session review. Start here.
- **`docs/plans/DAILY_MARKET_ANALYSIS.md`** — cross-asset macro. **Read live by
  `RiskManager._load_macro_rules()`** — see the warning header in that file.
- **`docs/research/RESEARCH_LEDGER.md`** — every hypothesis tested (HYP-001+).
- **`docs/research/STRATEGY_REGISTRY.md`** — every strategy, its grade, why.
- **`docs/research/PHASE3_FULL_SWEEP_RESULTS.md`** — how portfolio_v4 was chosen.
- **`docs/operations/INCIDENT_RUNBOOK.md`** — incident response and restart safety.
- **`docs/operations/CHANGE_MANAGEMENT.md`** — release gates and rollback discipline.

## Production validation

Run deterministic promotion checks (holdout, walk-forward, perturbation + gates):

`python -m scripts.production_validation --profile config/validation_profile.json`

## Daily routine

1. **Morning:** confirm the bot is running (`python -m src.core.main_loop`).
2. **During the day:** it trades its four legs autonomously within the hard rules.
3. **Evening:** ask for "tomorrow's plan" — regenerates the macro analysis and
   battle plan from live data (gold, silver, DXY, yields, oil, VIX).
4. **Trade log:** `docs/trade_logs/LIVE_TRADE_HISTORY.md` is updated from MT5.

## Status (2026-09-03)

portfolio_v4 is live on a **demo** account, grade B — validated on a single
~100-day window (PF ~1.5), no holdout yet. Real-money target: 2026-09-30. The
operating rulebook (position floor, tighter early-stage loss caps, paper→live
promotion path) is still unwritten.
