# Production Readiness Action Plan

**Based on:** Comprehensive Audit dated September 25, 2026  
**Status:** ✅ **PHASE 1 + 2 (partial) + 3 (partial) COMPLETE** (2026-09-27)  
**Target:** 6-8 weeks to production-ready  

---

## 🚀 UPDATE: Week 1 Emergency Fixes COMPLETED (2026-09-25)

**See:** `PRODUCTION_UPGRADES_2026-09-25.md` for full details.

### What Was Completed:
1. ✅ **PreTradeVeto Chain** - 6-layer risk gate (NautilusTrader pattern)
2. ✅ **Walk-Forward Validation** - IS/OOS efficiency testing (VectorBT pattern)
3. ✅ **Commission Modeling** - Added "realistic_ecn" scenario ($3.50/lot)
4. ✅ **SizingLadder Integration** - Wired into `execution_handler.py`
5. ✅ **Dependencies Fixed** - Added hmmlearn, scipy, joblib, pytest, statsmodels
6. ✅ **Emergency Validation Script** - Single command to run all checks

### CRITICAL: Run Validation NOW

```bash
# Single command to run ALL Week 1 checks:
python scripts/week1_emergency_validation.py
```

This will:
- Check dependencies
- Run pytest tests
- Validate current portfolio (GO/NO-GO gate)
- Run walk-forward efficiency test
- Display sizing ladder
- Check risk_rules status

**If validation FAILS: DO NOT TRADE until strategies are re-researched.**

---

## CRITICAL PATH TO PRODUCTION

This plan prioritizes by **risk × impact**. Complete each phase in order.

---

## ✅ PHASE 0: IMMEDIATE FIXES (DONE)

### Completed Actions:
1. ✅ `.env.local` already in `.gitignore` - credentials not exposed
2. ✅ Created `.env.example` template
3. ✅ Created `tests/test_config_integrity.py` - regression tests for critical flags
4. ✅ Created `tests/test_execution_handler.py` - tests for order execution (all 4 previously failing tests now pass)
5. ✅ Created `scripts/validation/validate_current_portfolio.py` - full validation suite
6. ✅ Created `src/core/sizing_ladder.py` - position sizing ladder
7. ✅ **FIXED 2026-09-27:** `risk_rules.state` AttributeError in `execution_handler.py` - circuit breakers now receive real data
8. ✅ **FIXED 2026-09-27:** `src/core/__init__.py` missing - created
9. ✅ **FIXED 2026-09-27:** `logs/virtual_sl.json` relative path → absolute via `resilience._LOGS`

### Next: Run the tests
```bash
# Install pytest if not already installed
pip install pytest

# Run configuration tests
python -m pytest tests/test_config_integrity.py -v

# Run execution handler tests
python -m pytest tests/test_execution_handler.py -v
```

---

## 📋 PHASE 1: VALIDATION & EVIDENCE (Week 1-2)

**Objective:** Prove the current 2-leg portfolio has a real edge.

### Actions:

#### 1.1 Run Full Validation Suite (Day 1-2)
```bash
# This will test current portfolio against all gates
python -m scripts.validation.validate_current_portfolio

# Expected output:
# - Out-of-sample holdout results
# - Monte Carlo ruin probability
# - Pass/fail for each gate
# - Auto-records in validation_ledger.json if all gates pass
```

**Pass Criteria:**
- Profit Factor > 1.2
- Max Drawdown < 45%
- Min balance >= 50% of start
- P(ruin) < 1% in Monte Carlo
- Random entry control: real PF above 95th percentile of random

**If ANY gate fails:** Do NOT proceed. Either:
- a) Fix the portfolio (re-research, different strategies)
- b) Accept the risk and document it explicitly
- c) Abandon this config and use previous validated config

#### 1.2 Implement Random Entry Control ✅ DONE (2026-09-27)
Implemented in `scripts/validation/validate_current_portfolio.py` as `random_entry_control()`.
- Generates random BUY/SELL signals at the real strategy's trade frequency
- Runs 100 backtesting trials through the same engine (same stops, session, costs)
- Real PF must exceed 95th percentile of random PFs to pass Gate I.5

