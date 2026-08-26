---
name: mt5-trade-auditor
description: Fetches live MetaTrader 5 deals using MCP and formats them into a persistent markdown trade ledger.
---

# MT5 Trade Auditor

When asked to check, save, or audit live trades, follow these steps:
1. Use the `call_mcp_tool` to call the `get_deals` endpoint on the `metatrader` server.
2. Identify trades with a profit/loss (ignoring internal deposit/withdrawal actions where profit is very large like 10000 or negative large numbers, typically look for real market trades).
3. Create or update a `c:\projects\ultra_core\docs\trade_logs\LIVE_TRADE_HISTORY.md` file.
4. Format the trades into a clean markdown table showing: Date, Ticket, Direction, Asset, Entry Price, Close Price, and Profit.
