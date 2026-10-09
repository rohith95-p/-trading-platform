"""
Generate daily trade report as markdown file
Automatically saves to daily_trade_progress/ folder
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.chdir(Path(__file__).resolve().parents[1])

import MetaTrader5 as mt5

IST = timezone(timedelta(hours=5, minutes=30))

def get_strategy_name(ticket, log_file_path):
    """
    Find strategy name by matching closed trade to nearest preceding order.
    Since closed trades don't store strategy (bug in main_loop.py line 597),
    we match by timestamp proximity.
    """
    if not log_file_path.exists():
        return "Unknown"
    
    # Build list of all orders with their timestamps and strategies
    orders = []
    closed_time = None
    
    with open(log_file_path, encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                
                # Store order entries
                if entry.get("kind") == "order":
                    orders.append({
                        'ts': entry.get('ts'),
                        'strategy': entry.get('strategy', 'Unknown'),
                        'direction': entry.get('direction'),
                        'price': entry.get('price')
                    })
                
                # Find our closed trade's timestamp
                if entry.get("kind") == "closed" and entry.get("ticket") == ticket:
                    closed_time = entry.get('ts')
            except:
                continue
    
    # If we found the closed time, find the nearest preceding order
    if closed_time and orders:
        # Find orders that happened before this close (within 60 minutes)
        candidates = [o for o in orders if o['ts'] < closed_time and (closed_time - o['ts']) < 3600]
        
        if candidates:
            # Return the most recent order before the close
            nearest = max(candidates, key=lambda x: x['ts'])
            return nearest['strategy']
    
    return "Unknown"


def generate_daily_report(target_date=None):
    """
    Generate daily report for a specific date
    If target_date is None, uses today
    Format: YYYY-MM-DD
    """
    if target_date is None:
        target_date = datetime.now(IST).strftime("%Y-%m-%d")
    
    # Parse target date
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    day_name = dt.strftime("%A")
    display_date = dt.strftime("%B %d, %Y")
    
    print(f"\n{'='*70}")
    print(f"Generating report for {day_name}, {display_date}")
    print(f"{'='*70}")
    
    # Initialize MT5
    if not mt5.initialize():
        print("❌ MT5 initialization failed")
        return None
    
    # Get current account info for ending balance
    account_info = mt5.account_info()
    if not account_info:
        mt5.shutdown()
        print("❌ Failed to get account info")
        return None
    
    current_balance = account_info.balance
    
    # Parse trade log for this date
    log_file = Path(f"logs/trades/{target_date}.jsonl")
    
    trades = []
    starting_balance = None
    
    if log_file.exists():
        with open(log_file) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("kind") == "closed":
                        ticket = entry.get("ticket")
                        profit = entry.get("profit", 0.0)
                        strategy = get_strategy_name(ticket, log_file)
                        timestamp = entry.get("ist", "Unknown")
                        
                        trades.append({
                            'ticket': ticket,
                            'profit': profit,
                            'strategy': strategy,
                            'time': timestamp.split()[1] if ' ' in timestamp else timestamp
                        })
                except Exception as e:
                    continue
    
    # Calculate metrics
    total_trades = len(trades)
    
    if total_trades == 0:
        # Zero trade day
        ending_balance = current_balance
        starting_balance = ending_balance  # No change
        day_pnl = 0.0
        winners = []
        losers = []
    else:
        day_pnl = sum(t['profit'] for t in trades)
        ending_balance = current_balance
        starting_balance = ending_balance - day_pnl
        
        winners = [t for t in trades if t['profit'] > 0]
        losers = [t for t in trades if t['profit'] < 0]
    
    num_winners = len(winners)
    num_losers = len(losers)
    win_rate = (num_winners / total_trades * 100) if total_trades > 0 else 0
    
    avg_win = sum(t['profit'] for t in winners) / num_winners if num_winners > 0 else 0
    avg_loss = sum(t['profit'] for t in losers) / num_losers if num_losers > 0 else 0
    
    gross_profit = sum(t['profit'] for t in winners)
    gross_loss = abs(sum(t['profit'] for t in losers))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    day_return = (day_pnl / starting_balance * 100) if starting_balance > 0 else 0
    
    mt5.shutdown()
    
    # Generate markdown report
    report = f"""# Daily Trade Report - {day_name}, {display_date}

## 📊 Account Summary
| Metric | Value |
|--------|-------|
| **Starting Balance** | ${starting_balance:.2f} |
| **Ending Balance** | ${ending_balance:.2f} |
| **Day P&L** | ${day_pnl:+.2f} |
| **Day Return** | {day_return:+.2f}% |
| **Target** | $10.00 |
| **Status** | {'✅ TARGET HIT' if day_pnl >= 10 else '❌ Below Target' if day_pnl < 10 and total_trades > 0 else '➖ No Trades'} |

---

