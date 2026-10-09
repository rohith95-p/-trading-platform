# 🎯 THURSDAY BATTLE PLAN - October 8, 2026

**Created:** 1:58 PM IST  
**Status:** Pre-market ready

---

## 📊 CURRENT SITUATION

### Account Status:
- **Balance:** $175.21
- **Starting Balance (Tuesday):** $185.84
- **Net P&L (Wed):** -$10.63 (-5.7%)
- **Account Type:** Exness Demo

### Yesterday (Wednesday) Recap:
- **3 trades executed, all SELL**
- **5:45 PM:** -$2.80
- **6:01 PM:** -$3.88  
- **6:15 PM:** Result unknown
- **DISASTER:** Dedup bug blocked trading for 2.5 hours during peak NY session (6:15-8:45 PM)
- **Daily loss limit triggered** at -3.6%, bot shut down at 6:18 PM
- **Lost ~2.5 hours of prime NY trading time** due to slow bug detection

### Market Conditions:
- **D1 Bias:** BEARISH (price $4,128 < EMA20 $4,224)
- **Spread:** $0.24 (normal)
- **Current Session:** London Open (1:58 PM IST)
- **Next Peak:** NY session 5:30-9:30 PM (3.5 hours away)

---

## 🎯 TODAY'S OBJECTIVES

### Primary Goal:
**Execute cleanly. Get 4-6 quality trades without bugs blocking the system.**

### Secondary Goals:
1. Monitor dedup bug fix (30-min auto-cleanup added to main_loop.py line 442)
2. Watch for daily loss limit triggers
3. Track if BEARISH bias allows enough SELL opportunities
4. Validate hourly Telegram monitoring is accurate

---

## ⚙️ FIXES DEPLOYED SINCE YESTERDAY

### 1. Dedup Bug Fix (CRITICAL)
- **File:** `src/core/main_loop.py` line 442
- **Fix:** Auto-clean dedup entries older than 30 minutes
- **Status:** ✅ Applied, needs live validation

### 2. Hourly Monitor Fix
- **File:** `scripts/hourly_monitor.py`
- **Fix:** Changed from reading `trade_ledger.jsonl` to `logs/trades/YYYY-MM-DD.jsonl`
- **Status:** ✅ Applied

### 3. New Monitoring Tools
- **`scripts/dedup_monitor.py`** - Early warning for stale dedup entries
- **`scripts/restart_bot.py`** - Quick recovery tool
- **Status:** ✅ Created, not yet integrated into workflow

---

## 📋 PRE-MARKET CHECKLIST

- [x] MT5 connected (Exness demo, account 198874999)
- [x] Symbol XAUUSDm tradeable, spread normal ($0.24)
- [x] No open positions
- [x] D1 bias confirmed: BEARISH → SELL only
- [x] Bot status checked (currently stopped after pre-market check)
- [x] Lock file cleared
- [ ] Bot started fresh at 4:30 PM
- [ ] Hourly monitor running
- [ ] Dedup monitor scheduled

---

## ⏰ TODAY'S TRADING SCHEDULE

### Phase 1: London Open (NOW - 3:30 PM)
- **Active Strategies:** 2/6 (LONDON_LIQUIDITY_SWEEP, FVG_LONDON_TIGHT)
- **Expected:** 0-1 trades
- **Action:** Let bot run, passive monitoring

### Phase 2: Pre-NY Setup (3:30 PM - 5:30 PM)
- **Active Strategies:** None (transition period)
- **Expected:** 0 trades
- **Action:** Run dedup monitor at 4:00 PM, 5:00 PM

### Phase 3: NY SESSION - CRITICAL WINDOW (5:30 PM - 9:30 PM) 🔥
- **Active Strategies:** All 6 strategies
- **Expected:** 4-6 trades (80% of daily volume)
- **Action:** 
  - **ACTIVE MONITORING** - check trade log every 30 min
  - Run dedup monitor at: 6:00, 7:00, 8:00, 9:00 PM
  - Watch for "deduped" spam in logs
  - If >10 consecutive "deduped" logs → restart bot immediately

### Phase 4: Post-Session (9:30 PM - 10:00 PM)
- Run end-of-day report
- Generate daily trade progress file
- Send final Telegram update

---

## 🚨 MONITORING PROTOCOL (ACTIVE NY SESSION)

### Every 30 Minutes During 5:30-9:30 PM:

```bash
# Quick status check
python scripts\daily_stats.py

# Dedup health check
python scripts\dedup_monitor.py

# Check last 10 trade log entries
Get-Content logs\trades\2026-10-08.jsonl | Select-Object -Last 10
```

