# Core Interface Documentation

## Overview

The Unified Trading Intelligence Platform uses a pluggable architecture based on four core interfaces. This design enables seamless integration of new components without modifying existing code, supporting the platform's extensibility requirements.

## Core Interfaces

### 1. ExchangeConnector Interface

The `ExchangeConnector` interface defines the contract for exchange integrations, enabling the platform to support multiple trading venues.

#### Purpose
- Abstract exchange-specific implementation details
- Provide unified API for order placement, position management, and balance queries
- Support multiple exchange types (CEX, DEX, prediction markets)

#### Key Methods

```python
async def connect(self) -> None:
    """Authenticate with exchange"""
```
Establishes connection and authenticates with the exchange using stored API credentials.

```python
async def disconnect(self) -> None:
    """Disconnect from exchange"""
```
Gracefully closes connection and cleans up resources.

```python
async def place_order(self, order: Order) -> Trade:
    """Place order and return trade"""
```
Places an order on the exchange and returns execution details. Must complete within 1 second.

```python
async def cancel_order(self, order_id: str) -> bool:
    """Cancel order"""
```
Cancels a pending order. Returns True if successful.

```python
async def get_positions(self) -> List[Position]:
    """Get open positions"""
```
Returns all currently open positions on the exchange.

```python
async def close_position(self, position_id: str) -> Trade:
    """Close position"""
```
Closes a specific position and returns the closing trade details.

```python
async def get_balance(self) -> Balance:
    """Get account balance"""
```
Returns current account balance including total, available, and used amounts.

```python
async def get_market_data(self, symbol: str) -> Dict[str, Any]:
    """Get market data for symbol"""
```
Returns current market data including price, volume, bid/ask spreads.

#### Data Classes

**Order**
```python
@dataclass
class Order:
    symbol: str              # Trading pair (e.g., 'BTC/USD')
    side: str               # 'buy' or 'sell'
    type: str               # 'market', 'limit', 'stop'
    size: float             # Order size
    price: Optional[float]  # Price for limit orders
    stop_price: Optional[float]  # Stop price for stop orders
    leverage: Optional[float]    # Leverage multiplier
```

**Trade**
```python
@dataclass
class Trade:
    id: str                 # Trade ID
    symbol: str             # Trading pair
    side: str               # 'buy' or 'sell'
    price: float            # Execution price
    size: float             # Executed size
    fee: float              # Trading fee
    timestamp: datetime     # Execution time
```

**Position**
```python
@dataclass
class Position:
    id: str                 # Position ID
    symbol: str             # Trading pair
    side: str               # 'long' or 'short'
    size: float             # Position size
    entry_price: float      # Entry price
    current_price: float    # Current market price
    pnl: float              # Profit/loss in currency
    pnl_percent: float      # Profit/loss percentage
```

**Balance**
```python
@dataclass
class Balance:
    total: float            # Total account balance
    available: float        # Available for trading
    used: float             # Locked in positions/orders
```

#### Example Implementation

