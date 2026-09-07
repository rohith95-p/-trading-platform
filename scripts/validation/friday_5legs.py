"""Friday 2026-09-04 (IST), the current 5-leg PORTFOLIO_V4, two ways:

  A) as validated/recorded -- the backtest engine doesn't enforce
     market_hours.py's 11:30-21:30 window (that guard only exists in the live
     execution path), so this is exactly what's in the ledger.
  B) as it would ACTUALLY execute live right now -- FVG_ASIA_SWEEP's session
     (02:30-11:30) sits entirely outside the enforced 11:30-21:30 window and
     would be silently blocked every time, so this variant drops that leg.
"""
from datetime import datetime, timezone, timedelta

from src.strategies.portfolio_v4 import PORTFOLIO_V4, FVGAsiaSweep
from src.backtesting.engine import BacktestEngine
from src.backtesting.costs import SCENARIOS
from scripts.validation.part1_suite import live_config, _bars, stats

IST = timezone(timedelta(hours=5, minutes=30))

def _ts(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())

bars = _bars()
start = _ts("2026-09-03 18:30")  # 2026-09-04 00:00 IST
end = _ts("2026-09-04 18:30")    # 2026-09-05 00:00 IST
cfg = live_config()

def report(label, strategies):
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run(strategies, start_ts=start, end_ts=end)
    print(f"\n=== {label} ===")
    if not res.trades:
        print("No trades.")
        return
    trades = sorted(res.trades, key=lambda t: t.entry_time)
    for t in trades:
        et = datetime.fromtimestamp(t.entry_time, tz=timezone.utc).astimezone(IST)
        xt = datetime.fromtimestamp(t.exit_time, tz=timezone.utc).astimezone(IST)
        direction = "BUY" if t.is_buy else "SELL"
        outcome = "WIN" if t.net_pl > 0 else ("LOSS" if t.net_pl < 0 else "BE")
        print(f"[{et:%m-%d %H:%M} -> {xt:%m-%d %H:%M} IST] {t.strategy:24s} {direction:4s} "
              f"R={t.r_multiple:+.2f} net=${t.net_pl:+.2f} -> {outcome}")
    s = stats(res.trades)
    print(f"Total: {s['n']} trades | WR={s['win_rate']:.1f}% PF={s['profit_factor']:.3f} "
          f"net=${s['net']:+.2f}")

report("A) AS VALIDATED (all 5 legs, no window restriction)",
       [cls() for cls in PORTFOLIO_V4])
report("B) AS IT WOULD ACTUALLY EXECUTE LIVE (Asia blocked by 11:30-21:30 window)",
       [cls() for cls in PORTFOLIO_V4 if cls is not FVGAsiaSweep])
