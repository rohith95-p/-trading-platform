"""
main_loop.py -- Ultra Core v3 Final Boss Orchestrator.

PHILOSOPHY:
  - NEVER hardcode dollar limits. Everything scales with ATR.
  - Fixed 0.02 lots, 0.04 total exposure (owner's hard rule, not a risk model).
  - Positions run to their fixed SL/TP -- no trailing, no pyramiding. Both were
    measured net-negative on the validation window (see ENABLE_TRAILING below).
  - portfolio_v4: two session-specialist legs (LARS/NVMR).
  - Direction gated by the D1 EMA20 bias; sessions in IST.

Resilience (src/core/resilience.py -- does not affect trading):
  - single-instance lockfile
  - kill switch: create a file named STOP in the project root -> flatten + halt
  - heartbeat file (logs/heartbeat), loop-state persistence (logs/loop_state.json)
  - startup safety check (right account, tradeable), MT5 auto-reconnect

Run:
    python -m src.core.main_loop
"""

import os
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
from src.core import resilience
from src.core import trade_log
from src.core import risk_rules
from src.core import market_hours
from src.core import news_filter  # III.5 -- blocks entries around tier-1 macro events
# MorningMomentum (grade H), EMAPullback (grade E), AsianSweep (grade E) were
# archived to src/strategies/archive/ on 2026-09-01 (rohith phase 3): all three
# scored below the random-entry control (HYP-020) and MorningMomentum's 83%
# claim was never reproducible (HYP-006). See docs/research/STRATEGY_REGISTRY.md.
# EMAStack (rohith phase 2, HYP-027) superseded 2026-09-01 by the 4-leg
# portfolio below -- kept in src/strategies/ema_stack.py for reference but
# no longer imported here.
from src.strategies.portfolio_v4 import PORTFOLIO_V4  # 2 legs: NVMR_TARGET_10 + LARS_LONDON (see portfolio_v4.py)

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
ENABLE_TRAILING = True
ENABLE_PYRAMIDING = False
CLOSE_ONLY_TRAIL = True

# D1 EMA20 direction gate -- ON. Reversed 2026-09-06 (HYP-064) after August 2026
# simulation proved that trading FVG strategies without trend filtering in a
# high-volatility environment causes extreme drawdowns. The gate flawlessly
# filtered out toxic counter-trend setups in August, turning a -79% maxDD failure
# into a +$44 profit (PF 1.40).
ENABLE_D1_GATE = True


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


def _close_all_positions(fetcher, executor, reason: str) -> None:
    """Flatten every open position on the symbol (kill switch)."""
    for pos in fetcher.get_positions():
        if executor.close_position(pos):
            log.warning(f"KILL SWITCH: closed #{pos.ticket} ({reason})")
        else:
            log.error(f"KILL SWITCH: FAILED to close #{pos.ticket} -- close it manually.")


def run():
    """Main entry point."""

    # Single-instance guard -- refuse to start if another main_loop is alive.
    if not resilience.acquire_lock():
        return

    try:
        _run_guarded()
    finally:
        resilience.release_lock()


