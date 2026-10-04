"""Check MT5 connection and account status"""
import MetaTrader5 as mt5

# Initialize MT5
if not mt5.initialize():
    print("❌ MT5 not connected!")
    print(f"Error: {mt5.last_error()}")
    exit(1)

# Get account info
info = mt5.account_info()
terminal = mt5.terminal_info()

if info:
    print("="*80)
    print("MT5 CONNECTION STATUS")
    print("="*80)
    print(f"✅ Connected: YES")
    print(f"Account: {info.login}")
    print(f"Broker: {info.company}")
    print(f"Server: {info.server}")
    print()
    print(f"Balance: ${info.balance:,.2f}")
    print(f"Equity: ${info.equity:,.2f}")
    print(f"Margin: ${info.margin:,.2f}")
    print(f"Free Margin: ${info.margin_free:,.2f}")
    print(f"Profit: ${info.profit:,.2f}")
    print()
    print(f"Account Type: {info.trade_mode}")
    print(f"Leverage: 1:{info.leverage}")
    print(f"Currency: {info.currency}")
    print()
    
    # Check if it's demo or real
    if info.trade_mode == 0:
        account_type = "DEMO ACCOUNT"
    elif info.trade_mode == 1:
        account_type = "REAL ACCOUNT"
    else:
        account_type = "UNKNOWN"
    
    print(f">>> {account_type}")
    
    # Get open positions
    positions = mt5.positions_get()
    print(f"\nOpen Positions: {len(positions) if positions else 0}")
    
    if positions:
        for pos in positions:
            print(f"  - {pos.symbol} {pos.type} {pos.volume} lots @ ${pos.price_open:.2f}")
    
    # Check XAUUSD symbol
    symbol_info = mt5.symbol_info("XAUUSD")
    if symbol_info:
        print(f"\nXAUUSD Symbol Info:")
        print(f"  Spread: {symbol_info.spread} points (~{symbol_info.spread * symbol_info.point:.1f} pips)")
        print(f"  Min lot: {symbol_info.volume_min}")
        print(f"  Max lot: {symbol_info.volume_max}")
        print(f"  Lot step: {symbol_info.volume_step}")
        print(f"  Stops level: {symbol_info.stops_level} points")
    else:
        print("\n⚠️ XAUUSD not available on this account!")
    
else:
    print("❌ Account info not available")

mt5.shutdown()
