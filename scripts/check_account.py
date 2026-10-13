import os
import MetaTrader5 as mt5

mt5.initialize()
login = int(os.environ.get("MT5_LOGIN", 198874999))
password = os.environ.get("MT5_PASSWORD", "")
server = os.environ.get("MT5_SERVER", "Exness-MT5Trial11")
if password:
    mt5.login(login, password, server)
else:
    mt5.login(login, server=server)

acc = mt5.account_info()
pos = mt5.positions_get()

print(f'Balance: ${acc.balance:.2f}')
print(f'Equity: ${acc.equity:.2f}')
print(f'Floating P/L: ${acc.equity - acc.balance:.2f}')
print(f'Open Positions: {len(pos) if pos else 0}')

if pos:
    for p in pos:
        print(f'  Ticket {p.ticket}: {p.type} {p.volume} lots @ {p.price_open}, current P/L: ${p.profit:.2f}')

mt5.shutdown()
