"""Phase 9 -- tier-2 M1-fidelity validation of the candidates_v2 survivors
that cleared multiple-testing correction on the tier-1 screen (11 candidates,
10 unique after XV2-111/114 duplicate found).

Every one of these looked strong in a fast next-bar-entry screen with no
daily-loss compounding -- exactly the setup that made a tier-1 rank-#11
candidate go to ~$0 last night once M1 sub-bar execution and the real daily
breaker were applied (HYP-025/026). This is that same check, at true M1
fidelity, real $105.74 balance, breaker on.

    python -m scripts.phase9_v2_validation <candidate_id>
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.research.candidates_v2 import build_library_v2
from src.research.market_study import build_features, session_mask
from src.strategies.base_strategy import Signal, mt5

RUNS_ROOT = os.path.join("research", "runs")


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


class V2Strategy:
    def __init__(self, cand, magic):
        self.cand, self.magic, self.name = cand, magic, cand.id

    def evaluate(self, m15_rates, m5_rates=None) -> Optional[Signal]:
        if m15_rates is None or len(m15_rates) < 260:
            return None
        f = build_features(m15_rates)
        raw = self.cand.rule(f)
        sig = np.where(session_mask(f["ist_hour"], self.cand.session), raw, 0)
        s = sig[-2]
        if s == 0 or np.isnan(s):
            return None
        if self.cand.direction_bias == "short" and s > 0:
            return None
        if self.cand.direction_bias == "long" and s < 0:
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
        "max_dd_pct": dd, "avg_stop_usd": avg_risk, "avg_risk_pct": avg_risk / start_bal * 100,
    }


def run(cand_id: str, out_dir: str):
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
    lib = {c.id: c for c in build_library_v2()}
    cand = lib[cand_id]

    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=105.74,
        sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=1, max_same_direction=1,
        enable_pyramiding=False, enable_consolidation_exit=False, enable_trailing=False,
        history_bars=900, warmup_bars=950,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
        tp_atr_mult=cand.tp_atr, sl_atr_mult_override=cand.sl_atr,
    )
    strat = V2Strategy(cand, magic=5000 + int(cand_id.split("-")[1]))
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run([strat], start_ts=_ts("2026-05-21"), end_ts=_ts("2026-08-29"))
    s = _stats(res.trades, 105.74)

    print(f"data {bars.hash_key()}  |  M1 LOADED  |  {cand_id} ({cand.family}) "
          f"sess={cand.session} tp={cand.tp_atr} sl={cand.sl_atr} bias={cand.direction_bias}")
    if s is None:
        print(f"{cand_id}: NO TRADES")
    else:
        pf = "inf" if s["pf"] == float("inf") else f"{s['pf']:.3f}"
        print(f"{cand_id}: n={s['n']} WR={s['wr']:.1f}% PF={pf} expR={s['exp_r']:+.4f} "
              f"net=${s['net']:+.0f} end=${s['end_bal']:.0f} minBal=${s['min_bal']:.0f} "
              f"DD={s['max_dd_pct']:.1f}% stop=${s['avg_stop_usd']:.2f} risk={s['avg_risk_pct']:.1f}%")

    with open(os.path.join(out_dir, f"result_{cand_id}.json"), "w", encoding="utf-8") as fh:
        json.dump({"candidate": cand_id, "family": cand.family, "session": list(cand.session),
                   "tp_atr": cand.tp_atr, "sl_atr": cand.sl_atr, "bias": cand.direction_bias,
                   "stats": s}, fh, indent=2, default=str)
    with open(os.path.join(out_dir, f"trades_{cand_id}.json"), "w", encoding="utf-8") as fh:
        json.dump([asdict(t) for t in res.trades], fh, indent=1, default=str)


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
