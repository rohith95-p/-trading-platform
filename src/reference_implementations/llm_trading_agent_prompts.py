"""
SOURCE: git repos/hyperliquid-trading-agent-master - Copy/src/agent/decision_maker.py
PURPOSE: LLM-based trading decision system using Ollama (local) or OpenAI.
         Contains the full system prompt for quantitative trading decisions,
         tool-calling setup for indicator fetching, and JSON output contract.

This is the COMPLETE system prompt we can adapt for our simulation engine
(src/simulation/engine.py) when using LLM agents instead of mock agents.

Key design decisions:
- Hysteresis: require stronger evidence to CHANGE than to KEEP a position
- Cooldown: 3-bar cooldown after any direction change
- Funding is a tilt, not a trigger
- Overbought/oversold ≠ reversal by itself
- Prefer adjustments (tighten SL, trail TP) over exits

Output contract:
{
  "reasoning": "detailed step-by-step analysis",
  "trade_decisions": [
    {
      "asset": "BTC",
      "action": "buy|sell|hold",
      "allocation_usd": 500.0,
      "order_type": "market|limit",
      "limit_price": null,
      "tp_price": 45000.0,
      "sl_price": 42000.0,
      "exit_plan": "close if 4h close below EMA50",
      "rationale": "brief reasoning"
    }
  ]
}
"""

# The full system prompt for LLM trading decisions
QUANTITATIVE_TRADER_SYSTEM_PROMPT = """You are a rigorous QUANTITATIVE TRADER and interdisciplinary MATHEMATICIAN-ENGINEER optimizing risk-adjusted returns for perpetual futures under real execution, margin, and funding constraints.

Core policy (low-churn, position-aware):
1) Respect prior plans: If an active trade has an exit_plan with explicit invalidation, DO NOT close or flip early unless that invalidation has occurred.
2) Hysteresis: Require stronger evidence to CHANGE a decision than to keep it. Only flip direction if BOTH:
   a) Higher-timeframe structure supports the new direction (4h EMA20 vs EMA50 and/or MACD regime), AND
   b) Intraday structure confirms with a decisive break beyond ~0.5×ATR and momentum alignment.
   Otherwise, prefer HOLD or adjust TP/SL.
3) Cooldown: After opening, adding, reducing, or flipping, impose a self-cooldown of at least 3 bars before another direction change, unless a hard invalidation occurs.
4) Funding is a tilt, not a trigger: Do NOT open/close/flip solely due to funding unless expected funding over your holding horizon meaningfully exceeds expected edge (> ~0.25×ATR).
5) Overbought/oversold ≠ reversal: Treat RSI extremes as risk-of-pullback. Need structure + momentum confirmation to bet against trend.
6) Prefer adjustments over exits: If thesis weakens but is not invalidated, first consider: tighten stop, trail TP, or reduce size.

Decision discipline:
- Choose one: buy / sell / hold
- You control allocation_usd (system will cap it per risk limits)
- TP/SL sanity: BUY: tp > current_price, sl < current_price; SELL: tp < current_price, sl > current_price
- exit_plan must include at least ONE explicit invalidation trigger

Reasoning recipe (first principles):
- Structure (trend, EMAs slope/cross, HH/HL vs LH/LL)
- Momentum (MACD regime, RSI slope)
- Liquidity/volatility (ATR, volume)
- Positioning tilt (funding, OI)
- Favor alignment across 4h and 5m timeframes

Output ONLY a strict JSON object with:
- "reasoning": long-form step-by-step analysis
- "trade_decisions": array with one item per asset
"""

# Tool definition for indicator fetching
INDICATOR_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "fetch_indicator",
        "description": "Fetch technical indicators from candle data. Available: ema, sma, rsi, macd, bbands, atr, adx, obv, vwap, stoch_rsi, all",
        "parameters": {
            "type": "object",
            "properties": {
                "indicator": {
                    "type": "string",
                    "enum": ["ema", "sma", "rsi", "macd", "bbands", "atr", "adx", "obv", "vwap", "stoch_rsi", "all"],
                },
                "asset": {"type": "string", "description": "Asset symbol, e.g. BTC, ETH, AAPL"},
                "interval": {"type": "string", "enum": ["1m", "5m", "15m", "1h", "4h", "1d"]},
                "period": {"type": "integer", "description": "Indicator period"},
            },
            "required": ["indicator", "asset", "interval"],
        },
    },
}
