import json
import sys
from src.strategies.portfolio_v4 import PORTFOLIO_V4
from scripts.validation.part1_suite import _bars, stats, live_config, run_window

def main():
    print("Loading bars...", flush=True)
    bars = _bars()
    
    # Backtest exactly September 3rd and 4th
    start_date = "2026-09-03"
    end_date = "2026-09-05"  # Non-inclusive upper bound for the dates
    
    # D1 Gate OFF to see the blocked trades
    cfg = live_config(enable_d1_bias_gate=False)
    
    # Monkey-patch the stub balance inside run_window by wrapping it
    import scripts.validation.part1_suite as p1
    old_run = p1.run_window
    def _run_window_10k(*args, **kwargs):
        eng = p1.BacktestEngine(bars=args[0], cost=p1.SCENARIOS["realistic"], config=args[1])
        eng.balance = 10000.0
        eng.stub.balance = 10000.0
        strats = kwargs.get('strategies') if kwargs.get('strategies') is not None else [c() for c in PORTFOLIO_V4]
        return eng.run(strats, start_ts=p1._ts(args[2]), end_ts=p1._ts(args[3]))
    
    strategies = [cls() for cls in PORTFOLIO_V4]
    
    print(f"Running backtest for {start_date} to {end_date}...", flush=True)
    res = _run_window_10k(bars, cfg, start_date, end_date, strategies=strategies)
    
    print("\n--- Trading Log for Sept 3 and Sept 4 ---")
    if not res.trades:
        print("No trades taken during this period.")
    else:
        for t in res.trades:
            direc = "BUY " if t.is_buy else "SELL"
            mfe_r = t.mfe_r if t.mfe_r is not None else 0.0
            print(f"[{t.entry_time}] {t.strategy:20} {direc} | Entry: {t.entry_price:.2f} | Exit: {t.exit_price:.2f} | Net: {t.net_pl:.2f} | MFE_R: {mfe_r:.2f} | Reason: {t.exit_reason}")
            
    print("\nCOMBINED RESULT:")
    print(json.dumps(stats(res.trades), indent=2))
    print("\nENGINE DIAGNOSTICS:")
    for k, v in res.diagnostics.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
