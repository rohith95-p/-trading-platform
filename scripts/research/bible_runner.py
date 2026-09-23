"""
Bible Strategy Loop Runner
Runs ONLY the 4 new Bible strategies (LARS, NVMR, PDHLR, LKOCS) across 5 SL/TP combos.
FVG variants are SKIPPED -- already done, winner is FVG_NY_TIGHT (0.5/1.5 baseline).

Bonferroni total_trials = 140 (120 FVG already tested + 20 new) to maintain
family-wise error rate integrity across the full research session.
"""

import numpy as np
import scipy.stats as stats
import sys

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.bible_strategies import LARSStrategy, NVMRStrategy, PDHLRStrategy, LKOCSStrategy
from src.research.metrics import deflated_sharpe_ratio, bonferroni_correction
from scripts.validation.part1_suite import _ts, START_BAL, TRAIN_START, TRAIN_END, OOS_START, OOS_END
import concurrent.futures

# ─── Config ────────────────────────────────────────────────────────────────────
MAX_WORKERS = 15
# Total trials in this research family (120 FVG already done + 20 new bible strats)
TOTAL_TRIALS = 140
IS_PF_GATE = 1.25  # same gate as before
IS_VARIANCE_PROXY = 1.0
# ───────────────────────────────────────────────────────────────────────────────


def make_strategies():
    """Generate parameterized instances for LARS, NVMR, LKOCS.
    PDHLR dropped: showed no IS edge (PF<1.1) in iteration 1.
    """
    bible_sl_tp = [(0.4, 1.2), (0.5, 1.5), (0.5, 2.0), (0.75, 1.5), (0.75, 2.0)]
    classes = [
        (LARSStrategy,  4001, "LARS"),
        (NVMRStrategy,  4003, "NVMR"),
        (LKOCSStrategy, 4010, "LKOCS"),
    ]
    strats = []
    for sl, tp in bible_sl_tp:
        for Cls, magic_base, tag in classes:
            s = Cls()
            s.sl_atr_mult = sl
            s.tp_atr_mult = tp
            s.name = f"{tag}_sl{sl}_tp{tp}"
            s.magic = magic_base + int(sl * 100) + int(tp * 10)
            strats.append(s)
    return strats


def _make_engine_cfg():
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


def run_chunk(args):
    start, end, strat_list = args
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1", "H4"))
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=_make_engine_cfg())
    return eng.run(strat_list, start_ts=_ts(start), end_ts=_ts(end)).trades


def run_parallel(start, end, strats, n_workers=MAX_WORKERS):
    # Chunk so each worker gets ~1-2 strategies (fine-grained for 15 cores)
    chunk_size = max(1, len(strats) // n_workers)
    chunks = [strats[i:i + chunk_size] for i in range(0, len(strats), chunk_size)]
    all_trades = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as exe:
        for trades in exe.map(run_chunk, [(start, end, c) for c in chunks]):
            all_trades.extend(trades)
    class _R:
        def __init__(self, t): self.trades = t
    return _R(all_trades)


def score_is(trades_by_name):
    scores = {}
    for name, trades in trades_by_name.items():
        rets = np.array([t.net_pl for t in trades])
        if len(rets) < 10:
            scores[name] = {"pf": 0, "net": 0, "sr": 0}
            continue
        w, l = rets[rets > 0], rets[rets < 0]
        pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
        sr = float(rets.mean() / rets.std()) if rets.std() > 0 else 0
        scores[name] = {"pf": pf, "net": float(rets.sum()), "sr": sr}
    return scores


def oos_reality_check(trades_by_name, total_trials):
    passed = []
    for name, trades in trades_by_name.items():
        rets = np.array([t.net_pl for t in trades])
        if len(rets) < 10:
            print(f"  [KILL] {name}: only {len(rets)} OOS trades.")
            continue
        w, l = rets[rets > 0], rets[rets < 0]
        pf = float(w.sum() / -l.sum()) if len(l) else 0.0
        std = rets.std()
        if std == 0:
            print(f"  [KILL] {name}: zero variance.")
            continue
        t_stat = (rets.mean() / std) * np.sqrt(len(rets))
        p_val = stats.t.sf(t_stat, df=len(rets) - 1)
        bonf_p = bonferroni_correction(p_val, total_trials)
        dsr = deflated_sharpe_ratio(rets, num_trials=total_trials, sr_variance=IS_VARIANCE_PROXY)
        ok = dsr > 0.95 and bonf_p < 0.05
        label = "PASS ✓" if ok else "FAIL"
        print(f"  [{label}] {name}")
        print(f"         OOS Net=${rets.sum():.2f}  PF={pf:.2f}  n={len(rets)}")
        print(f"         T={t_stat:.2f}  p={p_val:.4f}  Bonf-p={bonf_p:.4f}")
        print(f"         DSR={dsr:.4f}")
        print()
        if ok:
            passed.append(name)
    return passed


def main():
    print("=== BIBLE STRATEGY LOOP RUNNER ===", flush=True)
    print(f"Testing 20 Bible strategies only (FVG variants already done)", flush=True)
    print(f"IS Window : {TRAIN_START} -> {TRAIN_END}", flush=True)
    print(f"OOS Window: {OOS_START} -> {OOS_END}", flush=True)
    print(f"Bonferroni total_trials={TOTAL_TRIALS}  Workers={MAX_WORKERS}\n", flush=True)

    all_strats = make_strategies()
    print(f"Strategies to test: {len(all_strats)}", flush=True)
    for s in all_strats:
        print(f"  {s.name}", flush=True)
    print(flush=True)

    # ── IS phase ────────────────────────────────────────────────────────────
    print("Running IS backtest...", flush=True)
    is_res = run_parallel(TRAIN_START, TRAIN_END, all_strats, MAX_WORKERS)

    by_name = {}
    for t in is_res.trades:
        by_name.setdefault(t.strategy, []).append(t)

    is_scores = score_is(by_name)

    print("\n-- IS Results --------------------------------------------------", flush=True)
    survivors = []
    for name, sc in sorted(is_scores.items(), key=lambda x: -x[1]["pf"]):
        tag = "PASS" if sc["pf"] >= IS_PF_GATE else "fail"
        print(f"  [{tag}] {name:45s}  PF={sc['pf']:.3f}  Net=${sc['net']:.2f}  SR={sc['sr']:.3f}", flush=True)
        if sc["pf"] >= IS_PF_GATE:
            strat_obj = next((s for s in all_strats if s.name == name), None)
            if strat_obj:
                survivors.append(strat_obj)

    print(f"\n{len(survivors)} / {len(all_strats)} passed the IS gate (PF > {IS_PF_GATE}).", flush=True)

    if not survivors:
        print("No survivors -- done.", flush=True)
        return

    # -- OOS phase ------------------------------------------------------------
    print(f"\nRunning OOS backtest on {len(survivors)} survivors...", flush=True)
    oos_res = run_parallel(OOS_START, OOS_END, survivors, min(MAX_WORKERS, len(survivors)))

    oos_by_name = {}
    for t in oos_res.trades:
        oos_by_name.setdefault(t.strategy, []).append(t)

    print("\n=== FINAL OOS REALITY CHECK ===", flush=True)
    passed = oos_reality_check(oos_by_name, TOTAL_TRIALS)

    print(f"\n{'='*60}", flush=True)
    print(f"RESULT: {len(passed)} strategy/ies passed all gates.", flush=True)
    if passed:
        print("WINNERS:", flush=True)
        for n in passed:
            print(f"  => {n}", flush=True)
    print(flush=True)


if __name__ == "__main__":
    main()
