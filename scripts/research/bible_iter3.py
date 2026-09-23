"""
Bible Strategy Iteration 3:
  1. NVMR full-history stress test (2022-2026): confirm or deny the real edge.
  2. LARS with restored tight killzone (11:30-13:30 IST) + stronger sweep filter.
  3. LKOCS with lowered displacement threshold (0.8x ATR) + simplified unmitigated check.

Bonferroni total_trials stays at 140 (research family integrity).
"""

import numpy as np
import scipy.stats as stats
import sys

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.bible_strategies import LARSStrategy, NVMRStrategy, LKOCSStrategy
from src.research.metrics import deflated_sharpe_ratio, bonferroni_correction
from scripts.validation.part1_suite import _ts, START_BAL, TRAIN_START, TRAIN_END, OOS_START, OOS_END
import concurrent.futures

MAX_WORKERS = 15
TOTAL_TRIALS = 140
IS_PF_GATE = 1.25

# Full history for NVMR extended test
FULL_START = "2022-06-07"
FULL_END   = "2026-08-31"

# -- Apply iteration 3 patches to the strategy classes in-place --

# NVMR: already relaxed in iteration 2, keep same params
NVMR_VARIANTS = []
for sl, tp in [(0.4, 1.2), (0.5, 2.0)]:  # only the 2 IS survivors
    s = NVMRStrategy()
    s.sl_atr_mult = sl
    s.tp_atr_mult = tp
    s.name = f"NVMR_sl{sl}_tp{tp}"
    s.magic = 4003 + int(sl * 100) + int(tp * 10)
    NVMR_VARIANTS.append(s)

# LARS: restore tight killzone
LARSStrategy._london_kz = (11.5, 13.5)
LARSStrategy._min_sweep_wick_atr = 0.3  # wick beyond level must be > 0.3x ATR (new filter)

LARS_VARIANTS = []
for sl, tp in [(0.4, 1.2), (0.5, 1.5), (0.5, 2.0)]:
    s = LARSStrategy()
    s.sl_atr_mult = sl
    s.tp_atr_mult = tp
    s.name = f"LARS_sl{sl}_tp{tp}"
    s.magic = 4001 + int(sl * 100) + int(tp * 10)
    LARS_VARIANTS.append(s)

# LKOCS: lower displacement threshold to 0.8x
LKOCSStrategy._displacement_min = 0.8

LKOCS_VARIANTS = []
for sl, tp in [(0.5, 1.5), (0.5, 2.0), (0.75, 2.0)]:
    s = LKOCSStrategy()
    s.sl_atr_mult = sl
    s.tp_atr_mult = tp
    s.name = f"LKOCS_sl{sl}_tp{tp}"
    s.magic = 4010 + int(sl * 100) + int(tp * 10)
    LKOCS_VARIANTS.append(s)


def _cfg():
    return EngineConfig(
        symbol="XAUUSDm", starting_balance=START_BAL,
        sizing_mode="fixed", fixed_lots=0.01, dedup_per_candle=True,
        max_concurrent=2, max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False,
        enable_consolidation_exit=False,
        history_bars=250, warmup_bars=300,
        daily_loss_limit_mode="off",
        enable_d1_bias_gate=True, direction_gate="d1_ema20",
    )


def _run_chunk(args):
    start, end, strat_list = args
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1", "H4"))
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=_cfg())
    return eng.run(strat_list, start_ts=_ts(start), end_ts=_ts(end)).trades


