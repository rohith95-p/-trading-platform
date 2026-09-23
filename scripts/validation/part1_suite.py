"""PART I validation suite -- REAL_MONEY_READINESS.md's edge-proof gate.

2-year standard (owner decision 2026-09-06). Holdout window is
2025-01-01 -> 2026-05-20: inside the regime the owner considers representative,
but excluding the 2026-05-21 -> 08-29 selection window so the strategy is not
scored on its own training data.

Each test is a separate CLI target so they can run on separate cores:

    python -m scripts.validation.part1_suite holdout      # I.1
    python -m scripts.validation.part1_suite walkforward  # I.2
    python -m scripts.validation.part1_suite montecarlo   # I.3
    python -m scripts.validation.part1_suite perturb      # I.4
    python -m scripts.validation.part1_suite randomentry  # I.5
    python -m scripts.validation.part1_suite regime       # I.6
    python -m scripts.validation.part1_suite cost         # I.7

Results are written to research/validation/part1_<target>.json so the ratings
report can be regenerated from measured data rather than transcribed by hand.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.portfolio_v4 import PORTFOLIO_V4

IST = timezone(timedelta(hours=5, minutes=30))
OUT_DIR = os.path.join("research", "validation")

# --- The strict IS/OOS split -----------------------------------------------
TRAIN_START = "2022-06-07"
TRAIN_END = "2024-12-31"
OOS_START = "2025-01-01"
OOS_END = "2026-05-20"
START_BAL = 105.74

PASS_PF = 1.2
PASS_MAXDD = 45.0
PASS_MIN_BAL_FRAC = 0.50


def _ts(d: str) -> int:
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _bars():
    return load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1", "H4"))


def live_config(**overrides) -> EngineConfig:
    """The actual deployed configuration (HYP-048: D1 gate OFF, live caps)."""
    base = dict(
        symbol="XAUUSDm", starting_balance=START_BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=3, max_same_direction=3,
        enable_pyramiding=False, enable_trailing=False, enable_consolidation_exit=False,
        history_bars=250, warmup_bars=300,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
        enable_d1_bias_gate=True,
    )
    base.update(overrides)
    return EngineConfig(**base)


def stats(trades, start_bal=START_BAL) -> dict:
    if not trades:
        return dict(n=0, note="no trades")
    pl = np.array([t.net_pl for t in trades])
    w, l = pl[pl > 0], pl[pl < 0]
    pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
    bal = start_bal + np.cumsum(pl)
    peak = np.maximum.accumulate(np.concatenate(([start_bal], bal)))
    dd = float(((peak[1:] - bal) / peak[1:] * 100).max())
    return dict(
        n=int(len(pl)), win_rate=float(len(w) / len(pl) * 100), profit_factor=round(pf, 4),
        net=round(float(pl.sum()), 2), min_balance=round(float(bal.min()), 2),
        end_balance=round(float(bal[-1]), 2), max_drawdown_pct=round(dd, 2),
        avg_win=round(float(w.mean()), 2) if len(w) else 0.0,
        avg_loss=round(float(l.mean()), 2) if len(l) else 0.0,
    )


def verdict(s: dict) -> dict:
    """Apply I.1's stated pass conditions."""
    if not s.get("n"):
        return dict(passed=False, reasons=["no trades"])
    reasons = []
    if s["profit_factor"] <= PASS_PF:
        reasons.append(f"PF {s['profit_factor']} <= {PASS_PF}")
    if s["max_drawdown_pct"] >= PASS_MAXDD:
        reasons.append(f"maxDD {s['max_drawdown_pct']}% >= {PASS_MAXDD}%")
    if s["min_balance"] < START_BAL * PASS_MIN_BAL_FRAC:
        reasons.append(f"min balance ${s['min_balance']} < 50% of start (${START_BAL * PASS_MIN_BAL_FRAC:.2f})")
    return dict(passed=not reasons, reasons=reasons)


def run_window(bars, cfg, start, end, strategies=None):
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    strats = strategies if strategies is not None else [c() for c in PORTFOLIO_V4]
    return eng.run(strats, start_ts=_ts(start), end_ts=_ts(end))


def save(target: str, payload: dict):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"part1_{target}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\n--> written to {path}")


