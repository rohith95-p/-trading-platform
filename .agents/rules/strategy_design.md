# Strategy Design Rule: Avoid Multi-Timeframe Over-Optimization

When designing or coding trading strategies, **do not over-filter**. Requiring more than 2 or 3 indicators to align perfectly across multiple timeframes (e.g., H1 bias + M15 crossover) destroys trade frequency and causes severe lagging entries. 

**Best Practice:** Use a maximum of **one** moving average for trend direction (e.g., 50 EMA) and **one** oscillator for entry timing (e.g., RSI pullbacks). Simpler strategies mathematically outperform over-optimized ones in fast intraday trading (especially on XAUUSD).
