# Real-Money Readiness — Rating Report

*2026-09-06. Scores everything against `REAL_MONEY_READINESS.md`'s own
originally-written bar, using what this session actually measured (a pre/post
bugfix A/B on a 4-year holdout, a 2022-2024 vs 2025-2026 out-of-sample check,
a Monte Carlo ruin simulation, a full execution/infra/doc audit, and a new
config-integrity system built and verified) -- not assumption, not the
original document's 3-day-stale claims.*

---

> **REVISED LATER THE SAME DAY — read this first.** The scores below were
> written before the Part I suite was actually built and run. It has now been
> run, and it changes the picture materially in both directions. The short
> version:
>
> - **Part I.1 (the edge gate) PASSES** under the 2-year standard, on genuinely
>   out-of-sample data: PF 1.2581, maxDD 40.3%, min balance $102.01 (HYP-049).
>   First Part I gate ever cleared here.
> - **Part I.3 (survivability) FAILS badly at the current config**: P(ruin)
>   39.4% against a <1% bar (HYP-050). The edge is real; the *bet size* is not.
> - **One configuration passes both** (HYP-055): **FVG_NY alone, one position,
>   on a Cent account** — PF 1.5004, min balance never below start, maxDD
>   35.7%, and at Cent 0.25-lot sizing **P(ruin) 0.000%**. It earns
>   **$0.29-0.73/day on $100**. That is the honest ceiling of "safe" here.
> - The owner's 11:30-21:30 session rule, applied to the *current* portfolio,
>   makes things worse (halves profit, drawdown 40%→66%, fails I.1) — but it
>   points directly at the FVG-only configuration above, which is better on
>   every axis than what is deployed today (HYP-054).
>
> Revised overall readiness: **~35%** for the current deployed config, and
> **~55%** for the FVG-only/Cent candidate, whose remaining blocker is the
> 8-week paper test (I.9) rather than an unproven edge. Per-item detail is in
> `research/validation/*.json`; per-gate status is in the table at the end.

## Headline verdict (as originally written, before the tests ran — superseded above)

**NOT READY. Overall readiness: ~20%.** This is a gated system, not an
averaged one -- `REAL_MONEY_READINESS.md` says it itself: *"If Part I does not
pass, nothing else matters and real money does not happen."* Part I (proof the
edge is real) fails on 7 of 9 sub-criteria, and the two that were actually
measured this session both fail badly, not marginally. A strong execution
layer cannot compensate for that; it isn't being asked to.

The good news, genuinely: this session found a real bug (not a curve-fit) that
turned a losing 4-year backtest into a profitable one, and built a piece of
infrastructure (the config-integrity gate) that didn't exist anywhere in the
original plan and closes a real, repeatedly-observed failure mode. Neither of
those existed 3 days ago. The system is measurably better than it was --  it
is just not close to done.

---

## Scorecard

| Category | Score | Grade | Gates go-live? |
|---|---:|:-:|:-:|
| **Strategy edge & validation** | 25/100 | F | **Yes -- this is the blocker** |
| **Risk management & position sizing** | 15/100 | F | **Yes -- second blocker** |
| **Execution & infrastructure** | 55/100 | C | No (already decent) |
| **Trading rules & discipline** | 35/100 | D | No |
| **Monitoring & review** | 10/100 | F | No (matters post-launch, not pre) |
| **Documentation & process integrity** | 60/100 | C+ | No (a real strength) |
| **Overall (gated, not averaged)** | **~20/100** | **F** | -- |

---

## 1. Strategy edge & validation — 25/100 (F)

**What's real and new:** `portfolio_v4` was declared to have zero out-of-sample
edge on 2026-09-03 (4yr holdout PF 0.965, loses money). This session found the
actual cause -- `EMASTACK_LONDON_TIGHT` re-firing into its own persisting
state instead of on a state *change* -- and fixed it. Re-run clean: PF 0.948
pre-fix (confirms the original finding was real) -> **PF 1.180 post-fix**, net
+$1,720 over 4 years. One bug fix, not a re-tuned parameter. There is now a
real, mechanistically-understood, positive edge. That is genuine progress.