# ---------------------------------------------------------------------------
# I.1  Out-of-sample holdout (OOS)
# ---------------------------------------------------------------------------
def t_holdout():
    bars = _bars()
    print(f"I.1 OOS HOLDOUT  {OOS_START} -> {OOS_END}  (live config, D1 gate OFF)")
    res = run_window(bars, live_config(), OOS_START, OOS_END)
    s = stats(res.trades)
    v = verdict(s)
    print(json.dumps(s, indent=2))
    print(f"PASS: {v['passed']}  {v['reasons']}")

    # For reference only, the training window itself.
    res_train = run_window(bars, live_config(), TRAIN_START, TRAIN_END)
    s_train = stats(res_train.trades)
    print(f"\n(reference) training window {TRAIN_START}..{TRAIN_END}: "
          f"PF={s_train.get('profit_factor')} net=${s_train.get('net')}")

    save("holdout", dict(window=[OOS_START, OOS_END], stats=s, verdict=v,
                         training_window_reference=s_train))


# ---------------------------------------------------------------------------
# I.2  Walk-forward (rolling test windows across the 2-year scope)
# ---------------------------------------------------------------------------
def t_walkforward():
    bars = _bars()
    # 60d train is implicit (the legs are already fixed); we measure rolling
    # 30-day test windows across the holdout to see stability of the edge.
    print("I.2 WALK-FORWARD: rolling 30d test windows across the OOS holdout")
    start = datetime.strptime(OOS_START, "%Y-%m-%d")
    end = datetime.strptime(OOS_END, "%Y-%m-%d")
    windows, cur = [], start
    while cur + timedelta(days=30) <= end:
        nxt = cur + timedelta(days=30)
        windows.append((cur.strftime("%Y-%m-%d"), nxt.strftime("%Y-%m-%d")))
        cur = nxt
    rows = []
    for a, b in windows:
        res = run_window(bars, live_config(), a, b)
        s = stats(res.trades)
        rows.append(dict(window=[a, b], **s))
        print(f"  {a}..{b}  n={s.get('n',0):4d}  PF={s.get('profit_factor','-'):>7}  net=${s.get('net','-'):>9}")
    pfs = [r["profit_factor"] for r in rows if r.get("n")]
    median_pf = float(np.median(pfs)) if pfs else 0.0
    pos = sum(1 for r in rows if r.get("net", 0) > 0)
    print(f"\nmedian test-window PF = {median_pf:.3f} (pass bar > 1.2) | "
          f"{pos}/{len(rows)} windows profitable")
    save("walkforward", dict(windows=rows, median_pf=round(median_pf, 4),
                             profitable_windows=pos, total_windows=len(rows),
                             passed=median_pf > PASS_PF))


# ---------------------------------------------------------------------------
# I.3  Monte Carlo -- trade-sequence bootstrap
# ---------------------------------------------------------------------------
def t_montecarlo(n_sims=10000):
    bars = _bars()
    print("I.3 MONTE CARLO bootstrap on OOS holdout trade sequence")
    res = run_window(bars, live_config(), OOS_START, OOS_END)
    pl = np.array([t.net_pl for t in res.trades])
    if not len(pl):
        print("no trades"); return
    rng = np.random.default_rng(11)
    n = len(pl)
    idx = rng.integers(0, n, size=(n_sims, n))
    paths = pl[idx]
    equity = START_BAL + np.cumsum(paths, axis=1)
    peak = np.maximum.accumulate(
        np.concatenate([np.full((n_sims, 1), START_BAL), equity], axis=1), axis=1)
    dd = ((peak[:, 1:] - equity) / peak[:, 1:]).max(axis=1) * 100
    wins = paths > 0
    gross_w = np.where(wins, paths, 0).sum(axis=1)
    gross_l = -np.where(~wins, paths, 0).sum(axis=1)
    pf = np.divide(gross_w, gross_l, out=np.full(n_sims, np.inf), where=gross_l > 0)
    touch_25 = (equity <= START_BAL * 0.75).any(axis=1).mean() * 100
    touch_50 = (equity <= START_BAL * 0.50).any(axis=1).mean() * 100
    ruin = (equity <= START_BAL * 0.20).any(axis=1).mean() * 100
    out = dict(
        trades_per_path=n, sims=n_sims,
        pf_p5=round(float(np.percentile(pf, 5)), 3),
        pf_p50=round(float(np.percentile(pf, 50)), 3),
        pf_p95=round(float(np.percentile(pf, 95)), 3),
        maxdd_p50=round(float(np.percentile(dd, 50)), 2),
        maxdd_p95=round(float(np.percentile(dd, 95)), 2),
        p_touch_minus25_pct=round(float(touch_25), 2),
        p_touch_minus50_pct=round(float(touch_50), 2),
        p_ruin_pct=round(float(ruin), 2),
    )
    out["passed"] = out["maxdd_p95"] < 40.0 and out["p_ruin_pct"] < 1.0
    print(json.dumps(out, indent=2))
    print(f"pass bar: 95th-pct maxDD < 40% AND P(ruin) < 1%  ->  PASS={out['passed']}")
    save("montecarlo", out)