```python
from src.interfaces import ExchangeConnector, Order, Trade, Position, Balance

class AlpacaConnector(ExchangeConnector):
    """Alpaca stock broker connector"""
    
    def __init__(self, api_key: str, api_secret: str):
        super().__init__("alpaca", "cex")
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = None
    
    async def connect(self) -> None:
        """Connect to Alpaca API"""
        from alpaca_trade_api import REST
        self.client = REST(self.api_key, self.api_secret)
    
    async def disconnect(self) -> None:
        """Disconnect from Alpaca"""
        if self.client:
            self.client = None
    
    async def place_order(self, order: Order) -> Trade:
        """Place order on Alpaca"""
        response = self.client.submit_order(
            symbol=order.symbol,
            qty=order.size,
            side=order.side,
            type=order.type,
            time_in_force='day'
        )
        return Trade(
            id=response.id,
            symbol=order.symbol,
            side=order.side,
            price=float(response.filled_avg_price or 0),
            size=float(response.filled_qty or 0),
            fee=0.0,
            timestamp=datetime.now()
        )
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        try:
            self.client.cancel_order(order_id)
            return True
        except:
            return False
    
    async def get_positions(self) -> List[Position]:
        """Get open positions"""
        positions = self.client.get_positions()
        return [
            Position(
                id=p.asset_id,
                symbol=p.symbol,
                side='long' if float(p.qty) > 0 else 'short',
                size=abs(float(p.qty)),
                entry_price=float(p.avg_fill_price),
                current_price=float(p.current_price),
                pnl=float(p.unrealized_pl),
                pnl_percent=float(p.unrealized_plpc)
            )
            for p in positions
        ]
    
    async def close_position(self, position_id: str) -> Trade:
        """Close position"""
        # Implementation details...
        pass
    
    async def get_balance(self) -> Balance:
        """Get account balance"""
        account = self.client.get_account()
        return Balance(
            total=float(account.portfolio_value),
            available=float(account.buying_power),
            used=float(account.portfolio_value) - float(account.buying_power)
        )
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data"""
        # Implementation details...
        pass
```

---

### 2. StrategyExecutor Interface

The `StrategyExecutor` interface defines the contract for trading strategy implementations.

#### Purpose
- Standardize strategy execution interface
- Enable dynamic strategy loading and switching
- Support multiple strategy types (directional, grid, market-making)

#### Key Methods

```python
async def execute(self, market_data: MarketData) -> Optional[Signal]:
    """Execute strategy and return signal"""
```
Analyzes market data and returns a trading signal if conditions are met.

```python
def validate_config(self, config: Dict[str, Any]) -> bool:
    """Validate strategy configuration"""
```
Validates that the provided configuration is valid for this strategy.

```python
def get_required_indicators(self) -> list:
    """Get list of required indicators"""
```
Returns list of technical indicators required by this strategy.

#### Data Classes

**Signal**
```python
@dataclass
class Signal:
    asset: str              # Trading asset (e.g., 'BTC')
    direction: str          # 'buy', 'sell', or 'hold'
    confidence: float       # Confidence score [0, 1]
    rationale: str          # Explanation of signal
    timestamp: datetime     # Signal generation time
```

**MarketData**
```python
@dataclass
class MarketData:
    symbol: str             # Trading pair
    price: float            # Current price
    volume: float           # Current volume
    bid: float              # Current bid price
    ask: float              # Current ask price
    timestamp: datetime     # Data timestamp
    indicators: Dict[str, Any]  # Computed indicators
```

#### Example Implementation

```python
from src.interfaces import StrategyExecutor, Signal, MarketData

class RSIMomentumStrategy(StrategyExecutor):
    """RSI-based momentum strategy"""
    
    def __init__(self, rsi_threshold: float = 70.0):
        super().__init__("rsi_momentum", "directional")
        self.rsi_threshold = rsi_threshold
    
    async def execute(self, market_data: MarketData) -> Optional[Signal]:
        """Execute RSI momentum strategy"""
        rsi = market_data.indicators.get('rsi')
        if rsi is None:
            return None
        
        if rsi > self.rsi_threshold:
            return Signal(
                asset=market_data.symbol,
                direction='sell',
                confidence=min((rsi - self.rsi_threshold) / 30, 1.0),
                rationale=f"RSI {rsi:.1f} indicates overbought conditions",
                timestamp=market_data.timestamp
            )
        elif rsi < (100 - self.rsi_threshold):
            return Signal(
                asset=market_data.symbol,
                direction='buy',
                confidence=min((100 - self.rsi_threshold - rsi) / 30, 1.0),
                rationale=f"RSI {rsi:.1f} indicates oversold conditions",
                timestamp=market_data.timestamp
            )
        
        return None
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration"""
        if 'rsi_threshold' not in config:
            return False
        threshold = config['rsi_threshold']
        return 0 < threshold < 100
    
    def get_required_indicators(self) -> list:
        """Get required indicators"""
        return ['rsi']
```