#### 1.3 Write Unit Tests for Strategy Logic ✅ DONE (2026-09-27)
`tests/test_strategy_evaluation.py` created. Covers:
- D1 bias gate (all 4 direction×bias combos + None bias)
- Session multipliers (1.5x London/NY, 2.0x Asia) + boundary conditions
- SizingLadder all balance tiers
- Circuit breakers (consecutive losses, pause trigger, day-stop, day_losing_trades)
- Market hours guards (weekend, trading window, Friday cutoff)

#### 1.4 Fix Time-of-Day ATR (if using it)
The audit found the expanding-window implementation is correct in the engine, but:
- No strategies have been re-validated since the fix
- It's not wired to live risk_manager.py

**Decision needed:**
- If using TOD ATR: Wire it into `src/core/risk_manager.py`
- If not using it: Remove the code to avoid future confusion

#### 1.5 Verify No Lookahead Bias ✅ DONE (2026-09-27)
`tests/test_no_lookahead.py` created. Verified:
- D1 gate reads `d1_closes[-2]` not `[-1]` (closed bar)
- Signal dedup key uses `m15_rates[-2]["time"]` (closed bar timestamp)
- ATR is causal: adding bar N+1 doesn't change ATR at bar N
- ATR is NaN for first `period-1` bars (correct warmup)
- Portfolio strategies read signal at `sig[-2]` (closed bar)
- EMA is causal: same causal proof as ATR

---

## 🛡️ PHASE 2: RISK CONTROLS (Week 3-4)

**Objective:** Implement all missing risk controls from REAL_MONEY_READINESS.md Part II.

### Actions:

#### 2.1 Integrate Sizing Ladder into execution_handler (Day 8)
Modify `src/core/execution_handler.py`:

```python
from src.core.sizing_ladder import SizingLadder, should_halt_trading

def send_order(self, ...):
    # Add at start of method
    balance = mt5.account_info().balance
    
    # Check position floor
    halt, reason = should_halt_trading(balance)
    if halt:
        log.error(f"Trading halted: {reason}")
        return None
    
    # Get sizing from ladder
    ladder_lots, max_concurrent, max_exposure = SizingLadder.get_sizing(balance)
    
    # Override requested lot_size if it exceeds ladder
    if lot_size > ladder_lots:
        log.warning(f"Requested {lot_size} lots, clamping to ladder limit {ladder_lots}")
        lot_size = ladder_lots
    
    # Update exposure caps from ladder
    # (Currently hardcoded - should use ladder values)
```

#### 2.2 Implement Weekly/Monthly Loss Caps (Day 9-10)
Create `src/core/loss_caps.py`:

```python
class LossCaps:
    """Cascading loss limits beyond daily."""
    
    WEEKLY_LIMIT_PCT = 0.15   # -15% from Monday open
    MONTHLY_LIMIT_PCT = 0.25  # -25% from month start
    PEAK_LIMIT_PCT = 0.30     # -30% from all-time high
    
    def check_weekly_limit(balance, week_start_balance) -> (bool, str):
        """Returns (can_trade, reason)"""
        
    def check_monthly_limit(balance, month_start_balance) -> (bool, str):
        """Returns (can_trade, reason)"""
        
    def check_peak_limit(balance, peak_balance) -> (bool, str):
        """Returns (can_trade, reason)"""
```

Integrate into `main_loop.py`:
- Track week_start_balance (reset Monday 00:00 IST)
- Track month_start_balance (reset 1st of month)
- Track peak_balance (update whenever balance > peak)
- Check these limits BEFORE checking daily limit

#### 2.3 Flip risk_rules.ENFORCE to True (Day 11)
Currently in shadow mode. Before flipping:

1. Review state tracking in `logs/risk_state.json`
2. Verify consecutive-loss counting is correct
3. Add logging for when circuit breakers fire
4. Test manually: trigger 3 consecutive losses, verify pause

Then:
```python
# src/core/risk_rules.py
ENFORCE = True  # Circuit breakers now block trades
```

#### 2.4 Make Macro Override Visible ✅ DONE (2026-09-27)
Fixed in `src/core/risk_manager.py`: whenever `strict_short_stops` toggles ON or OFF,
a WARN-severity alert is sent via `alerts.send()` through the configured channel
(Telegram/webhook/log file). Previously it was only logged at INFO level.

