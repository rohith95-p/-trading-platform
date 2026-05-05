"""
SOURCE: git repos/Fiduciary-Sentinel-Core - Copy/mcp/signal_ranker.py
PURPOSE: Execution priority scoring — decides whether to act NOW or defer.
         Combines PPO output strength, council conviction, VAMP urgency,
         order book imbalance, and ATR into a single priority score [0-1].

Usage:
    from src.reference_implementations.signal_execution_priority import rank_signal
    
    result = rank_signal(
        action="BUY",
        action_value=0.7,      # PPO raw output
        conviction=0.6,        # Multi-agent consensus conviction
        urgency=0.8,           # Time-sensitivity score
        imbalance=0.4,         # Order book imbalance
        atr_pct=0.02           # ATR as % of price
    )
    if result["should_execute"]:
        place_order(...)
"""

from typing import Dict


def rank_signal(
    action: str,
    action_value: float,
    conviction: float,
    urgency: float,
    imbalance: float,
    atr_pct: float,
) -> Dict:
    """
    Compute execution priority score.

    Weights:
        30% PPO signal strength
        25% Multi-agent conviction alignment
        25% VAMP urgency
        10% Volatility penalty (lower ATR = better)
        10% Order book imbalance

    Args:
        action: "BUY", "SELL", or "HOLD"
        action_value: Raw PPO output [-1, 1]
        conviction: Council conviction [-1, +1] (positive = bullish)
        urgency: VAMP urgency score [0, 1]
        imbalance: LOB imbalance [-1, +1]
        atr_pct: ATR as fraction of price (e.g. 0.02 = 2%)

    Returns:
        {"priority": float, "should_execute": bool, "reasoning": str}
    """
    if action == "HOLD":
        return {"priority": 0.0, "should_execute": False, "reasoning": "HOLD — no execution needed."}

    ppo_strength = min(1.0, abs(action_value) * 5)

    conviction_alignment = 0.0
    if action == "BUY":
        conviction_alignment = max(0.0, conviction)
    else:
        conviction_alignment = max(0.0, -conviction)

    priority = (
        0.30 * ppo_strength +
        0.25 * conviction_alignment +
        0.25 * urgency +
        0.10 * (1.0 - min(1.0, atr_pct * 10)) +
        0.10 * abs(imbalance)
    )
    priority = max(0.0, min(1.0, priority))

    return {
        "priority": round(priority, 4),
        "should_execute": priority >= 0.3,
        "reasoning": (
            f"Priority: {priority:.2f} | "
            f"PPO: {ppo_strength:.2f} | "
            f"Conviction: {conviction_alignment:.2f} | "
            f"Urgency: {urgency:.2f} | "
            f"ATR: {atr_pct:.3f}"
        ),
    }
