# Kalshi Exchange Connector Documentation

## Overview

The Kalshi connector provides integration with Kalshi prediction markets through the ExchangeConnector interface. This connector operates in **paper trading mode only** and does not execute real trades.

## Features

- **Paper Trading Only**: All orders are simulated; no real money is at risk
- **Market Data Access**: Real-time market data, order books, and tickers
- **Order Simulation**: Simulates market and limit orders with realistic execution
- **Position Tracking**: Tracks paper positions and P&L
- **Rate Limiting**: Respects Kalshi API rate limits
- **Error Handling**: Comprehensive error handling with automatic retries

## Installation

The Kalshi connector is included in the unified trading platform. No additional installation is required.

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# Kalshi API Configuration
KALSHI_API_KEY=your_api_key_here
KALSHI_API_SECRET=your_api_secret_here
KALSHI_PAPER_TRADING=true  # Always true, enforced by connector
KALSHI_DEMO=true  # Use demo API endpoint
```

### API Keys

To obtain Kalshi API keys:

1. Sign up at [kalshi.com](https://kalshi.com)
2. Navigate to Settings > API
3. Generate API key and private key
4. Store securely in environment variables

**Note**: Even with real API keys, the connector will only execute paper trades.

## Usage

### Basic Example

```python
import asyncio
from src.exchanges.kalshi import KalshiConnector
from src.core.interfaces import Order, OrderSide, OrderType

async def main():
    # Initialize connector
    connector = KalshiConnector(
        api_key="your_api_key",
        private_key="your_private_key",
        demo=True,
        paper_trading=True,
    )
    
    # Connect to Kalshi
    await connector.connect()
    
    # Get available markets
    markets = await connector.get_markets()
    print(f"Found {len(markets)} markets")
    
    # Get market data
    ticker = await connector.get_ticker("PRES-2024")
    print(f"Current price: ${ticker.lastPrice:.2f}")
    
    # Place paper order
    order = Order(
        symbol="PRES-2024",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        size=10.0,
    )
    trade = await connector.place_order(order)
    print(f"Trade executed: {trade}")
    
    # Check positions
    positions = await connector.get_positions()
    for pos in positions:
        print(f"Position: {pos.symbol}, Size: {pos.size}, P&L: ${pos.unrealizedPnl:.2f}")
    
    # Check balance
    balance = await connector.get_balance()
    print(f"Balance: ${balance['USD']:.2f}")
    print(f"Total value: ${balance['total']:.2f}")
    
    # Disconnect
    await connector.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### Market Data

#### Get Markets

```python
markets = await connector.get_markets()
for market in markets:
    print(f"{market.symbol}: {market.baseAsset}/{market.quoteAsset}")
```

#### Get Order Book

```python
order_book = await connector.get_order_book("PRES-2024")
print(f"Best bid: ${order_book.bids[0][0]:.2f}")
print(f"Best ask: ${order_book.asks[0][0]:.2f}")
```

#### Get Ticker

```python
ticker = await connector.get_ticker("PRES-2024")
print(f"Last: ${ticker.lastPrice:.2f}")
print(f"Bid: ${ticker.bidPrice:.2f}")
print(f"Ask: ${ticker.askPrice:.2f}")
print(f"Volume: {ticker.volume24h}")
```

### Trading (Paper Mode)

#### Market Order

```python
order = Order(
    symbol="PRES-2024",
    side=OrderSide.BUY,
    type=OrderType.MARKET,
    size=10.0,
)
trade = await connector.place_order(order)
```

#### Limit Order

```python
order = Order(
    symbol="PRES-2024",
    side=OrderSide.BUY,
    type=OrderType.LIMIT,
    size=10.0,
    price=0.55,  # Price between 0 and 1
)
trade = await connector.place_order(order)
```

#### Sell Order

```python
order = Order(
    symbol="PRES-2024",
    side=OrderSide.SELL,
    type=OrderType.MARKET,
    size=5.0,
)
trade = await connector.place_order(order)
```

### Position Management

#### Get Single Position

```python
position = await connector.get_position("PRES-2024")
print(f"Size: {position.size}")
print(f"Avg Price: ${position.avgPrice:.2f}")
print(f"Current Price: ${position.currentPrice:.2f}")
print(f"Unrealized P&L: ${position.unrealizedPnl:.2f}")
```

#### Get All Positions

```python
positions = await connector.get_positions()
for pos in positions:
    pnl_pct = (pos.unrealizedPnl / (pos.avgPrice * pos.size)) * 100
    print(f"{pos.symbol}: {pos.size} @ ${pos.avgPrice:.2f} ({pnl_pct:+.2f}%)")
```

### Balance

```python
balance = await connector.get_balance()
print(f"Cash: ${balance['USD']:.2f}")
print(f"Positions Value: ${balance['positions_value']:.2f}")
print(f"Total: ${balance['total']:.2f}")
```

