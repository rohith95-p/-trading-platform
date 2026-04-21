# Interface Versioning Strategy

## Overview

This document outlines the versioning strategy for the Unified Trading Intelligence Platform's core interfaces. The strategy ensures backward compatibility while allowing for evolution and improvement of the platform.

## Semantic Versioning

All interfaces follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes to interface contract
- **MINOR**: New optional methods or parameters (backward compatible)
- **PATCH**: Bug fixes or documentation updates (backward compatible)

## Interface Versions

### ExchangeConnector v1.0

**Release Date**: 2024-01-15

**Methods**:
- `connect()` - Authenticate with exchange
- `disconnect()` - Disconnect from exchange
- `place_order(order)` - Place order
- `cancel_order(order_id)` - Cancel order
- `get_positions()` - Get open positions
- `close_position(position_id)` - Close position
- `get_balance()` - Get account balance
- `get_market_data(symbol)` - Get market data

**Data Classes**:
- `Order` - Order specification
- `Trade` - Trade execution details
- `Position` - Open position
- `Balance` - Account balance

**Changelog**:
- v1.0: Initial release

**Planned Enhancements**:
- v1.1: Add `get_order_status(order_id)` method
- v1.1: Add `get_order_history()` method
- v1.2: Add `modify_order(order_id, new_order)` method
- v2.0: Add async streaming for real-time updates

### StrategyExecutor v1.0

**Release Date**: 2024-01-15

**Methods**:
- `execute(market_data)` - Execute strategy
- `validate_config(config)` - Validate configuration
- `get_required_indicators()` - Get required indicators

**Data Classes**:
- `Signal` - Trading signal
- `MarketData` - Market data

**Changelog**:
- v1.0: Initial release

**Planned Enhancements**:
- v1.1: Add `get_parameters()` method
- v1.1: Add `set_parameters(params)` method
- v1.2: Add `get_performance_metrics()` method
- v2.0: Add multi-timeframe support

### Backtester v1.0

**Release Date**: 2024-01-15

**Methods**:
- `backtest(strategy_name, historical_data, config)` - Run backtest
- `compute_metrics(trades)` - Compute metrics

**Data Classes**:
- `BacktestTrade` - Trade in backtest
- `BacktestMetrics` - Performance metrics
- `BacktestResult` - Complete backtest result

**Changelog**:
- v1.0: Initial release

**Planned Enhancements**:
- v1.1: Add `optimize_parameters(strategy, data, param_ranges)` method
- v1.2: Add `walk_forward_analysis(strategy, data, window_size)` method
- v1.2: Add `monte_carlo_simulation(trades, num_simulations)` method
- v2.0: Add support for multi-asset backtesting

### DRLAgent v1.0

**Release Date**: 2024-01-15

**Methods**:
- `predict(state)` - Predict action
- `train(experiences)` - Train agent
- `save_model(path)` - Save model
- `load_model(path)` - Load model

**Data Classes**:
- `State` - Agent state
- `Action` - Agent action
- `Experience` - Training experience

**Changelog**:
- v1.0: Initial release

**Planned Enhancements**:
- v1.1: Add `get_model_info()` method
- v1.1: Add `evaluate(test_data)` method
- v1.2: Add `export_model(format)` method
- v2.0: Add support for multi-agent coordination

## Backward Compatibility Policy

### Guarantees

1. **Method Signatures**: Existing method signatures will not change within a major version
2. **Return Types**: Return types will not change within a major version
3. **Data Classes**: Existing fields in data classes will not be removed within a major version
4. **Behavior**: Core behavior will remain consistent within a major version

### Exceptions

Breaking changes may be introduced in major versions when:
- Security vulnerabilities require immediate action
- Performance improvements require architectural changes
- Fundamental design flaws need correction

In such cases, a migration guide will be provided.

## Adding New Methods

When adding new methods to an interface:

