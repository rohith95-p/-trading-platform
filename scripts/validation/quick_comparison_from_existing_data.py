"""
Quick 5 vs 6 Strategy Comparison Using Existing Validation Data
================================================================
Uses the already-run full_metrics_report.json to calculate what happens
if we remove TrendPullback from the portfolio.

Much faster than re-running full backtest.
"""

import json
from pathlib import Path

# Load the 6-strategy results (current)
report_path = Path("reports/full_metrics_report.json")
with open(report_path) as f:
    data = json.load(f)

print("=" * 80)
print("  QUICK PORTFOLIO COMPARISON: 5 vs 6 STRATEGIES")
print("  Using existing validation data from full_metrics_report.json")
print("=" * 80)

# Extract strategy-level data
strategies = data['core_metrics']['by_strategy']

# Identify TrendPullback
trendpullback_key = None
for key in strategies.keys():
    if 'TrendPullback' in key or 'TREND_PULLBACK' in key:
        trendpullback_key = key
        break

if not trendpullback_key:
    print("\n❌ TrendPullback strategy not found in report!")
    exit(1)

# Get TrendPullback metrics
tp_trades = strategies[trendpullback_key]['trades']
tp_net_pl = strategies[trendpullback_key]['net_pl']
tp_gross_profit = strategies[trendpullback_key]['gross_profit']
tp_gross_loss = strategies[trendpullback_key]['gross_loss']
tp_wins = strategies[trendpullback_key]['wins']
tp_pf = strategies[trendpullback_key]['profit_factor']

# Current 6-strategy totals
total_trades_6 = data['n_trades']
total_gross_profit_6 = data['core_metrics']['gross_profit']
total_gross_loss_6 = data['core_metrics']['gross_loss']
total_net_pl_6 = data['core_metrics']['net_pl']
total_wins_6 = data['core_metrics']['wins']
pf_6 = data['core_metrics']['profit_factor']
wr_6 = data['core_metrics']['win_rate']

# Calculate 5-strategy (remove TrendPullback)
total_trades_5 = total_trades_6 - tp_trades
total_gross_profit_5 = total_gross_profit_6 - tp_gross_profit
total_gross_loss_5 = total_gross_loss_6 - tp_gross_loss
total_net_pl_5 = total_net_pl_6 - tp_net_pl
total_wins_5 = total_wins_6 - tp_wins
pf_5 = total_gross_profit_5 / total_gross_loss_5 if total_gross_loss_5 > 0 else 0
wr_5 = (total_wins_5 / total_trades_5 * 100) if total_trades_5 > 0 else 0

print(f"\n{'METRIC':<30} {'6-STRATEGY':<20} {'5-STRATEGY':<20} {'DIFFERENCE':<20}")
print("=" * 80)

print(f"{'Total Trades':<30} {total_trades_6:<20} {total_trades_5:<20} {total_trades_6 - total_trades_5:<20}")
print(f"{'Win Rate %':<30} {wr_6:<20.2f} {wr_5:<20.2f} {wr_6 - wr_5:<20.2f}")
print(f"{'Profit Factor':<30} {pf_6:<20.3f} {pf_5:<20.3f} {pf_6 - pf_5:<20.3f}")
print(f"{'Gross Profit $':<30} {total_gross_profit_6:<20.2f} {total_gross_profit_5:<20.2f} {total_gross_profit_6 - total_gross_profit_5:<20.2f}")
print(f"{'Gross Loss $':<30} {total_gross_loss_6:<20.2f} {total_gross_loss_5:<20.2f} {total_gross_loss_6 - total_gross_loss_5:<20.2f}")
print(f"{'Net P&L $':<30} {total_net_pl_6:<20.2f} {total_net_pl_5:<20.2f} {total_net_pl_6 - total_net_pl_5:<20.2f}")

print(f"\n{'='*80}")
print(f"  TRENDPULLBACK CONTRIBUTION:")
print(f"{'='*80}")
print(f"  Trades:        {tp_trades:>6} ({tp_trades/total_trades_6*100:.1f}% of total)")
print(f"  Profit Factor: {tp_pf:>6.3f}")
print(f"  Net P&L:       ${tp_net_pl:>6.2f}")
print(f"  Win Rate:      {strategies[trendpullback_key]['win_rate']:>6.1f}%")

print(f"\n{'='*80}")
print(f"  ANALYSIS:")
print(f"{'='*80}")

# Decision logic
if pf_5 > pf_6:
    pf_verdict = f"✅ 5-STRATEGY has BETTER PF ({pf_5:.3f} vs {pf_6:.3f}) +{pf_5-pf_6:.3f}"
else:
    pf_verdict = f"❌ 6-STRATEGY has BETTER PF ({pf_6:.3f} vs {pf_5:.3f}) +{pf_6-pf_5:.3f}"

if total_net_pl_5 > total_net_pl_6:
    profit_verdict = f"✅ 5-STRATEGY has MORE PROFIT (+${total_net_pl_5 - total_net_pl_6:.2f})"
else:
    profit_verdict = f"❌ 6-STRATEGY has MORE PROFIT (+${total_net_pl_6 - total_net_pl_5:.2f})"

trade_count_pct = (tp_trades / total_trades_6) * 100

print(f"\n  Profit Factor: {pf_verdict}")
print(f"  Net Profit: {profit_verdict}")
print(f"  Trade Volume: TrendPullback provides {tp_trades} trades ({trade_count_pct:.1f}% of portfolio)")

print(f"\n{'='*80}")
print(f"  RECOMMENDATION:")
print(f"{'='*80}\n")

# Complex decision logic
if pf_5 >= 1.4 and (pf_5 - pf_6) >= 0.10:
    recommendation = "5-STRATEGY"
    reason = f"PF improvement is significant ({pf_5 - pf_6:+.3f}) and clears 1.4 threshold"
elif total_net_pl_5 > total_net_pl_6:
    recommendation = "5-STRATEGY"
    reason = f"Makes ${total_net_pl_5 - total_net_pl_6:.2f} MORE profit"
elif tp_trades > 3000 and abs(total_net_pl_6 - total_net_pl_5) < 500:
    recommendation = "6-STRATEGY"
    reason = f"TrendPullback adds {tp_trades} trades for diversification (profit impact: ${total_net_pl_6 - total_net_pl_5:+.2f})"
elif tp_pf < 1.10:
    recommendation = "5-STRATEGY"
    reason = f"TrendPullback PF ({tp_pf:.3f}) is too marginal, removing improves overall PF by {pf_5 - pf_6:+.3f}"
else:
    recommendation = "6-STRATEGY"
    reason = "Diversification and sample size benefits outweigh marginal differences"

print(f"  ✅ **RECOMMENDED: {recommendation}**\n")
print(f"  Reason: {reason}\n")

if recommendation == "5-STRATEGY":
    print(f"  Action: Remove TrendPullback from portfolio")
    print(f"  Expected PF: {pf_5:.3f}")
    print(f"  Expected Net P&L: ${total_net_pl_5:.2f}")
    print(f"  Trade count: {total_trades_5}")
else:
    print(f"  Action: Keep TrendPullback in portfolio")
    print(f"  Current PF: {pf_6:.3f}")
    print(f"  Current Net P&L: ${total_net_pl_6:.2f}")
    print(f"  Trade count: {total_trades_6}")

print(f"\n{'='*80}\n")
