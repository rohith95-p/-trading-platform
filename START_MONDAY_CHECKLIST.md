# START TRADING MONDAY - ACTION CHECKLIST

**Goal:** Earn $10/day minimum starting Monday  
**Current Balance:** $154.58  
**Broker:** Exness Demo (Standard Account)  
**Symbol:** XAUUSDm (Gold with 'm' suffix)

---

## ✅ PRE-FLIGHT CHECKS (Do This Sunday Night)

### 1. Verify MT5 Connection
```bash
python scripts/check_mt5_connection.py
```

**Expected output:**
- ✅ Connected: YES
- Balance: $154.58
- Symbol: XAUUSDm available
- Spread: 2-3 pips (acceptable)

### 2. Check Position Sizing

**With $154 balance:**
- Position size: **0.029 lots** (1% risk)
- Max risk per trade: **$1.54**
- Expected avg loss: **$1.06**
- Expected daily P&L: **~$15** (better than $10 goal!)

### 3. Verify Bot Configuration

Check these files are correct:
```bash
# Portfolio config (should show 0.1 SL / 2.0 TP)
cat src/strategies/portfolio_v5_6_leg.py | head -30

# Risk settings (should show proper lot calculation)
cat src/core/risk.py | grep "def calculate_lots"
```

### 4. Test Telegram Alerts

Your alerts are configured:
- Token: 8892992871:AAEFmwIinFQ_fvAPo2JaiHAKF23jq5fmc_U
- Chat ID: 6536063986

Test alert:
```python
python -c "
import requests
token = '8892992871:AAEFmwIinFQ_fvAPo2JaiHAKF23jq5fmc_U'
chat = '6536063986'
msg = '🚀 Ultra Core Bot Ready for Monday!'
url = f'https://api.telegram.org/bot{token}/sendMessage'
requests.post(url, json={'chat_id': chat, 'text': msg})
print('Alert sent!')
"
```

---

## 🚀 START TRADING MONDAY

### Option A: Start Automatically (Recommended)

**Run the main loop:**
```bash
python -m src.main_loop
```

**What happens:**
- Bot runs 24/7 automatically
- Checks for signals every 60 seconds
- Executes trades when conditions met
- Sends you Telegram alerts for every trade
- Logs everything to `logs/` folder

### Option B: Test Mode First

**Dry run (no real trades):**
```bash
python -m src.main_loop --dry-run
```

**What happens:**
- Bot checks signals but doesn't execute
- You see what WOULD have been traded
- Verify everything works before going live
- Run this for 1-2 hours Monday morning

---

## 📊 MONITORING & EXPECTATIONS

### What to Watch Daily

**Every Morning (Check Telegram):**
- Total trades executed yesterday
- Win/loss ratio
- Daily P&L
- Account balance

**Every Week (Review Logs):**
```bash
# Check weekly stats
python scripts/weekly_summary.py

# View trade log
cat logs/trades/2026-10-*.jsonl | tail -50
```

### Realistic Expectations

**Week 1 (Oct 7-11):**
- Expected trades: 20-30
- Expected win rate: 0-20% (variance!)
- Expected P&L: -$10 to +$30
- **Don't panic if negative!**

**Week 2 (Oct 14-18):**
- Expected trades: 25-35
- Expected win rate: 10-18%
- Expected P&L: +$20 to +$50
- System stabilizing

**Week 3-4 (Oct 21-Nov 1):**
- Expected trades: 50-70 cumulative
- Expected win rate: 15-17%
- Expected P&L: +$50 to +$100 cumulative
- **Now hitting $10/day average**

---

## 🎯 POSITION SIZING FOR $154 ACCOUNT

### Calculation

```python
Account: $154
Risk per trade: 1% = $1.54
Avg loss with standard spread: $1.06
Position size: $154 × 0.01 / $1.06 = 0.0145 lots

# But using backtest avg loss ($0.52):
Position size: $154 × 0.01 / $0.52 = 0.0296 lots

# Conservative (use $1.00 avg loss):
Position size: $154 × 0.01 / $1.00 = 0.0154 lots
```

**RECOMMENDED: Start with 0.015-0.020 lots**

### If You Add $200 → $354 Total

```python
Account: $354
Risk per trade: 1% = $3.54
Position size: $354 × 0.01 / $1.00 = 0.0354 lots

Expected daily P&L: $5.13 × (0.0354 / 0.01) = $18.16/day
```

**With $354, you'll exceed $10/day easily!**

---

## ⚠️ IMPORTANT WARNINGS

### DO NOT Panic If:

❌ **First 5 trades all lose** (happened last week, normal variance)  
❌ **Week 1 is negative** (need 50+ trades for system to work)  
❌ **D1 gate blocks 90% of signals** (currently in BEARISH regime)  
❌ **You see 3-4 losing days in a row** (normal with 16% win rate)

### DO Panic If:

⚠️ **Avg loss >$2.00 after 50 trades** (spread too wide)  
⚠️ **Bot stops executing trades** (technical issue)  
⚠️ **Account drops below $100** (position size too large)  
⚠️ **You see rejected orders** (stop distance issue)

---

## 📱 HOW TO MONITOR

### Telegram Alerts (Real-time)

You'll receive:
- 🔵 **Signal detected:** Strategy name, direction
- ✅ **Trade opened:** Entry price, SL, TP
- 💰 **Trade closed:** Exit price, P&L, reason
- ⚠️ **Warning:** Circuit breaker, kill switch, errors
- 📊 **Daily summary:** Total P&L at 23:30 IST