def _run_guarded():
    if not mt5.initialize():
        log.error("MT5 initialisation failed. Exiting.")
        return

    # Startup safety: right account, tradeable connection, symbol present.
    if not resilience.startup_safety_check(mt5, SYMBOL):
        log.error("Startup safety check FAILED. Not trading. Fix the above and restart.")
        return

    # Config-integrity gate: refuse to trade a configuration nobody has run
    # through a backtest and recorded. This is the fix for a real recurring
    # failure -- exposure caps raised without re-validating, the D1 gate left
    # in a different state than any tested backtest, a strategy fix that
    # silently changed what an unrelated script tested. See
    # src/core/validation_ledger.py and RESEARCH_LEDGER.md HYP-047/048.
    from src.core import validation_ledger
    _cfg_report = validation_ledger.check_live_config()
    if _cfg_report["validated"]:
        _res = _cfg_report["match"]["result"]
        log.info(f"CONFIG VALIDATED: fingerprint {_cfg_report['fingerprint']} matches "
                 f"{_cfg_report['match']['source']} ({_cfg_report['match']['recorded_at']}): {_res}")
    else:
        log.error(f"CONFIG NOT VALIDATED: live fingerprint {_cfg_report['fingerprint']} "
                  f"matches no recorded backtest.")
        for line in _cfg_report["diff"]:
            log.error(f"  differs from most recent recorded config: {line}")
        if os.environ.get("ULTRA_ALLOW_UNVALIDATED") != "1":
            log.error("Refusing to trade an unvalidated configuration. Re-run a backtest "
                       "and record it (validation_ledger.record), or set "
                       "ULTRA_ALLOW_UNVALIDATED=1 to override (not recommended).")
            return
        log.warning("ULTRA_ALLOW_UNVALIDATED=1 set -- proceeding on an unvalidated config.")

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

    # Restore loop state so a restart mid-candle can't re-fire a signal.
    _saved = resilience.load_state()
    if _saved.get("last_fired_candle"):
        for name, candle in _saved["last_fired_candle"].items():
            if name in last_fired_candle:
                last_fired_candle[name] = candle
    if _saved.get("drawdown_shutdown") and _saved.get("shutdown_date") == str(datetime.now(IST).date()):
        drawdown_shutdown = True
        shutdown_date = datetime.now(IST).date()
        log.info("STATE: daily drawdown shutdown restored for today.")

    mt5_fail_count = 0

    # Positions seen on the previous loop -- None until the first pass, so
    # positions already open at startup are adopted, not counted as closes.
    known_position_tickets = None

    log.info("=" * 60)
    log.info("Ultra Core v3 -- Final Boss Engine")
    log.info(f"Symbol: {SYMBOL}")
    log.info(f"Active Strategies: {[s.name for s in strategies]}")
    from src.core.execution_handler import MAX_CONCURRENT_POSITIONS as _mcp, MAX_TOTAL_VOLUME as _mtv
    log.info(f"Lots: FIXED {FIXED_LOT_SIZE} | Max exposure: {_mtv} | Max positions: {_mcp}")
    log.info(f"Daily loss cap: 6% of balance | Session: IST-adaptive")
    log.info(f"Trailing: {'ON' if ENABLE_TRAILING else 'OFF'} | "
             f"Pyramiding: {'ON' if ENABLE_PYRAMIDING else 'OFF'} | "
             f"D1 gate: {'ON' if ENABLE_D1_GATE else 'OFF'}")
    log.info(f"Resilience: lock={resilience.LOCK_FILE} | kill switch=create '{resilience.STOP_FILE}'")
    log.info(f"News filter: {'ENABLED' if news_filter.ENABLE_NEWS_FILTER else 'DISABLED'} "
             f"(±{news_filter.NEWS_BLACKOUT_MINUTES}min blackout around tier-1 events)")
    news_filter.invalidate_cache()  # ensure calendar is freshly loaded at startup
    _upcoming = news_filter.upcoming_events(hours_ahead=8.0)
    if _upcoming:
        log.info("Upcoming tier-1 events (next 8h):")
        for _ev in _upcoming:
            log.info(f"  {_ev['minutes_away']:>4}min: {_ev['name']} @ {_ev['utc_time']} UTC ({_ev['date']})")
    log.info("=" * 60)
    print(f"\n[{_ist_now()}] >>> Ultra Core v3 is LIVE.\n")

    current_date = datetime.now(IST).date()

    while True:
        try:
            now_ist = datetime.now(IST)
            
            # ----------------------------------------------------------
            # Midnight IST tasks
            # ----------------------------------------------------------
            if current_date != now_ist.date():
                log.info("Midnight IST transition detected. Running daily tasks.")
                try:
                    from src.core.daily_report import send_daily_report
                    send_daily_report(force=False)
                except Exception as e:
                    log.error(f"Failed to send daily report: {e}")
                current_date = now_ist.date()
            resilience.heartbeat()
            resilience.save_state(last_fired_candle, drawdown_shutdown, shutdown_date)

            # Feed closed-trade results to the risk_rules streak breakers. Runs
            # every loop -- a stop can fill while the bot is in drawdown_shutdown.
            known_position_tickets = _record_closed_trades(fetcher, known_position_tickets)

            # ----------------------------------------------------------
            # Kill switch: STOP file in the project root -> flatten + halt
            # ----------------------------------------------------------
            if resilience.kill_switch_active():
                log.warning("KILL SWITCH ACTIVE (STOP file present). Flattening and halting.")
                print(f"[{_ist_now()}] KILL SWITCH -- closing all positions, halting.")
                _close_all_positions(fetcher, executor, "STOP file")
                break

            # ----------------------------------------------------------
            # Friday Kill Switch: Flatten for the weekend
            # ----------------------------------------------------------
            if market_hours.should_flatten_for_weekend(now_ist):
                open_pos = fetcher.get_positions()
                if open_pos:
                    log.warning("FRIDAY KILL SWITCH: Market closing soon. Flattening all positions.")
                    print(f"[{_ist_now()}] FRIDAY KILL SWITCH -- flattening for the weekend.")
                    _close_all_positions(fetcher, executor, "Weekend Gap Avoidance")
                # Sleep and skip the rest of the loop until market reopens
                _time.sleep(LOOP_INTERVAL)
                continue

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
            # Gate 1b: News blackout (III.5) -- block entries around
            # scheduled tier-1 macro events (NFP, CPI, FOMC, PCE, etc.)
            # that spike XAUUSD spreads to 50-100 pts and cause extreme
            # slippage on the FVG legs' tight ~$5 stops.
            # ----------------------------------------------------------
            _news_blocked, _news_reason = news_filter.is_near_news_event(now_ist)
            if _news_blocked:
                log.info(f"NEWS FILTER: {_news_reason}")
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

            got_data = m15_rates is not None and len(m15_rates) >= 200
            mt5_fail_count = resilience.note_fetch_result(mt5, got_data, mt5_fail_count)
            if not got_data:
                _time.sleep(LOOP_INTERVAL)
                continue

            d1_bias = None
            if ENABLE_D1_GATE:
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
            actionable_signals = []

            for strategy in strategies:
                # Check pending confirmation (non-London signals)
                confirmed_signal = strategy.check_pending_confirmation(m15_rates)
                if confirmed_signal is not None:
                    if last_fired_candle.get(strategy.name) == signal_candle:
                        log.info(f"[{strategy.name}] confirmed signal DEDUPED (already acted this candle).")
                    else:
                        log.info(f"Pending signal CONFIRMED ({strategy.name}): {confirmed_signal.direction_str}")
                        if _d1_bias_allows(confirmed_signal, d1_bias, strategy.name):
                            actionable_signals.append((strategy, confirmed_signal))

                # Evaluate strategy
                signal = strategy.evaluate(m15_rates, m5_rates)

                if signal is not None:
                    if last_fired_candle.get(strategy.name) == signal_candle:
                        trade_log.signal(strategy.name, signal.direction_str, "deduped",
                                         "already acted on this candle", candle=signal_candle,
                                         session=session_name)
                        continue
                    if not _d1_bias_allows(signal, d1_bias, strategy.name):
                        trade_log.signal(strategy.name, signal.direction_str, "blocked",
                                         f"D1 bias gate ({d1_bias})", candle=signal_candle,
                                         session=session_name)
                        continue
                    if _leg_in_cooldown(strategy.name):
                        log.info(f"[{strategy.name}] {signal.direction_str} skipped -- reversal cooldown active.")
                        trade_log.signal(strategy.name, signal.direction_str, "blocked",
                                         "reversal cooldown active", candle=signal_candle,
                                         session=session_name)
                        continue

                    if is_london or getattr(strategy, "execute_immediately", False):
                        log.info(f"[{strategy.name}] {signal.direction_str} -- actionable immediately (session={session_name})")
                        actionable_signals.append((strategy, signal))
                    else:
                        candle_time = int(m15_rates[-2]["time"])
                        strategy.set_pending(signal, candle_time)
                        log.info(f"Signal queued for confirmation ({strategy.name} in {session_name}): {signal.direction_str}")
                        print(f"[{_ist_now()}] PENDING: {signal.direction_str} signal queued (session: {session_name}). Confirming next candle.")

            # ----------------------------------------------------------
            # HIGHLANDER RULE: Execute only the highest conviction signal
            # ----------------------------------------------------------
            if actionable_signals:
                # Rank by conviction based on strategy name
                rank_order = {
                    "FVG_NY_SWEEP_OR_VOID": 5,
                    "FVG_NY_SWEEP": 4,
                    "FVG_NY_VOID": 3,
                    "FVG_NY_TIGHT": 2,
                    "FVG_ASIA_SWEEP": 1,
                }
                
                # Sort signals by rank (descending)
                actionable_signals.sort(key=lambda x: rank_order.get(x[0].name.upper(), 0), reverse=True)
                
                best_strategy, best_signal = actionable_signals[0]
                
                if len(actionable_signals) > 1:
                    log.info(f"HIGHLANDER: {len(actionable_signals)} signals fired. Selected {best_strategy.name} as best conviction.")
                
                # Execute the best one
                _execute_signal(
                    best_signal, m15_rates, fetcher, risk, executor,
                    session_mult, session_name, best_strategy,
                )
                last_fired_candle[best_strategy.name] = signal_candle
                
                # Block the others and mark them as fired to prevent immediate re-fires
                for strat, sig in actionable_signals[1:]:
                    trade_log.signal(strat.name, sig.direction_str, "blocked",
                                     f"Highlander rule: overridden by {best_strategy.name}", candle=signal_candle,
                                     session=session_name)
                    log.info(f"[{strat.name}] {sig.direction_str} BLOCKED by Highlander rule (lost to {best_strategy.name}).")
                    last_fired_candle[strat.name] = signal_candle

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


