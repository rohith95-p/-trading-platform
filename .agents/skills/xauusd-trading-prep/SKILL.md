---
name: xauusd-trading-prep
description: The "tomorrow's plan" workflow for the Ultra Core XAUUSD bot — regenerate the daily macro analysis and battle plan from live data, matched to what the bot actually runs.
---

# XAUUSD Trading Preparation

## When to activate

- User asks for "tomorrow's plan" / a daily plan
- User asks to analyse Gold conditions or review the day's trades

## The "Tomorrow's Plan" workflow

**1. Pull cross-asset data.** Prefer the MT5 broker feed (matches what the bot
trades) over yfinance. Available Exness symbols: `XAUUSDm`, `XAGUSDm`, `DXYm`,
`USOILm`, `UKOILm`, `EURUSDm`, `USDJPYm`, `US500_x100m`, `USTEC_x100m`. Take
5-day D1 changes. yfinance is a fallback only (`GC=F`, `SI=F`, `DX-Y.NYB`,
`^TNX`, `CL=F`, `^VIX`).

**2. Regenerate `docs/plans/DAILY_MARKET_ANALYSIS.md`:**
- 5-day cross-asset table with the implication for gold
- Gold D1 price structure (recent OHLC, distance from the D1 EMA20)
- **The D1 EMA20 level** — this is the number that flips the live bias gate.
  State how far price is from it and whether that's within a session's range.
- ⚠️ **Never quote the two macro-rule trigger phrases in this file.**
  `RiskManager._load_macro_rules()` greps it and will switch every SHORT to a
  hardcoded 1.0x/2.0x ATR stop if both appear. Reference `risk_manager.py`
  instead. Keep the warning header that's already in the file.

**3. Regenerate `docs/plans/DAILY_BATTLE_PLAN.md`:**
- Market condition (macro vs price structure — note when they disagree)
- The 4 live legs, their sessions, their SL/TP (from `portfolio_v4.py`)
- Direction: decided by the D1 gate, not discretion. While price < D1 EMA20:
  shorts only. Longs are detected and logged as blocked.
- The hard risk rules (see below)
- Session review of the day's closed trades — read them against price action,
  and separate "was the direction right" from "was the size/exit right"
- A watch list of specific price levels

## What the bot actually runs

`portfolio_v4` via `python -m src.core.main_loop`:

| Leg | Session (IST) | SL / TP (×ATR) |
|---|---|---|
| SQUEEZE_ASIA | 02:30–11:30 | 2.0 / 4.0 |
| EMASTACK_LONDON_TIGHT | 11:30–15:30 | 0.75 / 3.0 |
| FVG_NY_TIGHT | 17:30–21:30 | 0.5 / 2.5 |
| RANGEREJECTION_NY_TIGHT | 17:30–21:30 | 0.75 / 2.25 |

There is no numbered strategy catalog ("Strategy #16" etc.) — that was
pre-research. Strategy candidates live in `src/research/candidates.py` (XAU-nnn
ids); the grades are in `docs/research/STRATEGY_REGISTRY.md`.

## Hard risk rules (enforced in code)

- 0.01 lots per order, always (`FIXED_LOT_SIZE`)
- 0.02 lots total exposure, max 2 concurrent (`MAX_TOTAL_VOLUME`)
- 6% daily loss breaker (realised + floating) → halts new entries to midnight IST
- No trailing stops, no pyramiding (backtested net-negative)
- D1 EMA20 bias gate → trade only with the daily trend

At 0.01 lots with these tight stops, real risk per trade is ~$5–9, i.e. ~4–6%
of a ~$140 account. That is above the textbook 1–2% and is a consequence of the
broker's 0.01 lot floor, not a choice. It is why one bad trade can approach the
daily breaker. This is the accepted trade-off — do not "fix" it by widening
stops or switching to a cent account without the owner asking.

## Account context

Demo account, ~$105 start, real-money target 2026-09-30. Framing must be in
real dollars at 0.01 lots. See agent memory [[xauusd-100-account-goal]] and
[[rohith-2-live-hardening]].
