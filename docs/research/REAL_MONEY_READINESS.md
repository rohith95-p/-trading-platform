# Real-Money Readiness — Full Roadmap

*Draft for review — 2026-09-03, rohith-2. Author: Claude (Sonnet 5). Nothing here
is implemented yet; this is the complete list of what should be done before
portfolio_v4 trades real money, and the rules to run it by once it does.*

---

## 0. Read this first — what "ready" and "consistent" actually mean

**The win rate is 24–30% by design, and that is correct.** These legs take a
small stop and aim for a target 2.25–4.0× larger. They lose ~7 trades in 10.
The edge is entirely in the size of the winners vs the losers (profit factor),
not in being right often.

Do **not** chase a higher hit rate. That is exactly what the trailing stop did
(win rate 29% → 53%, profit factor 1.58 → 0.59, account nearly wiped). "High
accuracy" in the everyday sense is a trap for this kind of system.

**"Consistent" here means:**
1. Positive expectancy that is *proven* to survive out-of-sample, cost stress,
   and bad market regimes — not just measured once on a lucky window.
2. Risk limits so hard that the worst realistic losing streak cannot end the
   account.
3. Zero discretion — the same rules produce the same trades every time,
   regardless of how anyone feels about the market.

Consistency is a property of the *process over hundreds of trades*, not of any
day or week. A day of +$3 / −$4 / flat is the system working.

---

## PART I — PROVE THE EDGE IS REAL

*This is the gate. If Part I does not pass, nothing else matters and real money
does not happen — regardless of the calendar.*

The current evidence for portfolio_v4 is **PF ≈ 1.5 on a single ~100-day window
(2026-05-21 → 08-29)** that was also the window the 4 legs were *selected* on.
That is a hypothesis, not proof. rohith-1 already found the 3 original live
strategies were statistically indistinguishable from random. The same bar must
be cleared here.

### I.1 Out-of-sample holdout test — HIGHEST PRIORITY
- Run portfolio_v4 **exactly as frozen** (no parameter changes, no re-selection)
  on the locked holdout period (the pre-2026 range the market study reserved).
- M15 fidelity is acceptable if M1 isn't available for that range — note the
  fill-model difference.
- **Pass condition:** combined PF > 1.2, max drawdown < 45%, account never below
  50% of start.
- If it fails: the legs are overfit to the selection window. Back to research.

### I.2 Walk-forward analysis
- Rolling windows: train 60d / test 20d / step 20d across all available history.
- On each *train* window, re-run the leg-selection sweep. On the *test* window,
  measure the selected portfolio.
- **Pass condition:** the same 3–4 leg *families* keep getting selected, and
  median test-window PF > 1.2.
- If each window selects different legs → the selection is fitting noise.

### I.3 Monte Carlo — trade-sequence bootstrap
- Take the actual per-trade P&L list. Resample with replacement 10,000×.
  Rebuild the equity curve each time.
- **Report distributions, not points:**
  - PF: 5th / 50th / 95th percentile
  - Max drawdown: 50th / 95th percentile
  - P(equity touches −25% / −50% / ruin)
  - P(a calendar month is negative)
  - Expected time to recover from a 20% drawdown
- **Pass condition:** 95th-percentile max drawdown < 40%; P(ruin at 0.01 lots) < 1%.

### I.4 Monte Carlo — parameter perturbation
- Jitter every threshold ±10–20%: ATR multipliers, session boundaries, EMA
  periods, gap-size thresholds, ADX cutoffs.
- Re-run the portfolio across the cloud of perturbed configs.
- **Pass condition:** PF stays > 1.2 across the whole cloud. If a 5% change to one
  parameter collapses PF, that parameter is overfit.

### I.5 Random-entry control — re-run per leg
- For each of the 4 legs: keep the exits and the session/time distribution,
  replace the *entry rule* with a random entry. Run 1,000×.
- **Pass condition:** the leg's real PF sits above the 95th percentile of its
  random distribution. A leg that doesn't clear this is deleted.

### I.6 Regime segmentation
- Slice every backtest by:
  - D1 trend: bull / bear / sideways
  - Volatility: ATR percentile quintiles
  - Structure: efficiency-ratio trending vs ranging
- Report PF and drawdown *per regime, per leg*.
- Use the result to decide whether legs should be gated by regime, not only by
  session. **Specifically: find where each leg bleeds and turn it off there.**

