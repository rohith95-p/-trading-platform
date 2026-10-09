"""
Hourly monitoring script - sends Telegram updates every hour
Runs until manually stopped (Ctrl+C)
"""
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.chdir(Path(__file__).resolve().parents[1])

from src.core import alerts
import MetaTrader5 as mt5

IST = timezone(timedelta(hours=5, minutes=30))

def get_current_status():
    """Get current account status and format for Telegram"""
    
    if not mt5.initialize():
        return "⚠️ MT5 connection failed"
    
    # Get account info
    account_info = mt5.account_info()
    if not account_info:
        mt5.shutdown()
        return "⚠️ Account info unavailable"
    
    balance = account_info.balance
    equity = account_info.equity
    
    # Get positions
    positions = mt5.positions_get(symbol="XAUUSDm")
    num_positions = len(positions) if positions else 0
    
    floating_pnl = 0.0
    if positions:
        floating_pnl = sum(p.profit for p in positions)
    
    # Get today's trades from trade ledger
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    day_pnl = 0.0
    day_trades = 0
    
    # Check today's trade log file
    trade_log_path = Path(f"logs/trades/{today_str}.jsonl")
    if trade_log_path.exists():
        import json
        with open(trade_log_path, encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    trade = json.loads(line)
                    if trade.get("kind") == "closed":
                        day_pnl += trade.get("profit", 0.0)
                        day_trades += 1
                except:
                    continue
    else:
        # Fallback to ledger file
        ledger_path = Path("logs/trade_ledger.jsonl")
        if ledger_path.exists():
            with open(ledger_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    trade = json.loads(line)
                    if trade.get("date", "").startswith(today_str):
                        if trade.get("action") == "close":
                            day_pnl += trade.get("pnl", 0.0)
                            day_trades += 1
    
    # Check heartbeat
    heartbeat_path = Path("logs/heartbeat")
    bot_status = "🟢 Running"
    if heartbeat_path.exists():
        hb_time = heartbeat_path.stat().st_mtime
        age_minutes = (time.time() - hb_time) / 60
        if age_minutes > 5:
            bot_status = f"🔴 Stale ({int(age_minutes)}m)"
    else:
        bot_status = "🔴 No heartbeat"
    
    mt5.shutdown()
    
    # Format message
    time_str = datetime.now(IST).strftime("%I:%M %p")
    pnl_emoji = "📈" if day_pnl > 0 else "📉" if day_pnl < 0 else "➖"
    
    msg = (
        f"<b>⏰ HOURLY UPDATE - {time_str} IST</b>\n\n"
        f"🤖 Bot: {bot_status}\n"
        f"💰 Balance: <b>${balance:.2f}</b>\n"
        f"💵 Equity: ${equity:.2f}\n\n"
        f"{pnl_emoji} <b>Day P&L: ${day_pnl:+.2f}</b>\n"
        f"📊 Trades: {day_trades}\n"
        f"📍 Open: {num_positions}\n"
        f"🔄 Floating: ${floating_pnl:+.2f}"
    )
    
    return msg


def main():
    print("="*70)
    print("HOURLY MONITOR STARTED")
    print("="*70)
    print("Will send Telegram updates every hour")
    print("Press Ctrl+C to stop")
    print("="*70)
    
    # Check if Telegram is configured
    if not alerts.configured():
        print("\n⚠️  WARNING: Telegram not configured!")
        print("Updates will only show in console, not sent to Telegram")
    
    # Send startup message
    startup_msg = (
        "🚀 <b>Hourly Monitor Started</b>\n"
        "Will send updates every hour\n"
        f"Started at: {datetime.now(IST).strftime('%I:%M %p IST')}"
    )
    alerts.send(startup_msg, severity=alerts.INFO)
    print(f"\n✓ Startup message sent")
    
    update_count = 0
    
    try:
        while True:
            # Wait 1 hour
            print(f"\nWaiting 1 hour... (Update #{update_count + 1} queued)")
            time.sleep(3600)  # 60 minutes
            
            # Get status and send
            msg = get_current_status()
            alerts.send(msg, severity=alerts.INFO)
            
            update_count += 1
            print(f"\n✓ Update #{update_count} sent at {datetime.now(IST).strftime('%I:%M %p IST')}")
            print(msg.replace("<b>", "").replace("</b>", ""))
            
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("STOPPING MONITOR")
        print("="*70)
        
        # Send shutdown message
        shutdown_msg = (
            "🛑 <b>Hourly Monitor Stopped</b>\n"
            f"Total updates sent: {update_count}\n"
            f"Stopped at: {datetime.now(IST).strftime('%I:%M %p IST')}"
        )
        alerts.send(shutdown_msg, severity=alerts.INFO)
        print("✓ Shutdown message sent")


if __name__ == "__main__":
    main()
