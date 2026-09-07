# Ultra Core / portfolio_v4 — Complete Fault List

*2026-09-03, rohith-2. Compiled after the audit loop confirmed portfolio_v4 has
no out-of-sample edge. This is why the system is being replaced, not patched.*

---

## 1. The strategy has no edge (fatal)

| Fault | Evidence |
|---|---|
| Fails out-of-sample | 4-year holdout PF **0.965**, net −$96, min balance $10 (`scripts/proximity_holdout.py`). Selection window PF 1.478. |
| Selection bias | 90+ candidates screened; best 4 kept **on the same window they were tested on**. The selection window (May–Aug 2026) is the best 6-month period in 4+ years. |
| Regime-dependent, unpredictably | Per 6-month window: 2023 & early-2026 PF 0.75–0.9 with 90–100% DD; 2024H2–2025 PF 1.2–1.4. Jan–May 2026 (−99.8%) → May–Aug 2026 (+PF 1.48), no warning. (`scripts/edge_by_period.py`) |
| Betting against a measured fact | Market study: M15 gold autocorrelation ≈ 0 at every lag; follow-through 48–50%. Trend-continuation legs contradict this. |
| Costs eat the edge | ~$0.26 spread on FVG_NY's $5.50 stop = ~5% headwind per trade; 330–800 trades per 6 months. |
| Fragile by construction | 22–30% win rate → lives on rare big winners. 7 exit variants tested (tight/wide/no-TP trail, breakeven ×4) — all worse than the fixed TP. |

## 2. The direction gate is broken by design

| Fault | Evidence |
|---|---|
| Inverts at turning points | D1 EMA20 gate said BULLISH through the Aug 26–31 crash ($4620→$4450), BEARISH through the Sep 1–3 bounce ($4282→$4421). |
| No fixable filter speed | D1 EMA20 lags; D1 EMA10 PF 1.40; M15 structure PF **0.33**; H4 structure PF 1.38; "both agree" 1.30. Nothing beats the slow gate, and the slow gate is wrong at turns. |
| Load-bearing for the wrong reason | "No gate" → only 39 trades over 4 years, because without it the 6% daily breaker trips almost every day. |

## 3. The risk model does not fit the capital

| Fault | Evidence |
|---|---|
| 0.01-lot floor = 5–9% risk/trade on $100 | Broker minimum. 3 losses ≈ −25%. First weeks live are structurally the riskiest. |
| Account-threatening variance even when winning | H2 2025 PF 1.40 but **79.5% drawdown**. H1 2025 PF 1.40, 33% DD. Too much variance for $105. |
| Daily breaker near-useless | 6% ≈ $6.34; one 0.01 trade can lose $5–9. It's a "1–2 loss" cap. No weekly / monthly / peak-drawdown limit. |

## 4. The live bot ran an unvalidated config

| Fault | Fixed? |
|---|---|
| Trailing stops + pyramiding were ON live — backtest PF **0.59**, −$93, 89% DD; neither in the validation | fixed rohith-2 |
| Dynamic sizer (risk_pct 0.15) live → opened 0.02–0.03 lot trades on a $105 account | fixed rohith-2 |
| Config drift: live = 2 concurrent + trail + pyramid; the validation = 1 concurrent, no trail, no pyramid | fixed rohith-2 |
| Macro-rule grep scans a markdown file for 2 English phrases, silently rewrites every short's stop; matched its own warning text | documented, not re-architected |

## 5. Process failures that allowed all of the above

- Candidate selection done **on the test window** — no walk-forward, no holdout, until rohith-2.
- Repo **never in version control** — 235 untracked files (fixed rohith-2, `3c5d838`).
- `.agents/rules/account_growth_rule.md` said "don't touch the 15% sizing until $200" — which is why the dangerous sizer stayed live (rewritten rohith-2).
- Docs described a non-existent system — README pointed at deleted `london_bot.py`; battle plan listed "Strategy #16", "Fib golden pocket" that no code implements (rewritten rohith-2).
- Metrics in R-multiples / synthetic PF hid near-ruin — a trade that took the account to ~$10 "looked fine" on net P&L (readiness doc, HYP-030).

## 6. FVG leg specifics

- Fires on **any** 3-bar gap, no size filter — ~19 signals/day, mostly noise. A 0.05–0.10% min-gap filter improved it in-sample (portfolio PF 1.478 → 1.53–1.55) but moot given §1.
- Its 0.5×ATR ≈ $5.50 stop is **below the session's own noise floor** — Phase 3 measured NY median adverse excursion at $8.69. Designed to be stopped by noise.

---

## One line

A pattern-search overfit to its best window, on a timeframe with no measured
edge, gated by a filter that inverts at turns, sized too big for the account,
and live in a configuration nobody ever tested.

## What survives rohith-2 as genuinely useful

- `src/core/resilience.py` — lockfile, kill switch, MT5 reconnect, startup safety check
- `src/research/structure.py` — reusable market-structure primitives
- `src/backtesting/` engine + the A/B harness (holdout, walk-forward, per-period)
- The knowledge that this approach does not work — found on demo, not on Sept 30
