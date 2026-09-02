# Daily Battle Plan (XAUUSD)
*Date: 2026-09-03 — written 00:30 IST, after the 09-02 session*

> This plan describes what the **bot actually runs** (`portfolio_v4` via
> `main_loop.py`). Earlier revisions listed discretionary setups ("Fib golden
> pocket", "Strategy #16") that no code implements. Those are removed — a plan
> the system cannot execute is not a plan.

## 1. Market Condition (see DAILY_MARKET_ANALYSIS.md for the full read)

- **Macro:** bearish for gold — DXY +0.48%, silver −5.83% (falling faster than
  gold), equities soft. Nothing has turned.
- **Price structure:** **conflicting.** 09-02 printed a bullish reversal candle
  — new low 4282.30, closed 4374.54 in the upper third of a 115-point range.
- **Volatility:** expanding. Daily ranges 76 → 139 → 115 vs ~88 baseline.
- **THE NUMBER TO WATCH: 4436** (D1 EMA20). Price is $62 below it. A close above
  flips the live D1 gate BEARISH → BULLISH: the bot stops shorting and starts
  buying. Within one session's range. **The short bias is provisional.**

## 2. What Actually Trades Tomorrow

| Leg | Session (IST) | SL / TP (×ATR) | Notes |
|---|---|---|---|
| SQUEEZE_ASIA | 02:30–11:30 | 2.0 / 4.0 | Widest stop, most robust to noise |
| EMASTACK_LONDON_TIGHT | 11:30–15:30 | 0.75 / 3.0 | Carried 09-02's profit |
| FVG_NY_TIGHT | 17:30–21:30 | 0.5 / 2.5 | Tightest stop — see risk note |
| RANGEREJECTION_NY_TIGHT | 17:30–21:30 | 0.75 / 2.25 | Smallest sample (n=26) |

Direction is decided by the D1 gate, not by discretion. While price < 4436:
**shorts only.** Longs are detected and logged as blocked.

## 3. Hard Risk Rules (enforced in code, not guidance)

- **0.01 lots, every order.** `FIXED_LOT_SIZE`, enforced in
  `ExecutionHandler.send_order` — the chokepoint. No dynamic sizing.
- **0.02 lots total exposure**, max 2 concurrent positions (`MAX_TOTAL_VOLUME`).
- **6% daily loss breaker** → halts new entries until midnight IST.
- Real risk per trade at 0.01 lots is **$5–9**, i.e. **4–6% of a $136 account**.
  This exceeds the "1–2% per trade" convention. It is a consequence of the
  broker's 0.01 lot floor, not a choice, and it is why the daily breaker can be
  hit by a single bad trade. Do not add a second simultaneous leg casually.

## 4. ✅ DONE — config corrected 2026-09-03 00:25 IST

`scripts/live_config_ab.py` (100-day backtest, all four legs on one shared
account) found the then-live configuration **net-negative and near
account-fatal**:

| Config | PF | Net | Max DD |
|---|---|---|---|
| **live now** (2 pos, trail ON, pyramid ON) | **0.592** | **−$93.59** | **89.0%** |
| best (2 pos, trail OFF, pyramid OFF) | 1.478 | +$843.43 | 21.4% |
| validated (1 pos, trail OFF, pyramid OFF) | 1.579 | +$714.18 | 22.0% |

**Trailing stops are the defect.** They raise win rate (29.6% → 52.9%) while
collapsing profit factor (1.579 → 0.592), because these legs depend on rare
large winners and the trail (activate 0.7×ATR, follow 0.3×ATR) cuts them at
roughly half an ATR. Live confirmation 09-02 22:22: FVG #2 trailed out at
+$4.70 with its target still $18 away.

**Applied:** `ENABLE_TRAILING = False` and `ENABLE_PYRAMIDING = False` added as
module flags in `main_loop.py`, guarding the trailing branch of
`_manage_open_positions()` and the `_check_pyramiding()` call. Positions now run
to their fixed SL/TP, as validated. `max_concurrent = 2` **kept** — that variant
tested best. Bot restarted 00:25 IST; startup banner now prints the live config.

**Incident during the change:** the first restart logged `Macro rule: strict
SHORT stops enabled`. The warning block added to `DAILY_MARKET_ANALYSIS.md`
spelled out the two trigger phrases verbatim in order to document them, and
`_load_macro_rules()` grep-matched its own documentation — silently switching
every SHORT to a hardcoded 1.0x/2.0x ATR stop. Fixed by referencing the source
file instead of quoting the strings, and restarting. **Lesson: that grep cannot
distinguish documentation from a directive.** A future hardening would move the
macro rule to an explicit key (e.g. a YAML front-matter flag) rather than
free-text matching.

## 5. Session Review — 2026-09-02

Balance $105.74 → **$135.76** (+$30.02, 6 trades).

| Time | Lot | P/L | Leg | Read |
|---|---|---|---|---|
| 14:58 | 0.03 | +$15.74 | EMASTACK | pre-fix oversize |
| 14:58 | 0.02 | +$22.32 | EMASTACK | pre-fix oversize |
| 15:46 | 0.03 | +$1.65 | EMASTACK | pre-fix oversize |
| 19:51 | 0.01 | −$8.68 | RANGEREJECTION | stopped by the spike it faded |
| 22:22 | 0.01 | +$4.70 | FVG | **trailed out early** |
| 23:14 | 0.01 | −$5.71 | FVG | stopped in chop |

**The pattern that matters:** the bot made money in the *trending* half of the
day (London, price falling 4452 → 4301) and lost money in the *reversal* half
(NY, price bouncing 4282 → 4397). All three NY shorts were directionally
correct — price fell after each entry — but two were stopped by noise first.

The three post-fix 0.01-lot trades netted **−$9.69**. That is the honest
baseline for the fixed-size system. The day's +$30 came entirely from the three
oversized pre-fix trades, which happened to win. Do not read 09-02 as evidence
the system is profitable.

## 6. Tomorrow's Watch List

1. **4436** — D1 EMA20. Close above = bias flips to longs. Highest-impact level.
2. **4282.30** — 09-02 low. Break below re-confirms the downtrend and validates
   continued shorts.
3. **Oil** (+8–9% in 5 days). A sustained energy spike is an inflation impulse
   that historically supports gold. Currently overridden by dollar strength; if
   DXY stalls, this flips the whole thesis.
4. **NY chop risk.** `phase3_worker.py` measured NY's median adverse excursion
   at **$8.69**. FVG_NY's stop is 0.5×ATR ≈ **$5.50** — below the session's own
   noise floor. Expect noise-stops there; it is a known structural weakness, not
   a malfunction.
