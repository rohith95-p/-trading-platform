# Liquidity-Sweep Reversal — mathematical-variation audit

*2026-09-12, autonomous session (owner asleep). Owner request: "liquidity
sweep, and market trend reversal … try creating mathematical variations."*

## What was built

`src/strategies/liquidity_sweep_reversal.py` — a parameterised **failed-breakout
/ stop-run fade**. Thesis: stops and breakout orders cluster just beyond an
obvious swing extreme; a bar that spikes *through* the level and closes back
*inside* the range ran that liquidity without genuine follow-through — a stop
hunt — and the reversal trades the return move. Same family as `_c_range_rejection`
(XAU-049) and the 20-year-audit "Failed breakout reversal", made precise.

Everything ran through the real `BacktestEngine` (M1 intrabar, SL-first,
realistic costs, $100 / 0.01 lot) — no vectorised shortcuts
(`.agents/rules/backtesting_guardrails.md`).

## The mathematical variations tested

| dimension | values |
|---|---|
| liquidity level | rolling N-bar high/low · last confirmed pivot · pivot cluster |
| lookback N | 10 · 20 · 40 |
| sweep penetration | any · 0.10×ATR · 0.25×ATR |
| close-reject depth | 0 · 0.25×ATR |
| confirmation | immediate · next-bar · **displacement candle** · CHoCH structure event |
| regime gate | none · ADX(14)<22 (range) · counter-EMA200 |
| session | NY 17:30–21:30 · London · all-24h |
| SL / TP (×ATR) | 0.75/1.5 · 1.0/2.0 · 1.5/3.0 · 0.75/3.0 · 2.0/2.0 |
| D1 EMA20 gate | off (base) · on |

22 cells on **2022–2026 broker M15** + 22 on **Jun–Sep 2026 true-M1**
(`scripts/validation/liq_sweep_reversal_matrix.py`), then a 7-variant shortlist
on the **Kaggle 22-year set split into 5 regime eras**, each era started fresh
at $100 (`scripts/validation/liq_sweep_22yr.py`).

## Result — no structural edge

**4-year matrix (2022–2026):** the family loses. Base PF 0.91; 15 of 22 cells
draw the $100 account below $15. Two cells looked alive:

| cell | n | PF | net | min bal | DD |
|---|---|---|---|---|---|
| `confirm = displacement` | 538 | **1.10** | +$161 | $92.70 | 37% |
| combo `displace / counter-EMA200 / SL0.75-TP2.5` | 205 | **1.48** | +$230 | $102 | 29% |

The recent-M1 window disagreed with the 4-year window on almost every cell
(`displace` there = PF 0.98; the cells that scored PF 1.4+ on recent-M1 scored
0.82–0.97 on the 4-year) — the hallmark of regime dependence, not edge.

**22-year regime test — the verdict.** Every shortlisted variant, positive
eras out of 5 / median PF (n ≥ 20):

| variant | +eras | median PF |
|---|---|---|
| base (control) | 0/5 | 0.79 |
| `displace` | **0/5** | **0.73** |
| `displace + range` | 2/5 (thin) | 0.71 |
| `choch` | 2/5 | n<12 per era — unusable |
| `choch + range` | 2/5 | n<7 per era — unusable |
| **combo `displace/counter/0.75-2.5`** (the matrix's best cell) | **1/5** | **0.71** |
| `displace` all-session | 0/5 | 0.63 |

The `displace` variant that returned +$161 / PF 1.10 on 2022–2026 loses in
**all five** regime eras when each is tested on its own (median PF 0.73). The
PF 1.48 combo — a four-parameter cell selected as best-of-44 — scores median
PF 0.71 across 22 years and is positive in **one** era, the one it was picked
on. Textbook selection bias, same failure mode as portfolio_v4 and HYP-066.

## Conclusion

**Liquidity-sweep reversal joins the graveyard** with `Range_rejection_wick`
and `Failed_breakout_reversal` (both "BLOWN" in the 20-year audit) and the
dynamic-stop / Renko / structural-TP ideas. On gold M15 the fade of a swept
level has negative per-trade expectancy after costs in every regime tested,
under every level definition, confirmation rule, regime filter and stop
geometry tried. Displacement confirmation is the least-bad variant and it is
still a loser.

Recorded as **HYP-070**. Not to be revisited without genuinely new evidence
(e.g. a different instrument, or tick-level sweep detection the M15 data
cannot express).

*Files: `src/strategies/liquidity_sweep_reversal.py`,
`scripts/validation/liq_sweep_reversal_matrix.py` +
`scripts/validation/liq_sweep_22yr.py`,
`research/validation/liq_sweep_reversal_matrix.json` +
`research/validation/liq_sweep_22yr.json`.*
