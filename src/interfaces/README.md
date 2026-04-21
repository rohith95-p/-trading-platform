# Core Interfaces

This directory contains the core pluggable interfaces for the Unified Trading Intelligence Platform.

## Overview

The platform uses a pluggable architecture based on four core interfaces:

1. **ExchangeConnector** - Exchange integrations
2. **StrategyExecutor** - Trading strategy implementations
3. **Backtester** - Backtesting engines
4. **DRLAgent** - Deep reinforcement learning agents

## Quick Start

### Using the Registry

```python
from src.interfaces.registry import registry
from src.interfaces.examples import MockExchangeConnector

# Register a component
registry.register_exchange("mock", MockExchangeConnector)

# Get a registered component
ExchangeClass = registry.get_exchange("mock")
exchange = ExchangeClass()
```

### Implementing a New Component

```python
from src.interfaces import ExchangeConnector, Order, Trade, Position, Balance

class MyExchange(ExchangeConnector):
    def __init__(self):
        super().__init__("my_exchange", "cex")
    
    async def connect(self):
        # Implementation
        pass
    
    async def disconnect(self):
        # Implementation
        pass
    
    async def place_order(self, order: Order) -> Trade:
        # Implementation
        pass
    
    # ... implement other abstract methods
```

## File Structure

```
interfaces/
├── __init__.py              # Public API exports
├── exchange_connector.py    # ExchangeConnector interface
├── strategy_executor.py     # StrategyExecutor interface
├── backtester.py           # Backtester interface
├── drl_agent.py            # DRLAgent interface
├── registry.py             # Component registry
├── examples.py             # Example implementations
└── README.md               # This file
```

## Interfaces

### ExchangeConnector

Defines the contract for exchange integrations.

**Key Methods**:
- `connect()` - Authenticate with exchange
- `disconnect()` - Disconnect from exchange
- `place_order(order)` - Place order
- `cancel_order(order_id)` - Cancel order
- `get_positions()` - Get open positions
- `close_position(position_id)` - Close position
- `get_balance()` - Get account balance
- `get_market_data(symbol)` - Get market data

**Example**:
```python
from src.interfaces.examples import MockExchangeConnector

exchange = MockExchangeConnector()
await exchange.connect()
balance = await exchange.get_balance()
```

### StrategyExecutor

Defines the contract for trading strategy implementations.

**Key Methods**:
- `execute(market_data)` - Execute strategy and return signal
- `validate_config(config)` - Validate configuration
- `get_required_indicators()` - Get required indicators

**Example**:
```python
from src.interfaces.examples import SimpleMovingAverageStrategy

strategy = SimpleMovingAverageStrategy(fast_period=20, slow_period=50)
signal = await strategy.execute(market_data)
```

### Backtester

Defines the contract for backtesting engines.

**Key Methods**:
- `backtest(strategy_name, historical_data, config)` - Run backtest
- `compute_metrics(trades)` - Compute performance metrics

**Example**:
```python
from src.interfaces.examples import SimpleBacktester

backtester = SimpleBacktester()
result = backtester.backtest("my_strategy", historical_data, {})
```

### DRLAgent

Defines the contract for deep reinforcement learning agents.

**Key Methods**:
- `predict(state)` - Predict action given state
- `train(experiences)` - Train agent on experiences
- `save_model(path)` - Save model to disk
- `load_model(path)` - Load model from disk

**Example**:
```python
from src.interfaces.examples import RandomAgent

agent = RandomAgent()
action = await agent.predict(state)
```

## Data Classes

### ExchangeConnector Data Classes

- **Order** - Order specification
- **Trade** - Trade execution details
- **Position** - Open position
- **Balance** - Account balance

### StrategyExecutor Data Classes

- **Signal** - Trading signal
- **MarketData** - Market data

### Backtester Data Classes

- **BacktestTrade** - Trade in backtest
- **BacktestMetrics** - Performance metrics
- **BacktestResult** - Complete backtest result

### DRLAgent Data Classes

- **State** - Agent state
- **Action** - Agent action
- **Experience** - Training experience

## Registry

The `InterfaceRegistry` provides dynamic component loading and management.

### Methods

```python
# Register components
registry.register_exchange(name, connector_class)
registry.register_strategy(name, strategy_class)
registry.register_backtester(name, backtester_class)
registry.register_agent(name, agent_class)

# Get components
registry.get_exchange(name)
registry.get_strategy(name)
registry.get_backtester(name)
registry.get_agent(name)

# List components
registry.list_exchanges()
registry.list_strategies()
registry.list_backtestors()
registry.list_agents()
```

## Examples

The `examples.py` module provides reference implementations:

- **MockExchangeConnector** - Mock exchange for testing
- **SimpleMovingAverageStrategy** - SMA crossover strategy
- **SimpleBacktester** - Basic backtester
- **RandomAgent** - Random action agent

## Testing

Run interface tests:

```bash
# Test interface contracts
pytest tests/unit/test_interfaces.py -v

# Test example implementations
pytest tests/unit/test_interface_examples.py -v

# Test all interface tests
pytest tests/unit/test_interfaces.py tests/unit/test_interface_examples.py -v
```

## Documentation

- [Interface Documentation](../../docs/INTERFACE_DOCUMENTATION.md) - Comprehensive guide with examples
- [Interface Versioning](../../docs/INTERFACE_VERSIONING.md) - Versioning strategy and migration guides

## Best Practices

1. **Always inherit from the appropriate interface**
   ```python
   class MyExchange(ExchangeConnector):
       pass
   ```

2. **Implement all abstract methods**
   ```python
   @abstractmethod
   async def connect(self) -> None:
       pass
   ```

3. **Use type hints**
   ```python
   async def place_order(self, order: Order) -> Trade:
       pass
   ```

4. **Add comprehensive docstrings**
   ```python
   async def place_order(self, order: Order) -> Trade:
       """
       Place order and return trade
       
       Args:
           order: Order to place
           
       Returns:
           Trade object with execution details
       """
       pass
   ```

5. **Handle errors gracefully**
   ```python
   try:
       # Implementation
       pass
   except ConnectionError as e:
       logger.error(f"Connection failed: {e}")
       raise
   ```

6. **Write comprehensive tests**
   ```python
   def test_my_exchange_place_order():
       exchange = MyExchange()
       order = Order(...)
       trade = await exchange.place_order(order)
       assert trade.symbol == order.symbol
   ```

## Contributing

When adding new interfaces or modifying existing ones:

1. Update the interface definition
2. Update the documentation
3. Add example implementation
4. Add comprehensive tests
5. Update the versioning strategy if needed

## Support

For questions or issues:

1. Check the [Interface Documentation](../../docs/INTERFACE_DOCUMENTATION.md)
2. Review the [Examples](./examples.py)
3. Look at the [Tests](../../tests/unit/test_interfaces.py)
4. Open an issue on GitHub

## License

See LICENSE file in the project root.
