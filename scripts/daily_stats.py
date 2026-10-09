"""
Daily Trading Statistics - Complete Performance Summary
Shows: P&L, Positions, Win Rate, PF, DD, Floating Profit, and more
"""
import MetaTrader5 as mt5
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

def load_trades_today():
    """Load today's trades from logs"""
    today = datetime.now().strftime('%Y-%m-%d')
    trade_file = Path(f'logs/trades/{today}.jsonl')
    
    if not trade_file.exists():
        return []
    
    trades = []
    with open(trade_file, 'r') as f:
        for line in f:
            if line.strip():
                trades.append(json.loads(line))
    return trades

def calculate_stats(trades):
    """Calculate win rate, PF, and other metrics with per-strategy breakdown"""
    if not trades:
        return None
    
    # Parse all trade events to match opens with closes
    trade_pairs = {}
    open_orders = {}
    
    for t in trades:
        kind = t.get('kind')
        
        # Track order opens
        if kind == 'order':
            ticket = t.get('ticket')
            strategy = t.get('strategy', 'UNKNOWN')
            timestamp = t.get('ist', 'N/A')
            
            if ticket:
                open_orders[ticket] = {
                    'strategy': strategy,
                    'time': timestamp,
                    'direction': t.get('direction'),
                    'price': t.get('price')
                }
        
        # Match closes with opens
        elif kind == 'close':
            ticket = t.get('ticket')
            pl = t.get('pl', 0)
            
            if ticket and ticket in open_orders:
                trade_info = open_orders[ticket]
                trade_info['pl'] = pl
                trade_info['close_time'] = t.get('ist', 'N/A')
                
                trade_pairs[ticket] = trade_info
    
    # If no matched pairs, try to extract from single records with 'pl'
    if not trade_pairs:
        for t in trades:
            if 'pl' in t:
                ticket = t.get('ticket', len(trade_pairs))
                trade_pairs[ticket] = {
                    'strategy': t.get('strategy', 'UNKNOWN'),
                    'time': t.get('ist', 'N/A'),
                    'pl': t.get('pl', 0),
                    'direction': t.get('direction', 'N/A'),
                    'price': t.get('price', 0)
                }
    
    if not trade_pairs:
        return None
    
    closed_trades = list(trade_pairs.values())
    
    wins = [t for t in closed_trades if t.get('pl', 0) > 0]
    losses = [t for t in closed_trades if t.get('pl', 0) <= 0]
    
    total_trades = len(closed_trades)
    win_count = len(wins)
    loss_count = len(losses)
    
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
    
    total_wins = sum(t.get('pl', 0) for t in wins)
    total_losses = abs(sum(t.get('pl', 0) for t in losses))
    
    profit_factor = (total_wins / total_losses) if total_losses > 0 else float('inf') if total_wins > 0 else 0
    
    net_pl = sum(t.get('pl', 0) for t in closed_trades)
    
    # Per-strategy breakdown
    strategy_stats = {}
    for t in closed_trades:
        strat = t.get('strategy', 'UNKNOWN')
        if strat not in strategy_stats:
            strategy_stats[strat] = {'trades': 0, 'wins': 0, 'losses': 0, 'pl': 0, 'times': []}
        
        strategy_stats[strat]['trades'] += 1
        strategy_stats[strat]['pl'] += t.get('pl', 0)
        
        if t.get('pl', 0) > 0:
            strategy_stats[strat]['wins'] += 1
        else:
            strategy_stats[strat]['losses'] += 1
        
        # Store timestamp
        if 'time' in t:
            strategy_stats[strat]['times'].append(t['time'])
    
    # Calculate per-strategy win rate
    for strat, data in strategy_stats.items():
        data['win_rate'] = (data['wins'] / data['trades'] * 100) if data['trades'] > 0 else 0
    
    return {
        'total_trades': total_trades,
        'wins': win_count,
        'losses': loss_count,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_wins': total_wins,
        'total_losses': total_losses,
        'net_pl': net_pl,
        'strategy_stats': strategy_stats,
        'trade_times': [t.get('time', t.get('close_time', 'N/A')) for t in closed_trades]
    }

def get_drawdown_info():
    """Get drawdown from risk state"""
    risk_file = Path('logs/risk_state.json')
    if risk_file.exists():
        with open(risk_file, 'r') as f:
            risk_state = json.load(f)
            return {
                'current_dd': risk_state.get('drawdown_pct', 0),
                'max_dd': risk_state.get('max_drawdown_pct', 0)
            }
    return {'current_dd': 0, 'max_dd': 0}

