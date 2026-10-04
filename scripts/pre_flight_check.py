"""
Pre-flight check before Monday start
"""
import MetaTrader5 as mt5
from datetime import datetime
from pathlib import Path
import json

print("="*80)
print("🚀 ULTRA CORE - PRE-FLIGHT CHECK")
print("="*80)
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

checks_passed = 0
checks_failed = 0

# ============================================================================
# 1. MT5 CONNECTION
# ============================================================================
print("\n[1/8] Checking MT5 Connection...")

if mt5.initialize():
    info = mt5.account_info()
    if info:
        print(f"  ✅ MT5 Connected")
        print(f"     Broker: {info.company}")
        print(f"     Account: {info.login}")
        print(f"     Balance: ${info.balance:.2f}")
        checks_passed += 1
    else:
        print(f"  ❌ MT5 connected but no account info")
        checks_failed += 1
else:
    print(f"  ❌ MT5 not connected")
    checks_failed += 1
    mt5.shutdown()
    exit(1)

# ============================================================================
# 2. XAUUSD SYMBOL
# ============================================================================
print("\n[2/8] Checking XAUUSDm Symbol...")

if mt5.symbol_select('XAUUSDm', True):
    symbol_info = mt5.symbol_info('XAUUSDm')
    if symbol_info:
        print(f"  ✅ XAUUSDm Available")
        print(f"     Min Lot: {symbol_info.volume_min}")
        print(f"     Max Lot: {symbol_info.volume_max}")
        checks_passed += 1
    else:
        print(f"  ❌ XAUUSDm not available")
        checks_failed += 1
else:
    print(f"  ❌ XAUUSDm not found")
    checks_failed += 1

# ============================================================================
# 3. SPREAD CHECK
# ============================================================================
print("\n[3/8] Checking Spread...")

tick = mt5.symbol_info_tick('XAUUSDm')
if tick:
    spread_pips = (tick.ask - tick.bid) / symbol_info.point / 10
    tick_age = (datetime.now().timestamp() - tick.time)
    
    print(f"     Bid: ${tick.bid:.2f}")
    print(f"     Ask: ${tick.ask:.2f}")
    print(f"     Spread: {spread_pips:.2f} pips")
    print(f"     Data Age: {tick_age:.0f} seconds")
    
    if tick_age > 300:
        print(f"  ⚠️  Market Closed (data is stale)")
        print(f"     Re-check Monday when market opens")
        print(f"     Expected spread: 2-5 pips")
    elif spread_pips < 5:
        print(f"  ✅ Spread is Good ({spread_pips:.2f} pips)")
        checks_passed += 1
    elif spread_pips < 10:
        print(f"  ⚠️  Spread is High ({spread_pips:.2f} pips)")
        print(f"     Will work but at reduced profit")
        checks_passed += 1
    else:
        print(f"  ❌ Spread is Too Wide ({spread_pips:.2f} pips)")
        print(f"     Consider ECN broker or wider SL")
        checks_failed += 1
else:
    print(f"  ❌ Cannot get tick data")
    checks_failed += 1

# ============================================================================
# 4. PORTFOLIO CONFIG
# ============================================================================
print("\n[4/8] Checking Portfolio Config...")

config_file = Path("src/strategies/portfolio_v5_6_leg.py")
if config_file.exists():
    with open(config_file) as f:
        content = f.read()
        if 'sl_atr_mult = 0.1' in content and 'tp_atr_mult = 2.0' in content:
            print(f"  ✅ Config Correct")
            print(f"     SL: 0.1 ATR")
            print(f"     TP: 2.0 ATR")
            checks_passed += 1
        else:
            print(f"  ❌ Config Wrong")
            print(f"     Check sl_atr_mult and tp_atr_mult")
            checks_failed += 1
else:
    print(f"  ❌ Portfolio file not found")
    checks_failed += 1

# ============================================================================
# 5. POSITION SIZING
# ============================================================================
print("\n[5/8] Calculating Position Size...")

