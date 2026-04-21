# Core Interfaces Documentation

This document provides comprehensive documentation for the four core pluggable interfaces that enable zero-refactoring integration of future phases.

## Overview

The Unified Trading Intelligence Platform uses a pluggable architecture with four core interfaces:

1. **ExchangeConnector** (TypeScript) - Unified abstraction for exchange integrations
2. **StrategyExecutor** (TypeScript) - Pluggable trading strategies
3. **Backtester** (Python) - Pluggable backtesting engines
4. **DRLAgent** (Python) - Pluggable reinforcement learning agents

## 1. ExchangeConnector Interface

### Purpose

Provides a unified abstraction for all exchange integrations (CEX, DEX, prediction markets, stock brokers), enabling seamless addition of new exchanges without modifying existing code.

### Location

`src/core/interfaces/ExchangeConnector.ts`

### Type Definitions

```typescript
interface Market {
  symbol: string;              // Trading pair symbol (e.g., "BTC-USD")
  baseAsset: string;           // Base asset (e.g., "BTC")
  quoteAsset: string;          // Quote asset (e.g., "USD")
  minOrderSize: number;        // Minimum order size
  maxOrderSize: number;        // Maximum order size
  pricePrecision: number;      // Decimal places for price
  sizePrecision: number;       // Decimal places for size
}

interface OrderBook {
  symbol: string;              // Trading pair symbol
  bids: [price: number, size: number][]; // Buy orders
  asks: [price: number, size: number][]; // Sell orders
  timestamp: number;           // Unix timestamp in milliseconds
}

interface Ticker {
  symbol: string;              // Trading pair symbol
  lastPrice: number;           // Last traded price
  bidPrice: number;            // Current bid price
  askPrice: number;            // Current ask price
  volume24h: number;           // 24-hour trading volume
  timestamp: number;           // Unix timestamp in milliseconds
}

interface Order {
  symbol: string;              // Trading pair symbol
  side: 'buy' | 'sell';        // Order side
  type: 'market' | 'limit';    // Order type
  size: number;                // Order size
  price?: number;              // Price (required for limit orders)
  timeInForce?: 'GTC' | 'IOC' | 'FOK'; // Time in force
}

interface Trade {
  id: string;                  // Unique trade ID
  orderId: string;             // Associated order ID
  symbol: string;              // Trading pair symbol
  side: 'buy' | 'sell';        // Trade side
  price: number;               // Execution price
  size: number;                // Executed size
  fee: number;                 // Trading fee
  timestamp: number;           // Unix timestamp in milliseconds
}

interface Position {
  symbol: string;              // Trading pair symbol
  size: number;                // Position size
  avgPrice: number;            // Average entry price
  currentPrice: number;        // Current market price
  unrealizedPnl: number;       // Unrealized profit/loss
  realizedPnl: number;         // Realized profit/loss
}

interface ExchangeConnector {
  name: string;                // Connector name (e.g., "Kalshi")
  type: 'cex' | 'dex' | 'prediction' | 'stocks'; // Exchange type
  
  // Connection management
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  isConnected(): boolean;
  
  // Market data
  getMarkets(): Promise<Market[]>;
  getOrderBook(symbol: string): Promise<OrderBook>;
  getTicker(symbol: string): Promise<Ticker>;
  
  // Trading
  placeOrder(order: Order): Promise<Trade>;
  cancelOrder(orderId: string): Promise<void>;
  getPosition(symbol: string): Promise<Position>;
  getPositions(): Promise<Position[]>;
  
  // Account
  getBalance(): Promise<{ [asset: string]: number }>;
}
```

### Usage Example

```typescript
import { ExchangeConnector, Order } from './interfaces/ExchangeConnector';

// Implement the interface for a specific exchange
class KalshiConnector implements ExchangeConnector {
  name = 'Kalshi';
  type = 'prediction' as const;
  private connected = false;
  
  async connect(): Promise<void> {
    // Initialize connection to Kalshi API
    this.connected = true;
  }
  
  async disconnect(): Promise<void> {
    this.connected = false;
  }
  
  isConnected(): boolean {
    return this.connected;
  }
  
  async getMarkets(): Promise<Market[]> {
    // Fetch available markets from Kalshi
    return [];
  }
  
  async placeOrder(order: Order): Promise<Trade> {
    // Place order on Kalshi
    return {
      id: 'trade_123',
      orderId: 'order_123',
      symbol: order.symbol,
      side: order.side,
      price: order.price || 0,
      size: order.size,
      fee: 0.001,
      timestamp: Date.now()
    };
  }
  
  // ... implement other methods
}

// Use the connector
const connector = new KalshiConnector();
await connector.connect();
const markets = await connector.getMarkets();
const order = await connector.placeOrder({
  symbol: 'TRUMP-USD',
  side: 'buy',
  type: 'limit',
  size: 10,
  price: 0.50
});
```

