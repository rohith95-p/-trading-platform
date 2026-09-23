---
name: agy-bot-health-check
description: "Perform a live health check on the production ultra_core trading bot using MT5 integrations and log audits."
---

# Live Bot Health Check Skill

## Context
When running an automated algorithmic trading bot in a production live-money environment, regular dev-ops audits are critical. This skill provides a standardized workflow for you (the agent) to verify the live bot's health without risking interference in its execution.

## Instructions
When the user asks you to "audit the bot", "check on the bot", or run a health check, follow these exact steps:

### 1. Verify MT5 Account Health (Using MCP)
1. Use the `call_mcp_tool` with the `metatrader` server to run `get_account_info`.
2. Extract the current account `balance`, `equity`, and `margin_free`.
3. Read `src/core/risk_rules.py` and extract the `HARD_KILL_BALANCE` variable.
4. **Validation:** If the current balance is at or below the hard kill balance, immediately alert the user with a massive `[!CAUTION]` block. 

### 2. Verify Open Positions (Using MCP)
1. Use the `metatrader` server to run `get_all_positions`.
2. Extract the active positions and their ticket numbers, symbols, volumes, and P&L.
3. Check `src/core/risk_rules.py` for the `max_exposure` or concurrent trades limit.
4. **Validation:** Ensure the bot has not exceeded its maximum allowed concurrent trades. If it has, alert the user immediately.

### 3. Audit Local Logs
1. Open the repository's main execution log (usually `docs/trade_logs/LIVE_TRADE_HISTORY.md` or a standard `.log` file if specified).
2. Look for any crash exceptions, traceback errors, or unexpected "pause" messages from the streak-breaker logic.

### 4. Present the Report
Create an artifact named `bot_health_report.md` summarizing the findings.
Include:
- **Timestamp of Audit**
- **Financial Status:** Current Balance, Hard Kill Threshold, Distance to Kill.
- **Position Status:** List of open trades and current aggregate exposure.
- **Log Status:** Any errors or warnings found in the local logs.
- **Final Verdict:** "🟢 HEALTHY", "🟡 WARNING", or "🔴 CRITICAL FAILURE".