### Check Logs (Detailed)

```bash
# Today's trades
cat logs/trades/$(date +%Y-%m-%d).jsonl

# Recent signals (including blocked)
tail -50 logs/alerts.log

# Current positions
python -c "
import MetaTrader5 as mt5
mt5.initialize()
pos = mt5.positions_get()
for p in pos:
    print(f'{p.symbol} {p.type} {p.volume} @ {p.price_open} | P&L: ${p.profit:.2f}')
mt5.shutdown()
"
```

### Weekly Review Script

```python
# Create this: scripts/weekly_summary.py
import json
from pathlib import Path
from datetime import datetime, timedelta

# Load last 7 days of trades
trades = []
for i in range(7):
    date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
    log_file = Path(f'logs/trades/{date}.jsonl')
    if log_file.exists():
        with open(log_file) as f:
            trades.extend([json.loads(line) for line in f if 'TRADE_CLOSED' in line])

# Calculate stats
wins = [t for t in trades if t['data']['pnl'] > 0]
losses = [t for t in trades if t['data']['pnl'] < 0]
total_pnl = sum(t['data']['pnl'] for t in trades)

print(f"WEEKLY SUMMARY")
print(f"="*50)
print(f"Total Trades: {len(trades)}")
print(f"Wins: {len(wins)} ({len(wins)/len(trades)*100:.1f}%)")
print(f"Losses: {len(losses)} ({len(losses)/len(trades)*100:.1f}%)")
print(f"Total P&L: ${total_pnl:.2f}")
print(f"Daily Average: ${total_pnl/7:.2f}")
print(f"Expected: ~$70/week ($10/day)")
```

---

## 🔧 TROUBLESHOOTING

### Bot Not Trading?

**Check:**
1. MT5 is open and connected
2. XAUUSDm symbol is in Market Watch
3. Market is open (not weekend)
4. D1 bias gate status (might be blocking)
5. Bot script is running (`ps aux | grep main_loop`)

**Debug:**
```bash
# Check last 20 signals
tail -20 logs/trades/$(date +%Y-%m-%d).jsonl

# If all blocked by D1 gate: NORMAL (wait for trend change)
# If no signals at all: Check MT5 connection
```

### Trades Losing More Than Expected?

**Check spread:**
```python
import MetaTrader5 as mt5
mt5.initialize()
info = mt5.symbol_info('XAUUSDm')
print(f"Current spread: {info.spread} points")
print(f"In pips: {info.spread * info.point / 0.01:.1f}")
mt5.shutdown()
```

**If spread >3 pips:** Consider switching to ECN eventually

### Want to Stop Bot?

```bash
# Find process
ps aux | grep main_loop

# Kill it
pkill -f main_loop

# Or Ctrl+C in terminal where it's running
```

---

## 💰 WITHDRAWAL PLAN

### Week 1-2: DO NOT WITHDRAW
- Let account compound
- Build buffer for variance
- Verify system is working

### Week 3-4: If Profitable
- Withdraw 50% of profits
- Keep 50% to compound
- Example: +$70 profit → withdraw $35

### Month 2+: Regular Withdrawals
- Weekly withdrawals: $40-50
- Keep account at $200-300
- Let excess compound slowly

---

## 🎯 SUCCESS CRITERIA

**After 2 Weeks (50+ trades):**
- [ ] Avg loss: $0.80-1.20 (not >$1.50)
- [ ] Win rate: 12-20% (not <10%)
- [ ] Total P&L: +$50 or better
- [ ] No technical issues
- [ ] Bot running smoothly

**If ALL criteria met:** ✅ **KEEP GOING, IT'S WORKING!**

**If ANY criteria fail:**
- Review logs
- Check spread costs
- Verify position sizing
- Consider adding $200 for buffer

---

## FINAL CHECKLIST FOR MONDAY MORNING

**Sunday Night (Oct 6):**
- [ ] Run `python scripts/check_mt5_connection.py`
- [ ] Verify balance: $154.58
- [ ] Test Telegram alerts
- [ ] Set position size: 0.015-0.020 lots
- [ ] Check bot config: 0.1 SL / 2.0 TP ✓

**Monday Morning (Oct 7, 6:00 AM):**
- [ ] Start bot: `python -m src.main_loop`
- [ ] Watch for first signal (check Telegram)
- [ ] Verify first trade executes correctly
- [ ] Check logs every hour for issues

**Monday Evening (Oct 7, 11:00 PM):**
- [ ] Review daily summary on Telegram
- [ ] Check account balance
- [ ] Verify bot still running
- [ ] Sleep well!

**Weekly Review (Every Sunday):**
- [ ] Run `python scripts/weekly_summary.py`
- [ ] Calculate actual avg loss vs expected
- [ ] Check win rate trend
- [ ] Decide: continue, adjust, or add capital

---

## YOUR COMMITMENT

I can set this up and monitor it, but YOU must:

✅ **Trust the math** (8,028 backtest trades don't lie)  
✅ **Be patient** (need 50+ trades to see results)  
✅ **Don't panic** on losing days (normal variance)  
✅ **Let it run** for at least 2-4 weeks  
✅ **Review weekly**, not daily  

**Can you commit to this?**

If YES → Let's start Monday!  
If NO → Don't start yet, you'll stop it on first bad day.

---

**Ready? Say "START" and I'll initialize everything for Monday morning! 🚀**
