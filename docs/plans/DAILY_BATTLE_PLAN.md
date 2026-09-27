# Daily Battle Plan (XAUUSD)

## Market Condition
- **Macro:** Bearish
- **Price Structure:** Bearish (Price < D1 EMA20).
- **Alignment:** Macro and Price Structure are in agreement.

## Strategy / Live Legs (from portfolio_v4.py)

| Leg | Session (IST) | Direction | SL / TP (×ATR) |
|---|---|---|---|
| SQUEEZE_ASIA | 02:30–11:30 | SHORT | 2.0 / 4.0 |
| EMASTACK_LONDON_TIGHT | 11:30–15:30 | SHORT | 0.75 / 3.0 |
| FVG_NY_TIGHT | 17:30–21:30 | SHORT | 0.5 / 2.5 |
| RANGEREJECTION_NY_TIGHT | 17:30–21:30 | SHORT | 0.75 / 2.25 |

*Note: Direction is decided by the D1 gate, not discretion. While price < D1 EMA20, shorts only. Longs are detected and logged as blocked.*

## Hard Risk Rules
- **Position Size:** 0.02 lots per order, always (`FIXED_LOT_SIZE`).
- **Max Exposure:** 0.04 lots total exposure, max 2 concurrent (`MAX_TOTAL_VOLUME`).
- **Loss Breaker:** 6% daily loss breaker (realised + floating) → halts new entries to midnight IST.
- **Management:** Trailing stops ON, pyramiding OFF.
- **D1 EMA20 bias gate:** Trade only with the daily trend.

## Session Review of Today's Closed Trades
- **Trades:** No trades executed today.
- **Analysis:** N/A.

## Watch List
- **D1 EMA20:** 4352.72 (Key flip level for bias gate)
- **Recent Price:** 4268.97