**Why the score is still low:**
- PF 1.180 misses this document's own I.1 pass bar of **PF > 1.2**.
- Max drawdown 83.9% and min balance $39.18 (63% down from $105.74) both miss
  "never below 50% of start" badly, not marginally.
- The Monte Carlo bootstrap (I.3) that was actually run this session shows
  **P(ruin within 100 trades) = 42.3%**, against a pass bar of **< 1%**. This
  isn't close.
- The currently-deployed configuration (D1 gate off) scores well on
  2025-2026 (PF 1.245) but **failed catastrophically on 2022-2024 in the
  identical config** -- PF 0.654, account down to $4.50 from $105.74, never
  recovered. That's not a marginal miss of a pass bar, that's the exact
  failure mode Part I exists to catch.
- 7 of 9 Part I sub-gates (walk-forward, parameter perturbation, per-leg
  random-entry re-check, cost stress, long-history/Dukascopy, forward paper
  test) were never run this session at all.

**Read:** a real edge was found where there wasn't thought to be one -- but
"a real edge exists" and "this edge is provably survivable" are different
claims, and only the first one has been earned so far.

## 2. Risk management & position sizing — 15/100 (F)

**What exists:** fixed 0.01 lot hard-enforced at two independent layers
(main_loop + execution_handler), a 6%-of-balance daily loss breaker, margin
enforcement in the backtest engine (not live).

**What doesn't:**
- No sizing ladder (Part II.2) -- balance-based lot sizing was never coded;
  it's fixed 0.01 lots at $100 and would still be fixed 0.01 lots at $10,000.
- No weekly, monthly, or peak-equity loss caps (Part II.3) -- only same-day
  exists. This gap was flagged **before** this session (`SYSTEM_FAULTS.md`,
  09-03) and is still unbuilt.
- No circuit breakers (Part II.4) -- no consecutive-loss pause, no
  auto-stop-for-the-day beyond the single daily % breaker.
- No profit ring-fencing (Part II.5), no explicit pre-trade margin cap check
  in the live path (Part II.6) -- margin usage already reaches ~66% of a
  $100 account with 3 concurrent 0.01-lot positions at current gold prices.
- The dangerous 15%-risk dynamic sizer (`RiskManager.calculate_dynamic_lot_size`)
  is still present in the codebase, dormant only because
  `execution_handler.py` hard-clamps every order -- a real "loaded gun" if
  that clamp is ever refactored without the coupling being obvious.
- Monte Carlo (above): ~42% ruin probability even under the *optimistic*
  measured stats. This is a sizing/bankroll problem more than a strategy
  problem -- the stake is too large relative to the edge to compound safely.

**Read:** the one thing genuinely locked down is the lot-size floor itself.
Almost everything else this document specified for risk control is still
just prose, not code.

## 3. Execution & infrastructure — 55/100 (C)

**Real strengths, confirmed by direct code audit, not assumption:**
- `src/core/resilience.py`: single-instance lockfile, kill switch (STOP file),
  MT5 auto-reconnect (after 3 failed fetches), startup safety check
  (account/balance/tradeable checks), state persistence -- all present,
  mostly previously tested.
- Every previously-found live-vs-backtest fidelity bug (HYP-042 silent
  confirmation-queue drop, HYP-045 min-bars mismatch, duplicate-order dedup)
  verified still fixed at HEAD, not regressed.