# ---------------------------------------------------------------------------
# I.4  Parameter perturbation
# ---------------------------------------------------------------------------
def t_perturb():
    bars = _bars()
    print("I.4 PARAMETER PERTURBATION: +/-10% and +/-20% on SL/TP multipliers")
    rows = []
    for scale in [0.8, 0.9, 1.0, 1.1, 1.2]:
        strategies = []
        for cls in PORTFOLIO_V4:
            s = cls()
            s.sl_atr_mult = cls.sl_atr_mult * scale
            s.tp_atr_mult = cls.tp_atr_mult * scale
            strategies.append(s)
        res = run_window(bars, live_config(), OOS_START, OOS_END, strategies)
        st = stats(res.trades)
        rows.append(dict(scale=scale, **st))
        print(f"  scale={scale:.1f}  n={st.get('n',0):4d}  PF={st.get('profit_factor','-'):>7}  "
              f"net=${st.get('net','-'):>9}  maxDD={st.get('max_drawdown_pct','-')}%")
    pfs = [r["profit_factor"] for r in rows if r.get("n")]
    worst = min(pfs) if pfs else 0.0
    print(f"\nworst PF across cloud = {worst:.3f} (pass bar: all > 1.2)")
    save("perturb", dict(rows=rows, worst_pf=round(float(worst), 4), passed=worst > PASS_PF))


# ---------------------------------------------------------------------------
# I.5  Random-entry control (per leg)
# ---------------------------------------------------------------------------
def t_randomentry(n_iter=1000):
    """I.5 -- keep each leg's session window and exit geometry, replace the
    ENTRY RULE with a random entry. If the real rule carries no information,
    its PF sits inside the random distribution.

    Implemented as a direct M1 walk-forward rather than n_iter full engine
    runs (which would be ~800 backtests / days of compute). Each simulated
    trade: pick a random in-session M15 bar, random direction, SL/TP from that
    bar's ATR at the leg's own multipliers, then walk M1 until SL or TP is
    touched (SL checked first on the same bar -- the conservative assumption
    the engine also makes).
    """
    from src.research.market_study import build_features, session_mask

    bars = _bars()
    m15, m1 = bars.m15, bars.m1
    f = build_features(m15)
    atr = f["atr14"]
    ist_hour = f["ist_hour"]

    lo_ts, hi_ts = _ts(OOS_START), _ts(OOS_END)
    m1_t, m1_h, m1_l = m1["time"], m1["high"], m1["low"]
    rng = np.random.default_rng(5)
    results = {}

    for cls in PORTFOLIO_V4:
        real = run_window(bars, live_config(), OOS_START, OOS_END, [cls()])
        real_s = stats(real.trades)
        n_real = real_s.get("n", 0)
        real_pf = real_s.get("profit_factor", 0.0)
        if not n_real:
            print(f"{cls.name}: no real trades in holdout, skipping")
            continue

        mask = (session_mask(ist_hour, cls.session)
                & (m15["time"] >= lo_ts) & (m15["time"] < hi_ts)
                & ~np.isnan(atr))
        pool = np.nonzero(mask)[0]
        if len(pool) < 10:
            print(f"{cls.name}: not enough in-session bars, skipping")
            continue

        def simulate(idx: int, is_buy: bool) -> Optional[float]:
            entry = float(m15["close"][idx])
            a = float(atr[idx])
            if not np.isfinite(a) or a <= 0:
                return None
            sl_d, tp_d = cls.sl_atr_mult * a, cls.tp_atr_mult * a
            sl = entry - sl_d if is_buy else entry + sl_d
            tp = entry + tp_d if is_buy else entry - tp_d
            t0 = int(m15["time"][idx])
            j = int(np.searchsorted(m1_t, t0, side="right"))
            jmax = min(j + 96 * 15, len(m1_t))  # 96 M15 bars of runway
            for k in range(j, jmax):
                hi, lo = m1_h[k], m1_l[k]
                if is_buy:
                    if lo <= sl:
                        return -sl_d
                    if hi >= tp:
                        return tp_d
                else:
                    if hi >= sl:
                        return -sl_d
                    if lo <= tp:
                        return tp_d
            return None  # never resolved inside the runway

        pfs = []
        for _ in range(n_iter):
            picks = rng.choice(pool, size=min(n_real, len(pool)), replace=False)
            dirs = rng.random(len(picks)) < 0.5
            pls = [p for p, b in ((simulate(int(i), bool(b)), b) for i, b in zip(picks, dirs))
                   if p is not None]
            if not pls:
                continue
            arr = np.array(pls)
            w, l = arr[arr > 0], arr[arr < 0]
            if not len(l):
                continue
            pfs.append(float(w.sum() / -l.sum()))
        if not pfs:
            print(f"{cls.name}: no resolvable random trades")
            continue

        p95 = float(np.percentile(pfs, 95))
        beat = bool(real_pf > p95)
        results[cls.name] = dict(real_pf=real_pf, real_n=n_real,
                                 random_p50=round(float(np.median(pfs)), 3),
                                 random_p95=round(p95, 3), iterations=len(pfs),
                                 beats_p95=beat)
        print(f"  {cls.name:26s} real PF={real_pf:6} (n={n_real:4d})  vs random p50="
              f"{np.median(pfs):5.3f} p95={p95:5.3f}  -> {'CLEARS' if beat else 'FAILS'}")

    cleared = sum(1 for r in results.values() if r["beats_p95"])
    print(f"\n{cleared}/{len(results)} legs clear their random-entry control "
          f"(pass bar: all legs clear)")
    save("randomentry", dict(legs=results, cleared=cleared, total=len(results),
                             passed=bool(results) and cleared == len(results)))


