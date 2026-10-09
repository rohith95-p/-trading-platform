"""
Quick Status - Fast snapshot without all the details
For when you just want P&L and positions
"""
import MetaTrader5 as mt5
from datetime import datetime

mt5.initialize()
mt5.login(198874999, 'Rohith@95', 'Exness-MT5Trial11')

acc = mt5.account_info()
positions = mt5.positions_get()
floating_pl = sum(p.profit for p in positions) if positions else 0.0

starting_balance = 154.58
day_pl = acc.balance - starting_balance + floating_pl

print(f"\n⚡ QUICK STATUS - {datetime.now().strftime('%H:%M:%S')}")
print(f"Balance: ${acc.balance:.2f} | Day P&L: ${day_pl:+.2f} ({(day_pl/starting_balance*100):+.1f}%)")
print(f"Open: {len(positions) if positions else 0} | Floating: ${floating_pl:+.2f}")
if positions:
    for p in positions:
        print(f"  #{p.ticket}: {'BUY' if p.type==0 else 'SELL'} {p.volume} @ {p.price_open:.2f} → ${p.profit:+.2f}")
print()

mt5.shutdown()
