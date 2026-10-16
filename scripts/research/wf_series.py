"""Dump per-trade series (entry_time, exit_time, net_pl@0.01lot, risk$@0.01lot) for strategy x geometry
over 2022-08 -> 2026-10 on the corrected engine (live window + D1 gate, realistic_ecn). Args: worker n_workers outdir"""
import sys, os, json, importlib, dataclasses, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import SCENARIOS
S = "src.strategies."
LIVE = [("TREND_PULLBACK_V5", S+"portfolio_v5_core", "TrendPullbackV5"), ("BB_MEAN_REVERSION_V5", S+"portfolio_v5_core", "BBMeanReversionV5"),
        ("NVMR_V5", S+"portfolio_v5_core", "NVMRPortfolioV5"), ("FVG_NY_TIGHT_V5", S+"portfolio_v5_core", "FVGNYTightV5")]
JOBS = [(l, m, c, g) for (l, m, c) in LIVE for g in ((0.5, 1.5), (1.0, 2.0), (2.0, 4.0))]
JOBS += [("SUPERTREND_EMA", S+"archive.supertrend_ema", "SupertrendEMA", None), ("SQUEEZE_ASIA", S+"portfolio_v4", "SqueezeBreakAsia", None),
         ("FVG_NY_SWEEP", S+"portfolio_v4", "FVGNYSweep", None), ("LIQ_SWEEP_REVERSAL", S+"liquidity_sweep_reversal", "LiquiditySweepReversal", None),
         ("BB_MEAN_REVERSION_V5", S+"portfolio_v5_core", "BBMeanReversionV5", (1.5, 3.0))]
if __name__ == "__main__":
    wi, nw, outdir = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
    ts = lambda d: int(d.replace(tzinfo=dt.timezone.utc).timestamp())
    for k, (label, mod, cls, g) in enumerate(JOBS):
        if k % nw != wi: continue
        s = getattr(importlib.import_module(mod), cls)()
        if g: s.sl_atr_mult, s.tp_atr_mult = g
        tag = f"{label}_{g[0]}_{g[1]}" if g else f"{label}_native"
        cfg = EngineConfig(sizing_mode="fixed", fixed_lots=0.01, starting_balance=100000.0, daily_loss_limit_mode="off")
        res = BacktestEngine(bars=bars, cost=SCENARIOS["realistic_ecn"], config=cfg).run([s], ts(dt.datetime(2022, 8, 1)), ts(dt.datetime(2026, 10, 14)))
        json.dump([[t.entry_time, t.exit_time, t.net_pl, abs(t.entry_price - t.initial_sl)] for t in res.trades], open(os.path.join(outdir, tag + ".json"), "w"))
        print("done", tag, len(res.trades), flush=True)