---

### 3. Backtester Interface

The `Backtester` interface defines the contract for backtesting engines.

#### Purpose
- Standardize backtesting interface
- Support multiple backtesting implementations
- Compute consistent performance metrics

#### Key Methods

```python
def backtest(
    self,
    strategy_name: str,
    historical_data: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> BacktestResult:
    """Run backtest"""
```
Runs a backtest of a strategy on historical data and returns results.

```python
def compute_metrics(self, trades: List[BacktestTrade]) -> BacktestMetrics:
    """Compute performance metrics"""
```
Computes performance metrics from a list of trades.

#### Data Classes

**BacktestTrade**
```python
@dataclass
class BacktestTrade:
    entry_time: datetime    # Trade entry time
    exit_time: datetime     # Trade exit time
    entry_price: float      # Entry price
    exit_price: float       # Exit price
    size: float             # Trade size
    pnl: float              # Profit/loss
    pnl_percent: float      # Profit/loss percentage
```

**BacktestMetrics**
```python
@dataclass
class BacktestMetrics:
    total_return: float     # Total return percentage
    annual_return: float    # Annualized return
    sharpe_ratio: float     # Sharpe ratio
    max_drawdown: float     # Maximum drawdown
    win_rate: float         # Percentage of winning trades
    profit_factor: float    # Gross profit / gross loss
    trades_count: int       # Total number of trades
    winning_trades: int     # Number of winning trades
    losing_trades: int      # Number of losing trades
    avg_win: float          # Average winning trade
    avg_loss: float         # Average losing trade
```

**BacktestResult**
```python
@dataclass
class BacktestResult:
    strategy_name: str      # Strategy name
    start_date: datetime    # Backtest start date
    end_date: datetime      # Backtest end date
    metrics: BacktestMetrics    # Performance metrics
    trades: List[BacktestTrade] # All trades
    equity_curve: List[float]   # Equity curve over time
```

#### Example Implementation

```python
from src.interfaces import Backtester, BacktestTrade, BacktestMetrics, BacktestResult
import pandas as pd
import numpy as np

class PandasBacktester(Backtester):
    """Pandas-based vectorized backtester"""
    
    def __init__(self):
        super().__init__("pandas")
    
    def backtest(
        self,
        strategy_name: str,
        historical_data: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> BacktestResult:
        """Run backtest using pandas"""
        df = pd.DataFrame(historical_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Generate signals (simplified)
        df['signal'] = 0
        df.loc[df['close'] > df['close'].rolling(20).mean(), 'signal'] = 1
        df.loc[df['close'] < df['close'].rolling(20).mean(), 'signal'] = -1
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        
        # Extract trades
        trades = self._extract_trades(df)
        
        # Compute metrics
        metrics = self.compute_metrics(trades)
        
        # Compute equity curve
        equity_curve = (1 + df['strategy_returns']).cumprod().tolist()
        
        return BacktestResult(
            strategy_name=strategy_name,
            start_date=df.index[0],
            end_date=df.index[-1],
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve
        )
    
    def compute_metrics(self, trades: List[BacktestTrade]) -> BacktestMetrics:
        """Compute metrics from trades"""
        if not trades:
            return BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        pnls = [t.pnl for t in trades]
        winning = [t.pnl for t in trades if t.pnl > 0]
        losing = [t.pnl for t in trades if t.pnl < 0]
        
        total_return = sum(pnls)
        win_rate = len(winning) / len(trades) if trades else 0
        profit_factor = sum(winning) / abs(sum(losing)) if losing else 0
        
        return BacktestMetrics(
            total_return=total_return,
            annual_return=total_return / len(trades) * 252 if trades else 0,
            sharpe_ratio=np.mean(pnls) / np.std(pnls) * np.sqrt(252) if np.std(pnls) > 0 else 0,
            max_drawdown=self._compute_max_drawdown(pnls),
            win_rate=win_rate,
            profit_factor=profit_factor,
            trades_count=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            avg_win=np.mean(winning) if winning else 0,
            avg_loss=np.mean(losing) if losing else 0
        )
    
    def _extract_trades(self, df: pd.DataFrame) -> List[BacktestTrade]:
        """Extract trades from dataframe"""
        trades = []
        # Implementation details...
        return trades
    
    def _compute_max_drawdown(self, pnls: List[float]) -> float:
        """Compute maximum drawdown"""
        cumsum = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumsum)
        drawdown = (cumsum - running_max) / running_max
        return float(np.min(drawdown)) if len(drawdown) > 0 else 0
```

