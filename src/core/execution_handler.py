"""
ExecutionHandler -- THE GATEKEEPER.

No hardcoded trade limits. Unlimited wins, protected losses.
  - Daily drawdown cap (via RiskManager) is the ONLY hard limit
  - Pyramiding: adds to winners at 0.5x ATR profit (max 2 concurrent)
  - 3x retry logic on order_send failures
  - All timestamps logged in IST
"""

import time as _time
import logging
import MetaTrader5 as _mt5
from typing import Any, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

mt5: Any = _mt5
log = logging.getLogger(__name__)

# IST offset
IST = timezone(timedelta(hours=5, minutes=30))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LOT_SIZE = 0.01
SYMBOL = "XAUUSDm"
MAX_CONCURRENT_POSITIONS = 2
ORDER_RETRY_COUNT = 3
ORDER_RETRY_DELAY_MS = 500


def _ist_now() -> str:
    """Return current IST time as a formatted string."""
    return datetime.now(IST).strftime("%I:%M:%S %p IST")


@dataclass
class TradeRecord:
    """Lightweight record of a trade we opened."""
    ticket: int
    strategy: str
    direction: str
    price: float
    sl: float
    tp: float
    atr: float
    session: str
    timestamp_ist: str


class ExecutionHandler:
    """Manages order execution with dynamic gating. No hardcoded trade caps."""

    def __init__(self, symbol: str = SYMBOL):
        self.symbol = symbol

    # ------------------------------------------------------------------
    # Position queries
    # ------------------------------------------------------------------

    def get_open_positions(self) -> list:
        """Return open positions for the symbol."""
        positions = mt5.positions_get(symbol=self.symbol)
        return list(positions) if positions else []

    def count_open_positions(self) -> int:
        return len(self.get_open_positions())

    def can_open_new_position(self) -> bool:
        """Max 2 concurrent positions (leverage guard for $100 account)."""
        return self.count_open_positions() < MAX_CONCURRENT_POSITIONS

    # ------------------------------------------------------------------
    # Order execution with retry
    # ------------------------------------------------------------------

    def send_order(
        self,
        signal: int,
        price: float,
        sl: float,
        tp: float,
        strategy_name: str,
        magic: int,
        lot_size: float,
        atr: float = 0.0,
        session: str = "",
        is_pyramid: bool = False,
    ) -> Optional[TradeRecord]:
        """Execute a market order on MT5 with 3x retry logic.

        No daily trade cap. The ONLY gate is:
          1. Max 2 concurrent positions (leverage guard)
          2. Daily drawdown cap (checked in main_loop before calling this)
        """
        if not self.can_open_new_position():
            log.warning(
                f"[{strategy_name}] BLOCKED: Max {MAX_CONCURRENT_POSITIONS} "
                f"concurrent positions. Wait for one to close."
            )
            print(f"[{_ist_now()}] BLOCKED: Max concurrent positions reached")
            return None

        direction = "BUY" if signal == mt5.ORDER_TYPE_BUY else "SELL"
        label = f"PYRAMID {direction}" if is_pyramid else direction

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": signal,
            "price": price,
            "sl": sl,
            "tp": tp,
            "magic": magic,
            "comment": f"{strategy_name}{'_PYR' if is_pyramid else ''}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Retry logic: 3 attempts with 500ms delay
        for attempt in range(1, ORDER_RETRY_COUNT + 1):
            res = mt5.order_send(request)

            if res is None:
                log.error(f"[{strategy_name}] order_send returned None (attempt {attempt}/{ORDER_RETRY_COUNT})")
                if attempt < ORDER_RETRY_COUNT:
                    _time.sleep(ORDER_RETRY_DELAY_MS / 1000.0)
                continue

            if res.retcode == mt5.TRADE_RETCODE_DONE:
                record = TradeRecord(
                    ticket=res.order,
                    strategy=strategy_name,
                    direction=label,
                    price=price,
                    sl=sl,
                    tp=tp,
                    atr=atr,
                    session=session,
                    timestamp_ist=_ist_now(),
                )

                msg = (
                    f"[{strategy_name}] {label} @ {price:.3f} | "
                    f"SL: {sl:.3f} | TP: {tp:.3f} | "
                    f"ATR: {atr:.3f} | Session: {session} | "
                    f"Open: {self.count_open_positions()}/{MAX_CONCURRENT_POSITIONS}"
                )
                log.info(msg)
                print(f"[{_ist_now()}] >> {msg}")
                return record

            else:
                log.error(
                    f"[{strategy_name}] Order FAILED (attempt {attempt}/{ORDER_RETRY_COUNT}): "
                    f"{res.comment} (code {res.retcode})"
                )
                if attempt < ORDER_RETRY_COUNT:
                    _time.sleep(ORDER_RETRY_DELAY_MS / 1000.0)

        print(f"[{_ist_now()}] FAILED: {strategy_name} after {ORDER_RETRY_COUNT} retries")
        return None

    # ------------------------------------------------------------------
    # Position modification (trailing stop)
    # ------------------------------------------------------------------

    def modify_sl(self, ticket: int, new_sl: float, tp: float, symbol: str) -> bool:
        """Modify the stop-loss of an existing position."""
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": symbol,
            "sl": new_sl,
            "tp": tp,
        }
        res = mt5.order_send(request)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            log.info(f"Trailing stop: #{ticket} SL -> {new_sl:.3f}")
            print(f"[{_ist_now()}] TRAIL: #{ticket} SL -> {new_sl:.3f}")
            return True
        return False

    # ------------------------------------------------------------------
    # Position closure
    # ------------------------------------------------------------------

    def close_position(self, position) -> bool:
        """Close an open position (for consolidation exit)."""
        close_type = (
            mt5.ORDER_TYPE_SELL
            if position.type == mt5.ORDER_TYPE_BUY
            else mt5.ORDER_TYPE_BUY
        )
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            return False

        price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": close_type,
            "position": position.ticket,
            "price": price,
            "magic": position.magic,
            "comment": "consolidation_exit",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res = mt5.order_send(request)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            log.info(f"Consolidation exit: closed #{position.ticket} @ {price:.3f}")
            print(f"[{_ist_now()}] CLOSED: #{position.ticket} (consolidation) @ {price:.3f}")
            return True
        return False
