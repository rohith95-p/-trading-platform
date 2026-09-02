# Rule: Multi-Strategy Session Architecture

Architectural guardrails for building, modifying, or auditing XAUUSD strategies
for the Ultra Core bot.

## 1. No monolithic strategies

Never build a single strategy that runs 24/5. Market regimes differ by session.
Each strategy is assigned to its session. The live portfolio (`portfolio_v4`):

| Leg | Session (IST) | Family |
|---|---|---|
| SQUEEZE_ASIA | 02:30–11:30 | volatility breakout |
| EMASTACK_LONDON_TIGHT | 11:30–15:30 | trend continuation |
| FVG_NY_TIGHT | 17:30–21:30 | structure / imbalance |
| RANGEREJECTION_NY_TIGHT | 17:30–21:30 | mean reversion |

## 2. The orchestrator pattern

- New strategies go in the `PORTFOLIO_V4` list in
  `src/strategies/portfolio_v4.py`, which `src.core.main_loop.run()` loads.
  (There is no `TradingEngine` class — the loop is `run()` with a `strategies`
  list.)
- `main_loop` evaluates all strategies each 60s scan, gated by session mask and
  the D1 EMA20 bias.
- `ExecutionHandler` arbitrates execution: `FIXED_LOT_SIZE` 0.01, `MAX_TOTAL_VOLUME`
  0.02, max 2 concurrent positions.
- `RiskManager.check_daily_drawdown` enforces the global daily loss cap:
  **6% of balance** (`DAILY_LOSS_LIMIT_PCT`), realised + floating. (The old
  "1.5x D1 ATR" cap was dimensionally broken — CRIT-4 — and is gone.)
- Positions run to their per-leg fixed SL/TP. **No trailing, no pyramiding** —
  both backtested net-negative (`scripts/live_config_ab.py`).

## 3. Mandatory verification

If a strategy underperforms, do NOT loosen its indicators. Backtest it across
sessions on the real engine (`src/backtesting/engine.py`, see rule
`strategy_design.md` and the `pandas-backtesting` skill). If it only works in
one session, gate it there. Every change is a hypothesis logged in
`docs/research/RESEARCH_LEDGER.md`.