## API Reference

### KalshiConnector

#### Constructor

```python
KalshiConnector(
    api_key: Optional[str] = None,
    private_key: Optional[str] = None,
    demo: bool = True,
    paper_trading: bool = True,
)
```

**Parameters**:
- `api_key`: Kalshi API key (optional for public data)
- `private_key`: Kalshi private key (optional for public data)
- `demo`: Use demo API endpoint (default: True)
- `paper_trading`: Force paper trading mode (default: True, always enforced)

#### Methods

##### Connection Management

- `async connect() -> None`: Connect to Kalshi API
- `async disconnect() -> None`: Disconnect from Kalshi API
- `is_connected() -> bool`: Check connection status

##### Market Data

- `async get_markets() -> List[Market]`: Get all available markets
- `async get_order_book(symbol: str) -> OrderBook`: Get order book for symbol
- `async get_ticker(symbol: str) -> Ticker`: Get ticker for symbol

##### Trading

- `async place_order(order: Order) -> Trade`: Place paper order
- `async cancel_order(order_id: str) -> None`: Cancel order (no-op in paper mode)

##### Positions

- `async get_position(symbol: str) -> Position`: Get position for symbol
- `async get_positions() -> List[Position]`: Get all positions

##### Account

- `async get_balance() -> Dict[str, float]`: Get account balance

## Paper Trading Details

### Initial Balance

The connector starts with $10,000 in paper money.

### Order Execution

- **Market Orders**: Execute at current ask (buy) or bid (sell) price
- **Limit Orders**: Execute at specified limit price
- **Fees**: 1% fee applied to all trades

### Position Tracking

Positions are tracked in memory and updated with each trade:
- Average price calculated using weighted average
- Unrealized P&L updated based on current market price
- Realized P&L tracked when positions are closed

### Balance Management

Balance is updated with each trade:
- Buy orders: Deduct cost + fee from balance
- Sell orders: Add proceeds - fee to balance
- Total value = cash balance + positions value

## Rate Limiting

The connector implements rate limiting to respect Kalshi API limits:
- **Limit**: 10 requests per second (conservative)
- **Window**: 1 second
- **Behavior**: Requests are queued and throttled automatically

## Error Handling

### Automatic Retries

Failed requests are automatically retried:
- **Max Retries**: 3 attempts
- **Retry Delay**: Exponential backoff (1s, 2s, 4s)
- **Retry Conditions**: Timeouts and transient errors

### Error Types

- `ValueError`: Invalid order parameters
- `Exception`: API errors, connection failures
- `asyncio.TimeoutError`: Request timeout after retries

### Example Error Handling

```python
try:
    trade = await connector.place_order(order)
except ValueError as e:
    print(f"Invalid order: {e}")
except Exception as e:
    print(f"Order failed: {e}")
```

## Limitations

### Paper Trading Only

This connector **does not support real trading**. All orders are simulated.

### Market Types

Only prediction markets are supported. Kalshi does not offer:
- Spot trading
- Futures
- Options
- Margin trading

### Order Types

Supported:
- Market orders
- Limit orders

Not supported:
- Stop orders
- Stop-limit orders
- Trailing stops

### Price Range

Prediction market prices must be between 0 and 1 (representing probabilities).

## Testing

### Unit Tests

Run unit tests:

```bash
pytest tests/unit/test_kalshi_connector.py -v
```

### Integration Tests

Integration tests require Kalshi API access:

```bash
# Set environment variables
export KALSHI_API_KEY=your_key
export KALSHI_API_SECRET=your_secret
export KALSHI_DEMO=true

# Run integration tests
pytest tests/integration/test_kalshi_integration.py -v
```

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to Kalshi API

**Solutions**:
- Check internet connection
- Verify API keys are correct
- Ensure demo mode is enabled for testing
- Check Kalshi API status

### Order Failures

**Problem**: Orders fail to execute

**Solutions**:
- Check order parameters (size, price)
- Verify sufficient paper balance
- Ensure symbol exists
- Check order type is supported

### Rate Limiting

**Problem**: Requests are slow or timing out

**Solutions**:
- Reduce request frequency
- Use batch operations where possible
- Increase rate limit window if needed

## Best Practices

1. **Always use demo mode** for testing
2. **Check balance** before placing orders
3. **Validate symbols** before trading
4. **Handle errors** gracefully
5. **Monitor positions** regularly
6. **Use limit orders** for better price control
7. **Test thoroughly** before deploying

## Support

For issues or questions:
- Check the [Kalshi API documentation](https://kalshi.com/docs)
- Review the [ExchangeConnector interface](./INTERFACE_DOCUMENTATION.md)
- Open an issue on GitHub

## License

This connector is part of the Unified Trading Intelligence Platform and is licensed under the MIT License.
