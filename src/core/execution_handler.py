"""
ExecutionHandler -- THE GATEKEEPER.

No hardcoded trade limits. Unlimited wins, protected losses.
  - Daily drawdown cap (via RiskManager) is the ONLY hard limit
  - Pyramiding: adds to winners at 0.5x ATR profit (max 3 concurrent, 2 per side)
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
SYMBOL = "XAUUSDm"

# Owner's rule (2026-09-02): total open exposure on the symbol must never exceed
# 0.02 lots. With FIXED_LOT_SIZE = 0.01 that is at most 2 concurrent positions.
# Was 3 (-> 0.03 lots possible, which is what the owner flagged).
MAX_CONCURRENT_POSITIONS = 2
MAX_SAME_DIRECTION_POSITIONS = 2

# Hard exposure ceiling, checked against actual open volume (bot + manual) so it
# holds even if a position is opened outside this handler.
MAX_TOTAL_VOLUME = 0.02

ORDER_RETRY_COUNT = 3
ORDER_RETRY_DELAY_MS = 500

# HARD LOT CAP. The account owner's rule: every position is 0.01 lots, always --
# fresh entries and pyramid adds alike. This is not a risk-model output, it is a
# fixed ceiling the owner set. The dynamic sizer (RiskManager.calculate_dynamic_
# lot_size, risk_pct=0.15) previously sized entries up to 0.02-0.03 lots on a
# ~$105 account; live evidence 2026-09-02 (tickets 633818770 @0.02, 633822753
# @0.03). Enforced here because send_order is the single chokepoint every order
# passes through -- no caller can exceed it.
FIXED_LOT_SIZE = 0.01

# Market orders were previously sent with no deviation, i.e. zero permitted
# slippage, against a price captured before the stop calculation ran. Any tick
# between capture and send rejected the order.
ORDER_DEVIATION_POINTS = 30


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

    def get_same_direction_count(self, is_buy: bool) -> int:
        positions = self.get_open_positions()
        target_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
        return sum(1 for p in positions if p.type == target_type)

    def can_open_new_position(self) -> bool:
        """Max concurrent positions (leverage guard)."""
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

        Gates applied here:
          1. MAX_CONCURRENT_POSITIONS (currently 2)
          2. MAX_SAME_DIRECTION_POSITIONS (currently 2)
          3. MAX_TOTAL_VOLUME (0.02 lots of open exposure, owner's hard cap)
        The daily drawdown cap is checked in main_loop before calling this.
        """
        if not self.can_open_new_position():
            log.warning(
                f"[{strategy_name}] BLOCKED: Max {MAX_CONCURRENT_POSITIONS} "
                f"concurrent positions. Wait for one to close."
            )
            print(f"[{_ist_now()}] BLOCKED: Max concurrent positions reached")
            return None

        # Hard 0.01-lot cap -- owner's rule, applied to every order regardless of
        # what the caller computed.
        if lot_size != FIXED_LOT_SIZE:
            log.warning(
                f"[{strategy_name}] lot size {lot_size} overridden to fixed "
                f"{FIXED_LOT_SIZE} (owner's hard cap)."
            )
            lot_size = FIXED_LOT_SIZE

        # Hard exposure ceiling: never let total open volume exceed 0.02 lots.
        open_volume = sum(p.volume for p in self.get_open_positions())
        if open_volume + lot_size > MAX_TOTAL_VOLUME + 1e-9:
            log.warning(
                f"[{strategy_name}] BLOCKED: open volume {open_volume:.2f} + "
                f"{lot_size:.2f} would exceed cap {MAX_TOTAL_VOLUME:.2f} lots."
            )
            print(f"[{_ist_now()}] BLOCKED: 0.02-lot exposure cap reached")
            return None

        is_buy = signal == mt5.ORDER_TYPE_BUY
        if self.get_same_direction_count(is_buy) >= MAX_SAME_DIRECTION_POSITIONS:
            log.warning(
                f"[{strategy_name}] BLOCKED: Max {MAX_SAME_DIRECTION_POSITIONS} "
                f"same-direction positions reached."
            )
            print(f"[{_ist_now()}] BLOCKED: Max same-direction positions reached")
            return None

        direction = "BUY" if is_buy else "SELL"
        label = f"PYRAMID {direction}" if is_pyramid else direction

        positions_before = self.count_open_positions()

        # Retry logic: 3 attempts with 500ms delay.
        for attempt in range(1, ORDER_RETRY_COUNT + 1):
            # HIGH-6: refresh the price on every attempt. Resubmitting the same
            # stale price after a requote can only fail again, or fill somewhere
            # the caller never intended.
            tick = mt5.symbol_info_tick(self.symbol)
            if tick is not None:
                price = tick.ask if is_buy else tick.bid

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": lot_size,
                "type": signal,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": ORDER_DEVIATION_POINTS,
                "magic": magic,
                "comment": f"{strategy_name}{'_PYR' if is_pyramid else ''}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            res = mt5.order_send(request)

            if res is None:
                # HIGH-6: None means "no reply", NOT "no fill". The server may
                # have accepted the order. Retrying blindly here is how one
                # signal becomes two positions. Check before retrying.
                log.error(
                    f"[{strategy_name}] order_send returned None "
                    f"(attempt {attempt}/{ORDER_RETRY_COUNT}) -- outcome unknown, verifying"
                )
                _time.sleep(ORDER_RETRY_DELAY_MS / 1000.0)
                if self.count_open_positions() > positions_before:
                    log.warning(
                        f"[{strategy_name}] order DID fill despite the null reply. "
                        f"Not retrying."
                    )
                    print(f"[{_ist_now()}] RECOVERED: {strategy_name} filled after null reply")
                    return None
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
