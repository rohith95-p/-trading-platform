"""Notification channel -- REAL_MONEY_READINESS.md IV.1.

The watchdog's `_alert()` has been a `print()` stub since it was written, which
means every failure it was built to catch (main_loop dying, hung heartbeat,
repeated restarts) announced itself only to a terminal nobody was watching.
The Sept 3-5 outage is the proof: main_loop, watchdog and protect_profit all
stopped, and nothing told anyone for two days.

Channels are opt-in via environment variables, so nothing here leaks config or
breaks if unconfigured:

    ULTRA_ALERT_TELEGRAM_TOKEN   + ULTRA_ALERT_TELEGRAM_CHAT   (Telegram bot)
    ULTRA_ALERT_WEBHOOK          (any POST-accepting URL: ntfy, Slack, Discord)

With neither set, alerts still land in logs/alerts.log and on stdout, so the
record exists even when delivery isn't configured. Every send is best-effort
and never raises -- an alerting failure must not take down trading.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Optional

log = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
ALERT_LOG = os.path.join("logs", "alerts.log")
TIMEOUT = 8

# Severity prefixes so a phone notification is triage-able at a glance.
INFO, WARN, CRITICAL = "INFO", "WARN", "CRITICAL"


def _record(line: str) -> None:
    try:
        os.makedirs(os.path.dirname(ALERT_LOG), exist_ok=True)
        with open(ALERT_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _telegram(text: str) -> bool:
    token = os.environ.get("ULTRA_ALERT_TELEGRAM_TOKEN")
    chat = os.environ.get("ULTRA_ALERT_TELEGRAM_CHAT")
    if not token or not chat:
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return 200 <= r.status < 300
    except (urllib.error.URLError, OSError, ValueError) as e:
        log.warning(f"telegram alert failed: {e}")
        return False


def _webhook(text: str, severity: str) -> bool:
    url = os.environ.get("ULTRA_ALERT_WEBHOOK")
    if not url:
        return False
    try:
        payload = json.dumps({"text": text, "severity": severity}).encode()
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return 200 <= r.status < 300
    except (urllib.error.URLError, OSError, ValueError) as e:
        log.warning(f"webhook alert failed: {e}")
        return False


def send(message: str, severity: str = WARN, context: Optional[dict] = None) -> bool:
    """Fire an alert on every configured channel. Returns True if any delivered."""
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    text = f"[{severity}] ULTRA CORE {now}\n{message}"
    if context:
        text += "\n" + "\n".join(f"  {k}: {v}" for k, v in context.items())

    _record(text.replace("\n", " | "))
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode('ascii'))

    delivered = False
    for fn in (lambda: _telegram(text), lambda: _webhook(text, severity)):
        try:
            delivered = fn() or delivered
        except Exception as e:  # belt and braces -- never propagate
            log.warning(f"alert channel raised: {e}")
    return delivered


def configured() -> bool:
    return bool(os.environ.get("ULTRA_ALERT_TELEGRAM_TOKEN")
                or os.environ.get("ULTRA_ALERT_WEBHOOK"))
