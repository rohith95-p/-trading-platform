import sys
from datetime import datetime, timezone
import numpy as np
from src.backtesting.data import load_bars
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.costs import SCENARIOS
from src.research.candidates import build_library
from scripts.phase3_worker import TightStopStrategy

def _ts(d): return int(datetime.strptime(d,'%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())

cid, sess_name, sess, sl, tp, label = sys.argv[1], sys.argv[2], eval(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
lib = {c.id: c for c in build_library()}
rule = lib[cid].rule
bars = load_bars('XAUUSDm', timeframes=('M15','M5','M1','D1'))

for trail_on in (False, True):
    cfg = EngineConfig(symbol='XAUUSDm', starting_balance=105.74, sizing_mode='fixed', fixed_lots=0.01,
        dedup_per_candle=True, max_concurrent=1, max_same_direction=1, enable_pyramiding=False,
        enable_consolidation_exit=False, enable_trailing=trail_on, history_bars=900, warmup_bars=950,
        daily_loss_limit_mode='balance_pct', daily_loss_limit_pct=0.06,
        tp_atr_mult=tp, sl_atr_mult_override=sl)
    strat = TightStopStrategy(f'{label}_trailtest', 9990+trail_on, rule, sess)
    eng = BacktestEngine(bars=bars, cost=SCENARIOS['realistic'], config=cfg)
    res = eng.run([strat], start_ts=_ts('2026-05-21'), end_ts=_ts('2026-08-29'))
    t = res.trades
    if not t:
        print(f'{label} trailing={trail_on}: NO TRADES', flush=True); continue
    net = np.array([x.net_pl for x in t])
    wins, losses = net[net>0], net[net<0]
    pf = wins.sum()/-losses.sum() if len(losses) else float('inf')
    mfe = np.mean([x.mfe_r for x in t])
    realized_r = np.mean([x.r_multiple for x in t])
    print(f'{label} trailing={trail_on}: n={len(t)} WR={len(wins)/len(net)*100:.1f}% PF={pf:.3f} '
          f'net=${net.sum():.0f} avg_MFE_R={mfe:.3f} avg_realized_R={realized_r:.3f} '
          f'capture={realized_r/mfe*100 if mfe else 0:.0f}%', flush=True)
