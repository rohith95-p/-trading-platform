# Daily Battle Plan (XAUUSD)
*Date: 2026-09-07 — written morning IST, preparing for the Monday session*

> This plan describes what the **bot actually runs** (`portfolio_v4` via
> `main_loop.py`).

## 1. Market Condition (see DAILY_MARKET_ANALYSIS.md for the full read)

- **Macro:** bearish for gold — DXY +0.48%, silver −5.83%. Dollar remains steady and pressures metals.
- **Price structure:** **bearish.** Friday's attempt to rally above the EMA20 failed, printing a heavy rejection candle (O:4480, C:4430). Monday has opened weaker (4403).
- **Volatility:** remains high (115-130 pt daily ranges last week).
- **THE NUMBER TO WATCH: 4438.51** (D1 EMA20). Price is roughly $35 below it. The live D1 gate is **BEARISH**. The bot will take shorts only.

## 2. What Actually Trades Today

| Leg | Session (IST) | SL / TP (×ATR) | Notes |
|---|---|---|---|
| SQUEEZE_ASIA | 02:30–11:30 | 2.0 / 4.0 | Widest stop, most robust to noise |
| EMASTACK_LONDON_TIGHT | 11:30–15:30 | 0.75 / 3.0 | Active in London |
| FVG_NY_TIGHT | 17:30–21:30 | 0.5 / 2.5 | Tightest stop — vulnerable to NY chop |
| RANGEREJECTION_NY_TIGHT | 17:30–21:30 | 0.75 / 2.25 | Smallest sample (n=26) |

Direction is decided by the D1 gate, not by discretion. While price < 4438.51:
**shorts only.** Longs are detected and logged as blocked.

## 3. Hard Risk Rules (enforced in code, not guidance)

- **0.01 lots, every order.** `FIXED_LOT_SIZE`, enforced in
  `ExecutionHandler.send_order`.
- **0.02 lots total exposure**, max 2 concurrent positions (`MAX_TOTAL_VOLUME`).
- **6% daily loss breaker** → halts new entries until midnight IST.
- Real risk per trade at 0.01 lots is **$5–9**. This is a consequence of the
  broker's 0.01 lot floor on a small account. A single bad trade approaches the breaker limit.
- **No trailing stops, no pyramiding** (disabled as of 09-03).

## 4. Session Review — 2026-09-04 (Friday)

On Friday, price opened above the EMA20, flipping the bias to LONG for the session.

| Time | Lot | P/L | Leg | Read |
|---|---|---|---|---|
| ~London | 0.01 | +$1.68 | EMASTACK_LONDON_TIGHT | early protect |
| ~London | 0.01 | +$2.45 | EMASTACK_LONDON_TIGHT | early protect |
| ~London | 0.01 | −$6.08 | EMASTACK_LONDON_TIGHT | full SL hit |
| ~London | 0.01 | −$4.88 | EMASTACK_LONDON_TIGHT | full SL hit |

**Net result: -$6.83.** The bot attempted to buy the pullback in London as price began to slide from its strong open, but the momentum was bearish and pushed through the tight stops. This highlights the vulnerability of the tight-stop legs when the intraday price action aggressively fights the D1 bias gate.

## 5. Today's Watch List

1. **4438.51** — D1 EMA20. The line in the sand. If price closes above, the bias flips back to long. Currently, it acts as overhead resistance.
2. **4365** — Friday's low. A break below accelerates the bearish structure.
3. **NY chop risk.** The NY session remains volatile. Expect noise-stops on the 0.5×ATR FVG_NY leg.