## 📈 Trading Statistics
| Metric | Value |
|--------|-------|
| **Total Trades** | {total_trades} |
| **Winners** | {num_winners} |
| **Losers** | {num_losers} |
| **Win Rate** | {win_rate:.1f}% |
| **Profit Factor** | {profit_factor:.2f} |
| **Avg Win** | ${avg_win:.2f} |
| **Avg Loss** | ${avg_loss:.2f} |
| **Best Trade** | ${max([t['profit'] for t in trades]) if trades else 0:.2f} |
| **Worst Trade** | ${min([t['profit'] for t in trades]) if trades else 0:.2f} |

---

"""

    if total_trades == 0:
        report += """## ⚠️ Zero Trade Day

**No trades executed today.**

**Possible Reasons:**
- D1 trend gate blocking signals
- Market consolidation/choppy conditions
- No clean setups matching strategy criteria
- Weekend or holiday (low liquidity)

**Note:** Zero-trade days are normal and expected. Backtests show 15-20% of days produce no trades.

---
"""
    else:
        report += f"""## 📋 Trade Details

### 🟢 Winning Trades ({num_winners})
"""
        if winners:
            report += "| # | Time | Strategy | P&L | Ticket |\n"
            report += "|---|------|----------|-----|--------|\n"
            for i, t in enumerate(winners, 1):
                report += f"| {i} | {t['time']} | {t['strategy']} | ${t['profit']:+.2f} | {t['ticket']} |\n"
        else:
            report += "*No winning trades*\n"
        
        report += f"\n### 🔴 Losing Trades ({num_losers})\n"
        if losers:
            report += "| # | Time | Strategy | P&L | Ticket |\n"
            report += "|---|------|----------|-----|--------|\n"
            for i, t in enumerate(losers, 1):
                report += f"| {i} | {t['time']} | {t['strategy']} | ${t['profit']:+.2f} | {t['ticket']} |\n"
        else:
            report += "*No losing trades*\n"
        
        report += "\n---\n\n"
        
        # Strategy breakdown
        strategy_stats = {}
        for t in trades:
            strat = t['strategy']
            if strat not in strategy_stats:
                strategy_stats[strat] = {'count': 0, 'pnl': 0.0, 'wins': 0, 'losses': 0}
            
            strategy_stats[strat]['count'] += 1
            strategy_stats[strat]['pnl'] += t['profit']
            if t['profit'] > 0:
                strategy_stats[strat]['wins'] += 1
            else:
                strategy_stats[strat]['losses'] += 1
        
        report += "## 📊 Strategy Breakdown\n"
        report += "| Strategy | Trades | W-L | P&L | Win Rate |\n"
        report += "|----------|--------|-----|-----|----------|\n"
        
        for strat, stats in sorted(strategy_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
            wr = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            report += f"| {strat} | {stats['count']} | {stats['wins']}-{stats['losses']} | ${stats['pnl']:+.2f} | {wr:.0f}% |\n"
        
        report += "\n---\n\n"
    
    # Add insights
    report += "## 💡 Key Insights\n\n"
    
    if total_trades == 0:
        report += "- No trading activity today\n"
        report += "- Bot was operational (check logs for signal blocks)\n"
        report += "- Balance preserved\n"
    elif day_pnl > 0:
        report += f"- ✅ Profitable day: ${day_pnl:.2f}\n"
        if day_pnl >= 10:
            report += f"- ✅ Daily target achieved ({day_pnl/10:.1f}x target)\n"
        if profit_factor >= 2.0:
            report += f"- 🔥 Excellent profit factor: {profit_factor:.2f}\n"
        if win_rate >= 50:
            report += f"- 💪 Win rate above 50%: {win_rate:.1f}%\n"
    else:
        report += f"- ❌ Red day: ${day_pnl:.2f}\n"
        if profit_factor < 1.0:
            report += f"- ⚠️ Profit factor below 1.0: {profit_factor:.2f}\n"
        if abs(avg_loss) > avg_win:
            report += f"- ⚠️ Average loss exceeds average win\n"
    
    report += f"\n---\n\n"
    report += f"**Report Generated:** {datetime.now(IST).strftime('%Y-%m-%d %I:%M:%S %p IST')}\n"
    report += f"**Source:** logs/trades/{target_date}.jsonl\n"
    
    # Save report
    output_dir = Path("daily_trade_progress")
    output_dir.mkdir(exist_ok=True)
    
    filename = f"{target_date}_{day_name}.md"
    output_path = output_dir / filename
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Report saved: {output_path}")
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Date: {display_date}")
    print(f"Trades: {total_trades}")
    print(f"P&L: ${day_pnl:+.2f}")
    print(f"Balance: ${starting_balance:.2f} → ${ending_balance:.2f}")
    print(f"{'='*70}\n")
    
    return output_path


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Generate for specific date
        target_date = sys.argv[1]
        generate_daily_report(target_date)
    else:
        # Generate for today
        generate_daily_report()
