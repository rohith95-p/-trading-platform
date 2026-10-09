# Daily Trade Progress Reports

This folder contains automated daily trading reports in markdown format.

## 📁 File Naming
Reports are saved as: `YYYY-MM-DD_DayName.md`

Examples:
- `2026-10-05_Monday.md`
- `2026-10-06_Tuesday.md`

## 📊 What Each Report Contains

### Account Summary
- Starting balance (from previous day close)
- Ending balance (actual MT5 balance)
- Day P&L (calculated correctly: ending - starting)
- Day return percentage
- Daily target status ($10/day)

### Trading Statistics
- Total trades
- Winners vs Losers
- Win rate percentage
- Profit factor
- Average win/loss
- Best and worst trades

### Trade Details
- Complete list of all trades
- Exact timestamps (IST)
- Strategy names
- Individual P&L
- Ticket numbers

### Strategy Breakdown
- Performance by strategy
- Win-loss record per strategy
- P&L contribution per strategy

### Key Insights
- Automated analysis
- Target achievement status
- Performance highlights

## 🚀 How to Generate Reports

### Automatic (End of Day)
```bash
python scripts/end_of_day.py
```
Run this every night before stopping the bot.

### Manual (Any Date)
```bash
python scripts/generate_daily_report.py YYYY-MM-DD
```

### Historical Batch
```bash
# Generate last 7 days
python scripts/generate_daily_report.py 2026-10-05
python scripts/generate_daily_report.py 2026-10-06
python scripts/generate_daily_report.py 2026-10-07
# ... etc
```

## 💡 Why This System?

**Problem:** Confusion about starting balance, daily P&L calculation
**Solution:** Every day has its own report with exact numbers

**Benefits:**
1. ✅ Clear starting/ending balance
2. ✅ Accurate P&L math (no confusion!)
3. ✅ Complete trade history
4. ✅ Strategy performance tracking
5. ✅ Historical record keeping
6. ✅ Easy to review past days

## 📈 Example Usage

**End of trading day:**
```bash
cd c:\projects\ultra_core
python scripts/end_of_day.py
```

**Review yesterday's performance:**
```bash
cd daily_trade_progress
notepad 2026-10-06_Tuesday.md
```

**Compare multiple days:**
Open several `.md` files side by side in your editor.

## 📝 Notes

- Reports are generated from `logs/trades/YYYY-MM-DD.jsonl`
- Zero-trade days are tracked (with explanation)
- Strategy names pulled from trade logs
- All times in IST timezone
- Balance reconciliation prevents math errors

---

**Created:** 2026-10-08
**Purpose:** Accurate daily trade tracking and historical record
