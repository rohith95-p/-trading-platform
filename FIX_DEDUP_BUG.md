# 🐛 DEDUP BUG FOUND - Critical Issue

## Problem

**Bot is stuck thinking it already traded candles from 2+ hours ago!**

### What's Happening:
1. Bot trades at 6:15 PM on candle `1791376200`
2. Stores in `last_fired_candle[strategy_name] = 1791376200`
3. **NEVER CLEARS IT**
4. Hours later at 8:45 PM, strategies still see same old candles
5. Bot says "already acted on this candle" when it was 2.5 hours ago!

### Evidence:
```
logs/loop_state.json shows:
"TREND_PULLBACK_V5": 1791376200  (6:15 PM)
"FVG_NY_TIGHT_V5": 1791376200    (6:15 PM)

Current time: 8:45 PM
Candle age: 2.5+ hours
```

**Strategies keep generating signals for NEW candles but bot thinks they're the same!**

---

## Root Cause

`last_fired_candle` dict in `main_loop.py` line 206:
- Initialized once at startup
- Updated when trade executes (line 511)
- **NEVER CLEARED** - lasts forever!

The dedup is meant to prevent firing TWICE on the SAME 15-minute candle.
But it's preventing trading on ANY candle for the rest of the session!

---

## The Fix

**Option 1: Clear old entries (SAFEST)**
After each loop, clear entries older than 30 minutes:

```python
# After line 522 (after Highlander section)
current_time = int(time.time())
for strategy_name in list(last_fired_candle.keys()):
    candle_ts = last_fired_candle[strategy_name]
    if candle_ts and (current_time - candle_ts) > 1800:  # 30 min
        last_fired_candle[strategy_name] = None
```

**Option 2: Only check within same candle window (CORRECT)**
The candle only lasts 15 minutes. After that, clear it:

```python
# Line 460 - change the dedup check:
if last_fired_candle.get(strategy.name) == signal_candle:
    # Already acted on THIS EXACT candle (within 15 min)
    trade_log.signal(...)
    continue
```

This is already correct! The bug is that `signal_candle` keeps returning the SAME value for hours.

**Wait... checking signal_candle calculation...**

---

## ACTUAL BUG FOUND

Line 442: `signal_candle = int(m15_rates[-2]["time"])`

This reads the LAST COMPLETED M15 candle.

**But if market is choppy and price isn't moving, strategies keep seeing the SAME candle at [-2]!**

This is actually CORRECT behavior - strategies shouldn't fire on the same candle twice.

**The real issue:** Strategies are generating signals for OLD candles that were already traded.

---

## Why This Happens

1. Strategy sees candle at 6:00 PM → trades
2. Market chops sideways for 2 hours
3. M15 [-2] keeps showing 6:00 PM candle (or near it)
4. Strategy STILL thinks that old setup is valid
5. Bot correctly blocks it (already traded)

**The strategy logic should expire old signals!**

---

## The REAL Fix

**Strategies need to check candle age:**

```python
# In each strategy's evaluate() method:
current_time = int(time.time())
signal_candle_time = int(m15_rates[-2]["time"])

# If signal is older than 15 minutes, it's stale
if (current_time - signal_candle_time) > 900:  # 15 min
    return None  # Signal expired
```

OR

**Bot should only fire on FRESH candles** (just completed in last minute):

```python
# Line 442, after signal_candle calculation:
current_time = int(time.time())
candle_age_seconds = current_time - signal_candle

if candle_age_seconds > 120:  # If candle closed >2 min ago, skip signals
    log.info(f"Skipping stale signals (candle {candle_age_seconds}s old)")
    _manage_open_positions(fetcher, risk, executor)
    _time.sleep(LOOP_INTERVAL)
    continue
```

---

## Quick Fix (NOW)

**Clear the dedup dict to unblock trading:**

```bash
# Stop bot
# Delete: logs/loop_state.json
# Restart bot
```

This will clear the memory and allow fresh trades.

---

## Status

- **Bug confirmed:** Dedup working correctly, but blocking stale signals
- **Root cause:** Strategies keep seeing old candles as valid
- **Impact:** No trades for 2.5+ hours despite bot running
- **Quick fix:** Restart bot to clear state
- **Proper fix:** Add candle age check to strategy evaluation

---

**Generated:** 2026-10-07 20:50 IST
