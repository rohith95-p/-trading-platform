"""Unit tests for execution-delay sensitivity analysis (P2-2)."""
import pytest
from scripts.validation.execution_delay_sensitivity import evaluate_delay_sensitivity


def test_evaluate_delay_sensitivity():
    """Verify execution delay induces predictable PF decay across 1, 5, 15 bars."""
    trades = [
        {"net_pl": 12.0},
        {"net_pl": 15.0},
        {"net_pl": -4.0},
        {"net_pl": -5.0},
        {"net_pl": 18.0},
        {"net_pl": -6.0},
    ]
    
    res = evaluate_delay_sensitivity(trades, delays=[0, 1, 5, 15])
    
    assert "delay_0_bars" in res
    assert "delay_1_bars" in res
    assert "delay_5_bars" in res
    assert "delay_15_bars" in res
    
    # 0-bar baseline has 0% decay
    assert res["delay_0_bars"]["pf_decay_pct"] == 0.0
    
    # Increasing delay must increase PF decay
    pf_0 = res["delay_0_bars"]["profit_factor"]
    pf_1 = res["delay_1_bars"]["profit_factor"]
    pf_5 = res["delay_5_bars"]["profit_factor"]
    pf_15 = res["delay_15_bars"]["profit_factor"]
    
    assert pf_0 > pf_1 >= pf_5 >= pf_15
    assert res["delay_15_bars"]["pf_decay_pct"] > res["delay_1_bars"]["pf_decay_pct"]
