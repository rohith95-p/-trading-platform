"""One-off trailing-stop manager for a single open position.

The main bot is stopped (it opens new trades, which we don't want right now).
This trails the stop on ONE existing position using the same ATR logic the live
system uses (RiskManager.calculate_trailing_stop: activate at 0.7*ATR profit,
trail 0.3*ATR behind price), and exits when the position closes.

Usage:  python -m scripts.trail_position <ticket>
"""
import sys
import time
import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta

from src.core.risk_manager import RiskManager

IST = timezone(timedelta(hours=5, minutes=30))
SYMBOL = "XAUUSDm"
POLL_SECONDS = 15


def _ist():
    return datetime.now(IST).strftime("%H:%M:%S IST")


def main(ticket: int):
    if not mt5.initialize():
        print("MT5 init failed:", mt5.last_error())
        return

    risk = RiskManager(SYMBOL)
    print(f"[{_ist()}] trailing manager started for #{ticket}. Ctrl-C to stop.")
    last_sl = None

    while True:
        try:
            pos = mt5.positions_get(ticket=ticket)
            if not pos:
                print(f"[{_ist()}] #{ticket} is closed. Done.")
                break
            p = pos[0]

            rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 50)
            atr = RiskManager.get_latest_atr(rates) if rates is not None else None
            if atr is None:
                time.sleep(POLL_SECONDS)
                continue

            new_sl = risk.calculate_trailing_stop(p, atr)
            side = "SELL" if p.type == mt5.ORDER_TYPE_SELL else "BUY"
            tag = ""
            if new_sl is not None and new_sl != last_sl:
                req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "symbol": SYMBOL,
                    "sl": new_sl,
                    "tp": p.tp,
                }
                res = mt5.order_send(req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    last_sl = new_sl
                    tag = f"  --> SL moved to {new_sl:.3f}"
                else:
                    tag = f"  --> SL move FAILED ({res.comment if res else 'no reply'})"

            print(f"[{_ist()}] {side} {p.volume} | now {p.price_current:.3f} "
                  f"entry {p.price_open:.3f} SL {p.sl:.3f} | P/L {p.profit:+.2f} "
                  f"| ATR {atr:.2f}{tag}")
        except Exception as e:
            print(f"[{_ist()}] error: {e}")
        time.sleep(POLL_SECONDS)

    mt5.shutdown()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 633836998)
