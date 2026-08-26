"""
main_loop.py -- Ultra Core v3 Final Boss Orchestrator.

PHILOSOPHY:
  - NEVER hardcode dollar limits. Everything scales with ATR.
  - UNLIMITED WINS, PROTECTED LOSSES (dynamic daily drawdown cap).
  - ONLY MorningMomentum strategy runs (strict 4-condition winner).
  - Pyramiding into winners, never averaging down.
  - All sessions allowed with adaptive risk multipliers (IST).

Run:
    python -m src.core.main_loop
"""

import time as _time
import logging
import numpy as np
import MetaTrader5 as _mt5
from typing import Any
from datetime import datetime, timezone, timedelta

mt5: Any = _mt5

from src.core.data_fetcher import DataFetcher
from src.core.risk_manager import RiskManager
from src.core.execution_handler import ExecutionHandler
from src.strategies.morning_momentum import MorningMomentum
from src.strategies.ema_pullback import EMAPullback
from src.strategies.asian_sweep import AsianSweep
from src.strategies.supertrend_ema import SupertrendEMA

# IST offset
IST = timezone(timedelta(hours=5, minutes=30))

# ---------------------------------------------------------------------------
# Logging (IST timestamps)
# ---------------------------------------------------------------------------

class ISTFormatter(logging.Formatter):
    """Log formatter that outputs timestamps in IST."""
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created, tz=IST)
        if datefmt:
            return ct.strftime(datefmt)
        return ct.strftime("%Y-%m-%d %I:%M:%S %p IST")

handler = logging.StreamHandler()
handler.setFormatter(ISTFormatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler])
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SYMBOL = "XAUUSDm"
LOOP_INTERVAL = 60  # seconds between scans


def _ist_now() -> str:
    return datetime.now(IST).strftime("%I:%M:%S %p IST")


def run():
    """Main entry point."""

    if not mt5.initialize():
        log.error("MT5 initialisation failed. Exiting.")
        return

    # --- Modules ---
    fetcher = DataFetcher(SYMBOL)
    risk = RiskManager(SYMBOL)
    executor = ExecutionHandler(SYMBOL)
    strategies = [MorningMomentum(), EMAPullback(), AsianSweep(), SupertrendEMA()]

    # Daily drawdown shutdown flag
    drawdown_shutdown = False
    shutdown_date = None

    log.info("=" * 60)
    log.info("Ultra Core v3 -- Final Boss Engine")
    log.info(f"Symbol: {SYMBOL}")
    log.info(f"Active Strategies: {[s.name for s in strategies]}")
    log.info(f"Risk: ATR-dynamic | Session: IST-adaptive")
    log.info(f"Drawdown Cap: 1.5 * D1_ATR | Pyramid: 0.5 * ATR")
    log.info("=" * 60)
    print(f"\n[{_ist_now()}] >>> Ultra Core v3 is LIVE.\n")

    while True:
        try:
            now_ist = datetime.now(IST)
            now_utc = datetime.now(timezone.utc)

            # ----------------------------------------------------------
            # Reset drawdown shutdown at midnight IST
            # ----------------------------------------------------------
            if drawdown_shutdown and shutdown_date != now_ist.date():
                drawdown_shutdown = False
                shutdown_date = None
                log.info("Midnight IST -- drawdown reset. Trading resumes.")
                print(f"[{_ist_now()}] RESET: New day, drawdown cleared.")

            if drawdown_shutdown:
                _time.sleep(LOOP_INTERVAL)
                continue

            # ----------------------------------------------------------
            # Gate 1: Spread filter
            # ----------------------------------------------------------
            if not risk.is_spread_ok():
                _time.sleep(LOOP_INTERVAL)
                continue

            # ----------------------------------------------------------
            # Gate 2: Dynamic daily drawdown cap
            # ----------------------------------------------------------
            d1_rates = fetcher.get_d1_rates(20)
            todays_pl = fetcher.get_todays_closed_pl()

            if d1_rates is not None:
                if not risk.check_daily_drawdown(d1_rates, todays_pl):
                    drawdown_shutdown = True
                    shutdown_date = now_ist.date()
                    print(
                        f"[{_ist_now()}] SHUTDOWN: Daily drawdown limit hit "
                        f"(P/L: ${todays_pl:.2f}). No more trades until midnight IST."
                    )
                    # Still manage open positions (trailing stops)
                    _manage_open_positions(fetcher, risk, executor)
                    _time.sleep(LOOP_INTERVAL)
                    continue

            # ----------------------------------------------------------
            # Fetch data
            # ----------------------------------------------------------
            m15_rates = fetcher.get_m15_rates(100)
            m5_rates = fetcher.get_m5_rates(25)

            if m15_rates is None:
                _time.sleep(LOOP_INTERVAL)
                continue

            # ----------------------------------------------------------
            # Session info
            # ----------------------------------------------------------
            session_mult = risk.get_session_multiplier(now_ist)
            session_name = risk.get_session_name(now_ist)
            is_london = risk.is_london_open(now_ist)

            # ----------------------------------------------------------
            # Evaluate all strategies
            # ----------------------------------------------------------
            for strategy in strategies:
                # Check pending confirmation (non-London signals)
                confirmed_signal = strategy.check_pending_confirmation(m15_rates)
                if confirmed_signal is not None:
                    log.info(f"Pending signal CONFIRMED ({strategy.name}): {confirmed_signal.direction_str}")
                    _execute_signal(
                        confirmed_signal, m15_rates, fetcher, risk, executor,
                        session_mult, session_name,
                    )

                # Evaluate strategy
                signal = strategy.evaluate(m15_rates, m5_rates)

                if signal is not None:
                    if is_london:
                        # London Open: execute IMMEDIATELY
                        log.info(f"LONDON OPEN signal ({strategy.name}): {signal.direction_str} -- executing immediately")
                        _execute_signal(
                            signal, m15_rates, fetcher, risk, executor,
                            session_mult, session_name,
                        )
                    else:
                        # Other sessions: queue for confirmation on next candle
                        candle_time = int(m15_rates[-2]["time"])
                        strategy.set_pending(signal, candle_time)
                        log.info(
                            f"Signal queued for confirmation ({strategy.name} in {session_name}): "
                            f"{signal.direction_str} -- waiting for next M15 close"
                        )
                        print(
                            f"[{_ist_now()}] PENDING: {signal.direction_str} signal "
                            f"queued (session: {session_name}). Confirming next candle."
                        )

            # ----------------------------------------------------------
            # Pyramiding: add to winning positions
            # ----------------------------------------------------------
            _check_pyramiding(fetcher, risk, executor, m15_rates, session_mult, session_name)

            # ----------------------------------------------------------
            # Manage open positions (trailing + consolidation)
            # ----------------------------------------------------------
            _manage_open_positions(fetcher, risk, executor)

        except Exception as e:
            log.error(f"Error in main loop: {e}", exc_info=True)
            print(f"[{_ist_now()}] ERROR: {e}")

        _time.sleep(LOOP_INTERVAL)


