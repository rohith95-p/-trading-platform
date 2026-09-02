---
description: Strict boundaries on autonomous decision making for the trading bot.
---

# Agent Boundaries & Trading Logic

**CRITICAL RULE:**
The AI agent must **NEVER** unilaterally make important trading logic decisions or impose directional biases (such as forcing "BUY ONLY" or "SELL ONLY" modes) without the explicit, unequivocal instruction from the USER.

1. **Mathematical Objectivity:** The bot must trade strictly based on the mathematical indicators programmed into the strategy. 
2. **No Unilateral Filters:** Do not hardcode filters, disable strategies, or restrict trade directions based on your own macro market analysis unless the user explicitly requests you to build a filter.
3. **Always Ask:** If you believe a safety measure is necessary, you must present it as a question or proposal, and wait for the user's direct confirmation before modifying any live trading code.

## User-approved measures (do not treat these as violations of the above)

As of rohith-2 (2026-09-02/03), with the user's explicit approval and backtest
evidence:
- **D1 EMA20 bias gate** — trade only in the direction of the daily trend. It is
  a formula (`daily close vs daily EMA20`), not discretion, and the user
  approved keeping it after seeing the A/B result (`scripts/d1_gate_ab.py`:
  gate off drops PF 1.5 → 1.09).
- **0.01-lot hard lock + 0.02 exposure cap** — owner's directive.
- **Trailing stops and pyramiding disabled** — backtested net-negative
  (`scripts/live_config_ab.py`).

Changing any of these back also requires explicit user instruction.