### Phase 1 Implementations

- **KalshiConnector**: Prediction market connector for Kalshi
- **PolymarketConnector**: Prediction market connector for Polymarket
- **AlpacaConnector**: Stock broker connector for Alpaca (paper trading only)

### Future Implementations (Phase 1.5+)

- **BinanceConnector**: CEX connector for Binance
- **CoinbaseConnector**: CEX connector for Coinbase
- **HyperliquidConnector**: DEX connector for Hyperliquid
- **dYdXConnector**: DEX connector for dYdX

---

## 2. StrategyExecutor Interface

### Purpose

Enables pluggable trading strategies with consistent execution and backtesting APIs, allowing new strategies to be added without modifying existing code.

### Location

`src/core/interfaces/StrategyExecutor.ts`

### Type Definitions

```typescript
interface Signal {
  asset: string;               // Asset to trade (e.g., "BTC")
  direction: 'long' | 'short' | 'neutral'; // Trade direction
  confidence: number;          // Confidence score [0, 1]
  rationale: string;           // Explanation for the signal
  indicators?: { [key: string]: number }; // Supporting indicators
  timestamp: number;           // Unix timestamp in milliseconds
}

interface BacktestResult {
  totalReturn: number;         // Total return percentage
  sharpeRatio: number;         // Sharpe ratio
  maxDrawdown: number;         // Maximum drawdown percentage
  winRate: number;             // Win rate [0, 1]
  trades: Trade[];             // List of trades
  equityCurve: { timestamp: number; equity: number }[]; // Equity over time
}

interface RiskCheck {
  approved: boolean;           // Whether the order is approved
  reason?: string;             // Reason for rejection
  adjustedSize?: number;       // Adjusted order size if needed
}

interface HistoricalData {
  symbol: string;              // Trading pair symbol
  timeframe: string;           // Timeframe (e.g., "1h", "1d")
  data: Array<{
    timestamp: number;         // Unix timestamp
    open: number;              // Opening price
    high: number;              // Highest price
    low: number;               // Lowest price
    close: number;             // Closing price
    volume: number;            // Trading volume
  }>;
}

interface StrategyParams {
  [key: string]: any;          // Strategy-specific parameters
}

interface Portfolio {
  totalValue: number;          // Total portfolio value
  positions: { [symbol: string]: number }; // Position sizes
  cash: number;                // Available cash
}

interface StrategyExecutor {
  name: string;                // Strategy name
  type: 'directional' | 'market-making' | 'grid' | 'arbitrage'; // Strategy type
  
  // Execution
  execute(signal: Signal): Promise<Trade>;
  
  // Backtesting
  backtest(data: HistoricalData, params: StrategyParams): Promise<BacktestResult>;
  
  // Risk management
  checkRisk(order: Order, portfolio: Portfolio): Promise<RiskCheck>;
}
```

### Usage Example

```typescript
import { StrategyExecutor, Signal, BacktestResult } from './interfaces/StrategyExecutor';

// Implement a directional strategy
class DirectionalStrategy implements StrategyExecutor {
  name = 'Directional Strategy';
  type = 'directional' as const;
  
  async execute(signal: Signal): Promise<Trade> {
    // Execute trade based on signal
    return {
      id: 'trade_456',
      orderId: 'order_456',
      symbol: signal.asset,
      side: signal.direction === 'long' ? 'buy' : 'sell',
      price: 100,
      size: 10,
      fee: 0.001,
      timestamp: Date.now()
    };
  }
  
  async backtest(data: HistoricalData, params: StrategyParams): Promise<BacktestResult> {
    // Run backtest on historical data
    return {
      totalReturn: 0.25,
      sharpeRatio: 1.5,
      maxDrawdown: 0.10,
      winRate: 0.65,
      trades: [],
      equityCurve: []
    };
  }
  
  async checkRisk(order: Order, portfolio: Portfolio): Promise<RiskCheck> {
    // Check if order violates risk limits
    const positionSize = order.size * 100; // Assume price is 100
    const maxPosition = portfolio.totalValue * 0.10; // 10% limit
    
    if (positionSize > maxPosition) {
      return {
        approved: false,
        reason: 'Position size exceeds 10% limit',
        adjustedSize: maxPosition / 100
      };
    }
    
    return { approved: true };
  }
}

// Use the strategy
const strategy = new DirectionalStrategy();
const signal: Signal = {
  asset: 'BTC',
  direction: 'long',
  confidence: 0.85,
  rationale: 'Price above 200-day EMA',
  timestamp: Date.now()
};

const trade = await strategy.execute(signal);
```

