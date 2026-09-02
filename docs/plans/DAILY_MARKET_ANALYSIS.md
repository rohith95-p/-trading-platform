# Daily Market Analysis (Global Macro Tracker)
*Date: 2026-09-03 (written 00:20 IST, covering the 2026-09-02 session)*

> **WARNING — this file changes live trading behaviour.**
> `RiskManager._load_macro_rules()` greps this document for two specific
> phrases (see the string literals in `src/core/risk_manager.py`, method
> `_load_macro_rules`). If BOTH appear, it sets `_strict_short_stops = True`,
> which **overrides every SHORT's stop/target to a hardcoded 1.0x / 2.0x ATR**
> — discarding the per-leg multipliers portfolio_v4 was validated with
> (0.5-0.75x SL, 2.25-4.0x TP).
>
> **Do not quote those phrases in this file**, not even to explain them. On
> 2026-09-03 this warning block originally spelled them out and thereby
> switched the override ON — the grep cannot tell documentation from a
> directive. Read them from the source file instead.
>
> Current state: override **OFF**, which is correct while gold is bearish.

## 5-Day Cross-Asset Read (measured from broker D1 closes)

| Asset | Current | 5-Day | Implication for Gold |
|---|---|---|---|
| **Gold (XAUUSDm)** | 4374.54 | **−4.79%** | Downtrend intact, but see the reversal note below. |
| **Silver (XAGUSDm)** | 65.11 | **−5.83%** | Falling *faster* than gold — metals complex weak, not a gold-specific story. |
| **DXY** | 99.58 | **+0.48%** | Dollar strength is the dominant driver pressuring gold. |
| **USDX (alt index)** | 580.26 | +0.94% | Confirms dollar bid. |
| **EURUSD** | 1.159 | −0.57% | Consistent with dollar strength. |
| **USDJPY** | 158.92 | −0.24% | Yen firming slightly — mild risk-off undertone. |
| **Brent (UKOILm)** | 94.31 | **+9.19%** | Large energy spike. Inflationary — a latent *bullish* gold catalyst. |
| **WTI (USOILm)** | 89.20 | **+7.67%** | Same. |
| **US500** | 7672 | −0.66% | Equities soft. |
| **USTEC** | 29110 | −1.52% | Tech leading the softness. |

## Gold Price Structure

| Date | Open | High | Low | Close | Range |
|---|---|---|---|---|---|
| 08-25 | 4679.80 | **4697.11** (peak) | 4605.20 | 4654.70 | 91.90 |
| 08-28 | 4594.61 | 4632.24 | 4445.29 | 4456.13 | **186.95** |
| 08-31 | 4458.30 | 4472.42 | 4396.35 | 4452.14 | 76.07 |
| 09-01 | 4452.22 | 4461.48 | 4322.67 | 4324.64 | 138.81 |
| **09-02** | 4324.69 | 4397.71 | **4282.30** | **4374.54** | 115.41 |

- **−6.9% from the 4697.11 peak** (Aug 25).
- **09-02 is a bullish reversal candle.** Price made a new swing low at 4282.30,
  then rallied $92 to close at 4374.54 — in the upper third of its own range.
  After five sessions of decline this is a textbook exhaustion/hammer shape.
- **Volatility is expanding:** daily ranges 76 → 139 → 115, against a ~88
  average earlier in the window. Stops sized off a flat ATR are being tested.

## Conclusion

The macro backdrop remains **bearish for gold**: the dollar is bid, silver is
falling harder than gold, and equities are soft without producing safe-haven
demand. Nothing in the cross-asset picture has turned.

**But the price structure and the macro no longer agree.** Today's daily candle
reversed off a new low and closed strong, and oil is up ~8-9% in five sessions —
an inflation impulse that historically supports gold and is currently being
overridden by dollar strength. That is an unstable configuration.

**The operative number is 4436** — the D1 EMA20. Gold closed $62 below it
(~1.4%). Given daily ranges of 115-140, that is **within a single session's
reach**. If price closes above 4436, the live D1 bias gate flips from BEARISH to
BULLISH, and the bot stops taking shorts and starts taking longs. Treat the
short bias as valid but **provisional**, not structural.