def main():
    # Connect to MT5
    if not mt5.initialize():
        print("❌ MT5 connection failed")
        return
    
    if not mt5.login(198874999, 'Rohith@95', 'Exness-MT5Trial11'):
        print("❌ MT5 login failed")
        mt5.shutdown()
        return
    
    # Get account info
    acc = mt5.account_info()
    if not acc:
        print("❌ Could not get account info")
        mt5.shutdown()
        return
    
    # Get open positions
    positions = mt5.positions_get()
    open_positions = len(positions) if positions else 0
    floating_pl = sum(p.profit for p in positions) if positions else 0.0
    
    # Load today's trades
    trades = load_trades_today()
    stats = calculate_stats(trades)
    
    # Get drawdown
    dd_info = get_drawdown_info()
    
    # Calculate day P&L
    starting_balance = 154.58  # Store this in config later
    day_pl = acc.balance - starting_balance + floating_pl
    
    mt5.shutdown()
    
    # Display formatted output
    print("=" * 80)
    print(f"📊 ULTRA CORE - DAILY STATS")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print()
    
    # Account Summary
    print("💰 ACCOUNT SUMMARY")
    print(f"   Balance:        ${acc.balance:.2f}")
    print(f"   Equity:         ${acc.equity:.2f}")
    print(f"   Day P&L:        ${day_pl:+.2f}")
    print(f"   Day Return:     {(day_pl/starting_balance*100):+.2f}%")
    print()
    
    # Positions
    print("📈 POSITIONS")
    print(f"   Open Positions: {open_positions}")
    if floating_pl != 0:
        print(f"   Floating P&L:   ${floating_pl:+.2f} {'🟢' if floating_pl > 0 else '🔴'}")
        if positions:
            for p in positions:
                direction = "BUY" if p.type == 0 else "SELL"
                print(f"      #{p.ticket}: {direction} {p.volume} lots @ {p.price_open:.2f}, P&L: ${p.profit:+.2f}")
    else:
        print(f"   Floating P&L:   $0.00")
    print()
    
    # Trading Stats
    if stats:
        print("📊 TRADING STATS (Today)")
        print(f"   Total Trades:   {stats['total_trades']}")
        print(f"   Wins:           {stats['wins']} ✅")
        print(f"   Losses:         {stats['losses']} ❌")
        print(f"   Win Rate:       {stats['win_rate']:.1f}%")
        print(f"   Profit Factor:  {stats['profit_factor']:.2f}")
        print(f"   Total Wins:     ${stats['total_wins']:.2f}")
        print(f"   Total Losses:   ${stats['total_losses']:.2f}")
        print(f"   Net P&L:        ${stats['net_pl']:+.2f}")
        print()
        
        # Trade Timings
        if stats['trade_times']:
            print("⏰ TRADE TIMINGS")
            for i, time in enumerate(stats['trade_times'][-5:], 1):  # Last 5 trades
                print(f"   Trade {len(stats['trade_times'])-5+i}: {time}")
            print()
        
        # Per-Strategy Performance
        if stats['strategy_stats']:
            print("🎯 STRATEGY BREAKDOWN")
            for strat, data in sorted(stats['strategy_stats'].items(), key=lambda x: x[1]['pl'], reverse=True):
                strat_name = strat.replace('_V5', '').replace('_', ' ')
                print(f"   {strat_name}:")
                print(f"      Trades: {data['trades']} | W/L: {data['wins']}/{data['losses']} | WR: {data['win_rate']:.0f}% | P&L: ${data['pl']:+.2f}")
            print()
    else:
        print("📊 TRADING STATS (Today)")
        print(f"   No closed trades yet")
        print()
    
    # Risk Metrics
    print("🛡️ RISK METRICS")
    print(f"   Current DD:     {dd_info['current_dd']:.2f}%")
    print(f"   Max DD Today:   {dd_info['max_dd']:.2f}%")
    print(f"   Risk Per Trade: 1%")
    print()
    
    # Status
    print("=" * 80)
    hour = datetime.now().hour
    if 0 <= hour < 6:
        session = "ASIAN (Low Activity)"
    elif 6 <= hour < 14:
        session = "LONDON (High Volume)"
    elif 14 <= hour < 22:
        session = "NY (Most Active)"
    else:
        session = "NY CLOSE (Winding Down)"
    
    print(f"📍 Current Session: {session}")
    
    # Day Summary (if end of day)
    if hour >= 22 or hour < 2:
        print()
        print("🌙 END OF DAY SUMMARY")
        print(f"   Day P&L:        ${day_pl:+.2f}")
        if stats:
            print(f"   Trades Taken:   {stats['total_trades']}")
            print(f"   Win Rate:       {stats['win_rate']:.1f}%")
            print(f"   Profit Factor:  {stats['profit_factor']:.2f}")
        print(f"   Target:         $10.00 {'✅ EXCEEDED' if day_pl >= 10 else '❌ MISSED' if day_pl < 0 else '⚠️ BELOW TARGET'}")
    
    print("=" * 80)

if __name__ == '__main__':
    main()
