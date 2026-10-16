"""
Quick Status - Fast snapshot without all the details
For when you just want P&L and positions
"""
import os
import sys
import re
from datetime import datetime

# Windows console encoding fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

mt5_connected = False
acc = None
positions = []
try:
    import MetaTrader5 as mt5
    if mt5.initialize():
        t_info = mt5.terminal_info()
        mt5_connected = bool(t_info and getattr(t_info, "connected", False))
        acc = mt5.account_info()
        positions = mt5.positions_get() or []
        mt5.shutdown()
except Exception:
    pass

# Fallback to engine state files if MT5 direct connection is busy
balance = None
equity = None
open_count = 0
positions_detail = []
if acc:
    balance = acc.balance
    equity = acc.equity
    open_count = len(positions)
else:
    pos_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "positions.txt")
    if os.path.exists(pos_file):
        try:
            with open(pos_file, "r") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            if lines:
                m = re.search(r"bal\s+([\d\.]+)\s+eq\s+([\d\.]+)\s+open\s+(\d+)", lines[0])
                if m:
                    balance = float(m.group(1))
                    equity = float(m.group(2))
                    open_count = int(m.group(3))
                positions_detail = lines[1:]
        except Exception:
            pass

floating_pl = (equity - balance) if (equity is not None and balance is not None) else 0.0

print(f"\n⚡ QUICK STATUS - {datetime.now().strftime('%H:%M:%S')}")
print(f"Broker Connection: {'🟢 CONNECTED' if mt5_connected else '🔴 DISCONNECTED'}")
if balance is not None:
    print(f"Balance: ${balance:.2f} | Equity: ${equity:.2f} | Floating: ${floating_pl:+.2f}")
else:
    print("Balance: UNKNOWN (MT5 Offline)")
print(f"Open Positions: {open_count}")
for pd in positions_detail:
    print(f"  {pd}")

# Check heartbeat
hb_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "heartbeat")
if os.path.exists(hb_file):
    try:
        age = datetime.now().timestamp() - os.path.getmtime(hb_file)
        print(f"Loop Engine: {'🟢 ACTIVE' if age <= 300 else '🔴 STALE'} ({age:.0f}s ago)")
    except Exception:
        pass
print()

