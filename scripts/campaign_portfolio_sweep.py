"""
Portfolio V5 Sweep — SHARED DATA VERSION
Loads bars ONCE in the main process. Workers receive only lightweight task configs.
Uses all 28 cores safely because data is shared via fork (copy-on-write on Windows
requires a different trick: we use a global variable set via initializer).
"""
import sys
import multiprocessing
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import SCENARIOS
from src.backtesting.metrics import summarize

from src.strategies.bible_strategies import NVMRStrategy, PDHLRStrategy
from src.strategies.liquidity_sweep_reversal import LiquiditySweepReversal
from src.strategies.ny_liquidity_expansion import NYLiquidityExpansion
from src.strategies.grid_strategies import TrendPullbackStrat, BBMeanReversionStrat
from src.strategies.eurusd_asian_range import EURUSDAsianRange
from src.strategies.forex_session_momentum import ForexSessionMomentum
from src.strategies.portfolio_v4 import FVGNYTight

SL = 0.1
TP = 1.0
START_TS = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp())
END_TS   = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())

ALL_STRAT_CLASSES = [
    NVMRStrategy, LiquiditySweepReversal, PDHLRStrategy,
    NYLiquidityExpansion, BBMeanReversionStrat, EURUSDAsianRange,
    ForexSessionMomentum, TrendPullbackStrat, FVGNYTight,
]

# Global shared bars (set by pool initializer)
_BARS = None

def init_worker(bars):
    global _BARS
    _BARS = bars

def worker(args):
    strat_names, max_concurrent = args
    global _BARS
    try:
        name_map = {c.__name__: c for c in ALL_STRAT_CLASSES}
        strat_classes = [name_map[n] for n in strat_names]

        cfg = EngineConfig(
            symbol="XAUUSDm", starting_balance=100.0,
            sizing_mode="fixed", fixed_lots=0.01,
            max_concurrent=max_concurrent,
            max_same_direction=max_concurrent,
            enable_trailing=False, enable_pyramiding=False,
            daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
            enable_d1_bias_gate=True,
        )
        strats = []
        for cls in strat_classes:
            s = cls()
            s.sl_atr_mult = SL
            s.tp_atr_mult = TP
            strats.append(s)

        eng = BacktestEngine(bars=_BARS, cost=SCENARIOS["realistic_ecn"], config=cfg)
        res = eng.run(strats, start_ts=START_TS, end_ts=END_TS)
        stats = summarize(res.trades, res.equity, cfg.starting_balance).to_dict()

        label = "ALL-9" if len(strat_classes) == 9 else strat_classes[0].__name__
        result = {
            "label": label,
            "max_concurrent": max_concurrent,
            "n_strats": len(strat_classes),
            "trades": stats.get("trades", 0),
            "pf": stats.get("profit_factor", 0.0),
            "net": stats.get("net_pl", 0.0),
            "dd": stats.get("max_drawdown_pct", 0.0),
            "wr": stats.get("win_rate", 0.0),
        }
        print(f"[DONE] {label:<28} mc={max_concurrent}: PF={result['pf']:.2f} Net=${result['net']:.2f} DD={result['dd']:.2f}% Trades={result['trades']}", flush=True)
        return result
    except Exception as e:
        print(f"[ERR] {strat_names} mc={max_concurrent}: {e}", flush=True)
        return None


def main():
    print("Loading bars once...", flush=True)
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
    print(f"Bars loaded. Spawning 28 workers...\n", flush=True)

    tasks = []
    for mc in range(2, 7):
        tasks.append(([c.__name__ for c in ALL_STRAT_CLASSES], mc))
    for cls in ALL_STRAT_CLASSES:
        tasks.append(([cls.__name__], 3))

    print(f"Total tasks: {len(tasks)}\n", flush=True)

    # Pass bars to each worker via initializer (one copy per worker, but
    # Windows doesn't support fork so this still copies — but 28 * 2yr ≈ 56GB
    # won't fit. So we use 14 workers which matches the 14 tasks perfectly:
    # each task gets its own worker, all run simultaneously, 14 * 2GB = 28GB
    # which is just under the 16GB limit... still too much.
    # REAL SOLUTION: reduce workers to 6 so RAM = 6 * 2GB = 12GB < 16GB.
    # 14 tasks / 6 workers = ~3 rounds, much faster than sequential.
    N_WORKERS = 6
    with multiprocessing.Pool(N_WORKERS, initializer=init_worker, initargs=(bars,)) as pool:
        results = [r for r in pool.imap_unordered(worker, tasks) if r is not None]

    # --- Final Report ---
    portfolio_results = sorted([r for r in results if r["n_strats"] == 9], key=lambda x: x["max_concurrent"])
    solo_results      = sorted([r for r in results if r["n_strats"] == 1],  key=lambda x: x["net"], reverse=True)

    print("\n\n========== FINAL REPORT (2024-2026, 2yr) ==========")
    print("\n--- FULL 9-STRATEGY PORTFOLIO: CONCURRENCY SWEEP ---")
    print(f"{'MaxConc':<8} | {'Trades':<7} | {'PF':<5} | {'Net PL':<10} | {'MaxDD':<8} | {'WR%'}")
    print("-" * 62)
    for r in portfolio_results:
        print(f"mc={r['max_concurrent']:<5}  | {r['trades']:<7} | {r['pf']:<5.2f} | ${r['net']:<9.2f} | {r['dd']:<7.2f}% | {r['wr']:.2f}%")

    print("\n--- INDIVIDUAL STRATEGY CONTRIBUTIONS ---")
    print(f"{'Strategy':<28} | {'Trades':<7} | {'PF':<5} | {'Net PL':<10} | {'MaxDD':<8} | {'WR%':<6} | Verdict")
    print("-" * 92)
    for r in solo_results:
        verdict = "KEEP" if r["net"] > 0 and r["pf"] > 1.2 else "BLEED -> REMOVE"
        print(f"{r['label']:<28} | {r['trades']:<7} | {r['pf']:<5.2f} | ${r['net']:<9.2f} | {r['dd']:<7.2f}% | {r['wr']:<5.2f}% | {verdict}")

    bleeders = [r["label"] for r in solo_results if r["net"] <= 0 or r["pf"] <= 1.2]
    keepers  = [r["label"] for r in solo_results if r["net"] > 0 and r["pf"] > 1.2]
    print(f"\nKEEPERS  ({len(keepers)}): {keepers}")
    print(f"BLEEDERS ({len(bleeders)}): {bleeders}")


if __name__ == "__main__":
    main()
