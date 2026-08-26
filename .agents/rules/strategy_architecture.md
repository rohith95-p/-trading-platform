# Rule: Multi-Strategy Session Architecture

When building, modifying, or auditing trading strategies for the Ultra Core bot (especially for XAUUSD), you MUST adhere to the following architectural guardrails:

## 1. No Monolithic Strategies
Never attempt to build a single "holy grail" strategy that runs 24/5. 
Market regimes change drastically between sessions. Strategies must be explicitly assigned to their optimal sessions:
- **London Open (11:30 - 15:30 IST):** High volatility, liquidity sweeps, breakouts.
- **NY / Overlap (15:30 - 21:30 IST):** Trend continuations, heavy institutional volume.
- **Asia (Overnight):** Low volume, consolidation. Best for data collection or strictly mean-reverting tight-range bots.

## 2. The Orchestrator Pattern
All new strategies must be loaded into the list of active strategies inside `src.core.main_loop.TradingEngine`. 
- The orchestrator evaluates all strategies simultaneously.
- `ExecutionHandler` arbitrates the signal execution (enforcing the global max concurrent positions limit).
- `RiskManager` enforces the global daily drawdown cap (1.5x D1 ATR) across *all* strategies.

## 3. Mandatory Verification
If a strategy begins underperforming, do NOT try to "fix" it by loosening its indicators. Instead, backtest it across different sessions. If it only works in London, strictly gate its execution to London hours.