### I.7 Cost & slippage stress
- Re-run at 1×, 1.5×, 2×, 3× the modeled (spread + commission + slippage).
- Plot PF vs cost multiplier; record the **breakeven cost multiple**.
- **Model slippage on stops explicitly:** stop fills at `stop ± (0.5–1.0 ×
  spread)` adverse in normal conditions, worse on gap-throughs. The FVG_NY leg
  ($5.50 stop) is extremely sensitive to this.
- **Model spread as a function of time-of-day:** spread widens at session
  opens/closes and at broker rollover (~00:00 server time).
- **Pass condition:** PF > 1.2 at 2× modeled cost with realistic stop slippage.

### I.8 Longer history
- Exness demo only carries ~100 days of M1. Source **Dukascopy XAUUSD tick data**
  (free, multi-year) and build a longer M1 series. It won't match the exact
  broker feed, but it gives real bear markets (2022), the 2020 crash-and-rip,
  and chop-only stretches to test against.
- Re-run I.1–I.7 on the long series.

### I.9 Forward paper test — the final filter
- Freeze the config completely. Run on demo for a **minimum of 8 weeks**, no
  changes of any kind.
- Each week: compare live-demo results to what the backtest produces for that
  exact date range.
- **Pass condition:** live-demo PF within 20% of backtest PF, and no unexplained
  behaviour in the logs.

---

## PART II — CAPITAL & RISK RULES (the written rulebook)

*Every number below must be decided and fixed before go-live. No discretion.*

### II.1 The starting-capital decision
At 0.01 lots (broker minimum) with these tight stops, one trade risks **$5–9**.
On a $100 account that is **5–9% per trade** — far above the 1–2% norm. The first
~$100–300 of live trading is therefore the *structurally riskiest* phase of the
entire plan, and it does not get safer with time — it gets safer only with
balance.

Pick one, in writing:
- **(A)** Start with **$300–500** so 0.01 lots ≈ 1.5–3% per trade. Strongly
  preferred.
- **(B)** Use an **Exness Cent account** (`XAUUSDc`, 0.10 "lot" = the same $1
  notional) for the first phase, so sizing granularity is 10× finer.
- **(C)** Start at ~$100 on the Standard account and *explicitly accept* that the
  first weeks run at 5–9% risk per trade, with a hard 2-loss daily stop.

### II.2 Position-sizing ladder
Write the exact table. Example shape (fill in after Part I):

| Balance | Per-order lots | Max total exposure | ~Risk per trade |
|---|---|---|---|
| < $200 | 0.01 | 0.01 (one position only) | 4–9% |
| $200–400 | 0.01 | 0.02 | 2–4% |
| $400–800 | 0.01 | 0.03 | 1.5–2.5% |
| > $800 | 0.02 | 0.04–0.06 | 1.5–2% |

Sizing is a lookup against balance. It is never a judgement call. Changes to the
ladder require the full validation cycle.

### II.3 Loss caps (cascading)
- **Per-trade:** whatever the ATR stop gives at 0.01 lots. Not adjustable.
- **Daily:** early phase **3%** or **2 losing trades**, whichever first → halt
  new entries to midnight IST. Loosens to 6% above $400.
- **Weekly:** −15% from Monday's opening balance → halt for the week, mandatory
  review before resuming.
- **Monthly:** −25% from month-start balance → **full stop**, re-run Part I
  before resuming.
- **All-time peak:** −30% from the highest equity ever reached → **hard kill**,
  written post-mortem required before any restart.

### II.4 Circuit breakers (intraday)
- **3 consecutive losses** (any leg) → pause all new entries 4 hours.
- **5 consecutive losses** → stop for the day.
- **Spread spike** > per-leg max → that leg skips entries (already partly built;
  make the max per-leg, not global).
- **Unexpected account state** (balance jump, wrong login, margin call flag) →
  halt and alert.

### II.5 Profit protection
- At each milestone ($150, $200, $300, $500, then every $250), **ring-fence** a
  fixed fraction (e.g. 30%) of the gain — move it to a sub-account or withdraw.
  A later blowup then cannot erase all progress.
- **Never add external funds to a drawing-down account.** It earns its way back
  or it gets shut off. Adding money to a loser is how accounts die slowly.

### II.6 Leverage / margin
- Max margin utilization **20%**. At the sizing ladder above this is automatic,
  but write it as a hard check in the startup safety block.

---

## PART III — TRADING RULES & DISCIPLINE