1. **Minor Version Bump**: New methods are added as optional with default implementations
2. **Documentation**: New methods are documented with examples
3. **Tests**: New methods are tested with unit and integration tests
4. **Migration Guide**: A guide is provided for implementers to adopt new methods

### Example: Adding a New Method

```python
class ExchangeConnector(ABC):
    """ExchangeConnector v1.1"""
    
    # Existing methods...
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> str:
        """
        Get order status (NEW in v1.1)
        
        Args:
            order_id: ID of order
            
        Returns:
            Order status: 'pending', 'filled', 'cancelled', 'rejected'
        """
        pass
```

## Deprecation Policy

When a method needs to be deprecated:

1. **Mark as Deprecated**: Add `@deprecated` decorator
2. **Provide Alternative**: Document the replacement method
3. **Transition Period**: Maintain deprecated method for at least 2 minor versions
4. **Remove in Major Version**: Remove deprecated method in next major version

### Example: Deprecating a Method

```python
from functools import wraps

def deprecated(message: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import warnings
            warnings.warn(message, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator

class ExchangeConnector(ABC):
    @deprecated("Use get_order_status() instead")
    async def check_order(self, order_id: str) -> bool:
        """Check if order is filled (DEPRECATED in v1.1)"""
        pass
```

## Version Checking

Implementations can check interface versions at runtime:

```python
from src.interfaces import ExchangeConnector

# Check interface version
if hasattr(ExchangeConnector, 'INTERFACE_VERSION'):
    version = ExchangeConnector.INTERFACE_VERSION
    print(f"Using ExchangeConnector {version}")

# Check for specific method
if hasattr(ExchangeConnector, 'get_order_status'):
    print("v1.1+ features available")
```

## Migration Guide: v1.0 to v1.1

### ExchangeConnector

**New Methods**:
- `get_order_status(order_id)` - Get status of a specific order
- `get_order_history()` - Get history of all orders

**Migration Steps**:
1. No changes required for existing implementations
2. Optionally implement new methods for enhanced functionality
3. Update tests to cover new methods

### Example Migration

```python
# Old implementation (v1.0)
class MyExchange(ExchangeConnector):
    async def place_order(self, order):
        # Implementation
        pass

# Updated implementation (v1.1)
class MyExchange(ExchangeConnector):
    async def place_order(self, order):
        # Implementation
        pass
    
    async def get_order_status(self, order_id):
        # New implementation
        pass
    
    async def get_order_history(self):
        # New implementation
        pass
```

## Version Compatibility Matrix

| Component | v1.0 | v1.1 | v1.2 | v2.0 |
|-----------|------|------|------|------|
| ExchangeConnector | ✓ | ✓ | ✓ | ✗ |
| StrategyExecutor | ✓ | ✓ | ✓ | ✗ |
| Backtester | ✓ | ✓ | ✓ | ✗ |
| DRLAgent | ✓ | ✓ | ✓ | ✗ |

**Legend**:
- ✓ = Supported
- ✗ = Not supported (breaking changes)

## Release Schedule

- **v1.0**: January 2024 (Current)
- **v1.1**: April 2024 (Planned)
- **v1.2**: July 2024 (Planned)
- **v2.0**: January 2025 (Planned)

## Communication

Version changes are communicated through:

1. **Release Notes**: Detailed changelog in GitHub releases
2. **Migration Guides**: Step-by-step guides for major versions
3. **Documentation**: Updated interface documentation
4. **Deprecation Warnings**: Runtime warnings for deprecated methods
5. **Email Notifications**: For critical changes

## Support

For questions about interface versioning:

1. Check the [Interface Documentation](./INTERFACE_DOCUMENTATION.md)
2. Review the [Examples](../src/interfaces/examples.py)
3. Open an issue on GitHub
4. Contact the development team

## Conclusion

The interface versioning strategy ensures that the Unified Trading Intelligence Platform can evolve while maintaining backward compatibility. By following semantic versioning and a clear deprecation policy, we enable developers to build on the platform with confidence.