---

### 4. DRLAgent Interface

The `DRLAgent` interface defines the contract for deep reinforcement learning agents.

#### Purpose
- Standardize DRL agent interface
- Support multiple RL algorithms (PPO, A2C, SAC)
- Enable agent training and inference

#### Key Methods

```python
async def predict(self, state: State) -> Action:
    """Predict action given state"""
```
Predicts the next action based on current state. Must complete within 500ms.

```python
def train(self, experiences: List[Experience]) -> Dict[str, float]:
    """Train agent on experiences"""
```
Trains the agent on a batch of experiences and returns training metrics.

```python
def save_model(self, path: str) -> None:
    """Save model to disk"""
```
Saves the trained model to disk for later loading.

```python
def load_model(self, path: str) -> None:
    """Load model from disk"""
```
Loads a previously trained model from disk.

#### Data Classes

**State**
```python
@dataclass
class State:
    price: float            # Current price
    indicators: Dict[str, float]  # Technical indicators
    position: float         # Current position size
    balance: float          # Current balance
    timestamp: int          # Unix timestamp
```

**Action**
```python
@dataclass
class Action:
    action_type: str        # 'buy', 'sell', or 'hold'
    size: float             # Action size
    confidence: float       # Confidence score [0, 1]
```

**Experience**
```python
@dataclass
class Experience:
    state: State            # Initial state
    action: Action          # Action taken
    reward: float           # Reward received
    next_state: State       # Resulting state
    done: bool              # Episode termination flag
```

#### Example Implementation

```python
from src.interfaces import DRLAgent, State, Action, Experience
import numpy as np

class PPOAgent(DRLAgent):
    """PPO reinforcement learning agent"""
    
    def __init__(self, state_dim: int, action_dim: int):
        super().__init__("ppo_agent", "ppo")
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.model = None
    
    async def predict(self, state: State) -> Action:
        """Predict action using PPO policy"""
        state_vector = self._state_to_vector(state)
        
        # Get action from policy
        action_probs = self.model.predict(state_vector)
        action_idx = np.argmax(action_probs)
        
        action_types = ['buy', 'sell', 'hold']
        return Action(
            action_type=action_types[action_idx],
            size=float(action_probs[action_idx]),
            confidence=float(np.max(action_probs))
        )
    
    def train(self, experiences: List[Experience]) -> Dict[str, float]:
        """Train PPO agent"""
        states = np.array([self._state_to_vector(e.state) for e in experiences])
        actions = np.array([self._action_to_vector(e.action) for e in experiences])
        rewards = np.array([e.reward for e in experiences])
        
        # PPO training loop (simplified)
        loss = self.model.train(states, actions, rewards)
        
        return {'loss': float(loss)}
    
    def save_model(self, path: str) -> None:
        """Save model"""
        if self.model:
            self.model.save(path)
    
    def load_model(self, path: str) -> None:
        """Load model"""
        # Implementation details...
        pass
    
    def _state_to_vector(self, state: State) -> np.ndarray:
        """Convert state to vector"""
        indicators = list(state.indicators.values())
        return np.array([state.price, state.position, state.balance] + indicators)
    
    def _action_to_vector(self, action: Action) -> np.ndarray:
        """Convert action to vector"""
        action_map = {'buy': 0, 'sell': 1, 'hold': 2}
        return np.array([action_map[action.action_type], action.size])
```