_COOLDOWN_FILE = "logs/cooldown.json"


def _leg_in_cooldown(name: str) -> bool:
    """True if scripts/protect_profit.py closed this leg on a reversal recently
    and it should not re-enter yet."""
    try:
        import json as _json
        with open(_COOLDOWN_FILE) as f:
            until = _json.load(f).get(name, 0)
        return _time.time() < until
    except (OSError, ValueError):
        return False


def _record_closed_trades(fetcher, known_tickets):
    """Feed every newly-closed position's realised P/L to the risk_rules streak
    breakers (II.4: consecutive-loss pause / stop-day, early-phase losing-trade
    cap).

    `record_trade_result()` existed but nothing ever called it, so
    consecutive_losses / day_losing_trades sat at 0 forever and those breakers
    could not fire even in shadow mode. This closes that gap. It is still
    shadow-only while risk_rules.ENFORCE is False -- it makes the breaker STATE
    real (persisted to logs/risk_state.json) so it can be measured now and works
    the moment ENFORCE is flipped on.

    known_tickets is None on the first loop after startup -- pre-existing
    positions are adopted, not counted as closes. A ticket whose deal history
    can't be read yet is retried next loop rather than lost.
    """
    current = {p.ticket for p in fetcher.get_positions()}
    if known_tickets is None:
        return current

    closed = known_tickets - current
    if not closed:
        return current

    acct = mt5.account_info()
    state = risk_rules.load_state()
    if acct is not None:
        # same day/week/month roll evaluate() does, so a close before the first
        # signal of a new day sees a reset day_losing_trades.
        state = risk_rules._roll_anchors(state, float(acct.balance), datetime.now(IST))

    still_pending = set()
    for ticket in closed:
        try:
            deals = mt5.history_deals_get(position=ticket)
            if not deals:
                still_pending.add(ticket)
                continue
            pl = sum((d.profit + d.swap + d.commission) for d in deals
                     if d.entry == mt5.DEAL_ENTRY_OUT)
            state = risk_rules.record_trade_result(pl, state=state)
            trade_log.position_closed(strategy="", ticket=ticket, profit=round(pl, 2),
                                      consecutive_losses=state.consecutive_losses,
                                      day_losing_trades=state.day_losing_trades,
                                      streak_pause_active=state.pause_until_ts > _time.time(),
                                      enforced=risk_rules.ENFORCE)
        except Exception as e:
            log.warning(f"streak breaker: could not record close of #{ticket}: {e}")
            still_pending.add(ticket)

    risk_rules.save_state(state)
    
    if closed:
        _check_vi3_tripwire(fetcher)

    return current | still_pending


