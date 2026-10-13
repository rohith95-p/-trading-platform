"""Unit tests for bootstrap confidence interval metrics (P2-1)."""
import pytest
from types import SimpleNamespace
from src.backtesting.metrics import bootstrap_ci_metrics


def test_bootstrap_ci_metrics_calculation():
    """Verify bootstrap CI metrics computes 95% confidence intervals for PF and Sortino."""
    # 20 trades with net positive edge (14 wins of +10, 6 losses of -5)
    trades = [SimpleNamespace(net_pl=10.0 + i) for i in range(14)] + [
        SimpleNamespace(net_pl=-3.0 - i) for i in range(6)
    ]
    
    ci = bootstrap_ci_metrics(trades, n_resamples=500, confidence_level=0.95, seed=123)
    
    assert ci["n_trades"] == 20
    assert ci["n_resamples"] == 500
    assert ci["confidence_level"] == 0.95
    
    # Observed PF = 231 / 33 = 7.0
    assert pytest.approx(ci["profit_factor"]["observed"], 0.01) == 7.0
    assert ci["profit_factor"]["ci_lower"] > 1.0  # Statistically positive edge
    assert ci["profit_factor"]["ci_upper"] >= ci["profit_factor"]["ci_lower"]
    
    # Observed Sortino is positive
    assert ci["sortino_ratio"]["observed"] > 0
    assert ci["sortino_ratio"]["ci_lower"] < ci["sortino_ratio"]["ci_upper"]


def test_bootstrap_ci_too_few_trades():
    """Returns empty dict if fewer than 5 trades."""
    trades = [SimpleNamespace(net_pl=1.0) for _ in range(3)]
    ci = bootstrap_ci_metrics(trades)
    assert ci == {}
