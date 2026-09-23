# Alpha Scraping Pipeline (Future Phase)

## Concept
Instead of manually theorizing and coding individual strategy mechanics from scratch, we can leverage the open-source quantitative community (TradingView, QuantConnect, GitHub, r/algotrading). 

By scraping the logic of popular indicators and strategies, we can rapidly expand our candidate pool from ~100 strategies to thousands.

## Execution Flow
1. **Sourcing**: Identify open-source logic (e.g., advanced Order Block finders, VWAP deviations, MACD divergence matrices).
2. **Translation**: Port the entry/exit logic into our Python `BaseStrategy` format, storing them in `src/research/candidates.py` or a new dedicated `scraped_candidates.py`.
3. **The Graveyard Test (Filtration)**: 
   - 99% of internet strategies are curve-fit and fail in actual tick-by-tick execution environments because they ignore slippage, spread variance, and rollover swaps.
   - We feed the translated strategies into our 22-year `BacktestEngine` (which mathematically simulates these brutal realities).
   - The engine instantly identifies and discards the garbage. The 1% that survive this gauntlet become our primary alpha generators.

## Scaling
Once strategies survive the Graveyard Test, they are submitted to the Institutional Walk-Forward Optimization (WFO) grid (detailed in `institutional_scale_testing.md`) to finalize their absolute optimal SL/TP geometries before live deployment on the $100 prop firm accounts.
