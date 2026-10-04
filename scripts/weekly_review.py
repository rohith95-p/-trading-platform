"""
Generate weekly trading review
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

print("="*80)
print("ULTRA CORE - WEEKLY REVIEW")
print("="*80)

# Load last 7 days of trades
start_date = datetime.now() - timedelta(days=7)
trades = []

for i in range(8):  # Check last 8 days
    date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
    log_file = Path(f'logs/trades/{date}.jsonl')
    
    if log_file.exists():
        with open(log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get('kind') == 'trade_closed':
                        trades.append(entry)
                except:
                    continue

if not trades:
    print("\n❌ No trades found in last 7 days!")
    print("   Bot might not be running or no trades executed yet.")
    exit(0)

print(f"\nReview Period: Last 7 days")
print(f"Trades Found: {len(trades)}")

# Calculate stats
wins = [t for t in trades if t['data']['pnl'] > 0]
losses = [t for t in trades if t['data']['pnl'] < 0]

total_pnl = sum(t['data']['pnl'] for t in trades)
win_rate = len(wins) / len(trades) * 100 if trades else 0

avg_win = sum(w['data']['pnl'] for w in wins) / len(wins) if wins else 0
avg_loss = sum(l['data']['pnl'] for l in losses) / len(losses) if losses else 0
expectancy = total_pnl / len(trades) if trades else 0

gross_profit = sum(w['data']['pnl'] for w in wins)
gross_loss = abs(sum(l['data']['pnl'] for l in losses))
profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

# Strategy breakdown
by_strategy = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0})
for t in trades:
    strat = t['data']['strategy']
    by_strategy[strat]['trades'] += 1
    by_strategy[strat]['pnl'] += t['data']['pnl']
    if t['data']['pnl'] > 0:
        by_strategy[strat]['wins'] += 1

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nTotal Trades: {len(trades)}")
print(f"  Wins: {len(wins)} ({win_rate:.1f}%)")
print(f"  Losses: {len(losses)} ({100-win_rate:.1f}%)")
print(f"Total P&L: ${total_pnl:.2f}")
print(f"Account Balance: Check MT5")

print("\n" + "="*80)
print("DETAILED METRICS")
print("="*80)
print(f"\nWin Rate: {win_rate:.1f}% (expected 16%, acceptable 12-20%)")
print(f"Avg Win: ${avg_win:.2f} (expected $17)")
print(f"Avg Loss: ${avg_loss:.2f} (expected $0.80-1.20)")
print(f"Expectancy: ${expectancy:.4f} (expected $0.75-1.00)")
print(f"Profit Factor: {profit_factor:.3f} (expected >1.3)")

# Assessment
print("\n" + "="*80)
print("METRICS ASSESSMENT")
print("="*80)

checks = {
    'Win Rate': (12 <= win_rate <= 20, win_rate, '12-20%'),
    'Avg Loss': (0.50 <= abs(avg_loss) <= 1.50, abs(avg_loss), '$0.50-1.50'),
    'Expectancy': (expectancy >= 0.50, expectancy, '>$0.50'),
    'Profit Factor': (profit_factor >= 1.3, profit_factor, '>1.3'),
}

passing = 0
for metric, (passed, value, expected) in checks.items():
    status = "✅ PASS" if passed else "❌ FAIL"
    passing += 1 if passed else 0
    print(f"{metric:<20} {status:<10} (Value: {value:.2f}, Expected: {expected})")

print(f"\nOverall: {passing}/4 metrics passing")

print("\n" + "="*80)
print("STRATEGY BREAKDOWN")
print("="*80)

for strat, stats in sorted(by_strategy.items(), key=lambda x: x[1]['pnl'], reverse=True):
    wr = stats['wins'] / stats['trades'] * 100 if stats['trades'] > 0 else 0
    print(f"\n{strat}:")
    print(f"  Trades: {stats['trades']}")
    print(f"  Win Rate: {wr:.1f}%")
    print(f"  P&L: ${stats['pnl']:.2f}")

print("\n" + "="*80)
print("VERDICT")
print("="*80)

if passing >= 3 and total_pnl >= 0:
    verdict = "✅ SYSTEM WORKING"
    recommendation = "CONTINUE trading"
    print(f"\n{verdict}")
    print(f"Recommendation: {recommendation}")
    print("  System is performing as expected")
    print("  Keep going to reach 50-100 trades")
    
elif passing >= 2 and total_pnl >= -30:
    verdict = "⚠️ SYSTEM NEEDS ATTENTION"
    recommendation = "CONTINUE but MONITOR CLOSELY"
    print(f"\n{verdict}")
    print(f"Recommendation: {recommendation}")
    print("  Some metrics off but not critical")
    print("  Need more trades to confirm trend")
    
elif passing >= 1 and total_pnl >= -50:
    verdict = "⚠️ SYSTEM UNDERPERFORMING"
    recommendation = "INVESTIGATE but continue for now"
    print(f"\n{verdict}")
    print(f"Recommendation: {recommendation}")
    print("  Results below expectations")
    print("  Check spread, execution, D1 gate")
    print("  Continue to 50 trades then decide")
    
else:
    verdict = "❌ SYSTEM NOT WORKING"
    recommendation = "PAUSE and INVESTIGATE"
    print(f"\n{verdict}")
    print(f"Recommendation: {recommendation}")
    print("  Multiple metrics failing")
    print("  Stop trading until we find root cause")

print("\n" + "="*80)
print("NEXT ACTIONS")
print("="*80)

if len(trades) < 20:
    print("\n⏰ Need more data!")
    print(f"   Current: {len(trades)} trades")
    print(f"   Target: 50-100 trades for reliable assessment")
    print(f"   Continue trading for another 1-2 weeks")
elif len(trades) < 50:
    print("\n📊 Getting there!")
    print(f"   Current: {len(trades)} trades")
    print(f"   Target: 50-100 trades")
    print(f"   Continue for another week to reach decision point")
else:
    print("\n🎯 Decision point reached!")
    print(f"   Trades: {len(trades)}")
    print(f"   Passing metrics: {passing}/4")
    if passing >= 3:
        print("   ✅ VERDICT: System works! Keep trading!")
    elif passing == 2:
        print("   ⚠️ VERDICT: Needs adjustment. Review spread/execution.")
    else:
        print("   ❌ VERDICT: System not working. Stop and investigate.")

print("\n" + "="*80)