### III.1 The bot trades, or nothing does
- **No manual entries. Ever.** Not "I see a great setup." The bot or nothing.
- **No manual management of open trades.** No moving stops, no early exits "to be
  safe," no letting it run past TP. (This was done on 2026-09-02 out of nerves —
  SL to 4308, TP to 4304. It should not have been. Those were not backtested
  actions and they inject discretion back into a system whose whole point is to
  remove it.)
- The **only** permitted manual action on a live position is the **kill switch**
  (III.6).

### III.2 The direction gate is law
- The D1 EMA20 bias gate decides direction. **No overriding it** because the
  move "obviously" continues. On 2026-09-02 a blocked long (FVG_NY BUY at ~4378)
  would have stopped out on the very next candle — the gate was right and the
  hindsight-perfect entry was a fantasy. This is the canonical example; re-read
  it whenever the urge to override appears.
- Open question for research (not a live override): the 20-day EMA is *slow* and
  held a stale bias through a full intraday reversal. Test faster variants
  (EMA10, H4 close, intraday EMA20 cross) — see Part V.

### III.3 One frozen config
- After Part I passes, the config is **frozen**. Any change requires:
  hypothesis → backtest → holdout → 4-week paper test → written entry in
  `RESEARCH_LEDGER.md` → deploy.
- **No hot-patching a live bot.** (Done tonight because the running config was
  net-negative; it should be a once-a-quarter event, always logged, never
  routine.)

### III.4 Session discipline
- Trust the session gates. No extending a session because it "looks good."
- No entries in the **last 15 minutes** of a leg's session (not enough runway).

### III.5 News blackout
- Maintain a hardcoded list of high-impact events (US CPI, NFP, FOMC decision +
  presser, PCE, PPI, GDP, ISM, Fed Chair speeches, Jackson Hole, major
  geopolitical scheduled events).
- **No new entries from −15 min to +15 min** around each. Existing positions are
  left to their stops.
- Refresh the list on the 1st of every month from an economic calendar.

### III.6 The kill switch
- A `STOP` file in the project root. The loop checks for it every scan. If
  present: close all positions at market, halt, alert, do not resume until the
  file is removed *and* a reason is logged.
- Tested before go-live: create the file mid-trade, confirm flat + halted +
  alerted within one scan.

### III.7 Operator discipline (the human)
- **Check the bot twice a day** (morning, evening). Not more. Over-monitoring
  leads to over-intervening.
- **Do not watch ticks.** The expectancy plays out over hundreds of trades.
- **Red day:** the system working as designed. Do nothing.
- **Green day:** the system working as designed. Do nothing. Do not increase size.
- **Do not take it personally.** The market is not doing anything *to you*.
- Keep a one-page "why I built this and how it works" note. Re-read it on bad days.

---

## PART IV — RESILIENCE & OPERATIONS

*A bot that silently dies at 3 a.m. is worse than no bot.*

> **Status 2026-09-03 (rohith-2):** IV.2, IV.3, IV.5, IV.7 and the kill switch
> (III.6) are **implemented and tested** — `src/core/resilience.py`, hooked into
> `main_loop._run_guarded()`. `scripts/watchdog.py` exists (IV.1) but is not
> auto-started and has **no alert channel** yet. IV.4 (external heartbeat
> monitor), IV.6 (weekend/rollover/maintenance), IV.8 (structured logging) and
> IV.9 (daily report) are still to do.

### IV.1 Watchdog + auto-restart
- A separate supervisor (Windows Task Scheduler entry, or a tiny `watchdog.py`)
  that checks `main_loop` is alive every 60 s, restarts it on death, and
  **alerts** (Telegram bot / push / email) on every restart with the last 50 log
  lines.

### IV.2 MT5 reconnection
- Current behaviour: if the MT5 terminal drops, `copy_rates_from_pos` returns
  `None`, the loop hits `continue`, and it spins forever — no trades, no error,
  no alert.
- Fix: after 3 consecutive `None` fetches, call `mt5.shutdown()` + re-`initialize()`.
  Alert if reconnect fails 3×.

### IV.3 State persistence
- Write `last_fired_candle` and the open-position → magic map to a JSON file each
  scan. Reload on startup so a restart mid-candle cannot re-fire a signal.

### IV.4 Heartbeat + external monitor
- Touch `logs/heartbeat` with a timestamp every scan. A separate cheap monitor
  (phone cron, UptimeRobot on a pushed status file, etc.) alerts if it goes
  stale > 3 min.

