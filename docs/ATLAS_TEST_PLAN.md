# Atlas Funded "Access" — rules we must test against (2026-10-16)

Sources: Atlas's own help/docs pages (help.atlasfunded.com: Access, Maximum drawdown, Prohibited practices, Margin usage; atlasfunded.com: Trading Rules, Terms) and the third-party reviews listed at the end. Where the official pages disagree with each other or with reviews, the **official Access page wins**, and the item is flagged "confirm with support".

## 1. The Access program, as Atlas states it

| Item | Evaluation | Funded |
|---|---|---|
| Entry | **$5** (account sizes $5K–$400K); funded fee is shown only at checkout | Pay within **30 days** of passing or the offer lapses |
| Profit target | **3 %** of start balance, on closed balance | none |
| Max drawdown | **10 %, trailing on equity** | **6 %, trailing on equity** |
| Daily loss | 5 % (trailing, end of day) | **3 %** (trailing, end of day) |
| Min trading days | none | 3 days with ≥ 0.5 % profit each, per payout cycle |
| Consistency | none | best day ≤ **40 %** of cycle profit when requesting payout (breach delays payout only) |
| Split | — | **90 %** |
| Payout timing | — | first after **28 days**, then every 14 days; $100 profit threshold |
| Time limit | none | inactivity limit 30 days |
| Leverage | up to 1:100 (gold figure not published) | same |
| Platforms | MT5, TradeLocker, Match-Trader | same |

Funded-only deductions and closures:
- **Atlas Protector:** a 2 % net floating loss of initial balance closes all positions and cuts the split to 50 % for that cycle; a second occurrence is a breach.
- **News window ±5 min** around high-impact events: profit on those trades is deducted.
- **Trades held under 3 minutes:** profit deducted.
- **Margin usage ≥ 80 %:** all positions closed, profits deducted.
- Fee refund: the **$5 only**, returned with the 3rd consecutive payout; the funded fee is **not** refunded.

Allowed (Prohibited-practices page): **EAs and algorithmic trading, overnight and weekend holding, scalping if funded trades are held ≥ 3 min.** Not allowed: hedging across accounts/firms, latency/tick arbitrage, account sharing, order flooding, logging in from several places to hide who trades.
Other pages: no new positions on Saturday/Sunday; VPN allowed with advance disclosure of location changes; Terms say a "major unexplained strategy change" can put the account at risk and that "some EAs are allowed, ask first".

## 2. Conflicts to resolve with Atlas support (before paying the funded fee)
1. Access is described as 1-step in the docs and as 2-step (5 % per phase, 8 % DD) by a review. Use the official: **one phase, 3 % target**.
2. A review says EAs are not allowed on Access; the official Prohibited-practices page says EAs are allowed; the Terms say ask first. **Get written approval of the exact bot setup.**
3. Funded fee amount for a $5K account (a third-party review says ≈ $78).
4. Gold: symbol name on the MT5 server, leverage, spread, commission.
5. How "trailing on equity" is computed with open trades, and whether the floor stops rising at some level.
6. The Terms mention a payout "50 % split cap on the first on-demand payout"; the Access page says 90 % split. Which applies to Access?
7. Does one-directional trading ever count as suspicious? (Trustpilot: "mostly took long positions".)

## 3. What we test (simulator requirements, in priority order)