def _check_vi3_tripwire(fetcher):
    """VI.3 tripwire: monitor rolling 30-trade live profit factor."""
    try:
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=60)
        deals = mt5.history_deals_get(start, now)
        if not deals:
            return
            
        magics = {3012, 3013, 3022, 3011, 3014}
        pls = []
        for d in deals:
            if d.symbol == fetcher.symbol and d.magic in magics and d.entry == mt5.DEAL_ENTRY_OUT:
                pl = float(d.profit) + float(d.swap) + float(d.commission)
                pls.append((int(d.time), pl))
                
        if len(pls) < 30:
            return
            
        pls.sort(key=lambda x: x[0])
        recent_30 = [x[1] for x in pls[-30:]]
        
        arr = np.array(recent_30, dtype=float)
        w, l = arr[arr > 0], arr[arr < 0]
        pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
        
        if pf < 0.8:
            msg = f"VI.3 TRIPWIRE: Rolling 30-trade PF is {pf:.2f} (<0.8). triggering KILL SWITCH."
            log.error(msg)
            from src.core import alerts
            alerts.send(msg, severity=alerts.CRITICAL)
            # Create STOP file to trigger kill switch on next loop
            with open(resilience.STOP_FILE, "w") as f:
                f.write(msg)
        elif pf < 1.0:
            msg = f"VI.3 TRIPWIRE WARN: Rolling 30-trade PF is {pf:.2f} (<1.0)."
            log.warning(msg)
            from src.core import alerts
            alerts.send(msg, severity=alerts.WARN)
    except Exception as e:
        log.warning(f"Could not check VI.3 tripwire: {e}")


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
    # IV.6 + owner's 11:30-21:30 trading window: weekend gap, rollover spread
    # spike, and no-night-trades are all checked here, before anything else.
    _mh_ok, _mh_why = market_hours.allow_new_entry()
    if not _mh_ok:
        trade_log.signal(signal.strategy_name, signal.direction_str, "blocked",
                         _mh_why, session=session_name)
        log.info(f"[{signal.strategy_name}] entry blocked -- {_mh_why}")
        return

    if strategy and getattr(strategy, "max_spread_pts", None):
        max_spread = strategy.max_spread_pts
        if not risk.is_spread_ok(max_spread):
            trade_log.signal(signal.strategy_name, signal.direction_str, "blocked",
                             f"spread > {max_spread}", session=session_name)
            log.info(f"[{signal.strategy_name}] entry blocked -- spread > {max_spread}")
            return

    if not executor.can_open_new_position():
        log.info("Cannot execute: max concurrent positions reached.")
        trade_log.signal(signal.strategy_name, signal.direction_str, "blocked",
                         "max concurrent positions reached", session=session_name)
        return

    tick = fetcher.get_tick()
    if tick is None:
        trade_log.signal(signal.strategy_name, signal.direction_str, "blocked",
                         "no tick available", session=session_name)
        return

    price = tick.ask if signal.is_buy else tick.bid

    sl_mult = getattr(strategy, "sl_atr_mult", None) or session_mult
    tp_mult = getattr(strategy, "tp_atr_mult", None)
    stops = risk.calculate_atr_stops(price, signal.is_buy, m15_rates, sl_mult, tp_mult)
    if stops is None:
        trade_log.signal(signal.strategy_name, signal.direction_str, "blocked",
                         "ATR stops unavailable", session=session_name)
        return

    # Part II shadow mode: record what the (not yet enforced) risk rulebook
    # would have decided, so its real-world impact can be measured before
    # ENFORCE is ever switched on. See src/core/risk_rules.py.
    try:
        _acct = mt5.account_info()
        if _acct is not None:
            _decision, _rstate = risk_rules.evaluate(
                balance=_acct.balance, equity=_acct.equity,
                margin_used=getattr(_acct, "margin", 0.0) or 0.0)
            risk_rules.save_state(_rstate)
            if not _decision.allow_new_entries:
                trade_log.gate("risk_rules_shadow", allowed=False, reason=_decision.reason,
                               strategy=signal.strategy_name, enforced=risk_rules.ENFORCE)
                if risk_rules.ENFORCE:
                    log.warning(f"[{signal.strategy_name}] BLOCKED by risk rules: {_decision.reason}")
                    return
    except Exception as _e:  # shadow logging must never break execution
        log.debug(f"risk_rules shadow evaluation skipped: {_e}")

    # Owner's rule: fixed 0.02 lots, no dynamic sizing. The 0.15 risk_pct sizer
    # put 0.02-0.03 lots on a ~$105 account (live, 2026-09-02). ExecutionHandler
    # also hard-caps this, but the call site now states the intent.
    lot_size = FIXED_LOT_SIZE

    result = executor.send_order(
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

    trade_log.order(
        strategy=signal.strategy_name, direction=signal.direction_str, lots=lot_size,
        price=price, sl=stops.sl, tp=stops.tp,
        retcode=getattr(result, "retcode", None),
        ticket=getattr(result, "order", None),
        atr=stops.atr, sl_atr_mult=sl_mult, tp_atr_mult=tp_mult,
        session=session_name, magic=signal.magic,
    )
    return result


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

            lot_size = FIXED_LOT_SIZE  # owner's rule: pyramid adds are also 0.02

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
        
    try:
        import json
        with open("logs/virtual_sl.json", "r") as f:
            virtual_sls = json.load(f)
    except Exception:
        virtual_sls = {}
        
    state_changed = False

    for pos in positions:
        # Trailing stop -- OFF by default, see ENABLE_TRAILING above.
        if ENABLE_TRAILING:
            ticket_str = str(pos.ticket)
            actual_broker_sl = pos.sl
            
            if CLOSE_ONLY_TRAIL and ticket_str in virtual_sls:
                pos.sl = virtual_sls[ticket_str]
                
            new_sl = risk.calculate_trailing_stop(pos, curr_atr)
            pos.sl = actual_broker_sl  # Restore
            
            if new_sl is not None:
                if CLOSE_ONLY_TRAIL:
                    virtual_sls[ticket_str] = new_sl
                    state_changed = True
                    log.info(f"Virtual Trailing SL for #{pos.ticket} updated to {new_sl}")
                else:
                    executor.modify_sl(pos.ticket, new_sl, pos.tp, pos.symbol)
                    
            if CLOSE_ONLY_TRAIL and ticket_str in virtual_sls:
                v_sl = virtual_sls[ticket_str]
                is_buy = pos.type == 0 # mt5.ORDER_TYPE_BUY
                last_closed_bar = m15_rates[-2]
                close_price = float(last_closed_bar["close"])
                
                # Check if the closed candle violated our virtual SL
                if is_buy and close_price <= v_sl:
                    log.warning(f"CLOSE-ONLY TRAIL HIT: #{pos.ticket} long closed at {close_price} (SL: {v_sl})")
                    executor.close_position(pos)
                    continue # Skip consolidation check since it's closed
                elif not is_buy and close_price >= v_sl:
                    log.warning(f"CLOSE-ONLY TRAIL HIT: #{pos.ticket} short closed at {close_price} (SL: {v_sl})")
                    executor.close_position(pos)
                    continue

        # Consolidation exit
        if risk.should_exit_consolidation(m15_rates):
            log.info(f"Consolidation detected -- closing #{pos.ticket}")
            executor.close_position(pos)
            
    if state_changed:
        try:
            import json
            with open("logs/virtual_sl.json", "w") as f:
                json.dump(virtual_sls, f)
        except Exception as e:
            log.error(f"Failed to save virtual SL state: {e}")


if __name__ == "__main__":
    run()