def run_parallel(start, end, strats, n_workers=MAX_WORKERS):
    chunk_size = max(1, len(strats) // n_workers)
    chunks = [strats[i:i + chunk_size] for i in range(0, len(strats), chunk_size)]
    all_trades = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as exe:
        for trades in exe.map(_run_chunk, [(start, end, c) for c in chunks]):
            all_trades.extend(trades)
    class _R:
        def __init__(self, t): self.trades = t
    return _R(all_trades)


def group_by_name(trades):
    d = {}
    for t in trades:
        d.setdefault(t.strategy, []).append(t)
    return d


def print_stats(name, trades, bonf_n):
    rets = np.array([t.net_pl for t in trades])
    if len(rets) < 10:
        print(f"  [KILL] {name}: only {len(rets)} trades.", flush=True)
        return False
    w, l = rets[rets > 0], rets[rets < 0]
    pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
    wr = 100 * len(w) / len(rets)
    std = rets.std()
    if std == 0:
        print(f"  [KILL] {name}: zero variance.", flush=True)
        return False
    t_stat = (rets.mean() / std) * np.sqrt(len(rets))
    p_val = float(stats.t.sf(t_stat, df=len(rets) - 1))
    bonf_p = bonferroni_correction(p_val, bonf_n)
    dsr = deflated_sharpe_ratio(rets, num_trials=bonf_n, sr_variance=1.0)
    ok = dsr > 0.95 and bonf_p < 0.05
    label = "PASS" if ok else "FAIL"
    print(f"  [{label}] {name}", flush=True)
    print(f"         n={len(rets)}  WR={wr:.1f}%  PF={pf:.3f}  Net=${rets.sum():.2f}", flush=True)
    print(f"         T={t_stat:.3f}  p={p_val:.5f}  Bonf-p={bonf_p:.4f}  DSR={dsr:.4f}", flush=True)
    print(flush=True)
    return ok


def main():
    print("=== BIBLE ITERATION 3 ===", flush=True)
    print(f"Workers={MAX_WORKERS}  Bonferroni(n={TOTAL_TRIALS})\n", flush=True)

    # ---------------------------------------------------------------
    # PART A: NVMR full-history test (2022-2026)
    # ---------------------------------------------------------------
    print("--- PART A: NVMR Full-History Test (2022-08-31) ---", flush=True)
    print("Goal: confirm PF>1.4 persists over 4+ years of unseen data.\n", flush=True)

    nvmr_res = run_parallel(FULL_START, FULL_END, NVMR_VARIANTS, MAX_WORKERS)
    nvmr_by = group_by_name(nvmr_res.trades)

    print("NVMR Full-History Results:", flush=True)
    nvmr_passed = []
    for name in sorted(nvmr_by):
        ok = print_stats(name, nvmr_by[name], TOTAL_TRIALS)
        if ok:
            nvmr_passed.append(name)

    # ---------------------------------------------------------------
    # PART B: LARS IS test with restored tight session
    # ---------------------------------------------------------------
    print("\n--- PART B: LARS IS Test (tight 11:30-13:30 session) ---", flush=True)
    lars_is = run_parallel(TRAIN_START, TRAIN_END, LARS_VARIANTS, MAX_WORKERS)
    lars_is_by = group_by_name(lars_is.trades)

    print("LARS IS Results:", flush=True)
    lars_survivors = []
    for name, trades in sorted(lars_is_by.items()):
        rets = np.array([t.net_pl for t in trades])
        w, l = rets[rets > 0], rets[rets < 0]
        pf = float(w.sum() / -l.sum()) if len(l) else 0.0
        tag = "PASS" if pf >= IS_PF_GATE else "fail"
        print(f"  [{tag}] {name:40s}  PF={pf:.3f}  n={len(rets)}", flush=True)
        if pf >= IS_PF_GATE:
            strat = next((s for s in LARS_VARIANTS if s.name == name), None)
            if strat:
                lars_survivors.append(strat)

    if lars_survivors:
        print(f"\nRunning LARS OOS on {len(lars_survivors)} survivors...", flush=True)
        lars_oos = run_parallel(OOS_START, OOS_END, lars_survivors, MAX_WORKERS)
        lars_oos_by = group_by_name(lars_oos.trades)
        print("\nLARS OOS Reality Check:", flush=True)
        for name in sorted(lars_oos_by):
            print_stats(name, lars_oos_by[name], TOTAL_TRIALS)

    # ---------------------------------------------------------------
    # PART C: LKOCS IS test with lowered threshold
    # ---------------------------------------------------------------
    print("\n--- PART C: LKOCS IS Test (displacement=0.8x ATR) ---", flush=True)
    lkocs_is = run_parallel(TRAIN_START, TRAIN_END, LKOCS_VARIANTS, MAX_WORKERS)
    lkocs_is_by = group_by_name(lkocs_is.trades)

    if not lkocs_is_by:
        print("  [KILL] LKOCS: still 0 trades. Strategy logic produces no signals.", flush=True)
    else:
        print("LKOCS IS Results:", flush=True)
        lkocs_survivors = []
        for name, trades in sorted(lkocs_is_by.items()):
            rets = np.array([t.net_pl for t in trades])
            w, l = rets[rets > 0], rets[rets < 0]
            pf = float(w.sum() / -l.sum()) if len(l) else 0.0
            tag = "PASS" if pf >= IS_PF_GATE else "fail"
            print(f"  [{tag}] {name:40s}  PF={pf:.3f}  n={len(rets)}", flush=True)
            if pf >= IS_PF_GATE:
                strat = next((s for s in LKOCS_VARIANTS if s.name == name), None)
                if strat:
                    lkocs_survivors.append(strat)

        if lkocs_survivors:
            print(f"\nRunning LKOCS OOS...", flush=True)
            lkocs_oos = run_parallel(OOS_START, OOS_END, lkocs_survivors, MAX_WORKERS)
            lkocs_oos_by = group_by_name(lkocs_oos.trades)
            print("\nLKOCS OOS Reality Check:", flush=True)
            for name in sorted(lkocs_oos_by):
                print_stats(name, lkocs_oos_by[name], TOTAL_TRIALS)

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------
    print("\n" + "=" * 60, flush=True)
    print("ITERATION 3 SUMMARY", flush=True)
    print("  NVMR full-history passes:", nvmr_passed or "None", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