### Phase 1 Implementations

- **DirectionalStrategy**: Basic long/short strategy based on signals

### Future Implementations (Phase 1.5+)

- **GridTradingStrategy**: Grid trading from Passivbot
- **MarketMakingStrategy**: Market making strategy
- **ArbitrageStrategy**: Arbitrage strategy

---

## 3. Backtester Interface

### Purpose

Enables pluggable backtesting engines with consistent APIs for strategy validation, allowing different backtesting implementations to be swapped without code changes.

### Location

`src/core/interfaces/backtester.py`

### Type Definitions

```python
@dataclass
class BacktestMetrics:
    """Performance metrics from a backtest run"""
    total_return: float        # Total return percentage
    sharpe_ratio: float        # Sharpe ratio
    max_drawdown: float        # Maximum drawdown percentage
    win_rate: float            # Win rate [0, 1]
    total_trades: int          # Total number of trades
    avg_trade_duration: float  # Average trade duration in days
    profit_factor: float       # Profit factor (gross profit / gross loss)

class Backtester(ABC):
    """Abstract base class for backtesting engines"""
    
    def __init__(self, backtester_type: str):
        """Initialize backtester"""
        self.type = backtester_type  # 'event-driven' or 'vectorized'
    
    @abstractmethod
    def run(self, strategy: Any, data: Any, params: Dict) -> Dict:
        """Run backtest and return results"""
        pass
    
    @abstractmethod
    def optimize(self, strategy: Any, data: Any, param_grid: Dict) -> Dict:
        """Optimize strategy parameters"""
        pass
    
    @abstractmethod
    def get_metrics(self, result: Dict) -> BacktestMetrics:
        """Compute performance metrics from backtest result"""
        pass
```

### Usage Example

```python
from src.core.interfaces.backtester import Backtester, BacktestMetrics
import pandas as pd

# Implement a vectorized backtester
class PandasBacktester(Backtester):
    def __init__(self):
        super().__init__('vectorized')
    
    def run(self, strategy, data, params):
        """Run backtest using pandas vectorized operations"""
        df = pd.DataFrame(data)
        
        # Generate signals
        df['signal'] = strategy.generate_signals(df, params)
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        
        # Calculate equity curve
        df['equity'] = (1 + df['strategy_returns']).cumprod() * 100000
        
        return {
            'equity_curve': df[['timestamp', 'equity']].to_dict('records'),
            'trades': [],
            'returns': df['strategy_returns'].tolist()
        }
    
    def optimize(self, strategy, data, param_grid):
        """Optimize strategy parameters"""
        best_params = None
        best_sharpe = -float('inf')
        
        for params in self._generate_param_combinations(param_grid):
            result = self.run(strategy, data, params)
            metrics = self.get_metrics(result)
            
            if metrics.sharpe_ratio > best_sharpe:
                best_sharpe = metrics.sharpe_ratio
                best_params = params
        
        return {'best_params': best_params, 'best_sharpe': best_sharpe}
    
    def get_metrics(self, result):
        """Compute performance metrics"""
        returns = result['returns']
        equity = result['equity_curve']
        
        total_return = (equity[-1]['equity'] - 100000) / 100000
        sharpe_ratio = self._compute_sharpe(returns)
        max_drawdown = self._compute_max_drawdown(equity)
        win_rate = sum(1 for r in returns if r > 0) / len(returns)
        
        return BacktestMetrics(
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=len(result['trades']),
            avg_trade_duration=0,
            profit_factor=0
        )
    
    def _compute_sharpe(self, returns):
        """Compute Sharpe ratio"""
        import numpy as np
        return np.mean(returns) / np.std(returns) * np.sqrt(252)
    
    def _compute_max_drawdown(self, equity_curve):
        """Compute maximum drawdown"""
        equities = [e['equity'] for e in equity_curve]
        peak = equities[0]
        max_dd = 0
        
        for equity in equities:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)
        
        return max_dd

# Use the backtester
backtester = PandasBacktester()
result = backtester.run(strategy, historical_data, {'period': 20})
metrics = backtester.get_metrics(result)
print(f"Sharpe Ratio: {metrics.sharpe_ratio}")
```

