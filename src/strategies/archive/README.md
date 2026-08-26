# Archived Strategies

These strategies were part of Ultra Core v1/v2 and have been **retired** from active trading.
They are preserved here for reference and potential future reactivation.

## Strategies

| File | Description | Status |
|---|---|---|
| `keltner_breakout.py` | ATR Keltner Channel breakout (M15) | Archived |
| `macd_cross.py` | MACD crossover + EMA200 trend filter | Archived |
| `asian_breakout.py` | Asian session range breakout | Archived |
| `pdhl_breakout.py` | Previous Day High/Low breakout | Archived |
| `london_bot.py` | Original monolithic bot (v1) | Archived |

## Why Archived?

The forensic audit (Aug 25, 2026) showed that:
1. Multiple simultaneous strategies caused over-trading (5 trades in 10 minutes).
2. The MorningMomentum strategy alone has an **83% backtest win rate** with strict 4-condition filtering.
3. The user explicitly requested: "ONLY keep the strict MorningMomentum strategy."

## How to Reactivate

To bring any strategy back, copy it from this folder to `src/strategies/` and register it in `main_loop.py`.
