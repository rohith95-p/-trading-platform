import unittest
from types import SimpleNamespace

import src.core.execution_handler as ex_mod
from src.core.execution_handler import ExecutionHandler
from src.core.risk_manager import RiskManager
from src.core.runtime_policy import RuntimePolicy


class _Mt5Stub:
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    TRADE_RETCODE_DONE = 10009

    def __init__(self):
        self._positions = []

    def account_info(self):
        return SimpleNamespace(balance=100.0)

    def positions_get(self, symbol=None):
        return self._positions

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(ask=4300.0, bid=4299.8)

    def order_send(self, request):
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=1, comment="ok")


class RiskAndExecutionTests(unittest.TestCase):
    def test_daily_drawdown_blocks(self):
        policy = RuntimePolicy(
            {
                "macro": {"strict_short_stops": False},
                "breakers": {"daily_loss_pct": 0.05},
                "promotion": {"stages": []},
            }
        )
        rm = RiskManager(policy=policy)
        self.assertFalse(rm.check_daily_drawdown(todays_pl=-4.0, floating_pl=-2.0, balance=100.0))

    def test_execution_stage_caps_block_third_position(self):
        policy = RuntimePolicy(
            {
                "promotion": {
                    "default_stage": "demo",
                    "stages": [
                        {
                            "name": "demo",
                            "min_balance": 0,
                            "max_balance": 999999,
                            "lot_size": 0.01,
                            "max_concurrent_positions": 2,
                            "max_same_direction_positions": 2,
                            "max_total_volume": 0.02,
                        }
                    ]
                }
            }
        )
        stub = _Mt5Stub()
        ex_mod.mt5 = stub
        h = ExecutionHandler(policy=policy)

        stub._positions = [
            SimpleNamespace(type=stub.ORDER_TYPE_BUY, volume=0.01),
            SimpleNamespace(type=stub.ORDER_TYPE_SELL, volume=0.01),
        ]
        self.assertFalse(h.can_open_new_position())


if __name__ == "__main__":
    unittest.main()