A. **Trailing-equity drawdown, not static.** 10 % in evaluation, **6 % when funded**. Our drawdowns are measured peak-to-trough, which is the right metric. At 0.25–0.5 % risk per trade, a 6 % trailing limit allows only 12–24 R of drawdown; strategies in this repo have 25–36 R. This is the binding constraint.
B. **Daily loss:** 3 % funded (5 % eval), reset 00:00 UTC. Several losing trades in a day must fit.
C. **Evaluation target 3 %** before a 10 % trailing breach: pass probability by rolling start dates.
D. **Funded cycle:** survive 28 days, ≥ 3 days at ≥ 0.5 % gain, best day ≤ 40 % of cycle profit, then payout = 90 % × profit. Expected first payout and probability of getting one.
E. **Atlas Protector:** 2 % floating loss of initial balance closes everything — equals a hard cap on open risk (two concurrent 1 % stops would hit it).
F. **Minimum hold 3 min and ±5 min news windows:** measure how much strategy profit comes from trades under 3 min or inside news windows (our 4 live legs: median trade lasts minutes).
G. **No new entries on weekends; margin use < 80 %** (1:100 leverage: 0.5 lot on a $5K account at $4,000 gold is ~$20,000 notional → check margin).
H. **Costs:** Atlas spread/commission on gold are unknown — rerun at 1×, 1.5×, 2× the Exness spread.
I. **Owner's pass bar (applied to every strategy):** profit factor > 1.2 out of sample; drawdown < 60 % of the firm's limit (< 3.6 % at the 6 % funded limit); no single day > 20 % of profit (stricter than Atlas's 40 %).
J. **Regime test:** results in 2023–24 (non-trending) and 2025–26 (trend) separately.

## 4. How we will "prove it"
No more waiting weeks: the proof is (1) the out-of-sample score against the bar above, (2) the live demo evidence we already have (Aug 24 – Oct 15, see `docs/GO_LIVE_DECISION_2026-10-16.md`), (3) a **pre-set kill rule** once live — stop trading the strategy after a 3 % drawdown from its peak or 8 consecutive losses, whichever is first — and (4) the $5 evaluation itself, which costs nothing beyond the fee if it fails.

## Sources
- Atlas Funded help pages: Access, Maximum drawdown, Prohibited practices, Margin usage (help.atlasfunded.com)
- Atlas Funded Trading Rules and Terms (atlasfunded.com/trading-rules, /terms)
- [Atlas Funded review 2026 (propfirmpal)](https://propfirmpal.com/firms/unverified/atlas-funded)
- [Atlas Funded review 2026 (propfirm201)](https://propfirm201.com/firms/atlas-funded)
- [Atlas Funded on PropFirmMap](https://propfirmmap.com/firms/atlasfunded)
- [Atlas Funded on Trustpilot](https://www.trustpilot.com/review/atlasfunded.com)

## 5. Results (2026-10-16) — scripts/research/atlas_score.py, wf_series.py, wf_new_candidates.py, wf_new_classes.py

Account $5,000; out-of-sample 2023-08 → 2026-10; limits used: funded 6 % trailing drawdown, 3 % daily; bar: PF > 1.2, drawdown < 60 % of the limit (3.6 %), best day ≤ 20 % of profit; "fit risk" = largest risk per trade that keeps drawdown under the bar.

| Strategy (best geometry) | PF all / 2023-24 / 2025-26 | Max DD (R) | Fit risk | Return at fit risk | Verdict |
|---|---|---|---|---|---|
| H1 Donchian 100, SL4/TP12 | 1.56 / 1.27 / 1.81 | 15.3 | 0.23 % | +7.5 %/yr | fails only the DD bar (needs ≥ 0.25 %) |
| H1 Donchian 100, SL3/TP9 | 1.55 / 1.01 / 2.07 | 17.1 | 0.21 % | +7.5 %/yr | fails DD bar |
| SQUEEZE_ASIA | 1.29 / 1.12 / 1.51 | 39.1 | 0.09 % | +3.6 %/yr | fails DD bar |
| SUPERTREND_EMA (archive) | 1.13 / 1.07 / 1.18 | 15.4 | 0.23 % | +3.1 %/yr | fails PF and DD |
| TREND_PULLBACK_V5 walk-forward geometry | 1.20 / – / 1.20 | 42.7 | 0.08 % | +5.2 %/yr | fails |
| BB, NVMR, FVG (all geometries, walk-forward) | 0.82–1.17 | 22–240 | ≤ 0.16 % | ≤ +2.3 %/yr | fail |
| New: AsiaVolBreakout / DailyOpenMomentum / LondonOpenDrive | 1.12 / 1.09 / 1.03 | 34 / 31 / 17 | ≈ 0.1 % | ≈ +1 %/yr | fail |
| XV2-078/108/111/132 | 0.89–1.16 | 27–130 | ≤ 0.13 % | ≤ +1.2 %/yr | fail |

(XV2-084 and XV2-104 produced zero trades in the engine and are untested.)

Atlas life cycle (closed-trade approximation; evaluation = +3 % before a 10 % trailing breach, no time limit; funded = survive 28 days at 6 % trailing / 3 % daily, ≥ 3 days with ≥ 0.5 % gain, best day ≤ 40 %, payout 90 %):

| Strategy | Risk / trade | Eval pass | Funded alive day 28 | Qualifies for 1st payout | Avg 1st payout |
|---|---|---|---|---|---|
| H1 Donchian SL4/TP12 | 0.20 % | 91 % | 100 % | 5 % | $150 |
| H1 Donchian SL4/TP12 | 0.50 % | 95 % | 100 % | 3 % | $376 |
| H1 Donchian SL3/TP9 | 0.35 % | 95 % | 100 % | 5 % | $252 |
| SQUEEZE_ASIA | 0.20 % | 95 % | 100 % | 38 % | $219 |
| SQUEEZE_ASIA | 0.50 % | 86 % | 94 % | 20 % | $461 |

Reading: passing the evaluation is easy in simulation (low target, no time limit). The funded rule "≥ 3 days with ≥ 0.5 % profit in the cycle" is the real bottleneck for slow trend systems (≈ 1–2 trades/week); it was tested only for the first cycle, later 14-day cycles give more chances. Actual trailing-equity breaches use open P/L, so real survival is lower than shown.
