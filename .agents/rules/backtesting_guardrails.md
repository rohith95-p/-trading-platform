---
description: Strict requirements for evaluating and backtesting trading strategies.
---

# Backtesting & Validation Guardrails

**CRITICAL RULE:**
Never evaluate or validate strategies using isolated scratch scripts, manual signal counting, or "fast vectorized" approximations that bypass the official execution engine. 

1. **Always Use BacktestEngine:** Any backtest, parameter sweep, or performance validation must be executed through the official `src.backtesting.engine.BacktestEngine`.
2. **Why:** The official engine strictly enforces M1 intrabar collision logic (checking stops first), `edge_trigger` state deduplication, and daily portfolio caps. Bypassing the engine drops these constraints and artificially inflates Win Rate and Profit Factor (lookahead bias).
3. **How:** Use or adapt the wrapper suites in `scripts/validation/part1_suite.py` to run permutations through the engine. Do not write custom signal iterators.
