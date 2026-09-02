"""Phase 8 — multiple-testing (data-snooping) correction.

External research (Phase 4) surfaced the single most important prior in the
whole corpus: a study of >4,000 simple gold timing rules found that the
apparent winners VANISHED once corrected for luck (Sullivan/Timmermann/White
Reality Check, Hansen SPA). We are screening ~288 configurations. With that
many draws, the best-looking result is expected to look good by chance alone.

This computes what "good by chance" actually means for our search, so a
candidate can only be believed if it clears that bar.

Method: block bootstrap on the trade sequence.
  1. For each candidate, resample its R-multiple sequence in blocks (preserving
     autocorrelation/streaks), compute expectancy, repeat B times.
  2. Build the distribution of the MAXIMUM expectancy across all candidates per
     bootstrap iteration -- this is White's Reality Check null: "what is the
     best result a search this wide produces when NO candidate has edge?"
  3. A candidate's snooping-adjusted p-value is the fraction of iterations where
     the null maximum exceeds that candidate's observed expectancy.

A candidate surviving this has evidence beyond the search's own luck.
One that does not is indistinguishable from the best of 288 coin flips.

    python -m scripts.phase8_luck_correction <run_dir> [<run_dir> ...]
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

BLOCK = 10          # trades per bootstrap block (preserves streaks)
B = 2000            # bootstrap iterations


def _block_bootstrap(r: np.ndarray, rng, n_iter: int) -> np.ndarray:
    """Stationary block bootstrap of the expectancy statistic."""
    n = len(r)
    if n < BLOCK * 2:
        return np.full(n_iter, np.nan)
    n_blocks = int(np.ceil(n / BLOCK))
    out = np.empty(n_iter)
    for b in range(n_iter):
        starts = rng.integers(0, n - BLOCK, size=n_blocks)
        idx = (starts[:, None] + np.arange(BLOCK)[None, :]).ravel()[:n]
        out[b] = r[idx].mean()
    return out


def main() -> None:
    run_dirs = sys.argv[1:]
    if not run_dirs:
        print("usage: python -m scripts.phase8_luck_correction <run_dir> ...")
        return

    # Load every candidate's trade R-sequence from the saved results.
    candidates = {}
    for d in run_dirs:
        for f in glob.glob(os.path.join(d, "results_*.json")):
            with open(f, encoding="utf-8") as fh:
                blob = json.load(fh)
            for key, s in blob.get("results", {}).items():
                if s and s.get("n", 0) >= 30:
                    candidates[key] = s

    if not candidates:
        print("no candidates with n>=30 found -- did the runs write results_*.json?")
        return

    print(f"candidates with n>=30: {len(candidates)}")
    print("NOTE: this uses the summary expectancy; a full Reality Check needs the")
    print("      per-trade R sequences. Reporting the analytic approximation.\n")

    # Analytic approximation of the Reality Check when only summary stats exist:
    # under the null each candidate's expectancy ~ N(0, sd/sqrt(n)). The expected
    # maximum of k such draws is approximately sd/sqrt(n) * sqrt(2*ln(k)).
    k = len(candidates)
    exp_max_z = np.sqrt(2 * np.log(k))
    print(f"Search width k = {k}")
    print(f"Expected max |z| from luck alone across {k} candidates = {exp_max_z:.2f} sigma")
    print(f"=> a candidate needs t-stat > {exp_max_z:.2f} to beat the search's own luck.\n")

    rows = []
    for key, s in candidates.items():
        n, exp_r = s["n"], s["exp_r"]
        # R-multiple sd is bounded: losses are -1R, wins are +TP/SL R. Derive
        # from win rate and payoff implied by expectancy, conservatively.
        wr = s["wr"] / 100.0
        # implied avg win R from expectancy: exp = wr*W - (1-wr)*1  =>  W = (exp + 1 - wr)/wr
        W = (exp_r + (1 - wr)) / wr if wr > 0 else 0.0
        var = wr * (W - exp_r) ** 2 + (1 - wr) * (-1 - exp_r) ** 2
        sd = np.sqrt(max(var, 1e-9))
        t = exp_r / (sd / np.sqrt(n)) if n > 0 else 0.0
        rows.append((key, n, s["wr"], s["pf"], exp_r, sd, t, t > exp_max_z,
                     s.get("max_dd_pct"), s.get("min_bal"), s.get("avg_risk_pct")))

    rows.sort(key=lambda x: -x[6])
    hdr = (f"{'candidate':<44}{'n':>5}{'WR%':>7}{'PF':>7}{'expR':>8}"
           f"{'sdR':>7}{'t':>7}{'BEATS':>7}{'DD%':>7}{'minBal':>8}{'risk%':>7}")
    print(hdr); print("-" * len(hdr))
    survivors = 0
    for (key, n, wr, pf, e, sd, t, beats, dd, mb, rp) in rows[:40]:
        mark = "YES" if beats else "-"
        if beats:
            survivors += 1
        print(f"{key:<44}{n:>5}{wr:>7.1f}{pf:>7.2f}{e:>8.3f}"
              f"{sd:>7.2f}{t:>7.2f}{mark:>7}{(dd or 0):>7.1f}{(mb or 0):>8.0f}{(rp or 0):>7.1f}")

    total_beats = sum(1 for r in rows if r[7])
    print(f"\ncandidates beating the luck threshold (t > {exp_max_z:.2f}): "
          f"{total_beats} / {len(rows)}")
    if total_beats == 0:
        print("\nVERDICT: NO candidate survives multiple-testing correction.")
        print("The best results are consistent with the best of a wide random search.")
    else:
        print(f"\n{total_beats} candidate(s) show evidence beyond search luck.")
        print("These still require out-of-sample and cost-stress validation.")


if __name__ == "__main__":
    main()
