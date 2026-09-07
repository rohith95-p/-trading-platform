"""Structured event log -- Part IV.8 of REAL_MONEY_READINESS.md.

The stated goal there: "any trading day can be fully reconstructed from the log
alone." That was never built. `logs/trade_ledger.jsonl` existed but nothing
wrote to it -- a single stale line from 2026-08-31 was its entire contents, so
the only real record of live behaviour was free-text `main_loop.log` plus the
broker's own deal history.

This is the missing piece, and it is also the substrate for the 8-week paper
test (I.9): without a machine-readable record of what the bot did and why, a
weekly "live vs backtest" comparison can't be automated.

Writes JSON lines to logs/trades/YYYY-MM-DD.jsonl (IST calendar day, rotated
daily). Every record carries: ts (unix), ist (readable), kind, and a payload.
Never raises -- a logging failure must not take down the trading loop.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
LOG_DIR = os.path.join("logs", "trades")

# Event kinds, so readers can filter without string-guessing.
SIGNAL = "signal"            # a strategy produced (or was denied) a signal
ORDER = "order"              # an order was sent, with the broker's reply
POSITION_CLOSED = "closed"   # a position finished, with realised P&L
GATE = "gate"                # a gate/breaker/cap decision
LIFECYCLE = "lifecycle"      # startup, shutdown, reconnect, kill switch
ERROR = "error"


def _path(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(IST)
    return os.path.join(LOG_DIR, f"{now.date().isoformat()}.jsonl")


def write(kind: str, **payload: Any) -> None:
    """Append one structured event. Silent on failure by design."""
    try:
        now = datetime.now(IST)
        rec = {
            "ts": int(now.timestamp()),
            "ist": now.strftime("%Y-%m-%d %H:%M:%S"),
            "kind": kind,
            **payload,
        }
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(_path(now), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    except Exception as e:  # never let logging break trading
        log.warning(f"trade_log write failed ({kind}): {e}")


# --- Convenience wrappers, so call sites stay readable ---------------------

def signal(strategy: str, direction: str, action: str, reason: str = "", **ctx) -> None:
    """action: 'fired' | 'blocked' | 'deduped' | 'queued'."""
    write(SIGNAL, strategy=strategy, direction=direction, action=action, reason=reason, **ctx)


def order(strategy: str, direction: str, lots: float, price: Optional[float] = None,
          sl: Optional[float] = None, tp: Optional[float] = None,
          retcode: Optional[int] = None, ticket: Optional[int] = None,
          comment: str = "", **ctx) -> None:
    write(ORDER, strategy=strategy, direction=direction, lots=lots, price=price,
          sl=sl, tp=tp, retcode=retcode, ticket=ticket, comment=comment, **ctx)


def position_closed(strategy: str, ticket: Optional[int], profit: float, **ctx) -> None:
    write(POSITION_CLOSED, strategy=strategy, ticket=ticket, profit=profit, **ctx)


def gate(name: str, allowed: bool, reason: str = "", **ctx) -> None:
    write(GATE, gate=name, allowed=allowed, reason=reason, **ctx)


def lifecycle(event: str, **ctx) -> None:
    write(LIFECYCLE, event=event, **ctx)


def error(where: str, message: str, **ctx) -> None:
    write(ERROR, where=where, message=message, **ctx)


# --- Reading back, for the weekly paper-test review ------------------------

def read_range(start: datetime, end: datetime) -> List[Dict[str, Any]]:
    """All events with ts in [start, end), across daily files."""
    out: List[Dict[str, Any]] = []
    day = start.astimezone(IST).date()
    last = end.astimezone(IST).date()
    while day <= last:
        p = os.path.join(LOG_DIR, f"{day.isoformat()}.jsonl")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    if start.timestamp() <= rec.get("ts", 0) < end.timestamp():
                        out.append(rec)
        day += timedelta(days=1)
    return out