### RED FLAGS (Restart Bot Immediately):
1. **>10 consecutive "deduped" logs** in trade log
2. **Dedup monitor alerts stale entries** (>20 min old)
3. **No new trades for >45 minutes** during NY peak (6-9 PM)
4. **Heartbeat older than 2 minutes**

### Quick Restart Command:
```bash
python scripts\restart_bot.py
```

---

## 📈 SUCCESS METRICS

### Minimum Viable Day:
- ✅ 3+ trades executed
- ✅ No dedup bug blocking >15 minutes
- ✅ System runs clean through NY session
- ✅ P&L: any result (today is about system reliability)

### Good Day:
- ✅ 4-6 trades executed
- ✅ Zero dedup incidents
- ✅ Hourly Telegram updates accurate
- ✅ P&L: break even or better

### Great Day:
- ✅ 6+ trades executed
- ✅ Clean system operation
- ✅ P&L: +$10 or more
- ✅ All monitoring tools validated

---

## 🎬 STARTUP SEQUENCE (Execute at 4:30 PM)

```bash
# 1. Final pre-check
python scripts\pre_market_check.py

# 2. Clear any stale state
Remove-Item logs\loop_state.json -ErrorAction SilentlyContinue

# 3. Start main bot
python -m src.core.main_loop

# 4. Start hourly Telegram monitor (separate terminal)
python scripts\hourly_monitor.py

# 5. Verify heartbeat after 1 minute
Get-Content logs\heartbeat
```

---

## 🔧 CONTINGENCY PLANS

### If Daily Loss Limit Triggers Again:
- **Threshold:** -3% ($175.21 → -$5.26 max loss)
- **Action:** Accept shutdown, don't override unless discussed
- **Why:** Risk management rule exists for a reason

### If Dedup Bug Recurs:
1. Run `python scripts\dedup_monitor.py`
2. Confirm stale entries
3. Run `python scripts\restart_bot.py`
4. Document timestamp and conditions
5. Investigate why 30-min cleanup failed

### If No Trades During NY Session:
1. Check D1 bias didn't flip mid-day
2. Verify strategies are generating signals (check logs for "blocked" vs "deduped")
3. Check MT5 connection status
4. Verify spread is normal (<$1)

---

## 📊 EXPECTED OUTCOMES

### Realistic Expectations:
- **Trades:** 3-6 (mostly SELL due to BEARISH bias)
- **Win Rate:** 40-50% (portfolio average)
- **P&L Range:** -$10 to +$15
- **Goal:** Clean execution > profit (system validation day)

### What Success Looks Like Tonight:
✅ Bot runs 6:00 AM - 9:30 PM without manual intervention  
✅ No dedup bug incidents  
✅ All trades logged correctly  
✅ Hourly Telegram updates accurate  
✅ End-of-day report generated cleanly  

---

## 📝 LESSONS FROM YESTERDAY

### What Went Wrong:
1. **Dedup bug detection took 2.5 hours** - should have caught it at 6:20 PM
2. **Reactive instead of proactive** - waited for user to notice instead of monitoring actively
3. **Wasted prime NY session hours** - cost ~4-6 potential trades

### What to Do Better Today:
1. **Active monitoring during NY session** - check logs every 30 min
2. **Use dedup_monitor.py** - automated early warning
3. **Fast response** - if anything looks wrong, investigate immediately
4. **Communicate proactively** - alert user to any anomalies, don't wait for questions

---

## 🎯 AGENT FOCUS AREAS TODAY

### Critical:
- Watch for dedup bug recurrence (new fix needs validation)
- Monitor trade log during 5:30-9:30 PM window
- Respond <5 minutes if red flags appear

### Important:
- Ensure hourly Telegram updates are accurate
- Track daily loss limit approach
- Validate all monitoring tools work as expected

### Nice to Have:
- Document any new edge cases discovered
- Track which strategies fire in BEARISH conditions
- Note any pattern in signal generation

---

## 📞 COMMUNICATION PLAN

### Telegram Updates (Automated):
- Every hour: balance, open positions, daily P&L
- Immediate: trade entries/exits

### Proactive Alerts (Manual):
- If dedup monitor detects stale entries
- If no trades by 7:00 PM during NY session
- If daily loss approaching -2.5% (alert before shutdown)
- Any system anomaly detected

### End of Day Summary:
- Total trades executed
- P&L breakdown
- System health report
- Any incidents/bugs encountered

---

## ✅ READY TO EXECUTE

**Current Time:** 1:58 PM IST  
**Next Action:** Start bot at 4:30 PM  
**Agent Status:** Alert and focused  
**User Expectation:** Clean execution, no more sloppy mistakes  

**LET'S TRADE PROPERLY TODAY.** 🎯

---

**Last Updated:** Thursday, October 8, 2026 - 1:58 PM IST
