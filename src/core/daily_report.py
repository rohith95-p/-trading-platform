"""daily_report.py -- Generates and sends a daily P&L summary."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone

from src.core import alerts, risk_rules, news_filter

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))


def generate_report(date_str: str) -> str:
    """Generate daily P&L report string for the given date (YYYY-MM-DD)."""
    log_path = os.path.join("logs", "trades", f"{date_str}.jsonl")
    trades = []
    
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("kind") == "closed":
                        trades.append(rec)
                except json.JSONDecodeError:
                    pass
    
    n_trades = len(trades)
    wins = [t for t in trades if t.get("profit", 0) > 0]
    losses = [t for t in trades if t.get("profit", 0) <= 0]
    win_rate = (len(wins) / n_trades * 100) if n_trades > 0 else 0
    day_pl = sum(t.get("profit", 0) for t in trades)
    
    state = risk_rules.load_state()
    # If state is missing a start balance, approximate with current peak equity
    ref_balance = state.day_start_balance if state.day_start_balance > 0 else state.peak_equity
    balance = ref_balance + day_pl
    
    dd_today = 0.0
    if ref_balance > 0 and day_pl < 0:
        dd_today = (abs(day_pl) / ref_balance) * 100
        
    # Check for tomorrow's news (next 24 hours from now)
    now_ist = datetime.now(IST)
    upcoming = news_filter.upcoming_events(hours_ahead=24, now=now_ist)
    
    # Format date: "17 Sep 2026"
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_date = dt.strftime("%d %b %Y")
    
    lines = [
        f"📊 Ultra Core Daily — {formatted_date}",
        f"Balance: ${balance:.2f} | Day P&L: {'+' if day_pl > 0 else ''}${day_pl:.2f}",
        f"Trades: {n_trades} | W: {len(wins)} | L: {len(losses)} | Win rate: {win_rate:.0f}%",
        f"Risk state: {state.consecutive_losses} consecutive losses | DD today: {dd_today:.1f}%",
    ]
    
    if upcoming:
        ev = upcoming[0]
        lines.append(f"News blackout tomorrow: {ev['name']} @ {ev['utc_time']} UTC")
    else:
        lines.append("News blackout tomorrow: None")
        
    return "\n".join(lines)


def send_daily_report(force: bool = False) -> None:
    """Send the daily report. If force is True, sends for today, else for yesterday."""
    now = datetime.now(IST)
    if force:
        date_str = now.strftime("%Y-%m-%d")
    else:
        date_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        
    # Check if there was activity before sending, unless forced
    log_path = os.path.join("logs", "trades", f"{date_str}.jsonl")
    if not force and not os.path.exists(log_path):
        log.info(f"daily_report: No activity found for {date_str}, skipping report.")
        return
        
    report = generate_report(date_str)
    alerts.send(report, severity=alerts.INFO)