### IV.5 Startup safety block
On every start, refuse to run unless ALL pass:
- symbol resolves and is tradeable
- spread is within sane bounds
- `account_info().login` matches the expected account number
- balance within an expected range (catches wrong-account connection)
- `trade_allowed` is True (catches investor-password connection — error 10017)
- AutoTrading enabled (catches error 10027)

### IV.6 Broker realities
- **Maintenance window:** Exness has a short daily maintenance window. Detect
  "market closed" / "trade disabled" and pause gracefully instead of retry-spamming.
- **Weekend:** gold gaps on Sunday open. Decide and document: **close all
  positions Friday ~21:00 IST**, no positions held over the weekend.
- **Rollover:** spreads balloon around 00:00 server time. No entries in that
  ±10 min window.

### IV.7 Single-instance guard
- Lockfile (`logs/main_loop.lock` with PID). Refuse to start a second instance.
  (The "two processes" scare on 2026-09-02 was a venv launcher stub, not a real
  double-run — but a real double-run is a genuine risk and this prevents it.)

### IV.8 Logging
- Structured JSON lines, rotated daily, retained 90 days.
- Log: every signal (fired / blocked / deduped + reason), every order (full
  request + full response), every SL/TP set, every gate decision, every
  exception with stack trace, every reconnect, every breaker trip.
- Goal: any trading day can be fully reconstructed from the log alone.

### IV.9 Daily auto-report
- 23:30 IST cron: trades today, P&L, balance vs plan, current drawdown, error
  count, bot uptime %, any breaker trips. Delivered to the operator.

### IV.10 Backups
- Repo is in git (done). Additionally: daily export of the MT5 account statement
  and the trade ledger to a dated file; weekly off-machine copy.

---

## PART V — STRATEGY IMPROVEMENTS (validate each before applying)

### V.1 On the table now
- **FVG size filter.** LuxAlgo test 2026-09-03: minimum ~$4.4 gap → PF 1.66 →
  2.11, max drawdown 28.5% → 19.6%, on ~half the trades. Validate on the
  holdout, then apply.
- **Faster D1 gate.** A/B EMA10 / H4 close / intraday EMA20 cross vs the current
  D1 EMA20. Pick by holdout PF. The current gate is too slow on reversal days.

### V.2 Exit research (currently the weakest-researched layer)
- Per leg, on the holdout: fixed TP (current) vs trail-after-1.5×ATR vs
  partial-at-2×ATR-then-runner vs ATR Chandelier vs time-stop-at-N-bars.
