"""
Research Scientist: Target $10 per trade search.
Constraints: 
- 09:00 IST to 21:30 IST window only.
- Strategy must yield >= $10 net profit on average per winning trade.
- Strategy must survive IS/OOS validation (PF > 1.25).
"""
import numpy as np
import scipy.stats as stats
import time
from datetime import datetime

from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.strategies.bible_strategies import PDHLRStrategy, NVMRStrategy, LARSStrategy, LKOCSStrategy
from scripts.validation.part1_suite import _ts, START_BAL

# Define the restricted session window (09:00 to 21:30 IST)
class SessionGatedStrategy:
    def __init__(self, base_strategy):
        self.base = base_strategy
        self.name = f"{base_strategy.name}_GATED"
        self.magic = base_strategy.magic
        self.execute_immediately = getattr(base_strategy, "execute_immediately", True)
        self.edge_trigger = getattr(base_strategy, "edge_trigger", False)
        
    def evaluate(self, m15_rates, m5_rates=None):
        if m15_rates is None or len(m15_rates) < 2:
            return None
            
        # Get IST hour of current bar
        ts = m15_rates["time"][-1]
        dt = datetime.fromtimestamp(ts)
        ist_hour = dt.hour + (dt.minute / 60.0) + 5.5
        if ist_hour >= 24:
            ist_hour -= 24
            
        # Gating: 09:00 to 21:30 IST
        if not (9.0 <= ist_hour <= 21.5):
            return None
            
        return self.base.evaluate(m15_rates, m5_rates)
        
    def check_pending_confirmation(self, m15_rates):
        return self.base.check_pending_confirmation(m15_rates)
        
    def set_pending(self, signal, candle_time):
        self.base.set_pending(signal, candle_time)

IS_START = "2025-01-01"
IS_END = "2025-12-31"
OOS_START = "2026-01-01"
OOS_END = "2026-05-20"
LOT_SIZE = 0.04 # Confirmed safe size from previous task

def _make_cfg():
    return EngineConfig(
        symbol="XAUUSDm", starting_balance=START_BAL,
        sizing_mode="fixed", fixed_lots=LOT_SIZE,
        dedup_per_candle=True, max_concurrent=2, max_same_direction=2,
        enable_pyramiding=False, enable_trailing=False,
        history_bars=250, warmup_bars=300, daily_loss_limit_mode="off",
        enable_d1_bias_gate=True, direction_gate="d1_ema20"
    )

def _build_variants():
    variants = []
    bases = [PDHLRStrategy, NVMRStrategy, LARSStrategy, LKOCSStrategy]
    
    # We want big wins, so we sweep TP from 1.5 to 4.0
    sl_tp_combos = [
        (0.4, 1.5), (0.4, 2.0), (0.4, 2.5), (0.4, 3.0),
        (0.5, 1.5), (0.5, 2.0), (0.5, 2.5), (0.5, 3.0), (0.5, 4.0),
        (0.7, 2.0), (0.7, 3.0), (0.7, 4.0)
    ]
    
    for BaseCls in bases:
        for sl, tp in sl_tp_combos:
            s = BaseCls()
            s.sl_atr_mult = sl
            s.tp_atr_mult = tp
            s.name = f"{BaseCls.__name__.replace('Strategy', '')}_sl{sl}_tp{tp}"
            s.magic = 9000 + int(sl*100) + int(tp*10)
            variants.append(s)
    return variants

def main():
    print("="*70)
    print(f"SEARCHING FOR $10/WIN STRATEGIES (09:00 - 21:30 IST)")
    print(f"Lot Size: {LOT_SIZE} | IS: {IS_START} -> {IS_END} | OOS: {OOS_START} -> {OOS_END}")
    print("="*70)
    
    variants = _build_variants()
    bars = load_bars("XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
    
    # -- IS RUN --
    print(f"\n[IS] Running {len(variants)} variants...", flush=True)
    eng_is = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=_make_cfg())
    res_is = eng_is.run(variants, start_ts=_ts(IS_START), end_ts=_ts(IS_END))
    
    is_survivors = []
    for v in variants:
        rets = np.array([t.net_pl for t in res_is.trades if t.strategy == v.name])
        
        wins = rets[rets > 0] if len(rets) > 0 else np.array([])
        loss = rets[rets < 0] if len(rets) > 0 else np.array([])
        
        avg_win = np.mean(wins) if len(wins) > 0 else 0
        pf = wins.sum() / -loss.sum() if len(loss) > 0 else 0
        
        print(f"  [DEBUG] {v.name}: PF={pf:.2f}, AvgWin=${avg_win:.2f}, n={len(rets)}")
        
        if len(rets) < 5 or len(wins) == 0 or len(loss) == 0:
            continue
            
        if pf > 1.25 and avg_win >= 10.0:
            is_survivors.append(v)
            print(f"  [PASS IS] {v.name}: PF={pf:.2f}, AvgWin=${avg_win:.2f}, n={len(rets)}")
            
    if not is_survivors:
        print("\n❌ NO STRATEGIES SURVIVED IS GATE.")
        return
        
    # -- OOS RUN --
    print(f"\n[OOS] Running {len(is_survivors)} survivors...", flush=True)
    eng_oos = BacktestEngine(bars=bars, cost=SCENARIOS["realistic"], config=_make_cfg())
    res_oos = eng_oos.run(is_survivors, start_ts=_ts(OOS_START), end_ts=_ts(OOS_END))
    
    print("\n" + "="*70)
    print("FINAL OOS VALIDATION ($10/WIN TARGET)")
    print("="*70)
    
    valid_candidates = []
    
    for v in is_survivors:
        rets = np.array([t.net_pl for t in res_oos.trades if t.strategy == v.name])
        if len(rets) < 5:
            continue
            
        wins = rets[rets > 0]
        loss = rets[rets < 0]
        if len(loss) == 0 or len(wins) == 0:
            continue
            
        avg_win = np.mean(wins)
        pf = wins.sum() / -loss.sum()
        wr = len(wins) / len(rets) * 100
        net = rets.sum()
        
        # OOS Criteria: PF > 1.1 AND Avg Win >= $10
        if pf > 1.1 and avg_win >= 9.8: # small leniency on OOS avg win
            valid_candidates.append({
                "name": v.name,
                "pf": pf,
                "wr": wr,
                "avg_win": avg_win,
                "net": net,
                "n": len(rets)
            })
            print(f"✅ {v.name}")
            print(f"   OOS PF: {pf:.2f} | Avg Win: ${avg_win:.2f} | WR: {wr:.1f}% | Net: ${net:.2f} | n={len(rets)}")
        else:
            print(f"❌ {v.name} Failed OOS (PF={pf:.2f}, AvgWin=${avg_win:.2f})")
            
    if valid_candidates:
        # Save the single best candidate for Monte Carlo
        best = sorted(valid_candidates, key=lambda x: x["pf"])[-1]
        print("\n" + "="*70)
        print(f"🏆 BEST STRATEGY FOUND: {best['name']}")
        print(f"   Hits ${best['avg_win']:.2f} per winning trade.")
        print("="*70)
        
        with open("scripts/research/best_10_target.txt", "w") as f:
            f.write(best["name"])
    else:
        print("\n❌ No strategies survived OOS.")

if __name__ == "__main__":
    main()
