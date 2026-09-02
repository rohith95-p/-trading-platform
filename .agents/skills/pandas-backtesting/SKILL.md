---
name: pandas-backtesting
description: How to backtest a strategy for Ultra Core. Use the project's execution-realistic engine, not a throwaway yfinance loop.
---

# Backtesting Workflow

**Do not write a fresh yfinance + pandas backtester.** The project has an
execution-realistic engine that reproduces what `main_loop` would actually have
done, on the same broker M1 data the bot trades. A yfinance `GC=F` loop gives
different prices, different spreads, and results that will not match live.

## Use the engine

```python
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS

bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
cfg = EngineConfig(
    symbol="XAUUSDm", starting_balance=105.74,
    sizing_mode="fixed", fixed_lots=0.01,
    max_concurrent=2, max_same_direction=2,
    enable_trailing=False, enable_pyramiding=False,
    daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
    enable_d1_bias_gate=True,
)
eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
res = eng.run([Strategy()], start_ts=..., end_ts=...)
```

The config must mirror the **live** rules (fixed 0.01, 0.02 cap, no trail, no
pyramid, 6% breaker, D1 gate) or the result does not describe the real system.

## Worked examples in `scripts/`

- `scripts/live_config_ab.py` — all 4 legs on one shared account, config A/B
- `scripts/d1_gate_ab.py` — D1 bias gate on vs off
- `scripts/luxalgo_fvg_ab.py` — single-leg entry-rule variants
- `scripts/portfolio_merge_v4_full.py` — how portfolio_v4 was validated

## Data

M1/M5/M15/H1/H4/D1 `.npy` bars live in `research/data/` (gitignored).
Regenerate with `python -m scripts.fetch_history`. The window with true M1 data
is **2026-05-21 → 2026-08-29** (~100 days) — the only validation window, no
holdout yet.

## Reporting

Always report: trades, win rate, **profit factor**, net $, max drawdown %, and
minimum balance. For a ~$100 account, translate to real dollars at 0.01 lots —
R-multiples and synthetic PF have repeatedly hidden near-ruin events.