- The current fixed TP multiples were chosen on the *training* window.
- Also test: move stop to breakeven after +1×ATR (note: this can *hurt* by
  killing winners at BE — measure, don't assume).

### V.3 Regime & volatility gating
- Skip or halve size when ATR percentile > 90th (stops meaningless) or < 10th
  (targets unreachable).
- From I.6: turn each leg off in the regime where it bleeds.

### V.4 Per-leg spread gate
- FVG_NY ($5.50 stop) should reject entries at a spread that SQUEEZE_ASIA ($22
  stop) tolerates. Replace the single global `MAX_SPREAD_POINTS` with a per-leg
  value scaled to its stop distance.

### V.5 Leg-correlation check
- FVG_NY and RANGEREJECTION_NY trade the same session, often the same direction.
  Measure their trade-level correlation. If high, they are one bet at 2× size,
  not diversification — and `max_same_direction` should be 1, not 2.

### V.6 Account-level anti-martingale
- After a green week, allow the *upper* end of the sizing ladder; after a red
  week, the *lower* end. Systematic, bounded, not discretionary.

### V.7 What NOT to add
- No new strategies. No new indicators. No new timeframes. No fundamental-data
  pipeline. The research is explicit that over-filtering kills these systems and
  there are already enough entries. The missing piece is *proof*, not *more
  system*.

---

## PART VI — MONITORING, REVIEW & LEARNING

### VI.1 Weekly review (every Sunday)
- Actual vs backtest-expected for the week, per leg.
- Drawdown vs limits.
- **Rule-adherence audit:** did any manual intervention happen? Why? (The answer
  should almost always be "no".)
- Log it in a running `docs/trade_logs/WEEKLY_REVIEW.md`.

### VI.2 Monthly deep review
- Re-run the full backtest with the last month's live data appended.
- Has live PF diverged from backtest PF? By how much?
- If live is materially worse (see tripwire) for **2 consecutive months** →
  halt, re-run Part I.

### VI.3 The divergence tripwire (quantitative, not a feeling)
- Track rolling 30-trade PF from live results.
- **If it drops below 1.0 → pause new entries, investigate before resuming.**
- **If it drops below 0.8 → full stop, treat as edge decay, re-validate.**

### VI.4 Automated trade journal
- Every trade recorded with: leg, session, entry/exit, P&L, MFE, MAE, and what
  the backtest expected for that setup family. Builds the dataset for VI.2 and
  future research.

### VI.5 Edge-decay awareness
- All edges decay as they get crowded or as the regime that produced them ends.
- Quarterly: explicitly ask "is this still working, and is there a reason it
  might stop?" Plan for the day it stops, not just the day it works.

---

## PART VII — THE GO-LIVE GATE

*Real money does not start until every box is checked. The 2026-09-30 date is a
target, not a deadline that overrides this list.*

**Edge (Part I):**
- [ ] Holdout test: PF > 1.2, drawdown < 45%, never below 50% of start
- [ ] Walk-forward: stable leg selection, median test PF > 1.2
- [ ] Monte Carlo: 95th-pct drawdown < 40%, P(ruin) < 1%
- [ ] Parameter perturbation: PF > 1.2 across the ±20% cloud
- [ ] Every leg clears its random-entry control on out-of-sample data
- [ ] Cost stress: PF > 1.2 at 2× cost with stop-slippage modeled
- [ ] Long-history (Dukascopy) test covers ≥ 1 bear market and 1 chop period
- [ ] 8+ week forward paper test, live-demo PF within 20% of backtest

**Rules (Parts II–III):**
- [ ] Starting capital decided; if ~$100, first-phase risk accepted in writing
- [ ] Sizing ladder table filled in and coded as a balance lookup
- [ ] All loss caps (daily/weekly/monthly/peak) decided and coded
- [ ] Circuit breakers coded and unit-tested
- [ ] Profit ring-fencing schedule decided
- [ ] News blackout list built and wired in
- [ ] The rulebook is a single finished document

**Resilience (Part IV):**
- [ ] Watchdog + auto-restart + alert — tested by killing the process
- [ ] MT5 reconnect — tested by pulling the network
- [ ] Kill switch — tested mid-trade
- [ ] Startup safety block — tested against a wrong-account connection
- [ ] Structured logging + daily auto-report live
- [ ] Weekend flatten + rollover skip + maintenance-window handling coded

**Operations:**
- [ ] One dry-run week where the operator follows the rulebook by hand to confirm
      it is actually followable
- [ ] Broker: master password, AutoTrading on, correct account verified
- [ ] "Kill criteria" document written — the conditions for shutting this down
      permanently

---

## PART VIII — POST-LIVE OPERATIONS

- **Week 1–2:** minimum size regardless of what the ladder allows. Check daily.
  Intervene never (kill switch only).
- **First negative month:** mandatory halt + review. Do not "push through."
- **Monthly:** re-validate with live data appended (VI.2).
- **Quarterly:** full re-validation; assess edge decay (VI.5).
- **Scaling:** move up the sizing ladder only on balance, never on a good feeling.
- **The account is disposable.** If it blows the −30% peak kill, it is done —
  post-mortem, then decide from scratch whether to restart. It never gets a
  top-up.

---

## APPENDIX — EXPLICITLY DO NOT

- Do not optimise parameters to raise backtest PF (that *is* overfitting).
- Do not add strategies, indicators, or timeframes.
- Do not override the bot's direction based on a macro view.
- Do not move stops or targets on open trades.
- Do not add funds to a drawing-down account.
- Do not skip the holdout because training results look good.
- Do not go live on 2026-09-30 if the Part VII gate is not 100% passed.
- Do not run this on money you need for anything else.
- Do not confuse a high win rate with a good system — for this system they are
  opposites.

---

## PRIORITY ORDER (if time is short)

1. **I.1 Holdout test** — one script, one day. Go/no-go on everything.
2. **I.3 Monte Carlo bootstrap** — turns "35% drawdown" into a real worst case.
3. **II — write the rulebook** — it is the mission's actual deliverable.
4. **IV.1 + IV.2 + IV.6 watchdog / reconnect / kill switch** — stop the bot from
   dying silently.
5. **I.7 cost & slippage stress** — is PF 1.5 real or an artifact of optimistic
   fills?
6. **I.9 8-week paper test** — the clock on this starts the day the config
   freezes, so freeze early.
7. Everything else.
