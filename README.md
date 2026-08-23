# UltraCore Trading Platform - Headless Signal Generator

This is a lightweight, headless backend for generating trading signals for MetaTrader 5 (MT5). 
It relies on FastAPI for the web server, Pandas and NumPy for computation, and custom logic for indicators and Kelly criterion sizing.

## API Endpoint

**POST `/analyze`**

Accepts OHLCV data and returns a trading signal.

### Request Body Example:
```json
{
  "symbol": "EURUSD",
  "history": [
    {
      "timestamp": "2026-08-22T10:00:00Z",
      "open": 1.1000,
      "high": 1.1050,
      "low": 1.0950,
      "close": 1.1020,
      "volume": 1000
    }
  ],
  "balance": 10000.0
}
```
*(Note: At least 200 historical candles are required to compute the EMA200).*

### Response Example:
```json
{
  "action": "BUY",
  "size": 1.25,
  "confidence": 0.8,
  "reason": "Oversold in an uptrend",
  "stop_loss": 1.0900,
  "take_profit": 1.1200
}
```

## Running the Server

1. Create a virtual environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the FastAPI server:
   ```bash
   uvicorn src.main:app --reload
   ```
