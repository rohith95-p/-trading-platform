"""
main_loop.py -- Ultra Core v3 Final Boss Orchestrator.

PHILOSOPHY:
  - NEVER hardcode dollar limits. Everything scales with ATR.
  - Fixed 0.01 lots, 0.02 total exposure (owner's hard rule, not a risk model).
  - Positions run to their fixed SL/TP -- no trailing, no pyramiding. Both were
    measured net-negative on the validation window (see ENABLE_TRAILING below).
  - portfolio_v4: four session-specialist legs (Asia/London/NY).
  - Direction gated by the D1 EMA20 bias; sessions in IST.

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
from src.core.execution_handler import ExecutionHandler, FIXED_LOT_SIZE
# MorningMomentum (grade H), EMAPullback (grade E), AsianSweep (grade E) were
# archived to src/strategies/archive/ on 2026-09-01 (rohith phase 3): all three
# scored below the random-entry control (HYP-020) and MorningMomentum's 83%
# claim was never reproducible (HYP-006). See docs/STRATEGY_REGISTRY.md.
# EMAStack (rohith phase 2, HYP-027) superseded 2026-09-01 by the 4-leg
# portfolio below -- kept in src/strategies/ema_stack.py for reference but
# no longer imported here.
from src.strategies.portfolio_v4 import PORTFOLIO_V4  # rohith phase 3: 4-leg session-specialist portfolio, PF 1.512, $703 net over ~100d (HYP-036/038)

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

# ---------------------------------------------------------------------------
# Exit-management switches (rohith-2, 2026-09-03)
#
# Both were ON live and NEITHER was in the backtest that validated portfolio_v4.
# scripts/live_config_ab.py replayed the same 100 days with all four legs on one
# shared account and measured the difference:
#
#   2 pos, trail OFF, pyramid OFF  ->  PF 1.478   net +$843.43   maxDD 21.4%
#   2 pos, trail ON,  pyramid ON   ->  PF 0.592   net  -$93.59   maxDD 89.0%
#
# Trailing is the killer. It activates at 0.7*ATR and follows 0.3*ATR behind,
# so it exits around 0.4*ATR net -- but these legs target 2.25-4.0*ATR and live
# entirely on rare large winners. It lifts win rate (29.6% -> 52.9%) while
# collapsing profit factor, converting 2.5*ATR winners into 0.4*ATR ones.
# Live confirmation 2026-09-02 22:22: FVG #2 trailed out at +$4.70 with its
# target still $18 away.
#
# Pyramiding adds a second full-size position 0.5*ATR into a move -- a worse
# entry, more extended, with its own full stop -- so a reversal loses on both.
#
# Positions now run to their fixed SL/TP, exactly as validated.
ENABLE_TRAILING = False
ENABLE_PYRAMIDING = False


def _ist_now() -> str:
    return datetime.now(IST).strftime("%I:%M:%S %p IST")


def _calc_ema(closes: np.ndarray, period: int) -> np.ndarray:
    ema = np.full_like(closes, np.nan, dtype=float)
    if len(closes) >= period:
        multiplier = 2.0 / (period + 1.0)
        ema[period - 1] = np.mean(closes[:period])
        for i in range(period, len(closes)):
            ema[i] = (closes[i] - ema[i - 1]) * multiplier + ema[i - 1]
    return ema


def run():
    """Main entry point."""

    if not mt5.initialize():
        log.error("MT5 initialisation failed. Exiting.")
        return

    # --- Modules ---
    fetcher = DataFetcher(SYMBOL)
    risk = RiskManager(SYMBOL)
    executor = ExecutionHandler(SYMBOL)
    # rohith phase 3 (2026-09-01): portfolio_v4 replaces EMAStack alone.
    # Validated together (PF 1.512, $703 net/~100d) is not the same claim as
    # "EMAStack plus these 4" -- that 5-strategy combination was never tested,
    # so EMAStack is not run alongside them. See HYP-036/038.
    strategies = [cls() for cls in PORTFOLIO_V4]

    # Daily drawdown shutdown flag
    drawdown_shutdown = False
    shutdown_date = None

    # CRIT-1: the loop re-reads the same closed M15 candle every 60s, so an
    # unchanged signal fires up to 15 times and opens duplicate positions one
    # minute apart. Live evidence: 2026-08-25 06:23:47 and 06:24:44, both SHORT,
    # -$27.81 and -$27.77. Record the candle each strategy last acted on and
    # refuse to act on it twice.
    last_fired_candle: dict = {s.name: None for s in strategies}

    log.info("=" * 60)
    log.info("Ultra Core v3 -- Final Boss Engine")
    log.info(f"Symbol: {SYMBOL}")
    log.info(f"Active Strategies: {[s.name for s in strategies]}")
    log.info(f"Lots: FIXED {FIXED_LOT_SIZE} | Max exposure: 0.02 | Max positions: 2")
    log.info(f"Daily loss cap: 6% of balance | Session: IST-adaptive")
    log.info(f"Trailing: {'ON' if ENABLE_TRAILING else 'OFF'} | "
             f"Pyramiding: {'ON' if ENABLE_PYRAMIDING else 'OFF'}")
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
            #
            # HIGH-7: this gate blocks new entries only. It must NOT skip
            # position management -- wide spreads and fast adverse moves are the
            # same events, so freezing the trailing stop here disengaged
            # protection exactly when it was needed.
            # ----------------------------------------------------------
            if not risk.is_spread_ok():
                _manage_open_positions(fetcher, risk, executor)
                _time.sleep(LOOP_INTERVAL)
                continue

            # ----------------------------------------------------------
            # Gate 2: Dynamic daily drawdown cap
            # ----------------------------------------------------------
            todays_pl = fetcher.get_todays_closed_pl()
            # CRIT-4: unrealised loss now counts toward the daily limit. The bot
            # could previously sit on a large floating loss and keep opening
            # trades, because only closed deals were measured.
            floating_pl = sum(p.profit for p in fetcher.get_positions())

            if True:
                if not risk.check_daily_drawdown(
                    todays_pl=todays_pl, floating_pl=floating_pl
                ):
                    drawdown_shutdown = True
                    shutdown_date = now_ist.date()
                    print(
                        f"[{_ist_now()}] SHUTDOWN: Daily drawdown limit hit "
                        f"(realised ${todays_pl:.2f} + floating ${floating_pl:.2f}). "
                        f"No more trades until midnight IST."
                    )
                    # Still manage open positions (trailing stops)
                    _manage_open_positions(fetcher, risk, executor)
                    _time.sleep(LOOP_INTERVAL)
                    continue

            # ----------------------------------------------------------
            # Fetch data & Macro Bias
            # ----------------------------------------------------------
            m15_rates = fetcher.get_m15_rates(250)
            m5_rates = fetcher.get_m5_rates(100)

            if m15_rates is None or len(m15_rates) < 200:
                _time.sleep(LOOP_INTERVAL)
                continue

            d1_bias = None
            d1_rates_macro = fetcher.get_d1_rates(50)
            if d1_rates_macro is not None and len(d1_rates_macro) >= 20:
                d1_closes = d1_rates_macro["close"]
                d1_ema20 = _calc_ema(d1_closes, 20)
                if not np.isnan(d1_ema20[-1]):
                    d1_bias = "BULLISH" if d1_closes[-1] > d1_ema20[-1] else "BEARISH"

            # ----------------------------------------------------------
            # Session info
            # ----------------------------------------------------------
            session_mult = risk.get_session_multiplier(now_ist)
            session_name = risk.get_session_name(now_ist)
            is_london = risk.is_london_open(now_ist)

            # ----------------------------------------------------------
            # Evaluate all strategies
            # ----------------------------------------------------------
            # Time of the last CLOSED candle -- the one strategies read at [-2].
            # It is the deduplication key: it stays constant for 15 minutes.
            signal_candle = int(m15_rates[-2]["time"])

            for strategy in strategies:
                # Check pending confirmation (non-London signals)
                confirmed_signal = strategy.check_pending_confirmation(m15_rates)
                if confirmed_signal is not None:
                    if last_fired_candle.get(strategy.name) == signal_candle:
                        log.info(f"[{strategy.name}] confirmed signal DEDUPED (already acted this candle).")
                    else:
                        log.info(f"Pending signal CONFIRMED ({strategy.name}): {confirmed_signal.direction_str}")
                        # Apply the same D1 bias gate fresh signals get. Previously
                        # confirmed signals bypassed it entirely.
                        if _d1_bias_allows(confirmed_signal, d1_bias, strategy.name):
                            _execute_signal(
                                confirmed_signal, m15_rates, fetcher, risk, executor,
                                session_mult, session_name, strategy,
                            )
                            last_fired_candle[strategy.name] = signal_candle

                # Evaluate strategy
                signal = strategy.evaluate(m15_rates, m5_rates)

                if signal is not None:
                    if last_fired_candle.get(strategy.name) == signal_candle:
                        # Same unchanged candle, already acted on. This is the
                        # single highest-cost defect in the live record.
                        continue
                    # D1 Bias Gate
                    if not _d1_bias_allows(signal, d1_bias, strategy.name):
                        continue

                    # rohith phase 3: the backtest engine that validated portfolio_v4
                    # (and, undiscovered until now, EMAStack before it) has NO concept
                    # of a "queue and confirm next candle" delay -- every signal is
                    # immediately actionable. Strategies opting into that via
                    # `execute_immediately = True` get the same path London already
                    # had, instead of silently falling into the pending-confirmation
                    # queue where check_pending_confirmation() returning None forever
                    # means the signal is dropped and NEVER executes. This is what a
                    # direct trace against real account history caught: 3 of 4
                    # portfolio_v4 legs would never have traded live without this.
                    if is_london or getattr(strategy, "execute_immediately", False):
                        log.info(f"[{strategy.name}] {signal.direction_str} -- executing immediately (session={session_name})")
                        _execute_signal(
                            signal, m15_rates, fetcher, risk, executor,
                            session_mult, session_name, strategy,
                        )
                        last_fired_candle[strategy.name] = signal_candle
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
            if ENABLE_PYRAMIDING:
                _check_pyramiding(fetcher, risk, executor, m15_rates, session_mult,
                                  session_name, now_ist=now_ist)

            # ----------------------------------------------------------
            # Manage open positions (trailing + consolidation)
            # ----------------------------------------------------------
            _manage_open_positions(fetcher, risk, executor)

        except Exception as e:
            log.error(f"Error in main loop: {e}", exc_info=True)
            print(f"[{_ist_now()}] ERROR: {e}")

        _time.sleep(LOOP_INTERVAL)


def _d1_bias_allows(signal, d1_bias, strategy_name: str) -> bool:
    """Daily-trend gate, shared by the fresh and confirmed signal paths.

    Previously only fresh signals were gated; confirmed pending signals executed
    without ever consulting the daily bias.
    """
    if not d1_bias:
        return True
    if signal.is_buy and d1_bias == "BEARISH":
        log.info(f"[{strategy_name}] BUY blocked by D1 BEARISH bias.")
        return False
    if not signal.is_buy and d1_bias == "BULLISH":
        log.info(f"[{strategy_name}] SELL blocked by D1 BULLISH bias.")
        return False
    return True


def _execute_signal(signal, m15_rates, fetcher, risk, executor, session_mult, session_name, strategy=None):
    """Calculate stops and execute a signal.

    `strategy` is optional so every existing caller keeps working unchanged.
    When the firing strategy carries its own `sl_atr_mult`/`tp_atr_mult`
    (portfolio_v4 legs, rohith phase 3), those override the session-default
    multiplier and the shared TP_ATR_MULTIPLIER constant for this order only.
    Absent on a strategy -> falls back to exactly the prior behaviour.
    """
    if not executor.can_open_new_position():
        log.info("Cannot execute: max concurrent positions reached.")
        return

    tick = fetcher.get_tick()
    if tick is None:
        return

    price = tick.ask if signal.is_buy else tick.bid

    sl_mult = getattr(strategy, "sl_atr_mult", None) or session_mult
    tp_mult = getattr(strategy, "tp_atr_mult", None)
    stops = risk.calculate_atr_stops(price, signal.is_buy, m15_rates, sl_mult, tp_mult)
    if stops is None:
        return

    # Owner's rule: fixed 0.01 lots, no dynamic sizing. The 0.15 risk_pct sizer
    # put 0.02-0.03 lots on a ~$105 account (live, 2026-09-02). ExecutionHandler
    # also hard-caps this, but the call site now states the intent.
    lot_size = FIXED_LOT_SIZE

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


def _check_pyramiding(fetcher, risk, executor, m15_rates, session_mult, session_name,
                      now_ist=None):
    """Check if any open position qualifies for pyramiding.

    MED-14: this path had no session check at all, so a strategy gated to
    "London Open only" could add exposure at 04:30 IST. Backtesting found 50
    such entries scattered across hours 00-08 and 21-23. Pyramiding is now
    confined to the hours the strategies themselves trade (11:30-21:30 IST).
    """
    positions = fetcher.get_positions()
    if not positions:
        return

    now_ist = now_ist or datetime.now(IST)
    tv = now_ist.hour + now_ist.minute / 60.0
    if not (11.5 <= tv < 21.5):
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

            lot_size = FIXED_LOT_SIZE  # owner's rule: pyramid adds are also 0.01

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
        # Trailing stop -- OFF by default, see ENABLE_TRAILING above.
        if ENABLE_TRAILING:
            new_sl = risk.calculate_trailing_stop(pos, curr_atr)
            if new_sl is not None:
                executor.modify_sl(pos.ticket, new_sl, pos.tp, pos.symbol)

        # Consolidation exit
        if risk.should_exit_consolidation(m15_rates):
            log.info(f"Consolidation detected -- closing #{pos.ticket}")
            executor.close_position(pos)


if __name__ == "__main__":
    run()