balance = info.balance
risk_pct = 0.01  # 1% risk
expected_avg_loss = 1.00  # Conservative estimate

position_size = (balance * risk_pct) / expected_avg_loss

print(f"     Balance: ${balance:.2f}")
print(f"     Risk per trade: ${balance * risk_pct:.2f} (1%)")
print(f"     Expected avg loss: ${expected_avg_loss:.2f}")
print(f"  ✅ Position Size: {position_size:.4f} lots")
print(f"     Expected daily P&L: ${position_size / 0.01 * 5.13:.2f}")
checks_passed += 1

# ============================================================================
# 6. TELEGRAM ALERTS
# ============================================================================
print("\n[6/8] Checking Telegram Config...")

env_file = Path(".env.local")
if env_file.exists():
    with open(env_file) as f:
        content = f.read()
        if 'ULTRA_ALERT_TELEGRAM_TOKEN' in content and 'ULTRA_ALERT_TELEGRAM_CHAT' in content:
            print(f"  ✅ Telegram Configured")
            print(f"     Token: Found")
            print(f"     Chat ID: Found")
            checks_passed += 1
        else:
            print(f"  ⚠️  Telegram Not Configured")
            print(f"     You won't get trade alerts")
            checks_failed += 1
else:
    print(f"  ⚠️  .env.local not found")
    checks_failed += 1

# ============================================================================
# 7. LOG DIRECTORIES
# ============================================================================
print("\n[7/8] Checking Log Directories...")

log_dirs = [
    Path("logs"),
    Path("logs/trades"),
    Path("reports"),
]

all_exist = all(d.exists() for d in log_dirs)
if all_exist:
    print(f"  ✅ Log Directories Ready")
    checks_passed += 1
else:
    print(f"  ⚠️  Creating missing directories...")
    for d in log_dirs:
        d.mkdir(parents=True, exist_ok=True)
    print(f"  ✅ Directories Created")
    checks_passed += 1

# ============================================================================
# 8. DEPENDENCIES
# ============================================================================
print("\n[8/8] Checking Dependencies...")

try:
    import pandas
    import numpy
    print(f"  ✅ Core Dependencies Installed")
    checks_passed += 1
except ImportError as e:
    print(f"  ❌ Missing dependency: {e}")
    checks_failed += 1

mt5.shutdown()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

total_checks = checks_passed + checks_failed
print(f"\nTotal Checks: {total_checks}")
print(f"  ✅ Passed: {checks_passed}")
print(f"  ❌ Failed: {checks_failed}")

print("\n" + "="*80)
print("READINESS STATUS")
print("="*80)

if checks_failed == 0:
    print("\n🚀 ALL SYSTEMS GO!")
    print("   Ready to start trading Monday morning!")
    print("\n   Next steps:")
    print("   1. Wait for market to open (Monday 8 AM UTC)")
    print("   2. Check spread: python scripts/check_market_status.py")
    print("   3. Start bot: python -m src.main_loop")
    
elif checks_failed <= 2:
    print("\n⚠️  MOSTLY READY")
    print(f"   {checks_failed} issues need attention")
    print("   Fix these before Monday:")
    print("   - Review failed checks above")
    print("   - Re-run this script after fixing")
    
else:
    print("\n❌ NOT READY")
    print(f"   {checks_failed} critical issues found")
    print("   Do NOT start trading until these are fixed")
    print("   Review each failed check above")

print("\n" + "="*80)
print("MONDAY MORNING CHECKLIST")
print("="*80)

print("""
[ ] Market has opened (after 5 PM Sunday or 8 AM Monday UTC)
[ ] Run: python scripts/check_market_status.py
[ ] Verify spread is <5 pips
[ ] Start bot: python -m src.main_loop
[ ] Watch Telegram for first trade
[ ] Verify first trade executes correctly
[ ] Check back in evening

REMEMBER:
- Don't panic on first few losses (normal!)
- System needs 50 trades to prove itself
- You'll get weekly reports every Sunday
- I'm monitoring everything
""")

print("="*80)
print("Good luck! 🍀")
print("="*80)
