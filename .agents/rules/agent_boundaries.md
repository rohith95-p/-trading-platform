---
description: Strict boundaries on autonomous decision making for the trading bot.
---

# Agent Boundaries & Trading Logic

**CRITICAL RULE:**
The AI agent must **NEVER** unilaterally make important trading logic decisions or impose directional biases (such as forcing "BUY ONLY" or "SELL ONLY" modes) without the explicit, unequivocal instruction from the USER.

1. **Mathematical Objectivity:** The bot must trade strictly based on the mathematical indicators programmed into the strategy. 
2. **No Unilateral Filters:** Do not hardcode filters, disable strategies, or restrict trade directions based on your own macro market analysis unless the user explicitly requests you to build a filter.
3. **Always Ask:** If you believe a safety measure is necessary, you must present it as a question or proposal, and wait for the user's direct confirmation before modifying any live trading code.
