# Ultra Core — repository guide

**What this is:** an autonomous MetaTrader 5 bot that trades XAUUSD (gold) on a
small account at a fixed 0.01 lots, plus the research pipeline that built and
keeps validating it. Single symbol, single broker (Exness demo #198874999),
Windows + Python 3.11.

**Read this first** if you're picking the project up. It is the map: what runs,
where everything lives, what state it's in, and what's still broken.

Last updated: 2026-09-08.

---

## 1. The one-minute mental model

```
                 research pipeline                        live loop
   MT5 bars ──> features ──> candidate rules ──> backtest ──> validation_ledger
   (.npy)       (market_study) (candidates.py)   (engine.py)   (fingerprint)
                                                                    │
                                              main_loop.py checks ──┘ then trades
```

- **Strategies are data, not classes-per-idea.** Every entry rule lives in
  `src/research/candidates.py` as a function returning a +1/0/−1 signal array,
  keyed by an `XAU-###` id. `src/strategies/portfolio_v4.py` wraps a chosen few
  into live `BaseStrategy` objects.
- **The backtest engine is the source of truth.** `src/backtesting/engine.py`
  fills on M1 (or M5/M15 when M1 isn't available), models spread + slippage +
  the 6% daily breaker, and is what every number in the ledger comes from.
- **Nothing goes live unvalidated.** `main_loop` fingerprints its own config on
  startup and refuses to trade unless that exact fingerprint is in
  `research/validation_ledger.json`. (See §6 — this gate is currently tripping.)

---

## 2. Entry points — what to run

| Command | What it does |
|---|---|
| `python -m src.core.main_loop` | **The bot.** Connects to MT5, runs `PORTFOLIO_V4`, trades within the hard rules. This is the only thing that touches the account. |
| `python -m scripts.fetch_history` | Re-download price bars from MT5 into `research/data/*.npy` (gitignored, regenerable). Do this first on a fresh clone. |
| `python -m scripts.validation.part1_suite holdout` | The real out-of-sample edge test (2025-01-01 → 2026-05-20). Also: `walkforward montecarlo perturb randomentry regime cost ladder`. |
| `python -m scripts.validation.aug_5legs [START] [END]` | Backtest the current legs over any window, live config, with per-leg breakdown. Defaults to August 2026. |
| `python -m scripts.watchdog` | Restarts `main_loop` if it dies. Not auto-started; no alerting yet. |
| `python -m scripts.protect_profit` | Manual one-shot: move stops to lock in profit on open positions. Run by hand. |

Everything under `scripts/` runs as `python -m scripts.<name>` from the repo
root (they import `src.*`).

---

## 3. What runs live — current config (2026-09-08)

`main_loop` runs **`PORTFOLIO_V4`** from `src/strategies/portfolio_v4.py`:

| Leg | Magic | Session IST | SL/TP ×ATR | Notes |
|---|---|---|---|---|
| `FVG_NY_SWEEP_OR_VOID` | 3022 | 17:30–21:30 | 0.50 / 2.50 | liquidity-filtered FVG — carries the book |
| `FVG_NY_TIGHT` | 3013 | 17:30–21:30 | 0.50 / 2.50 | unfiltered FVG — trades the gaps the filter rejects |

Same underlying gap detector (candidate `XAU-092`) for both. The engine's
**Highlander rule** allows only one FVG leg to fire per M15 candle, ranked
`SWEEP_OR_VOID > SWEEP > VOID > TIGHT > ASIA`.

**Benched, in the file but not in the list:**
- `FVGNYSweep`, `FVGNYVoid` — strict subsets of `SWEEP_OR_VOID`, always lose the
  Highlander ranking, took 0 trades in every backtest window. Removed 2026-09-08.
- `FVGAsiaSweep` (magic 3021) — net-negative over 1- and 3-month windows (its
  morning stop-outs burn the shared 6% daily breaker and starve the NY legs);
  helps only over a full year. Off until the $100-account early months are past.
- `SqueezeBreakAsia`, `EMAStackLondonTight`, `RangeRejectionNYTight`,
  `FVGNYTight`'s old siblings — the original 2026-09-01 4-leg portfolio, kept
  for reference. Declared dead (no OOS edge) 2026-09-03, partially revived via
  the FVG liquidity work (HYP-059+).

**Hard rules, enforced in code** (`src/core/execution_handler.py`,
`src/core/main_loop.py`), not guidance:

| Rule | Value | Where |
|---|---|---|
| Lot size | **0.01 per order, always** (pyramid adds too) | `FIXED_LOT_SIZE` in `execution_handler.py` |
| Total exposure | **0.02 lots**, **2** concurrent positions | `MAX_TOTAL_VOLUME`, `MAX_CONCURRENT_POSITIONS` |
| Daily loss breaker | **6%** of balance → no new entries until 00:00 IST | `risk_manager.py` |
| D1 EMA20 bias gate | **ON** — only trade with the daily trend (HYP-065, reversed the earlier "off" decision) | `ENABLE_D1_GATE` in `main_loop.py` |
| Trading window | **06:00–21:30 IST**, no weekend holds, skip ±10 min around 00:00 UTC rollover | `src/core/market_hours.py` |
| Trailing stops | **OFF** (backtested PF 0.592, −$93.59 — it's the killer) | `ENABLE_TRAILING` in `main_loop.py` |
| Pyramiding | **OFF** | `ENABLE_PYRAMIDING` |

**Account:** Exness-MT5Trial11 demo #198874999. Real-money target date was
2026-09-30; the operating rulebook (sizing floor, tighter early loss caps,
paper→live promotion path) is still unwritten — that's the main open
deliverable. See `docs/research/REAL_MONEY_READINESS.md`.

---

## 4. Directory map — where everything lives

```
src/
  core/                     THE LIVE SYSTEM
    main_loop.py              the loop: scan → signal → gate → execute → manage
    execution_handler.py      the single order chokepoint; enforces 0.01 / caps
    risk_manager.py           ATR stops, session multipliers, 6% breaker, macro-rule grep
    data_fetcher.py           pulls M15/M5/M1/D1 bars from MT5 at runtime
    market_hours.py           weekend flatten, trading window, rollover skip
    resilience.py             lockfile, kill switch (create file `STOP`), reconnect, heartbeat
    risk_rules.py             per-balance sizing ladder (Part II of the readiness doc)
    validation_ledger.py      config fingerprint record + startup check
    system_config.py          the dataclass that gets fingerprinted
    trade_log.py              structured JSONL event log → logs/trades/YYYY-MM-DD.jsonl
    alerts.py                 alert stubs (no channel wired yet)
  strategies/
    portfolio_v4.py           LIVE: PORTFOLIO_V4 list + every leg class (live + benched)
    base_strategy.py          BaseStrategy / Signal / mt5 shim
    ema_stack.py, luxalgo_fvg.py, supertrend_ema.py, trend_sniper_sar.py
                              RESEARCH ONLY — not imported by main_loop
    archive/                  strategies that lost to the random-entry control
  research/
    candidates.py             THE RULE LIBRARY — build_library() → {XAU-###: Candidate}
    candidates_v2.py          later screening variant
    market_study.py           build_features(), session_mask(), atr(), time_of_day_atr()
    liquidity.py              liquidity_state(), is_liquidity_void() — the FVG filters
    structure.py              BigBeluga/SMC-style pivots, BOS/CHoCH, order blocks (A/B tool)
    screener.py               candidate screening harness
  backtesting/
    engine.py                 BacktestEngine — fills, costs, breaker, Highlander, gates
    data.py                   load_bars() → BarSet(m15, m5, m1, d1, h4)
    costs.py                  SCENARIOS: observed / realistic / stressed
    metrics.py                PF, drawdown, ruin, etc.

scripts/
  validation/               CURRENT backtests. part1_suite.py is the gate suite.
                            aug_5legs.py, combined_portfolio_5legs.py, last_month.py, …
  d1_study/                 daily-timeframe research (the "D1 system" plan)
  oneoff/                   superseded one-shot utilities, kept for reference
  archive/                  dead diagnostics
    rohith2_deadend/          A/B tests that all came back negative (kept as a record)
  fetch_history.py, watchdog.py, protect_profit.py, run_backtest.py   top-level utilities
  phase2_*, phase3_*, tier2_*, portfolio_merge_*, screen_*   OLD research runners (see §7)

research/
  data/                    XAUUSDm_{M1,M5,M15,H1,H4,D1}.npy + .manifest.json
                           .npy is gitignored — regenerate with scripts.fetch_history
  validation/              part1_*.json + every scripts/validation/*.json result
  validation_ledger.json   the config-fingerprint allowlist main_loop checks
  runs/                    timestamped backtest outputs (Aug–Sep 2026). Mostly historical.
  candidates/, market/, screen/, d1_study/   research artifacts

docs/
  REPO_GUIDE.md            this file
  plans/
    DAILY_BATTLE_PLAN.md     current market read + live config + session review — start here daily
    DAILY_MARKET_ANALYSIS.md cross-asset macro. READ LIVE by RiskManager._load_macro_rules()
                             — see the warning header; certain phrases flip a live risk override
    DAILY_GOALS.md, BATTLE_PLAN_2026-09-01_MORNING.md
  research/
    RESEARCH_LEDGER.md       every hypothesis HYP-001..HYP-065+ with verdict and evidence — the spine
    STRATEGY_REGISTRY.md     every strategy, its grade, why
    REAL_MONEY_READINESS.md  the go-live gate: Parts I–VI, what's done, what's open
    SYSTEM_FAULTS.md         the fault list that declared portfolio_v4 dead (2026-09-03)
    D1_SYSTEM_PLAN.md        the daily-timeframe replacement plan
    PHASE3_FULL_SWEEP_RESULTS.md   how the original portfolio_v4 was chosen
    EXTERNAL_INDICATORS_ASSESSMENT.md   BigBeluga / LuxAlgo SMC tests (all negative)
    AUDIT_LOOP.md, MONDAY_PLAN_ANALYSIS_*.md, REAL_MONEY_READINESS_RATING_*.md
    reference/luxalgo_smc_pine.txt   the raw LuxAlgo SMC Pine source, for reference
  trade_logs/
    LIVE_TRADE_HISTORY.md    closed deals pulled from MT5 (STALE — see §6)
    STATUS_YYYY-MM-DD.md     point-in-time trading status reports

reports/                   longer-form analysis write-ups (Sep 1–2, historical)
.agents/                   AI skills (mt5-trade-auditor, xauusd-trading-prep, pandas-backtesting) + rules
logs/                      runtime output — all gitignored except loop_state.json + trade_ledger.jsonl
  trades/                    the structured JSONL day logs from trade_log.py
```

---

## 5. How the live loop works (one scan)

`main_loop._run_guarded()` → `run()`, every 60 s:

1. **Resilience checks** — lockfile held? kill switch file `STOP` present → flatten
   and halt. Restore `logs/loop_state.json` so a mid-candle restart can't re-fire.
2. **Startup only:** MT5 safety check (login 198874999, trade allowed, balance in
   range, symbol tradeable) + config-integrity gate (§6).
3. **Fetch** the last 250 M15 + M5/M1/D1 bars from MT5.
4. **D1 bias** — daily close vs D1 EMA20 → BULLISH / BEARISH.
5. For each leg, `evaluate()` on the closed M15 bar → maybe a `Signal`.
6. **Gates**, in order: dedup (same candle already acted), D1 bias (block
   counter-trend), `market_hours.allow_new_entry()` (window / weekend / rollover),
   exposure caps (0.02 / 2 positions), Highlander (one FVG leg per candle).
7. **Execute** survivors immediately (no next-candle confirm) at 0.01 lots via
   `ExecutionHandler.send_order` — the one place lot size and caps are enforced.
8. **Manage** open positions: fixed SL/TP only (trailing OFF), consolidation
   exit, weekend flatten after Fri 22:30 IST.
9. **Breaker** — if today's realised loss ≥ 6% of balance, stop opening until
   00:00 IST.

The backtest engine mirrors all of this. Where they differ historically has
been a bug every time (HYP-042/045: main_loop's queue-and-confirm silently
dropped signals the engine executed immediately → `execute_immediately = True`
on every leg).

---

## 6. Known loose ends (as of 2026-09-08)

1. **Config-integrity gate — CLEARED 2026-09-08.** The live 2-leg + D1-gate-ON
   config (fingerprint `c7526993730d7348`) is now recorded in
   `research/validation_ledger.json` via
   `scripts/validation/record_live_config.py`. `main_loop` will start.
   **But the recorded OOS holdout (2025-01-01 → 2026-05-20) FAILS I.1 on
   drawdown:** n=559, PF 1.61, net +$916, min balance $104.20 (never below the
   $105.74 start), **maxDD 46.95% (> the 45% bar)**. This is the known 2-leg
   NY-only correlation cost (HYP-064 found the same with 4 legs at 54.7%) —
   drawdown deepens without a different-session leg to fill NY's rough
   stretches, even though P(ruin) stays low. The gate only checks "was this run
   and written down", not "was it good" — the I.1 failure is recorded
   explicitly in the ledger entry. Live at your discretion; the drawdown is the
   thing to watch this week.
2. **`ENABLE_TRAILING` had been flipped to `True`** in the working tree,
   contradicting its own comment block and every backtest. Reverted to `False`
   2026-09-08. If you see it `True` again, that's a regression.
3. **`README.md` is stale** — describes the 4-leg session-specialist portfolio
   and a "no edge, don't trade" status from 2026-09-03 that later FVG work
   (HYP-059+) moved past. This guide supersedes it.
4. **`docs/trade_logs/LIVE_TRADE_HISTORY.md` stops at 2026-09-02 17:44** —
   missing the Sep 2 evening + Sep 3 fills. Re-run the mt5-trade-auditor skill.
5. **`scripts/paper_test_review.py` has stale magics** (`3011–3014` = the old
   legs). The live magics are `3013` + `3022`. Fix before relying on the weekly
   live-vs-backtest comparison.
6. **`main_loop.py` line 44 comment** still says "kept in ema_stack.py" and the
   HYP numbers in nearby comments predate the FVG rework — cosmetic, but
   misleading when reading fast.
7. **Rulebook unwritten.** The core deliverable in
   `xauusd-100-account-goal` / `REAL_MONEY_READINESS.md` Part II — position
   floor, early-stage loss caps tighter than 6%, paper→live promotion path —
   does not exist yet.

---

## 7. Housekeeping done 2026-09-08

- Deleted: `debug_output.txt` / `debug_output2.txt` (identical scratch), stale
  `logs/*.log` + `logs/main_loop.lock` + `logs/heartbeat` + `logs/positions.txt`
  (all regenerable / gitignored), all `__pycache__/` and `.pytest_cache/`.
- Moved: the loose `Smart Money Concepts … copy` Pine file from the repo root to
  `docs/research/reference/luxalgo_smc_pine.txt`.
- Staged the removal of `scripts/{d1_gate_ab,live_config_ab,luxalgo_fvg_ab}.py`
  (already superseded by copies in `scripts/archive/rohith2_deadend/`).

### Proposed but NOT done (needs a decision — see the session notes)

- **`scripts/` top level is cluttered** with ~20 superseded research runners
  (`phase2_*`, `phase3_*`, `tier2_*`, `portfolio_merge_v2/v3/honest`,
  `screen_candidates*`, `growth_path_*`, `robustness.py`, `survivability.py`).
  They're tracked history. Options: move to `scripts/archive/`, or leave.
- **`research/runs/` is 43 MB / 136 files** of Aug–Sep 2026 backtest outputs,
  75 tracked. The `RESEARCH_LEDGER` cites some by path. Options: keep, or prune
  to manifests + summaries only and drop the rest.
- **`src/` has 7 empty leftover dirs** (`analysis config data diagnostics
  execution logging orchestration`) — nothing on disk, nothing imports them.
  Safe to `rmdir`.
- **`reports/` (Sep 1–2)** overlaps `docs/research/`. Could fold in.