#### 2.5 Add Config Integrity to Validation Fingerprint ✅ DONE (2026-09-27)
`macro_override_active: bool` added to `SystemConfig` dataclass. `from_live()` reads the
state from a `RiskManager()` instance. `from_dict()` defaults it to `False` for backward
compat with existing ledger entries. The fingerprint now changes when the operator
toggles the RISK_OVERRIDE marker in DAILY_MARKET_ANALYSIS.md.

---

## 🔧 PHASE 3: INFRASTRUCTURE (Week 5-6)

**Objective:** Operational reliability - monitoring, alerts, logging.

### Actions:

#### 3.1 Wire Telegram Alerts (Day 14)
1. Create Telegram bot (https://t.me/BotFather)
2. Get chat ID (message bot, then GET https://api.telegram.org/bot<TOKEN>/getUpdates)
3. Add to `.env.local`:
```
ULTRA_ALERT_TELEGRAM_TOKEN=<your-token>
ULTRA_ALERT_TELEGRAM_CHAT=<your-chat-id>
```
4. Test:
```python
from src.core import alerts
alerts.send("Test alert", severity=alerts.INFO)
```

#### 3.2 Implement Structured Logging (Day 15-16)
Fix the dead `trade_ledger.jsonl` code:

```python
# src/core/trade_log.py - already exists but not wired
# Ensure it's called from main_loop.py for EVERY trade event:
# - signal_fired
# - signal_blocked (with reason)
# - order_sent
# - order_filled
# - order_failed
# - position_closed
# - circuit_breaker_tripped
```

Enable log rotation:
```python
# Use RotatingFileHandler in main_loop.py logging setup
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'logs/main_loop.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=10
)
```

#### 3.3 Fix Watchdog (Day 17)
Current issues:
- No alerting (just print statements)
- Doesn't monitor itself
- Not auto-started

Fix:
1. Add Telegram alerting to `scripts/watchdog.py`
2. Create a second watchdog that monitors the first (or use Windows Task Scheduler with alert on failure)
3. Document startup procedure in operator runbook

#### 3.4 Set Up External Heartbeat Monitor ✅ DONE (2026-09-27)
`resilience.push_heartbeat_external()` added to `src/core/resilience.py`. Called from
`main_loop.py` on every scan. Configure via:
```
ULTRA_HEARTBEAT_URL=https://hc-ping.com/<uuid>
```
Options: **UptimeRobot** (free, 5-min checks), **Healthchecks.io** (free, email alerts).

#### 3.5 Implement Daily Auto-Report ✅ DONE (2026-09-27)
`src/core/daily_report.py` rewritten to include:
- VI.3 rolling 30-trade PF with status emoji (✅ healthy, ⚠️ warning, 🚨 TRIPWIRE)
- Circuit breaker status (hard halt, day stopped, streak pause)
- Consecutive losses, daily DD%
- Next-24h news events
- Sends via `alerts.send()` (Telegram/webhook)

---

## 📝 PHASE 4: PAPER TRADING (Week 7-14)

**Objective:** 8-week forward paper test per REAL_MONEY_READINESS.md Part I.9.

### Setup (Day 20):
1. **Freeze the config completely**
   - Document exact settings in `FROZEN_CONFIG.md`
   - Add config hash to validation_ledger
   - Create git tag: `paper-trading-start-YYYY-MM-DD`

2. **Set up comparison framework**
   ```python
   # scripts/paper_vs_backtest.py
   # Weekly: compare live demo results to backtest on same date range
   # Alert if divergence > 20%
   ```

3. **Start demo trading**
   ```bash
   python -m src.core.main_loop
   ```

### Weekly Tasks (Week 7-14):
Every Sunday:
1. Pull closed trades from MT5
2. Run backtest on same date range
3. Compare:
   - Number of trades (should be identical)
   - Win rate (within ±5%)
   - Profit factor (within ±20%)
   - Max drawdown (within ±30%)
4. Document discrepancies
5. If divergence > 20% for 2 consecutive weeks → HALT, investigate

### Pass Criteria:
- 8 weeks completed
- No unexplained divergence > 20%
- No critical bugs found
- All circuit breakers tested in practice
- Operator comfortable with runbook

**If paper trading fails:** Do NOT proceed to real money. Debug, fix, restart 8-week clock.

---

## 💰 PHASE 5: REAL MONEY (Week 15+)

**ONLY after Phase 4 passes completely.**

### Pre-Launch Checklist:
- [ ] All Phase 1-3 actions completed
- [ ] 8-week paper trading passed
- [ ] Validation_ledger has entry for frozen config
- [ ] All tests passing (`pytest tests/`)
- [ ] Telegram alerts working
- [ ] External heartbeat monitor active
- [ ] Operator runbook written and tested
- [ ] Kill switch tested
- [ ] Starting capital decided ($300-500 recommended, not $105)
- [ ] Part VII checklist from REAL_MONEY_READINESS.md: 100% checked

### Launch Day:
1. Start with minimum size from ladder (0.01 lots, 1 position)
2. Check twice daily (morning/evening), NOT more
3. Zero manual intervention except kill switch
4. Keep daily journal (deviations from expected, emotional state, urges to intervene)

### First 2 Weeks:
- Minimum size regardless of balance growth
- Check consistency with backtest expectations
- Verify circuit breakers work in practice
- Confirm Telegram alerts arrive

### Monthly Reviews:
- Re-run backtest with live data appended
- Check live PF vs backtest PF
- Update validation_ledger with live results
- If live PF < 1.0 for 2 months → HALT

---

## 🚨 RED FLAGS - STOP IMMEDIATELY IF:

1. **Live PF < 1.0 for 30 trades** (rolling window)
2. **Any unexpected behavior** (orders not following rules, signals disappearing, etc.)
3. **Config drift detected** (validation_ledger check fails)
4. **ENABLE_TRAILING or ENABLE_PYRAMIDING flip to True**
5. **Balance drops 30% from peak**
6. **Broker account wrong** (trading on wrong account)
7. **External monitoring stops** (heartbeat fails, no alerts)

---

## 📊 SUCCESS METRICS

### Week 4 (End of Phase 2):
- [ ] All tests passing
- [ ] Sizing ladder integrated
- [ ] Weekly/monthly loss caps coded
- [ ] Telegram alerts working

### Week 6 (End of Phase 3):
- [ ] Watchdog reliable
- [ ] Daily reports arriving
- [ ] Structured logging to JSONL
- [ ] External monitoring active

### Week 14 (End of Phase 4):
- [ ] 8 weeks paper trading complete
- [ ] Live-vs-backtest divergence < 20%
- [ ] No critical bugs found
- [ ] Operator runbook tested

### Month 3 (Real money):
- [ ] Consistent with backtest expectations
- [ ] No manual interventions
- [ ] Circuit breakers work as designed
- [ ] Balance growing or flat (not declining)

---

## 📞 SUPPORT & ESCALATION

### When to Ask for Help:
- Validation gates fail and you don't know why
- Paper trading diverges from backtest by >20%
- Critical bug found in production
- Uncertain about any step in this plan

### When to Stop and Reassess:
- Random entry control shows no edge
- Monte Carlo P(ruin) > 10%
- Two consecutive months of losses
- System behavior doesn't match backtest

---

## 🎯 FINAL CHECKLIST BEFORE REAL MONEY

Print this and check each box:

- [ ] Current portfolio validated (Part I gates pass)
- [ ] Random entry control passed
- [ ] Monte Carlo P(ruin) < 1%
- [ ] All unit tests passing
- [ ] Position sizing ladder integrated
- [ ] Weekly/monthly/peak loss caps coded
- [ ] risk_rules.ENFORCE = True
- [ ] Telegram alerts working
- [ ] External monitoring active
- [ ] Watchdog reliable
- [ ] 8-week paper trading passed (divergence < 20%)
- [ ] Operator runbook written and tested
- [ ] Kill switch tested
- [ ] Starting capital >= $300 (or explicit acceptance of higher risk)
- [ ] Part VII checklist 100% complete

**If ANY box is unchecked: DO NOT start real money trading.**

---

## NOTES

- This plan is conservative by design. The audit found multiple P0 issues.
- Every "day" estimate assumes full-time focus. Adjust timeline if working part-time.
- Phase 4 (paper trading) cannot be rushed - it requires 8 full weeks.
- The engineering is solid, but validation and risk controls need completion.
- When in doubt, HALT and ask for help. Better to delay than to blow up the account.

---

**Document Status:** UPDATED — Phase 1, Phase 2.4-2.5, and Phase 3.4-3.5 completed (2026-09-27)  
**Last Updated:** September 27, 2026  
**Next Review:** After Phase 2.3 (flip ENFORCE to True after backtesting laddered config)