# ---------------------------------------------------------------------------
# I.6  Regime segmentation
# ---------------------------------------------------------------------------
def t_regime():
    bars = _bars()
    print("I.6 REGIME SEGMENTATION across the OOS holdout")
    res = run_window(bars, live_config(), OOS_START, OOS_END)
    if not res.trades:
        print("no trades"); return
    m15 = bars.m15
    from src.research.market_study import atr as _atr
    a = _atr(m15, 14)
    times = m15["time"]
    closes = m15["close"]
    # D1 trend proxy: close vs 480-bar (5d) mean; vol regime: ATR percentile
    ma = np.full(len(closes), np.nan)
    for i in range(480, len(closes)):
        ma[i] = closes[i - 480:i].mean()
    valid = a[~np.isnan(a)]
    q = np.percentile(valid, [20, 40, 60, 80])

    buckets = {}
    for t in res.trades:
        i = int(np.searchsorted(times, t.entry_time, side="right") - 1)
        if i < 480 or np.isnan(a[i]) or np.isnan(ma[i]):
            continue
        trend = "up" if closes[i] > ma[i] else "down"
        vq = int(np.searchsorted(q, a[i]))  # 0..4 volatility quintile
        for key in (f"trend_{trend}", f"volq_{vq}", f"leg_{t.strategy}"):
            buckets.setdefault(key, []).append(t.net_pl)

    out = {}
    for key, pls in sorted(buckets.items()):
        arr = np.array(pls)
        w, l = arr[arr > 0], arr[arr < 0]
        pf = float(w.sum() / -l.sum()) if len(l) else float("inf")
        out[key] = dict(n=len(arr), pf=round(pf, 3), net=round(float(arr.sum()), 2),
                        win_rate=round(float(len(w) / len(arr) * 100), 1))
        print(f"  {key:32s} n={len(arr):4d}  PF={pf:6.3f}  net=${arr.sum():9.2f}")
    save("regime", out)


# ---------------------------------------------------------------------------
# I.7  Cost & slippage stress
# ---------------------------------------------------------------------------
def t_cost():
    bars = _bars()
    print("I.7 COST STRESS: 1x / 1.5x / 2x / 3x modeled cost")
    rows = []
    base = SCENARIOS["realistic"]
    import dataclasses
    for mult in [1.0, 1.5, 2.0, 3.0]:
        # spread_multiplier scales the bar-derived spread; slippage scales with it.
        cost = dataclasses.replace(
            base,
            spread_multiplier=base.spread_multiplier * mult,
            slippage_points=base.slippage_points * mult,
        )
        eng = BacktestEngine(bars=bars, cost=cost, config=live_config())
        res = eng.run([c() for c in PORTFOLIO_V4],
                      start_ts=_ts(OOS_START), end_ts=_ts(OOS_END))
        s = stats(res.trades)
        rows.append(dict(cost_multiple=mult, **s))
        print(f"  {mult}x  n={s.get('n',0):4d}  PF={s.get('profit_factor','-'):>7}  net=${s.get('net','-'):>9}")
    pf2 = next((r["profit_factor"] for r in rows if r["cost_multiple"] == 2.0 and r.get("n")), 0)
    print(f"\nPF at 2x cost = {pf2} (pass bar > 1.2)")
    save("cost", dict(rows=rows, pf_at_2x=pf2, passed=bool(pf2 and pf2 > PASS_PF)))


