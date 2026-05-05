# Reference Implementations

Original source code extracted from reference repositories before deletion.
Each file is self-contained with full documentation of its source and purpose.

## Files

| File | Source Repo | What It Is | Used In Our Code |
|------|-------------|------------|-----------------|
| `ppo_regime_clustering.py` | Fiduciary-Sentinel-Core | Market regime detection via autoencoder + K-Means. Provides auxiliary loss for PPO training. | `src/drl/ppo_agent.py` (architecture) |
| `fractional_differentiation.py` | Fiduciary-Sentinel-Core | de Prado fracdiff — makes price series stationary while preserving memory. | `src/drl/training_env.py` (state preprocessing) |
| `signal_execution_priority.py` | Fiduciary-Sentinel-Core | Execution priority scoring — combines PPO strength, conviction, urgency, ATR into [0-1] score. | `src/simulation/consensus.py` (scoring pattern) |
| `confluence_filter.py` | Fiduciary-Sentinel-Core | 4-pillar trade authorization: Fear&Greed + Volume + SMC/FVG + Candlestick. | `src/drl/guardrails.py` (guardrail concept) |
| `walk_forward_backtester.py` | Fiduciary-Sentinel-Core | Walk-forward validation for PPO agents. More rigorous than simple train/test split. | `src/backtesting/pandas_backtester.py` (methodology) |
| `technical_indicators_pure_python.py` | hyperliquid-trading-agent | Pure Python indicators (EMA, RSI, MACD, ATR, BBands, ADX, OBV, VWAP, StochRSI). No dependencies. | `src/intelligence/indicators.py` (NumPy version) |
| `llm_trading_agent_prompts.py` | hyperliquid-trading-agent | Full LLM system prompt for quantitative trading decisions + tool definitions. | `src/simulation/engine.py` (agent prompts) |
| `binance_futures_api.py` | hyperliquid-trading-agent | Binance USD-M Futures testnet client using official SDK. | `src/exchanges/binance.py` (aiohttp version) |
| `fiduciary_sentinel_core.py` | Fiduciary-Sentinel-Core | FiduciarySentinel — constitutional guardrails with 6 checks (cooldown, hours, momentum, sentiment, volatility, drawdown, regime). | `src/drl/guardrails.py` |
| `fiduciary_rl_agent.py` | Fiduciary-Sentinel-Core | DualHeadPPO with auxiliary regime clustering loss. POLICY_KWARGS: [72,144,72,144] Tanh. | `src/drl/ppo_agent.py` |
| `fiduciary_trading_env.py` | Fiduciary-Sentinel-Core | Design notes for 21-dim obs space, circuit breaker, reward function. | `src/drl/training_env.py` |
| `hyperliquid_risk_manager.py` | hyperliquid-trading-agent | 7-check risk validation chain with daily drawdown tracking. | `src/risk/manager.py` |
| `polymarket_classifier.py` | polymarket-pipeline | Claude classification prompt (direction + materiality). | `src/intelligence/news_classifier.py` |
| `polymarket_news_stream.py` | polymarket-pipeline | Twitter/Telegram/RSS aggregator with deduplication. | `src/intelligence/news_stream.py` |

## What We Actually Built vs What We Borrowed

Our implementations are NOT copies — they are rewrites that:
1. Follow our unified interface contracts (ExchangeConnector, DRLAgent, etc.)
2. Use consistent patterns (aiohttp, FastAPI, Pydantic)
3. Add paper trading enforcement
4. Add property-based tests
5. Integrate with our risk management layer

The reference implementations here are preserved so you can:
- Understand the original design decisions
- Upgrade our implementations with more sophisticated algorithms
- Use the pure Python indicators as a fallback
- Implement walk-forward validation for the PPO agent