### Phase 1 Implementation

- **PandasBacktester**: Vectorized backtester using pandas (1-2 min for 1 year)

### Phase 1.5 Upgrade (drop-in replacement)

- **VectorBTBacktester**: 10-100x faster, same interface

---

## 4. DRLAgent Interface

### Purpose

Enables pluggable reinforcement learning agents with consistent prediction and training APIs, allowing different RL algorithms to be swapped without code changes.

### Location

`src/core/interfaces/drl_agent.py`

### Type Definitions

```python
class DRLAgent(ABC):
    """Abstract base class for Deep Reinforcement Learning agents"""
    
    def __init__(self, name: str, algorithm: str):
        """Initialize DRL agent"""
        self.name = name
        self.algorithm = algorithm  # 'PPO', 'A2C', 'SAC', etc.
    
    @abstractmethod
    def predict(self, state: np.ndarray) -> int:
        """Predict action from state
        
        Returns:
            action: 0 (hold), 1 (buy), 2 (sell)
        """
        pass
    
    @abstractmethod
    def train(self, env: Any, total_timesteps: int) -> None:
        """Train agent on environment"""
        pass
    
    @abstractmethod
    def save(self, path: str) -> None:
        """Save model weights"""
        pass
    
    @abstractmethod
    def load(self, path: str) -> None:
        """Load model weights"""
        pass
```

### Usage Example

```python
from src.core.interfaces.drl_agent import DRLAgent
import numpy as np

# Implement a PPO agent
class PPOAgent(DRLAgent):
    def __init__(self, name='PPO Agent'):
        super().__init__(name, 'PPO')
        self.model = None
    
    def predict(self, state: np.ndarray) -> int:
        """Predict action from state"""
        # Use trained model to predict action
        action, _ = self.model.predict(state, deterministic=True)
        return int(action)
    
    def train(self, env, total_timesteps: int) -> None:
        """Train agent on environment"""
        from stable_baselines3 import PPO
        
        self.model = PPO('MlpPolicy', env, verbose=1)
        self.model.learn(total_timesteps=total_timesteps)
    
    def save(self, path: str) -> None:
        """Save model weights"""
        self.model.save(path)
    
    def load(self, path: str) -> None:
        """Load model weights"""
        from stable_baselines3 import PPO
        self.model = PPO.load(path)

# Use the agent
agent = PPOAgent()

# Train on environment
agent.train(env, total_timesteps=100000)

# Make predictions
state = np.array([100, 50, 0.5])  # [price, volume, rsi]
action = agent.predict(state)  # 0=hold, 1=buy, 2=sell

# Save and load
agent.save('models/ppo_agent.zip')
agent.load('models/ppo_agent.zip')
```

### Phase 1 Implementation

- **PPOAgent**: Proximal Policy Optimization agent from Fiduciary Sentinel

### Phase 2 Enhancements

- **EnsembleDRLAgent**: Weighted voting across multiple agents (PPO, A2C, SAC)

---

## Integration Guidelines

### Adding a New Exchange Connector

1. Create a new class implementing `ExchangeConnector`
2. Implement all required methods
3. Register in exchange router
4. No changes needed to existing connectors

### Adding a New Strategy

1. Create a new class implementing `StrategyExecutor`
2. Implement all required methods
3. Register in strategy registry
4. No changes needed to existing strategies

### Adding a New Backtester

1. Create a new class extending `Backtester`
2. Implement all abstract methods
3. Update backtesting service to use new backtester
4. No changes needed to strategies or other components

### Adding a New DRL Algorithm

1. Create a new class extending `DRLAgent`
2. Implement all abstract methods
3. Update DRL service to use new agent
4. No changes needed to other components

---

## Testing

All interfaces include comprehensive unit tests and property-based tests to ensure correctness:

- **Unit Tests**: Test each interface implementation in isolation
- **Integration Tests**: Test interface interactions
- **Property-Based Tests**: Verify universal properties hold across all inputs

See `tests/unit/test_interfaces.py` and `tests/property/test_interfaces.py` for examples.
