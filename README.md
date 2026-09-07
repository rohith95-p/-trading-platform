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

Runs **`PORTFOLIO_V4`** (`src/strategies/portfolio_v4.py`) — currently two
NY-session fair-value-gap legs on candidate `XAU-092`:

| Leg | Magic | Session IST | SL/TP ×ATR |
|---|---|---|---|
| `FVG_NY_SWEEP_OR_VOID` | 3022 | 17:30–21:30 | 0.5 / 2.5 |
| `FVG_NY_TIGHT` | 3013 | 17:30–21:30 | 0.5 / 2.5 |

Hard rules, enforced in code (not guidance):

- **0.01 lots per order**, always — `ExecutionHandler.send_order`
- **0.02 lots total exposure**, max **2** concurrent positions
- **6% daily loss breaker** → no new entries until 00:00 IST
- **D1 EMA20 bias gate ON** → only trades with the daily trend
- **06:00–21:30 IST** trading window, nothing held over the weekend
- No trailing stops, no pyramiding (both backtested net-negative)

## Status (2026-09-08)

Demo account only (Exness-MT5Trial11 #198874999). The FVG-liquidity rework
(RESEARCH_LEDGER HYP-059+) recovered a measurable edge after the original
4-leg portfolio was declared dead in September; the out-of-sample holdout
(2025-01 → 2026-05) passes at PF ~1.26. Two things still block real money: the
config-integrity gate needs the current config recorded (see REPO_GUIDE §6),
and the operating rulebook (sizing floor, early loss caps, paper→live path) is
unwritten.

## Fresh clone

```
python -m scripts.fetch_history          # download price bars (gitignored)
python -m scripts.validation.part1_suite holdout   # the OOS edge test
```
