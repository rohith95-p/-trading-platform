"""
Tests for Task 20: Advanced Features & Analytics
"""

import math
import pytest
from datetime import datetime, timedelta

from src.portfolio.multi_strategy import MultiStrategyPortfolio
from src.risk.advanced_analytics import AdvancedRiskAnalytics
from src.backtesting.advanced_filters import BacktestFilter


class FakeTrade:
    def __init__(self, pnl: float, symbol: str = "BTC", entry_offset: int = 0, duration_hours: int = 2):
        self.pnl = pnl
        self.symbol = symbol
        self.entry_time = datetime(2024, 1, 1) + timedelta(days=entry_offset)
        self.exit_time = self.entry_time + timedelta(hours=duration_hours)
        self.pnl_percent = pnl / 100.0


class TestMultiStrategyPortfolio:
    def test_add_and_len(self):
        p = MultiStrategyPortfolio(total_capital=10_000)
        p.add_strategy("alpha", 0.5)
        p.add_strategy("beta", 0.3)
        assert len(p) == 2

    def test_contains(self):
        p = MultiStrategyPortfolio()
        p.add_strategy("alpha", 0.4)
        assert "alpha" in p
        assert "beta" not in p

    def test_add_duplicate_raises(self):
        p = MultiStrategyPortfolio()
        p.add_strategy("alpha", 0.4)
        with pytest.raises(ValueError, match="already exists"):
            p.add_strategy("alpha", 0.2)

    def test_add_exceeds_100pct_raises(self):
        p = MultiStrategyPortfolio()
        p.add_strategy("alpha", 0.6)
        with pytest.raises(ValueError, match="exceed 100%"):
            p.add_strategy("beta", 0.5)

    def test_remove_strategy(self):
        p = MultiStrategyPortfolio()
        p.add_strategy("alpha", 0.5)
        p.remove_strategy("alpha")
        assert len(p) == 0

    def test_remove_nonexistent_raises(self):
        p = MultiStrategyPortfolio()
        with pytest.raises(KeyError):
            p.remove_strategy("ghost")

    def test_get_portfolio_metrics(self):
        p = MultiStrategyPortfolio(total_capital=10_000)
        p.add_strategy("alpha", 0.6)
        p.add_strategy("beta", 0.4)
        metrics = p.get_portfolio_metrics()
        assert metrics["strategy_count"] == 2
        assert abs(metrics["total_value"] - 10_000) < 1e-6

    def test_rebalance(self):
        p = MultiStrategyPortfolio(total_capital=10_000)
        p.add_strategy("alpha", 0.5)
        p.add_strategy("beta", 0.5)
        p.update_strategy_value("alpha", 7_000)
        p.rebalance()
        metrics = p.get_portfolio_metrics()
        assert abs(metrics["allocations"]["alpha"]["actual_pct"] - 0.5) < 0.01

    def test_clone_strategy(self):
        p = MultiStrategyPortfolio(total_capital=10_000)
        p.add_strategy("alpha", 0.3, config={"param": 42})
        p.clone_strategy("alpha", "alpha_v2")
        assert "alpha_v2" in p

    def test_update_strategy_value_updates_pnl(self):
        p = MultiStrategyPortfolio(total_capital=10_000)
        p.add_strategy("alpha", 0.5)
        p.update_strategy_value("alpha", 6_000)
        metrics = p.get_portfolio_metrics()
        assert metrics["pnl_by_strategy"]["alpha"] == pytest.approx(1_000)


class TestAdvancedRiskAnalytics:
    def setup_method(self):
        self.analytics = AdvancedRiskAnalytics()
        self.returns = [-0.05, -0.03, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06]

    def test_var_empty(self):
        assert self.analytics.compute_var([]) == 0.0

    def test_var_positive(self):
        assert self.analytics.compute_var(self.returns, confidence=0.95) >= 0.0

    def test_cvar_gte_var(self):
        var = self.analytics.compute_var(self.returns, confidence=0.95)
        cvar = self.analytics.compute_cvar(self.returns, confidence=0.95)
        assert cvar >= var - 1e-9

    def test_beta_identical_series(self):
        r = [0.01, -0.02, 0.03, -0.01, 0.02]
        assert abs(self.analytics.compute_beta(r, r) - 1.0) < 1e-9

    def test_correlation_matrix_diagonal(self):
        data = {"A": [0.01, -0.02, 0.03, 0.01], "B": [-0.01, 0.02, -0.03, 0.02]}
        matrix = self.analytics.compute_correlation_matrix(data)
        assert matrix["A"]["A"] == pytest.approx(1.0)
        assert matrix["B"]["B"] == pytest.approx(1.0)

    def test_correlation_matrix_symmetric(self):
        data = {"A": [0.01, -0.02, 0.03, 0.01], "B": [-0.01, 0.02, -0.03, 0.02]}
        matrix = self.analytics.compute_correlation_matrix(data)
        assert matrix["A"]["B"] == pytest.approx(matrix["B"]["A"])

    def test_sortino_empty(self):
        assert self.analytics.compute_sortino_ratio([]) == 0.0

    def test_sortino_mixed_returns(self):
        r = [0.05, -0.02, 0.03, -0.01, 0.04, -0.03]
        assert math.isfinite(self.analytics.compute_sortino_ratio(r))


class TestBacktestFilter:
    def setup_method(self):
        self.f = BacktestFilter()
        self.trades = [
            FakeTrade(pnl=100, symbol="BTC", entry_offset=0),
            FakeTrade(pnl=-50, symbol="ETH", entry_offset=1),
            FakeTrade(pnl=200, symbol="BTC", entry_offset=2),
            FakeTrade(pnl=-10, symbol="SOL", entry_offset=3),
            FakeTrade(pnl=75, symbol="ETH", entry_offset=4),
        ]

    def test_filter_by_date_range(self):
        result = self.f.filter_by_date_range(
            self.trades, datetime(2024, 1, 2), datetime(2024, 1, 4)
        )
        assert len(result) == 3

    def test_filter_by_min_pnl(self):
        result = self.f.filter_by_min_pnl(self.trades, min_pnl=50)
        assert all(t.pnl >= 50 for t in result)

    def test_filter_by_symbol(self):
        result = self.f.filter_by_symbol(self.trades, ["BTC"])
        assert all(t.symbol == "BTC" for t in result)

    def test_filter_by_win_loss_wins(self):
        result = self.f.filter_by_win_loss(self.trades, wins_only=True)
        assert all(t.pnl > 0 for t in result)

    def test_compute_trade_analytics_values(self):
        result = self.f.compute_trade_analytics(self.trades)
        assert result["total_trades"] == 5
        assert result["best_trade"] == 200
        assert result["worst_trade"] == -50
        assert result["win_rate"] == pytest.approx(0.6)

    def test_compute_trade_analytics_duration(self):
        result = self.f.compute_trade_analytics(self.trades)
        assert result["avg_duration_seconds"] == pytest.approx(7200)