---

## Interface Registry

The `InterfaceRegistry` provides dynamic component loading and management.

### Usage

```python
from src.interfaces.registry import registry
from src.exchanges import AlpacaConnector

# Register a new exchange connector
registry.register_exchange("alpaca", AlpacaConnector)

# Get registered connector
AlpacaClass = registry.get_exchange("alpaca")
connector = AlpacaClass(api_key, api_secret)

# List all registered exchanges
exchanges = registry.list_exchanges()
```

### Registry Methods

```python
def register_exchange(self, name: str, connector_class: Type[ExchangeConnector]) -> None:
    """Register exchange connector"""

def register_strategy(self, name: str, strategy_class: Type[StrategyExecutor]) -> None:
    """Register strategy executor"""

def register_backtester(self, name: str, backtester_class: Type[Backtester]) -> None:
    """Register backtester"""

def register_agent(self, name: str, agent_class: Type[DRLAgent]) -> None:
    """Register DRL agent"""

def get_exchange(self, name: str) -> Type[ExchangeConnector]:
    """Get exchange connector class"""

def get_strategy(self, name: str) -> Type[StrategyExecutor]:
    """Get strategy executor class"""

def get_backtester(self, name: str) -> Type[Backtester]:
    """Get backtester class"""

def get_agent(self, name: str) -> Type[DRLAgent]:
    """Get DRL agent class"""

def list_exchanges(self) -> list:
    """List all registered exchanges"""

def list_strategies(self) -> list:
    """List all registered strategies"""

def list_backtestors(self) -> list:
    """List all registered backtestors"""

def list_agents(self) -> list:
    """List all registered agents"""
```

---

## Interface Versioning Strategy

### Version Management

Interfaces follow semantic versioning to maintain backward compatibility:

- **Major Version**: Breaking changes to interface contract
- **Minor Version**: New optional methods or parameters
- **Patch Version**: Bug fixes or documentation updates

### Versioning Implementation

```python
class ExchangeConnector(ABC):
    """
    ExchangeConnector v1.0
    
    Changelog:
    - v1.0: Initial release with core methods
    - v1.1: Added get_market_data method
    """
    
    INTERFACE_VERSION = "1.0"
    INTERFACE_NAME = "ExchangeConnector"
```

### Backward Compatibility

- New methods are added as optional with default implementations
- Deprecated methods are marked with `@deprecated` decorator
- Version checking is performed at registration time

### Migration Path

When breaking changes are necessary:

1. Create new interface version (e.g., `ExchangeConnectorV2`)
2. Maintain old interface for backward compatibility
3. Provide migration guide for implementers
4. Deprecate old interface after transition period

---

## Best Practices

### 1. Implementation Guidelines

- Always inherit from the appropriate interface
- Implement all abstract methods
- Use type hints for all parameters and returns
- Add comprehensive docstrings
- Handle errors gracefully

### 2. Error Handling

```python
class MyExchange(ExchangeConnector):
    async def place_order(self, order: Order) -> Trade:
        try:
            # Implementation
            pass
        except ConnectionError as e:
            logger.error(f"Connection failed: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid order: {e}")
            raise
```

### 3. Testing

- Write unit tests for each implementation
- Test all abstract methods
- Test error conditions
- Verify performance requirements

### 4. Documentation

- Document all configuration parameters
- Provide usage examples
- Explain any limitations or constraints
- Include troubleshooting guide

---

## Conclusion

The pluggable interface architecture enables the Unified Trading Intelligence Platform to support multiple implementations of core components without code modification. By following these guidelines and best practices, developers can easily extend the platform with new exchanges, strategies, backtesting engines, and DRL agents.