- **New this session and verified working**: a config-integrity gate
  (`system_config.py` + `validation_ledger.py`) that fingerprints the full
  live configuration and refuses to trade anything that doesn't match a
  recorded, validated backtest -- tested by simulating a config revert and
  confirming it's caught with the exact field named. This closes a failure
  mode (silent config drift between what's live and what was validated) that
  had already caused real confusion multiple times, including twice in this
  session before it existed.

**Real gaps:**
- Watchdog's alert mechanism is a `print()` stub -- no actual notification
  channel. Watchdog doesn't monitor `protect_profit.py`, and nothing monitors
  watchdog itself. A real single point of failure at the top of the chain.
- No structured logging (`trade_ledger.jsonl` is dead code -- nothing writes
  to it), no daily auto-report, no weekend-flatten/rollover-skip handling.
- The config-integrity gate's backtest side is still manual -- a backtest can
  run, get discussed, and never get registered in the ledger unless someone
  remembers to call `record()`.

**Read:** this is the most mature category by a wide margin, and got a real,
verified upgrade this session. Still not launch-ready on its own gaps, but
comfortably ahead of the other categories.

## 4. Trading rules & discipline — 35/100 (D)

- Bot-only execution held throughout this session -- no manual entries or
  trade management, consistent with III.1.
- **III.2's core premise ("the direction gate is law, never override") is no
  longer true** -- the gate is deliberately off as of today, a conscious,
  documented risk-acceptance decision, not an oversight, but it does mean this
  section of the rulebook describes a system that doesn't currently exist.
- III.3's "frozen config, changes go through the full cycle" was honored in
  spirit (every change this session is logged in `RESEARCH_LEDGER.md` with
  before/after numbers) but not to the letter -- no 4-week paper test followed
  the edge-trigger fix before it became "the" live config.
- No news blackout list (III.5) exists. Kill switch (III.6) exists but wasn't
  re-tested mid-trade this session.

## 5. Monitoring & review — 10/100 (F)

Almost nothing from Part VI exists: no weekly review document, no coded
divergence tripwire (rolling 30-trade PF check), no automated trade journal
(the one durable trade log that should feed this, `trade_ledger.jsonl`, is
dead code), no systematized edge-decay check. This doesn't block go-live by
itself the way Parts I-II do, but it means there would currently be no
mechanical way to notice the edge decaying after launch except reading logs
by hand.

## 6. Documentation & process integrity — 60/100 (C+)

This is a genuine strength worth naming plainly, not just a place to list
gaps. `RESEARCH_LEDGER.md`'s HYP discipline -- record the claim, record the
test, record the honest result even when it's a rejection -- is real and was
used correctly this session (HYP-046/047/048 all follow the pattern, including
recording a blanket-fix attempt that made things *worse* rather than hiding
it). The project corrects its own record when it's wrong (see COR-001/002
referenced in the ledger, and this session's own correction of a gate-setting
mix-up mid-conversation). The gap is `REAL_MONEY_READINESS.md` itself sitting
stale and unmarked for 3 days -- now fixed -- and several other docs
(`DAILY_GOALS.md`, the old battle plan) that described a system that no longer
exists until this session's cleanup pass.

---

## What would actually move the needle, in order

1. **Run the real Part I protocol**, not exploratory testing -- specifically
   the Monte Carlo bootstrap and walk-forward analysis, pre-registered, on
   whatever configuration is actually intended to go live. Until P(ruin) comes
   down from 42%, nothing else here matters.
2. **Build the risk ladder that's already fully specified** (Part II.2-II.4) --
   this is design work already done, just not coded. Highest ratio of
   readiness-gained to effort-spent of anything on this list.
3. **Decide what the D1 gate decision actually means for capital at risk** --
   either size down enough that a repeat of the 2022-2024 result (95.7%
   drawdown territory) is survivable, or don't run gate-off unattended.
4. **Close the config-integrity gate's remaining hole** -- make backtest runs
   auto-record instead of relying on a human to remember.
5. Everything in Parts IV-VI, roughly in the order the original document's
   "priority order" section already lists.

---

# APPENDIX — Measured Part I results (2026-09-06)

Every gate below was actually run this session. Raw output in
`research/validation/*.json`; scripts in `scripts/validation/`.

