"""Trade statistics.

The previous engine reported win rate, net profit and max drawdown -- all three
computed from a fixed +/-$5 payoff, which made them functions of the win count
alone. These metrics are computed from realised exit prices, and include the
excursion and duration measures needed to tell a strategy with an edge apart
from one whose exits happen to be lucky.

Added 2026-09-28 (rohith research note):
  - calmar_ratio: annualised return / max drawdown.  No normality assumption.
  - omega_ratio:  integral of P(R>r) / P(R<r) above a threshold (default 0).
    Captures the full return distribution without assuming Gaussian tails.
  - sortino_ratio: mean return / downside deviation.  Penalises only losing
    volatility, unlike Sharpe which penalises upside volatility equally.
  - k_eff_correction(): standalone function.  Computes the Vertox/eigenspectrum
    effective number of tested strategies (K_eff) from the correlation matrix
    of variant return series.  Use this instead of the raw strategy count when
    applying a Bonferroni / Deflated-Sharpe multiple-testing penalty -- DePrado
    assumes independence between trials, which massively overstates the penalty
    when parameter variants are correlated.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class TradeStats:
    trades: int = 0
    wins: int = 0
    losses: int = 0
    scratches: int = 0
    win_rate: float = 0.0

    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_pl: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0

    avg_win: float = 0.0
    avg_loss: float = 0.0
    median_win: float = 0.0
    median_loss: float = 0.0
    payoff_ratio: float = 0.0
    breakeven_win_rate: float = 0.0
    win_rate_margin: float = 0.0

    total_r: float = 0.0
    expectancy_r: float = 0.0
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0

    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration_days: float = 0.0
    recovery_factor: float = 0.0

    max_consec_wins: int = 0
    max_consec_losses: int = 0

    avg_mae_r: float = 0.0
    avg_mfe_r: float = 0.0
    mfe_capture: float = 0.0

    avg_minutes_open: float = 0.0
    median_minutes_open: float = 0.0
    avg_minutes_to_mfe: float = 0.0

    duplicate_trades: int = 0
    duplicate_pl: float = 0.0
    pyramid_trades: int = 0
    pyramid_pl: float = 0.0
    ambiguous_trades: int = 0

    exit_reasons: Dict[str, int] = field(default_factory=dict)
    by_session: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_month: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_strategy: Dict[str, Dict[str, float]] = field(default_factory=dict)

    start_balance: float = 0.0
    end_balance: float = 0.0
    return_pct: float = 0.0

    # --- Distribution-agnostic risk-adjusted return metrics ---
    # None of these use standard deviation of the *full* return series, so
    # they remain valid for the fat-tailed, skewed XAUUSD trade P&L distribution.
    calmar_ratio: float = 0.0          # annualised_return / max_drawdown_pct
    omega_ratio: float = 0.0           # integral above threshold / integral below
    sortino_ratio: float = 0.0         # mean_trade_pl / downside_std (losses only)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b else default


def _bucket(trades: Sequence[Any], key) -> Dict[str, Dict[str, float]]:
    """Group trades and report the few numbers that matter per group."""
    out: Dict[str, Dict[str, float]] = {}
    for t in trades:
        k = key(t)
        b = out.setdefault(k, {"trades": 0, "wins": 0, "net_pl": 0.0,
                               "gross_profit": 0.0, "gross_loss": 0.0})
        b["trades"] += 1
        b["net_pl"] += t.net_pl
        if t.net_pl > 0:
            b["wins"] += 1
            b["gross_profit"] += t.net_pl
        else:
            b["gross_loss"] += abs(t.net_pl)
    for b in out.values():
        b["win_rate"] = round(_safe_div(b["wins"], b["trades"]) * 100, 1)
        b["profit_factor"] = round(_safe_div(b["gross_profit"], b["gross_loss"],
                                             float("inf") if b["gross_profit"] else 0.0), 3)
        b["net_pl"] = round(b["net_pl"], 2)
        b["gross_profit"] = round(b["gross_profit"], 2)
        b["gross_loss"] = round(b["gross_loss"], 2)
    return out


def summarize(trades: Sequence[Any], equity: Sequence[Any],
              start_balance: float) -> TradeStats:
    s = TradeStats(start_balance=round(start_balance, 2))
    s.trades = len(trades)
    if not trades:
        s.end_balance = round(start_balance, 2)
        return s

    pls = np.array([t.net_pl for t in trades], dtype=float)
    rs = np.array([t.r_multiple for t in trades], dtype=float)

    wins = pls[pls > 0]
    losses = pls[pls < 0]
    s.wins, s.losses = int(len(wins)), int(len(losses))
    s.scratches = int((pls == 0).sum())
    s.win_rate = round(_safe_div(s.wins, s.trades) * 100, 2)

    s.gross_profit = round(float(wins.sum()), 2)
    s.gross_loss = round(float(abs(losses.sum())), 2)
    s.net_pl = round(float(pls.sum()), 2)
    s.profit_factor = round(_safe_div(s.gross_profit, s.gross_loss,
                                      float("inf") if s.gross_profit else 0.0), 3)
    s.expectancy = round(float(pls.mean()), 4)

    s.avg_win = round(float(wins.mean()), 2) if len(wins) else 0.0
    s.avg_loss = round(float(abs(losses.mean())), 2) if len(losses) else 0.0
    s.median_win = round(float(np.median(wins)), 2) if len(wins) else 0.0
    s.median_loss = round(float(abs(np.median(losses))), 2) if len(losses) else 0.0
    s.payoff_ratio = round(_safe_div(s.avg_win, s.avg_loss), 3)
    if s.avg_win + s.avg_loss > 0:
        s.breakeven_win_rate = round(s.avg_loss / (s.avg_win + s.avg_loss) * 100, 2)
        s.win_rate_margin = round(s.win_rate - s.breakeven_win_rate, 2)

    s.total_r = round(float(rs.sum()), 3)
    s.expectancy_r = round(float(rs.mean()), 4)
    win_r, loss_r = rs[rs > 0], rs[rs < 0]
    s.avg_win_r = round(float(win_r.mean()), 3) if len(win_r) else 0.0
    s.avg_loss_r = round(float(abs(loss_r.mean())), 3) if len(loss_r) else 0.0

    # --- drawdown from the realised equity path ---
    eq = [start_balance] + [t.balance_after for t in trades]
    times = [trades[0].entry_time] + [t.exit_time for t in trades]
    peak, peak_t = eq[0], times[0]
    max_dd, max_dd_pct, max_dur = 0.0, 0.0, 0.0
    for v, ts in zip(eq, times):
        if v > peak:
            peak, peak_t = v, ts
        dd = peak - v
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = _safe_div(dd, peak) * 100
        max_dur = max(max_dur, (ts - peak_t) / 86400.0)
    s.max_drawdown = round(max_dd, 2)
    s.max_drawdown_pct = round(max_dd_pct, 2)
    s.max_drawdown_duration_days = round(max_dur, 1)
    s.recovery_factor = round(_safe_div(s.net_pl, max_dd), 3)

    # --- streaks ---
    cw = cl = 0
    for p in pls:
        if p > 0:
            cw += 1
            cl = 0
        elif p < 0:
            cl += 1
            cw = 0
        s.max_consec_wins = max(s.max_consec_wins, cw)
        s.max_consec_losses = max(s.max_consec_losses, cl)

    # --- excursions ---
    mae = np.array([t.mae_r for t in trades], dtype=float)
    mfe = np.array([t.mfe_r for t in trades], dtype=float)
    s.avg_mae_r = round(float(mae.mean()), 3)
    s.avg_mfe_r = round(float(mfe.mean()), 3)
    # How much of the favourable excursion the exit actually banked. A low number
    # against a positive MFE is the signature of an exit clipping its winners.
    s.mfe_capture = round(_safe_div(float(rs.mean()), float(mfe.mean())), 3)

    mins = np.array([t.minutes_open for t in trades], dtype=float)
    s.avg_minutes_open = round(float(mins.mean()), 1)
    s.median_minutes_open = round(float(np.median(mins)), 1)
    s.avg_minutes_to_mfe = round(float(np.mean([t.minutes_to_mfe for t in trades])), 1)

    dupes = [t for t in trades if t.duplicate_of is not None]
    s.duplicate_trades = len(dupes)
    s.duplicate_pl = round(sum(t.net_pl for t in dupes), 2)
    pyr = [t for t in trades if t.is_pyramid]
    s.pyramid_trades = len(pyr)
    s.pyramid_pl = round(sum(t.net_pl for t in pyr), 2)
    s.ambiguous_trades = sum(1 for t in trades if t.intrabar_ambiguous)

    for t in trades:
        s.exit_reasons[t.exit_reason] = s.exit_reasons.get(t.exit_reason, 0) + 1

    s.by_session = _bucket(trades, lambda t: t.session)
    s.by_strategy = _bucket(trades, lambda t: t.strategy)
    s.by_month = _bucket(
        trades,
        lambda t: datetime.fromtimestamp(t.exit_time, tz=timezone.utc)
        .astimezone(IST).strftime("%Y-%m"),
    )

    s.end_balance = round(trades[-1].balance_after, 2)
    s.return_pct = round(_safe_div(s.net_pl, start_balance) * 100, 2)

    # --- Calmar Ratio ---
    # Annualised return (assume ~252 trading days, scale by avg trade duration).
    # Using trade-count-based annualisation: trades_per_year = n / years.
    if s.avg_minutes_open > 0 and s.trades > 0:
        minutes_in_year = 252 * 6.5 * 60  # ~252 trading days, 6.5h/day
        trades_per_year = minutes_in_year / s.avg_minutes_open
        annualised_return_pct = s.expectancy * trades_per_year / start_balance * 100
    else:
        annualised_return_pct = s.return_pct
    s.calmar_ratio = round(_safe_div(annualised_return_pct, s.max_drawdown_pct), 3)

    # --- Omega Ratio (threshold = 0, i.e. every dollar counts) ---
    # Omega = sum(gains above threshold) / sum(losses below threshold).
    # This is literally just Profit Factor when threshold=0, but expressed as
    # a ratio of partial expectations -- distribution-free by construction.
    # A threshold > 0 can be set to represent a minimum acceptable return.
    threshold = 0.0
    gains_above = float(np.sum(np.maximum(pls - threshold, 0)))
    losses_below = float(np.sum(np.maximum(threshold - pls, 0)))
    s.omega_ratio = round(_safe_div(gains_above, losses_below,
                                    float('inf') if gains_above else 0.0), 3)

    # --- Sortino Ratio ---
    # Uses only the *downside* semi-deviation, so large winners don't inflate
    # the denominator the way they would in Sharpe.  Threshold = 0.
    downside = pls[pls < threshold] - threshold          # negative deviations
    downside_std = float(np.std(downside)) if len(downside) > 1 else 0.0
    s.sortino_ratio = round(_safe_div(float(pls.mean()), downside_std), 3)

    return s


# ---------------------------------------------------------------------------
# Statistical confidence
# ---------------------------------------------------------------------------


def bootstrap_expectancy(trades: Sequence[Any], n: int = 5000,
                         seed: int = 7) -> Dict[str, float]:
    """Bootstrap CI for per-trade expectancy.

    A backtest reports one path. This asks how much of that path is sampling
    noise: if the 5th percentile of resampled expectancy is negative, the sample
    does not establish a positive edge regardless of the headline profit factor.
    """
    if len(trades) < 5:
        return {}
    rng = np.random.default_rng(seed)
    pls = np.array([t.net_pl for t in trades], dtype=float)
    draws = rng.choice(pls, size=(n, len(pls)), replace=True).mean(axis=1)
    return {
        "mean": round(float(draws.mean()), 4),
        "p05": round(float(np.percentile(draws, 5)), 4),
        "p50": round(float(np.percentile(draws, 50)), 4),
        "p95": round(float(np.percentile(draws, 95)), 4),
        "prob_negative": round(float((draws < 0).mean()), 4),
    }


def monte_carlo_paths(trades: Sequence[Any], start_balance: float,
                      n: int = 5000, seed: int = 7) -> Dict[str, float]:
    """Reshuffle trade order to get a drawdown distribution.

    The realised sequence is one ordering out of many. Reshuffling holds the
    trade population fixed and asks what drawdown the same edge could have
    produced in a less kind order.
    """
    if len(trades) < 5:
        return {}
    rng = np.random.default_rng(seed)
    pls = np.array([t.net_pl for t in trades], dtype=float)
    dds, finals, ruins = [], [], 0
    for _ in range(n):
        path = rng.permutation(pls)
        eq = start_balance + np.cumsum(path)
        eq = np.concatenate([[start_balance], eq])
        peak = np.maximum.accumulate(eq)
        dd = (peak - eq)
        dds.append(float(dd.max()))
        finals.append(float(eq[-1]))
        if eq.min() <= start_balance * 0.5:
            ruins += 1
    dds_a, fin_a = np.array(dds), np.array(finals)
    return {
        "median_max_dd": round(float(np.percentile(dds_a, 50)), 2),
        "p95_max_dd": round(float(np.percentile(dds_a, 95)), 2),
        "worst_max_dd": round(float(dds_a.max()), 2),
        "median_final": round(float(np.percentile(fin_a, 50)), 2),
        "p05_final": round(float(np.percentile(fin_a, 5)), 2),
        "prob_50pct_drawdown": round(ruins / n, 4),
        "prob_final_below_start": round(float((fin_a < start_balance).mean()), 4),
    }


def drop_best_worst(trades: Sequence[Any]) -> Dict[str, Any]:
    """How dependent is the result on a handful of trades?

    If removing the three best trades flips the strategy negative, the edge lives
    in outliers rather than in the rule.
    """
    if len(trades) < 10:
        return {}
    pls = sorted(t.net_pl for t in trades)
    total = sum(pls)
    out: Dict[str, Any] = {"net_pl": round(total, 2)}
    for k in (1, 3, 5):
        out[f"drop_best_{k}"] = round(total - sum(pls[-k:]), 2)
        out[f"drop_worst_{k}"] = round(total - sum(pls[:k]), 2)
    top3 = sum(pls[-3:])
    out["top3_share_of_gross_profit"] = round(
        _safe_div(top3, sum(p for p in pls if p > 0)) * 100, 1
    )
    return out


# ---------------------------------------------------------------------------
# Correlation-aware multiple-testing correction  (Vertox K_eff, 2026-05-14)
# ---------------------------------------------------------------------------


def k_eff_correction(
    return_series: Sequence[Sequence[float]],
    n_tested_raw: int,
) -> Dict[str, Any]:
    """Compute the effective number of independent strategies (K_eff).

    DePrado's Deflated Sharpe Ratio corrects for multiple testing by applying
    a Bonferroni penalty scaled by the *raw* number of trials (n_tested_raw).
    This dramatically overstates the penalty when parameter variants are
    correlated -- testing SL=0.4 vs SL=0.5 is not two independent experiments.

    Vertox (2026-05-14) defines K_eff via the eigenspectrum of the return
    correlation matrix Sigma:

        p_i   = lambda_i / sum(lambda)          # normalised eigenvalues
        H     = -sum(p_i * log(p_i))            # Shannon entropy of spectrum
        K_eff = exp(H)                           # effective count in [1, K]

    Intuition:
      - All strategies identical  -> one dominant eigenvalue -> H=0 -> K_eff=1
      - All strategies independent -> flat eigenspectrum   -> H=log(K) -> K_eff=K
      - Real portfolios land somewhere in between.

    The Bonferroni p-value threshold to use is alpha / K_eff rather than
    alpha / K, making the multiple-testing correction correlation-aware.

    Args:
        return_series: list/array of per-trade P&L series, one per strategy
                       variant.  Series need not be the same length -- shorter
                       ones are aligned to the overlapping window.
        n_tested_raw:  raw number of strategy configurations tested (K).

    Returns dict with keys:
        k_raw          -- the raw count you passed in
        k_eff          -- correlation-aware effective count
        reduction_pct  -- how much smaller K_eff is vs K (pct)
        eigenvalues    -- sorted eigenvalues of the correlation matrix
        bonferroni_raw -- alpha=0.05 / K
        bonferroni_keff-- alpha=0.05 / K_eff  (the honest threshold)
    """
    if not return_series or n_tested_raw < 2:
        return {
            "k_raw": n_tested_raw,
            "k_eff": float(n_tested_raw),
            "reduction_pct": 0.0,
            "eigenvalues": [],
            "bonferroni_raw": round(0.05 / max(n_tested_raw, 1), 6),
            "bonferroni_keff": round(0.05 / max(n_tested_raw, 1), 6),
            "note": "Need >= 2 series to compute correlation structure.",
        }

    # Align series lengths to the minimum common length (latest window).
    min_len = min(len(s) for s in return_series)
    if min_len < 5:
        return {
            "k_raw": n_tested_raw,
            "k_eff": float(n_tested_raw),
            "reduction_pct": 0.0,
            "eigenvalues": [],
            "bonferroni_raw": round(0.05 / n_tested_raw, 6),
            "bonferroni_keff": round(0.05 / n_tested_raw, 6),
            "note": "Too few overlapping trades to estimate correlation.",
        }

    mat = np.array([list(s)[-min_len:] for s in return_series], dtype=float)

    # Correlation matrix (use numpy corrcoef; handles constant series gracefully).
    corr = np.corrcoef(mat)                    # shape (K, K)
    # Clip to [-1, 1] to handle floating-point edge cases.
    corr = np.clip(corr, -1.0, 1.0)

    # Eigenvalue decomposition.  corrcoef is symmetric so eigvalsh is stable.
    eigenvalues = np.linalg.eigvalsh(corr)     # ascending order
    eigenvalues = np.maximum(eigenvalues, 0)   # numerical noise -> tiny negatives

    total = eigenvalues.sum()
    if total == 0:
        k_eff = float(n_tested_raw)
    else:
        p = eigenvalues / total                # normalised (sums to 1)
        # Shannon entropy of eigenspectrum.
        # Filter to strictly positive entries before log to avoid divide-by-zero
        # warnings (numpy evaluates both branches of np.where before masking).
        p_nz = p[p > 0]
        h = -float(np.sum(p_nz * np.log(p_nz)))
        k_eff = math.exp(h)                    # in [1, K] by construction

    k_eff = min(k_eff, float(n_tested_raw))    # cap at K (numerical safety)
    reduction_pct = round((1.0 - k_eff / n_tested_raw) * 100, 1)

    return {
        "k_raw": n_tested_raw,
        "k_eff": round(k_eff, 2),
        "reduction_pct": reduction_pct,
        "eigenvalues": [round(float(e), 4) for e in sorted(eigenvalues, reverse=True)],
        "bonferroni_raw": round(0.05 / n_tested_raw, 6),
        "bonferroni_keff": round(0.05 / k_eff, 6),
        "interpretation": (
            f"Your {n_tested_raw} tested configs are effectively {k_eff:.1f} "
            f"independent experiments ({reduction_pct:.0f}% correlation overlap). "
            f"Use p < {0.05/k_eff:.4f} as your significance threshold, "
            f"not p < {0.05/n_tested_raw:.4f}."
        ),
    }
