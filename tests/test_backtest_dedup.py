import unittest
from dataclasses import asdict
from datetime import datetime, timezone

import numpy as np

from src.backtesting.costs import SCENARIOS
from src.backtesting.data import BarSet, DataManifest, SymbolSpec
from src.backtesting.engine import BacktestEngine, EngineConfig
from src.strategies.base_strategy import BaseStrategy, Signal


def _bars(n, step, start):
    dtype = [
        ("time", np.int64),
        ("open", np.float64),
        ("high", np.float64),
        ("low", np.float64),
        ("close", np.float64),
        ("tick_volume", np.int64),
        ("spread", np.int32),
        ("real_volume", np.int64),
    ]
    arr = np.zeros(n, dtype=dtype)
    for i in range(n):
        t = start + i * step
        o = 4300.0 + i * 0.02
        c = o + 0.01
        arr[i] = (t, o, c + 0.03, o - 0.03, c, 100, 30, 0)
    return arr


class AlwaysBuy(BaseStrategy):
    name = "ALWAYS_BUY"
    magic = 9876
    sl_atr_mult = 0.2
    tp_atr_mult = 0.2

    def evaluate(self, rates, m5_rates=None):
        return Signal(direction=0, strategy_name=self.name, magic=self.magic, is_buy=True)


class DedupBacktestTests(unittest.TestCase):
    def _barset(self):
        start = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
        m15 = _bars(500, 900, start)
        m1 = _bars(500 * 15, 60, start)
        spec = SymbolSpec(
            symbol="XAUUSDm",
            digits=3,
            point=0.001,
            trade_tick_size=0.001,
            trade_tick_value=0.1,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            contract_size=100.0,
        )
        mf = DataManifest(
            symbol="XAUUSDm",
            timeframe="M15",
            bars=len(m15),
            first_time="",
            last_time="",
            sha256="dummy",
            server="local",
            downloaded_utc="",
            spec=asdict(spec),
        )
        return BarSet(
            symbol="XAUUSDm",
            m15=m15,
            m5=None,
            m1=m1,
            d1=None,
            spec=spec,
            manifests={"M15": mf},
        )

    def _run(self, dedup):
        cfg = EngineConfig(
            symbol="XAUUSDm",
            starting_balance=500.0,
            dedup_per_candle=dedup,
            max_concurrent=50,
            max_same_direction=50,
            enable_pyramiding=False,
            enable_consolidation_exit=False,
            enable_trailing=False,
            enable_d1_bias_gate=False,
            sizing_mode="fixed",
            fixed_lots=0.01,
            history_bars=250,
            warmup_bars=300,
            sl_atr_mult_override=0.2,
            tp_atr_mult=0.2,
        )
        engine = BacktestEngine(self._barset(), SCENARIOS["frictionless"], cfg)
        out = engine.run([AlwaysBuy()])
        return len(out.trades)

    def test_dedup_reduces_trade_count(self):
        no_dedup = self._run(False)
        dedup = self._run(True)
        self.assertGreater(no_dedup, dedup)


if __name__ == "__main__":
    unittest.main()