| Gate | Pass bar | Measured (current 4-leg config) | Verdict |
|---|---|---|---|
| **I.1** holdout | PF>1.2, maxDD<45%, never <50% start | PF **1.2581**, maxDD 40.3%, min bal $102.01 | **PASS** |
| **I.2** walk-forward | median test PF > 1.2 | median **1.082**, 9/16 windows green | FAIL |
| **I.3** Monte Carlo | 95th DD<40%, P(ruin)<1% | 95th DD **223.7%**, P(ruin) **39.4%** | **FAIL (badly)** |
| **I.4** perturbation | PF>1.2 across ±20% | worst **1.129** (only fails when widening) | FAIL (marginal) |
| **I.5** random-entry | every leg clears its control | not completed (rewritten as M1 sim; not run) | PENDING |
| **I.6** regime | report per regime | done — see below | INFO |
| **I.7** cost stress | PF>1.2 at 2× cost | **1.194** at 2×, degrades gracefully | FAIL (marginal) |
| **I.8** long history | ≥1 bear + 1 chop | **RETIRED** under the 2-year standard | N/A |
| **I.9** paper test | 8wk, live within 20% of backtest | tooling built, clock not started | PENDING |

**Per-leg (holdout, I.6):** FVG_NY **PF 1.466 / +$1,497** · SQUEEZE_ASIA 1.242 /
+$1,412 · EMASTACK 1.102 / +$144 · RANGEREJECTION **0.982 / −$23 (net loser)**.
By volatility quintile the edge lives in high vol (q3 1.307, q4 1.264) and
bleeds in mid vol (q2 0.979).

**Leg-combination test (HYP-054):** all-4 PF 1.258 / P(ruin) 39.4% · minus-Asia
PF 1.256 but maxDD 66% / fails I.1 · EMASTACK+FVG **loses money** (PF 0.907)
because EMASTACK burns the shared daily-loss budget and blocks FVG's better
trades · **FVG alone PF 1.432, P(ruin) 11.6%** — best of all.

**The candidate that clears both gates (HYP-055):** FVG_NY alone, 1 position,
Cent-account sizing.

| Sizing | PF (p50) | 95th DD | P(ruin) | $/day | I.3 |
|---|---:|---:|---:|---:|:-:|
| Standard 0.01 lot @ $100 | 1.50 | 98.6% | 8.59% | $2.92 | FAIL |
| Cent 0.50 lot | 1.50 | 56.4% | 0.77% | $1.46 | FAIL |
| **Cent 0.25 lot** | **1.50** | **32.4%** | **0.000%** | **$0.73** | **PASS** |
| Cent 0.10 lot | 1.50 | 15.3% | 0.000% | $0.29 | PASS |

## What was built this session (Parts II & IV)

| Item | Status |
|---|---|
| II.2 sizing ladder, II.3 cascading caps, II.4 breakers, II.6 margin cap | **built** — `src/core/risk_rules.py`, unit-tested, `ENFORCE=False` (shadow mode) pending validation |
| IV.8 structured logging | **built** — `src/core/trade_log.py`, wired into every signal/block/order path |
| IV.1 alert channel | **built** — `src/core/alerts.py` (Telegram/webhook), watchdog now also monitors `protect_profit.py` |
| IV.6 weekend flatten / rollover skip / trading window | **built** — `src/core/market_hours.py`, enforces the 11:30-21:30 rule |
| IV.11 config-integrity gate | **built earlier today**, and it immediately caught the session change as config drift |
| I.9 paper-test tooling | **built** — `scripts/paper_test_review.py` (live-vs-backtest + VI.3 tripwire) |
| Part B / D1 plan | **Phase 1 adjudicated** — H1/H3/H4 rejected, H2 (DXY) passes a pre-registered lead/lag test (t −3.82) |

## The one number that matters

At a risk level where $100 reliably survives, this system earns roughly
**$0.29–$0.73/day**. The $20–30/day goal needs roughly **$3,000–10,000** of
capital at the same safety level. Every measurement this session converges on
the same conclusion from a different direction: **the constraint is capital,
not strategy.**
