---
name: pandas-backtesting
description: Standardized workflow for writing custom Python backtesters using yfinance and pandas.
---

# Pandas Backtesting Workflow

When asked to backtest a strategy, follow this exact workflow:

1. **Data Fetching (yfinance)**
   - Use `yfinance` to pull OHLCV data.
   - For Gold, use `tickers='GC=F'` (Futures) with a fallback to `XAUUSD=X`.
   - **Timeframe Limits:** 
     - If the user requests < 60 days, use `interval='15m'`.
     - If the user requests > 60 days, you MUST use `interval='1h'` or `1d` due to API limits.

2. **Indicator Computation**
   - Calculate all technical indicators (EMA, MACD, RSI, ATR) vectorially on the DataFrame before the loop.
   - Always calculate ATR for dynamic Stop Loss sizing.

3. **Simulation Loop**
   - Use a row-by-row iteration (`for i in range(1, len(df)):`) to simulate live trading.
   - Maintain state variables: `in_trade`, `entry_price`, `stop_loss`, `take_profit`, `trade_type`, `capital`.
   - Apply strict Risk:Reward ratios (e.g. 1:1.5 or 1:2) and manage trade exits (hitting SL/TP) before checking for new entries.

4. **Reporting**
   - Always output Total Trades, Wins, Losses, Win Rate (%), and Net Profit ($).
