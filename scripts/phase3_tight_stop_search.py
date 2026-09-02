"""Phase 3 — the hypothesis Phase 1 actually generated.

Phase 1 found: the broker imposes no minimum stop distance, so risk per trade
is a design choice. The account tolerates a $5-10 stop (4.7-9.5%). That stop is
only statistically valid where the noise floor is below it -- ASIA (MAE p50
$5.77) and LATE (p50 $5.16), not NY ($8.69) or OVERLAP ($10.14).

So the question is NOT "which strategy is best" but:
  Does ANY entry rule produce positive expectancy with a $5-10 stop,
  in a low-noise session, after real costs, at true M1 fidelity?

Runs with M1 loaded (the Phase 0 error corrected) over the only window where
M1 exists: 2026-05-21 -> 2026-08-29. That is a SMALL SAMPLE (~3.5 months) and
results must be reported as such -- this is a screening pass, not validation.

    python -m scripts.phase3_tight_stop_search
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.research.candidates import build_library
from src.research.market_study import build_features
from src.strategies.base_strategy import Signal, mt5

RUNS_ROOT = os.path.join("research", "runs")

# IST session bounds. LATE wraps midnight-adjacent but does not cross it.
SESSIONS = {
    "ASIA": (2.5, 11.5),
    "LATE": (21.5, 24.0),
    "LONDON": (11.5, 15.5),
    "NY": (17.5, 21.5),
}

# Entry rules drawn from the existing library, one per structural family.
RULES = {
    "ema_stack": "XAU-005",
    "hhll_structure": "XAU-026",
    "fvg": "XAU-092",
    "orb": "XAU-075",
    "squeeze_break": "XAU-062",
    "range_rejection": "XAU-049",
    "atr_expansion": "XAU-064",
    "low_vol_revert": "XAU-070",
}

# Stop multipliers to test. At current ATR ~10, these are ~$5 / $7.5 / $10.
SL_MULTS = [0.5, 0.75, 1.0]
# Reward:risk -- Phase 1 requires >=1:2 since MFE/MAE ~1.0 gives nothing free.
TP_MULTS = {0.5: [1.5, 2.5], 0.75: [2.25, 3.0], 1.0: [2.0, 3.0]}


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _mask(ist_hour, sess):
    a, b = sess
    return (ist_hour >= a) & (ist_hour < b)


class TightStopStrategy:
    def __init__(self, name, magic, rule, sess):
        self.name, self.magic, self.rule, self.sess = name, magic, rule, sess

    def evaluate(self, m15_rates, m5_rates=None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < 260:
            return None
        f = build_features(m15_rates)
        sig = np.where(_mask(f["ist_hour"], self.sess), self.rule(f), 0)
        s = sig[-2]
        if s == 0 or np.isnan(s):
            return None
        return Signal(direction=mt5.ORDER_TYPE_BUY if s > 0 else mt5.ORDER_TYPE_SELL,
                      strategy_name=self.name, magic=self.magic, is_buy=bool(s > 0))

    def check_pending_confirmation(self, m15_rates):
        return None

    def set_pending(self, signal, candle_time):
        pass


def _stats(trades, start_bal):
    if not trades:
        return None
    net = np.array([t.net_pl for t in trades])
    r = np.array([t.r_multiple for t in trades])
    bal = np.concatenate([[start_bal], [t.balance_after for t in trades]])
    peak = np.maximum.accumulate(bal)
    dd = float((np.divide(peak - bal, peak, out=np.zeros_like(bal), where=peak > 0)).max() * 100)
    wins, losses = net[net > 0], net[net < 0]
    pf = wins.sum() / -losses.sum() if len(losses) else float("inf")
    avg_risk = float(np.mean([abs(t.entry_price - t.initial_sl) for t in trades]))
    return {
        "n": len(trades), "wr": float(len(wins) / len(net) * 100), "pf": float(pf),
        "exp_r": float(r.mean()), "net": float(net.sum()),
        "end_bal": float(bal[-1]), "min_bal": float(bal.min()),
        "max_dd_pct": dd, "avg_stop_usd": avg_risk,
        "avg_risk_pct": avg_risk / start_bal * 100,
    }


def run():
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
    lib = {c.id: c for c in build_library()}
    print(f"data {bars.hash_key()}  |  M1 LOADED (Phase 0 correction applied)")
    print("window 2026-05-21 -> 2026-08-29 (~3.5mo, the ONLY M1-covered period)")
    print("SCREENING PASS -- small sample, not validation\n")

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_phase3_tight_stops"
    out = os.path.join(RUNS_ROOT, run_id)
    os.makedirs(out, exist_ok=True)

    hdr = (f"{'rule':<16}{'sess':<8}{'SL':>5}{'TP':>5}{'n':>5}{'WR%':>7}{'PF':>7}"
           f"{'expR':>8}{'net$':>8}{'minBal':>8}{'DD%':>7}{'stop$':>7}{'risk%':>7}")
    print(hdr); print("-" * len(hdr))

    results = {}
    magic = 4000
    for rule_name, cid in RULES.items():
        rule = lib[cid].rule
        for sess_name, sess in SESSIONS.items():
            for sl in SL_MULTS:
                for tp in TP_MULTS[sl]:
                    magic += 1
                    cfg = EngineConfig(
                        symbol="XAUUSDm", starting_balance=105.74,
                        sizing_mode="fixed", fixed_lots=0.01,
                        dedup_per_candle=True, max_concurrent=1, max_same_direction=1,
                        enable_pyramiding=False, enable_consolidation_exit=False,
                        enable_trailing=False, history_bars=900, warmup_bars=950,
                        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
                        tp_atr_mult=tp, sl_atr_mult_override=sl,
                    )
                    strat = TightStopStrategy(f"{rule_name}_{sess_name}", magic, rule, sess)
                    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
                    res = eng.run([strat], start_ts=_ts("2026-05-21"), end_ts=_ts("2026-08-29"))
                    s = _stats(res.trades, 105.74)
                    key = f"{rule_name}|{sess_name}|SL{sl}|TP{tp}"
                    results[key] = s
                    if s is None:
                        continue
                    pf = "inf" if s["pf"] == float("inf") else f"{s['pf']:.2f}"
                    print(f"{rule_name:<16}{sess_name:<8}{sl:>5.2f}{tp:>5.2f}{s['n']:>5}"
                          f"{s['wr']:>7.1f}{pf:>7}{s['exp_r']:>8.3f}{s['net']:>8.0f}"
                          f"{s['min_bal']:>8.0f}{s['max_dd_pct']:>7.1f}"
                          f"{s['avg_stop_usd']:>7.2f}{s['avg_risk_pct']:>7.1f}", flush=True)

    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as fh:
        json.dump({"data_hash": bars.hash_key(), "results": results}, fh, indent=2, default=str)
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    run()
