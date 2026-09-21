import unittest

from src.core.runtime_policy import RuntimePolicy


class RuntimePolicyTests(unittest.TestCase):
    def test_stage_selection_by_balance(self):
        p = RuntimePolicy(
            {
                "promotion": {
                    "default_stage": "demo",
                    "stages": [
                        {
                            "name": "demo",
                            "min_balance": 0,
                            "max_balance": 199.99,
                            "lot_size": 0.01,
                            "max_concurrent_positions": 1,
                            "max_same_direction_positions": 1,
                            "max_total_volume": 0.01,
                        },
                        {
                            "name": "live",
                            "min_balance": 200,
                            "max_balance": 999999,
                            "lot_size": 0.02,
                            "max_concurrent_positions": 2,
                            "max_same_direction_positions": 2,
                            "max_total_volume": 0.04,
                        },
                    ]
                },
                "macro": {"strict_short_stops": True},
                "breakers": {"daily_loss_pct": 0.05},
            }
        )
        self.assertEqual(p.stage_for_balance(100).name, "demo")
        self.assertEqual(p.stage_for_balance(350).name, "live")
        self.assertTrue(p.strict_short_stops())
        self.assertEqual(p.daily_loss_pct(0.06), 0.05)


if __name__ == "__main__":
    unittest.main()
