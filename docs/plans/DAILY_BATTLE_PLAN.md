# DAILY BATTLE PLAN — 2026-09-30 (IST)

_Generated: 2026-09-30 11:19 IST | Account: REAL | Balance: $163.24_

---

## ⚡ ACCOUNT STATUS

| Field | Value |
|---|---|
| Balance | **$163.24** |
| Equity | $163.24 |
| Free Margin | $163.24 |
| Open Positions | **0** (flat) |
| Daily Loss Cap | **6%** (~$9.79) |
| Hard Kill Threshold | N/A (ENFORCE=False) |

---

## 🎯 MARKET CONDITION & BIAS

**D1 EMA20 ≈ 4,266 | Current Price ~4,175 → 91 pts BELOW**

> **⚠️ BIAS GATE = SHORT ONLY**
> Price is ~91 points below D1 EMA20 — well inside a bearish regime.
> ALL long signals must be detected, BLOCKED, and logged.
> This is enforced in code via the D1 bias gate. Verify it's working.

**Macro vs Price Structure:**
- Macro: DXY rising (+0.75% 5-day), EUR falling → USD bid ✅ bearish for gold
- Price structure: Sep 28 crash day (-127 pts), Sep 29–30 dead-cat bounce ~4175
- **Verdict: Both AGREE — bear trend, short bias.** No conflict today.

**Today's theme:** Quarter-end (Sep 30). Expect **elevated volatility** and possible stop-hunts in both directions. Month-end rebalancing flows can spike gold briefly. Do not chase moves; wait for clean FVG/EMA stack signals on shorts.

---

## 📐 LIVE LEGS & SESSION SCHEDULE (IST today)

| Leg | IST Window | SL × ATR | TP × ATR | H1 ATR ~16pt | SL pts | TP pts |
|---|---|---|---|---|---|---|
| SQUEEZE_ASIA | 02:30–11:30 ✅ *done* | 2.0 | 4.0 | 16 | ~32 | ~64 |
| EMASTACK_LONDON_TIGHT | **11:30–15:30** ← NOW | 0.75 | 3.0 | 16 | ~12 | ~48 |
| FVG_NY_TIGHT | 17:30–21:30 | 0.5 | 2.5 | 16 | ~8 | ~40 |
| RANGEREJECTION_NY_TIGHT | 17:30–21:30 | 0.75 | 2.25 | 16 | ~12 | ~36 |

**At 0.01 lots, 1pt = $0.10 → each SL = ~$0.80–3.20 real risk**

---

## 🔑 KEY PRICE LEVELS TO WATCH

| Level | Type | Notes |
|---|---|---|
| **4,200** | 🔴 Resistance | Round number + Sep 28 opening area |
| **4,186** | 🔴 Resistance | Sep 29 recovery high — supply zone |
| **4,175** | ⚪ Current | Now |
| **4,155–4,165** | 🔴 Weak resistance | Sep 28 8–11 UTC consolidation zone |
| **4,133** | 🟢 Support | Sep 28 D1 close |
| **4,111** | 🟢 Key support | Sep 28 intraday low — structure |

**Short setups to watch:**
1. Rejection at 4,186–4,200 during London session → short with tight SL above 4,200
2. Any FVG fill into 4,175–4,186 area during NY open → short entry

**Long signals:** **BLOCKED** per D1 bias gate. Log them.

---

## 📋 SEP 28 TRADE REVIEW (Yesterday's session)

> Full P&L detail in [`LIVE_TRADE_HISTORY.md`](../trade_logs/LIVE_TRADE_HISTORY.md)

**8 trades, all LONG, all stopped out. Total: -$7.90**

### Was the direction right?
**No.** Gold dropped 127 points on Sep 28. The market was in a strong intraday downtrend from open. Every entry added longs into a waterfall sell-off.

### Was the D1 gate respected?
**Unclear.** The EMA20 gate should have blocked all longs (price was already below ~4260 pre-crash). Either:
- (a) The D1 EMA20 wasn't computed correctly on Sep 28, or
- (b) The gate was computed relative to a different time (e.g., last close = Sep 27 = 4260, EMA20 might have still been above 4260 as of market open), which could have allowed 1 long before the crash kicked in

### Was the size/exit right?
The SL sizes were appropriate (0.8–1.1 per trade). The problem was direction, not exits. The exits (SL hits) worked correctly — they cut losses fast (< 1 pt adverse move each).

### Action items:
- [ ] Verify the D1 bias gate computation in `main_loop.py` — ensure EMA20 is calculated from the *closed* D1 bar, not the live bar
- [ ] Add a circuit breaker log line showing D1 EMA20 value and decision at each session open
- [ ] Review why 8 sequential losing LONGS were allowed (should have hit the 5-loss circuit breaker after trade #5)

---

## 🛡️ HARD RISK RULES FOR TODAY

| Rule | Value | Status |
|---|---|---|
| Lot size | 0.01 | ✅ Fixed |
| Max concurrent positions | 2 (balance <$200 → ladder) | ✅ |
| Max total volume | 0.02 | ✅ |
| Daily loss cap | 6% = ~$9.79 | ✅ Fresh (no P&L today yet) |
| D1 bias gate | SHORT ONLY | ⚠️ Must verify in code |
| Consecutive loss pause | 3 losses → 4h pause | ✅ |
| Day stop circuit breaker | 5 losses → done for day | ✅ |

**Bot command:** `python -m src.core.main_loop`

---

## 🕰️ TONIGHT'S WATCH LIST

- **17:30 IST** — NY legs activate. Monitor for short setups below 4,186
- **Quarter-end caution** — Expect 1–3 false spikes 19:00–21:00 IST
- **Do not trade the spike** — wait for confirmed direction after month-end flows settle
- **Target for the session:** 1 clean short trade with 2.5×ATR TP (if signal appears)
