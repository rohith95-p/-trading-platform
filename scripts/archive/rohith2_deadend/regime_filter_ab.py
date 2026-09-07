"""LOOP iteration 4 -- can a regime / equity-curve filter salvage portfolio_v4?

edge_by_period showed: 2024H2-2025 worked (PF 1.2-1.4), 2023 + early-2026 were
account-killers (PF 0.75-0.9, 90-100% DD), net-negative over 4 years.

Two filter families, run on the FULL 4-year window (M15 fidelity):
  A. Equity-curve pause -- stop opening trades when balance is > X% below its
     peak; resume when it recovers to within Y%. No external data.
  B. D1 volatility regime -- only trade when D1 ATR% is in a band, or when D1
     ADX says trending. (added later if A shows promise)

If NOTHING lifts the 4-year PF meaningfully above 1.0 with survivable DD, the
answer is: mechanical M15 gold entries have no edge -> option C.

    python -m scripts.regime_filter_ab
"""
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.portfolio_v4 import PORTFOLIO_V4


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
START, END, BAL = "2022-07-01", "2026-05-19", 105.74

VARIANTS = [
    ("baseline (no filter)",            dict()),
    ("equity pause -20% / resume -10%", dict(equity_pause_dd=0.20, equity_resume_dd=0.10)),
    ("equity pause -25% / resume -12%", dict(equity_pause_dd=0.25, equity_resume_dd=0.12)),
    ("equity pause -30% / resume -15%", dict(equity_pause_dd=0.30, equity_resume_dd=0.15)),
    ("equity pause -15% / resume -8%",  dict(equity_pause_dd=0.15, equity_resume_dd=0.08)),
]

print(f"HOLDOUT {START} -> {END} | M15 | ${BAL} | 4 legs | frozen exits\n")
print(f"{'variant':<34} {'n':>5} {'WR':>6} {'PF':>7} {'net$':>9} {'minBal':>8} {'DD%':>6} {'pauses':>7}")
print("-" * 88)

for label, extra in VARIANTS:
    cfg = EngineConfig(
        symbol="XAUUSDm", starting_balance=BAL, sizing_mode="fixed", fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=2, max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False, enable_consolidation_exit=False,
        history_bars=250, warmup_bars=300,
        daily_loss_limit_mode="balance_pct", daily_loss_limit_pct=0.06,
        enable_d1_bias_gate=True, direction_gate="d1_ema20", **extra,
    )
    eng = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=cfg)
    res = eng.run([c() for c in PORTFOLIO_V4], start_ts=_ts(START), end_ts=_ts(END))
    pl = np.array([t.net_pl for t in res.trades])
    if not len(pl):
        print(f"{label:<34} NO TRADES"); continue
    w, l = pl[pl > 0], pl[pl < 0]
    pf = w.sum() / -l.sum() if len(l) else 99.0
    bal = BAL + np.cumsum(pl)
    peak = np.maximum.accumulate(np.concatenate(([BAL], bal)))
    dd = ((peak[1:] - bal) / peak[1:] * 100).max()
    pauses = res.diag.get("equity_pauses", 0) if hasattr(res, "diag") else 0
    print(f"{label:<34} {len(pl):>5} {len(w)/len(pl)*100:>5.1f}% {pf:>7.3f} "
          f"{pl.sum():>9.2f} {bal.min():>8.2f} {dd:>5.1f}% {pauses:>7}")