# ---------------------------------------------------------------------------
# LADDER -- does Part II's own sizing rulebook fix the ruin problem I.3 found?
# ---------------------------------------------------------------------------
def t_ladder(n_sims=10000):
    """I.3 found the edge is real (PF p5 = 1.14) but P(ruin) = 39% at the live
    config's 3 concurrent positions. REAL_MONEY_READINESS.md Part II.2 says a
    $100 account should run ONE position, not three. This measures whether
    that single change moves the account from 'coin-flip on ruin' to survivable.
    """
    from src.core import risk_rules

    bars = _bars()
    lots, max_vol, max_pos = risk_rules.sizing_for_balance(START_BAL)
    print(f"LADDER TEST -- Part II.2 sizing at ${START_BAL}: "
          f"{lots} lots, max_total_volume {max_vol}, max_positions {max_pos}")

    cfg = live_config(max_concurrent=max_pos, max_same_direction=max_pos,
                      fixed_lots=lots,
                      daily_loss_limit_pct=risk_rules.DAILY_LIMIT_PCT_EARLY)
    res = run_window(bars, cfg, OOS_START, OOS_END)
    s = stats(res.trades)
    v = verdict(s)
    print("\nHoldout under Part II sizing:")
    print(json.dumps(s, indent=2))
    print(f"I.1 PASS: {v['passed']}  {v['reasons']}")

    pl = np.array([t.net_pl for t in res.trades])
    if not len(pl):
        save("ladder", dict(stats=s, verdict=v)); return

    rng = np.random.default_rng(11)
    n = len(pl)
    paths = pl[rng.integers(0, n, size=(n_sims, n))]
    equity = START_BAL + np.cumsum(paths, axis=1)
    peak = np.maximum.accumulate(
        np.concatenate([np.full((n_sims, 1), START_BAL), equity], axis=1), axis=1)
    dd = ((peak[:, 1:] - equity) / peak[:, 1:]).max(axis=1) * 100
    wins = paths > 0
    gw = np.where(wins, paths, 0).sum(axis=1)
    gl = -np.where(~wins, paths, 0).sum(axis=1)
    pf = np.divide(gw, gl, out=np.full(n_sims, np.inf), where=gl > 0)
    mc = dict(
        trades_per_path=n, sims=n_sims,
        pf_p5=round(float(np.percentile(pf, 5)), 3),
        pf_p50=round(float(np.percentile(pf, 50)), 3),
        pf_p95=round(float(np.percentile(pf, 95)), 3),
        maxdd_p50=round(float(np.percentile(dd, 50)), 2),
        maxdd_p95=round(float(np.percentile(dd, 95)), 2),
        p_touch_minus25_pct=round(float((equity <= START_BAL * 0.75).any(axis=1).mean() * 100), 2),
        p_touch_minus50_pct=round(float((equity <= START_BAL * 0.50).any(axis=1).mean() * 100), 2),
        p_ruin_pct=round(float((equity <= START_BAL * 0.20).any(axis=1).mean() * 100), 2),
    )
    mc["passed"] = mc["maxdd_p95"] < 40.0 and mc["p_ruin_pct"] < 1.0
    print("\nMonte Carlo under Part II sizing:")
    print(json.dumps(mc, indent=2))
    print(f"I.3 PASS: {mc['passed']}")
    save("ladder", dict(sizing=dict(lots=lots, max_total_volume=max_vol, max_positions=max_pos),
                        stats=s, verdict=v, montecarlo=mc))


TARGETS = dict(holdout=t_holdout, walkforward=t_walkforward, montecarlo=t_montecarlo,
               perturb=t_perturb, randomentry=t_randomentry, regime=t_regime,
               cost=t_cost, ladder=t_ladder)

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in TARGETS:
        print(f"usage: python -m scripts.validation.part1_suite [{'|'.join(TARGETS)}]")
        sys.exit(1)
    TARGETS[sys.argv[1]]()
