"""
Pre-Market Checklist - Run before starting trading each day
Checks everything important before market open
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.chdir(Path(__file__).resolve().parents[1])

import MetaTrader5 as mt5

IST = timezone(timedelta(hours=5, minutes=30))

def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")

def print_section(text):
    print(f"\n{'─'*70}")
    print(f"📋 {text}")
    print(f"{'─'*70}")

def check_mark(condition, true_msg, false_msg):
    if condition:
        print(f"  ✅ {true_msg}")
        return True
    else:
        print(f"  ❌ {false_msg}")
        return False

def main():
    now = datetime.now(IST)
    today = now.strftime("%A, %B %d, %Y")
    
    print_header(f"PRE-MARKET CHECK - {today}")
    print(f"Current Time: {now.strftime('%I:%M %p IST')}\n")
    
    checks_passed = 0
    checks_failed = 0
    warnings = 0
    
    # ================================================================
    # 1. MT5 CONNECTION
    # ================================================================
    print_section("1. MT5 Connection & Account")
    
    if not mt5.initialize():
        print("  ❌ CRITICAL: MT5 initialization failed")
        print("  → Solution: Open MT5 terminal manually")
        return
    
    checks_passed += 1
    print("  ✅ MT5 initialized")
    
    account_info = mt5.account_info()
    if not account_info:
        print("  ❌ CRITICAL: Cannot get account info")
        mt5.shutdown()
        return
    
    checks_passed += 1
    print(f"  ✅ Account: {account_info.login}")
    print(f"  ✅ Server: {account_info.server}")
    print(f"  ✅ Balance: ${account_info.balance:.2f}")
    print(f"  ✅ Equity: ${account_info.equity:.2f}")
    
    # Check if demo or real
    if "demo" in account_info.server.lower() or "trial" in account_info.server.lower():
        print(f"  ℹ️  Account Type: DEMO")
    else:
        print(f"  ⚠️  Account Type: REAL MONEY")
        warnings += 1
    
    # ================================================================
    # 2. SYMBOL STATUS
    # ================================================================
    print_section("2. Symbol Status (XAUUSDm)")
    
    symbol_info = mt5.symbol_info("XAUUSDm")
    if not symbol_info:
        print("  ❌ CRITICAL: Cannot get XAUUSDm symbol info")
        checks_failed += 1
    else:
        checks_passed += 1
        print(f"  ✅ Symbol: {symbol_info.name}")
        print(f"  ✅ Bid: ${symbol_info.bid:.2f}")
        print(f"  ✅ Ask: ${symbol_info.ask:.2f}")
        print(f"  ✅ Spread: {symbol_info.spread} points ({(symbol_info.ask - symbol_info.bid):.2f} $)")
        
        # Check if trading allowed
        if symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
            print("  ✅ Trading: ALLOWED")
            checks_passed += 1
        else:
            print("  ❌ Trading: DISABLED")
            checks_failed += 1
        
        # Warn about high spread
        spread_dollars = symbol_info.ask - symbol_info.bid
        if spread_dollars > 1.0:
            print(f"  ⚠️  HIGH SPREAD: ${spread_dollars:.2f} (normal is $0.20-0.50)")
            warnings += 1
    
    # ================================================================
    # 3. OPEN POSITIONS
    # ================================================================
    print_section("3. Open Positions")
    
    positions = mt5.positions_get(symbol="XAUUSDm")
    if positions is None:
        positions = []
    
    if len(positions) == 0:
        print("  ✅ No open positions (clean slate)")
        checks_passed += 1
    else:
        print(f"  ⚠️  {len(positions)} position(s) still open")
        warnings += 1
        for pos in positions:
            pnl = pos.profit
            pnl_icon = "🟢" if pnl > 0 else "🔴"
            print(f"     {pnl_icon} Ticket #{pos.ticket}: {pos.type_str} @ ${pos.price_open:.2f} | P&L: ${pnl:+.2f}")
    
    # ================================================================
    # 4. BOT STATUS
    # ================================================================
    print_section("4. Bot Status")
    
    # Check lock file
    lock_file = Path("logs/main_loop.lock")
    if lock_file.exists():
        print("  ⚠️  Lock file exists (bot may be running)")
        warnings += 1
        try:
            age = (datetime.now().timestamp() - lock_file.stat().st_mtime) / 60
            print(f"     Lock age: {age:.1f} minutes")
            if age > 10:
                print("     💡 Stale lock - safe to delete")
        except:
            pass
    else:
        print("  ✅ No lock file (bot not running)")
        checks_passed += 1
    
    # Check heartbeat
    heartbeat_file = Path("logs/heartbeat")
    if heartbeat_file.exists():
        try:
            age = (datetime.now().timestamp() - heartbeat_file.stat().st_mtime) / 60
            if age < 5:
                print(f"  ⚠️  Heartbeat is RECENT ({age:.1f}m ago) - bot might be running!")
                warnings += 1
            else:
                print(f"  ✅ Heartbeat stale ({age:.0f}m ago) - bot is stopped")
                checks_passed += 1
        except:
            print("  ✅ Heartbeat file exists but can't read")
    else:
        print("  ✅ No heartbeat file")
        checks_passed += 1
    
    # ================================================================
    # 5. YESTERDAY'S PERFORMANCE
    # ================================================================
    print_section("5. Yesterday's Performance")
    
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_report = Path(f"daily_trade_progress/{yesterday}*.md")
    
    import glob
    reports = glob.glob(str(yesterday_report))
    
    if reports:
        print(f"  ✅ Yesterday's report exists: {Path(reports[0]).name}")
        # Try to extract P&L
        try:
            with open(reports[0], encoding='utf-8') as f:
                content = f.read()
                if "Day P&L" in content:
                    import re
                    match = re.search(r'Day P&L.*?\$([+-]?\d+\.\d+)', content)
                    if match:
                        pnl = float(match.group(1))
                        icon = "📈" if pnl > 0 else "📉" if pnl < 0 else "➖"
                        print(f"     {icon} P&L: ${pnl:+.2f}")
        except:
            pass
    else:
        print(f"  ℹ️  No report for yesterday ({yesterday})")
    
    # ================================================================
    # 6. MARKET HOURS
    # ================================================================
    print_section("6. Market Hours & Schedule")
    
    current_hour = now.hour + now.minute / 60.0
    
    # Trading window
    if 6.0 <= current_hour < 21.5:
        print(f"  ✅ Within trading window (6:00 AM - 9:30 PM)")
        checks_passed += 1
    else:
        print(f"  ⚠️  Outside trading window (current: {now.strftime('%I:%M %p')})")
        warnings += 1
    
    # Session info
    if 11.5 <= current_hour < 15.5:
        print("  📍 Current: London Open session (11:30 AM - 3:30 PM)")
    elif 17.5 <= current_hour < 21.5:
        print("  📍 Current: NY Morning session (5:30 PM - 9:30 PM) 🔥")
    elif 6.0 <= current_hour < 11.5:
        print("  📍 Current: Pre-London (6:00 AM - 11:30 AM)")
    else:
        print("  📍 Current: Outside trading hours")
    
    # Best trading times
    print(f"\n  🔥 Peak Times Today:")
    print(f"     • London Open: 11:30 AM - 3:30 PM")
    print(f"     • NY Session:  5:30 PM - 9:30 PM (BEST)")
    
    # ================================================================
    # 7. D1 BIAS
    # ================================================================
    print_section("7. Daily Trend Bias (D1 Gate)")
    
    d1_rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_D1, 0, 100)
    if d1_rates is not None and len(d1_rates) >= 20:
        closes = d1_rates['close']
        
        # Calculate EMA20
        def calc_ema(data, period):
            ema = [sum(data[:period]) / period]
            multiplier = 2.0 / (period + 1.0)
            for price in data[period:]:
                ema.append((price - ema[-1]) * multiplier + ema[-1])
            return ema
        
        ema20 = calc_ema(closes, 20)
        current_price = closes[-2]  # D1[-2] is completed daily bar
        current_ema = ema20[-2]
        
        if current_price > current_ema:
            bias = "BULLISH"
            icon = "🟢"
            allowed = "BUY trades allowed, SELL blocked"
        else:
            bias = "BEARISH"
            icon = "🔴"
            allowed = "SELL trades allowed, BUY blocked"
        
        gap = abs(current_price - current_ema)
        gap_pct = (gap / current_ema) * 100
        
        print(f"  {icon} D1 Bias: {bias}")
        print(f"     Price: ${current_price:.2f}")
        print(f"     EMA20: ${current_ema:.2f}")
        print(f"     Gap: ${gap:.2f} ({gap_pct:.2f}%)")
        print(f"     → {allowed}")
        
        checks_passed += 1
    else:
        print("  ⚠️  Cannot calculate D1 bias")
        warnings += 1
    
    # ================================================================
    # 8. DISK SPACE
    # ================================================================
    print_section("8. System Health")
    
    # Check logs directory size
    logs_size = 0
    logs_path = Path("logs")
    if logs_path.exists():
        for file in logs_path.rglob("*"):
            if file.is_file():
                logs_size += file.stat().st_size
        
        logs_mb = logs_size / (1024 * 1024)
        print(f"  ✅ Logs size: {logs_mb:.1f} MB")
        
        if logs_mb > 100:
            print(f"     ⚠️  Logs are getting large (>100 MB)")
            warnings += 1
    
    # Check daily report folder
    reports_path = Path("daily_trade_progress")
    if reports_path.exists():
        report_count = len(list(reports_path.glob("*.md")))
        print(f"  ✅ Daily reports: {report_count} files")
    
    mt5.shutdown()
    
    # ================================================================
    # SUMMARY
    # ================================================================
    print_header("SUMMARY")
    
    print(f"\n✅ Checks Passed: {checks_passed}")
    if warnings > 0:
        print(f"⚠️  Warnings: {warnings}")
    if checks_failed > 0:
        print(f"❌ Checks Failed: {checks_failed}")
    
    print(f"\n{'='*70}")
    
    if checks_failed > 0:
        print("🔴 CRITICAL ISSUES FOUND - DO NOT START BOT")
        print("   Fix the issues above before trading")
    elif warnings > 0:
        print("🟡 READY WITH WARNINGS")
        print("   Review warnings above, then start bot if OK")
    else:
        print("🟢 ALL SYSTEMS GO - READY TO TRADE")
        print("   Start bot: python -m src.core.main_loop")
    
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