def _execute_signal(signal, m15_rates, fetcher, risk, executor, session_mult, session_name):
    """Calculate stops and execute a signal."""
    if not executor.can_open_new_position():
        log.info("Cannot execute: max concurrent positions reached.")
        return

    tick = fetcher.get_tick()
    if tick is None:
        return

    price = tick.ask if signal.is_buy else tick.bid

    stops = risk.calculate_atr_stops(price, signal.is_buy, m15_rates, session_mult)
    if stops is None:
        return

    lot_size = risk.calculate_dynamic_lot_size(price, stops.sl, risk_pct=0.15)

    executor.send_order(
        signal=signal.direction,
        price=price,
        sl=stops.sl,
        tp=stops.tp,
        strategy_name=signal.strategy_name,
        magic=signal.magic,
        lot_size=lot_size,
        atr=stops.atr,
        session=session_name,
    )


def _check_pyramiding(fetcher, risk, executor, m15_rates, session_mult, session_name):
    """Check if any open position qualifies for pyramiding."""
    positions = fetcher.get_positions()
    if not positions:
        return

    if not executor.can_open_new_position():
        return

    curr_atr = risk.get_latest_atr(m15_rates)
    if curr_atr is None:
        return

    for pos in positions:
        is_buy = pos.type == mt5.ORDER_TYPE_BUY
        if risk.check_pyramid_condition(pos.price_open, pos.price_current, curr_atr, is_buy):
            # Check if we already pyramided this position (look for matching magic+direction)
            existing = [p for p in positions if p.type == pos.type and p.magic == pos.magic]
            if len(existing) >= 2:
                continue  # Already pyramided

            tick = fetcher.get_tick()
            if tick is None:
                continue

            price = tick.ask if is_buy else tick.bid
            stops = risk.calculate_atr_stops(price, is_buy, m15_rates, session_mult)
            if stops is None:
                continue

            lot_size = risk.calculate_dynamic_lot_size(price, stops.sl, risk_pct=0.15)

            profit_dist = abs(pos.price_current - pos.price_open)
            log.info(
                f"PYRAMID: {pos.comment} moved {profit_dist:.2f} in profit "
                f"(threshold: {0.5 * curr_atr:.2f}). Adding position."
            )

            executor.send_order(
                signal=mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
                price=price,
                sl=stops.sl,
                tp=stops.tp,
                strategy_name=pos.comment.replace("_PYR", ""),
                magic=pos.magic,
                lot_size=lot_size,
                atr=stops.atr,
                session=session_name,
                is_pyramid=True,
            )
            break  # Only pyramid once per cycle


def _manage_open_positions(fetcher, risk, executor):
    """Run trailing stop logic and consolidation exit checks."""
    positions = fetcher.get_positions()
    if not positions:
        return

    m15_rates = fetcher.get_m15_rates(20)
    if m15_rates is None:
        return

    curr_atr = risk.get_latest_atr(m15_rates)
    if curr_atr is None:
        return

    for pos in positions:
        # Trailing stop
        new_sl = risk.calculate_trailing_stop(pos, curr_atr)
        if new_sl is not None:
            executor.modify_sl(pos.ticket, new_sl, pos.tp, pos.symbol)

        # Consolidation exit
        if risk.should_exit_consolidation(m15_rates):
            log.info(f"Consolidation detected -- closing #{pos.ticket}")
            executor.close_position(pos)


if __name__ == "__main__":
    run()
