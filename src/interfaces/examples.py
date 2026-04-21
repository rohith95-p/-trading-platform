"""
Example implementations of core interfaces.
These serve as templates for implementing new components.
"""

from abc import ABC
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from .exchange_connector import ExchangeConnector, Order, Trade, Position, Balance
from .strategy_executor import StrategyExecutor, Signal, MarketData
from .backtester import Backtester, BacktestTrade, BacktestMetrics, BacktestResult
from .drl_agent import DRLAgent, State, Action, Experience


# ============================================================================
# Example ExchangeConnector Implementation
# ============================================================================

class MockExchangeConnector(ExchangeConnector):
    """
    Mock exchange connector for testing and development.
    
    This is a simple in-memory implementation that simulates exchange behavior
    without connecting to a real exchange.
    """
    
    def __init__(self, name: str = "mock", exchange_type: str = "cex"):
        super().__init__(name, exchange_type)
        self.connected = False
        self.positions: Dict[str, Position] = {}
        self.balance = Balance(total=100000.0, available=100000.0, used=0.0)
        self.trades: List[Trade] = []
        self.order_counter = 0
    
    async def connect(self) -> None:
        """Simulate connection to exchange"""
        await asyncio.sleep(0.1)  # Simulate network delay
        self.connected = True
    
    async def disconnect(self) -> None:
        """Simulate disconnection from exchange"""
        self.connected = False
    
    async def place_order(self, order: Order) -> Trade:
        """Simulate order placement"""
        if not self.connected:
            raise RuntimeError("Not connected to exchange")
        
        self.order_counter += 1
        trade = Trade(
            id=f"trade_{self.order_counter}",
            symbol=order.symbol,
            side=order.side,
            price=order.price or 100.0,
            size=order.size,
            fee=order.size * (order.price or 100.0) * 0.001,  # 0.1% fee
            timestamp=datetime.now()
        )
        
        self.trades.append(trade)
        
        # Update balance
        cost = trade.price * trade.size + trade.fee
        if order.side == "buy":
            self.balance.available -= cost
            self.balance.used += cost
        else:
            self.balance.available += cost
            self.balance.used -= cost
        
        return trade
    
    async def cancel_order(self, order_id: str) -> bool:
        """Simulate order cancellation"""
        return True
    
    async def get_positions(self) -> List[Position]:
        """Get all open positions"""
        return list(self.positions.values())
    
    async def close_position(self, position_id: str) -> Trade:
        """Close a position"""
        if position_id not in self.positions:
            raise ValueError(f"Position {position_id} not found")
        
        position = self.positions[position_id]
        trade = Trade(
            id=f"close_{position_id}",
            symbol=position.symbol,
            side="sell" if position.side == "long" else "buy",
            price=position.current_price,
            size=position.size,
            fee=position.size * position.current_price * 0.001,
            timestamp=datetime.now()
        )
        
        del self.positions[position_id]
        return trade
    
    async def get_balance(self) -> Balance:
        """Get account balance"""
        return self.balance
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data for symbol"""
        return {
            "symbol": symbol,
            "price": 100.0,
            "volume": 1000.0,
            "bid": 99.9,
            "ask": 100.1,
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# Example StrategyExecutor Implementation
# ============================================================================

class SimpleMovingAverageStrategy(StrategyExecutor):
    """
    Simple Moving Average (SMA) crossover strategy.
    
    Generates buy signals when fast MA crosses above slow MA,
    and sell signals when fast MA crosses below slow MA.
    """
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        super().__init__("sma_crossover", "directional")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.price_history: List[float] = []
    
    async def execute(self, market_data: MarketData) -> Optional[Signal]:
        """Execute SMA crossover strategy"""
        self.price_history.append(market_data.price)
        
        # Need enough history
        if len(self.price_history) < self.slow_period + 1:
            return None
        
        # Calculate moving averages
        fast_ma = sum(self.price_history[-self.fast_period:]) / self.fast_period
        slow_ma = sum(self.price_history[-self.slow_period:]) / self.slow_period
        
        prev_fast_ma = sum(self.price_history[-self.fast_period-1:-1]) / self.fast_period
        prev_slow_ma = sum(self.price_history[-self.slow_period-1:-1]) / self.slow_period
        
        # Check for crossover
        if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
            return Signal(
                asset=market_data.symbol.split("/")[0],
                direction="buy",
                confidence=0.7,
                rationale=f"Fast MA ({fast_ma:.2f}) crossed above Slow MA ({slow_ma:.2f})",
                timestamp=market_data.timestamp
            )
        elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
            return Signal(
                asset=market_data.symbol.split("/")[0],
                direction="sell",
                confidence=0.7,
                rationale=f"Fast MA ({fast_ma:.2f}) crossed below Slow MA ({slow_ma:.2f})",
                timestamp=market_data.timestamp
            )
        
        return None
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate strategy configuration"""
        if "fast_period" not in config or "slow_period" not in config:
            return False
        
        fast = config["fast_period"]
        slow = config["slow_period"]
        
        return isinstance(fast, int) and isinstance(slow, int) and 0 < fast < slow
    
    def get_required_indicators(self) -> list:
        """Get required indicators"""
        return ["price"]


# ============================================================================
# Example Backtester Implementation
# ============================================================================

class SimpleBacktester(Backtester):
    """
    Simple backtester for testing strategy performance.
    
    This is a basic implementation that doesn't account for slippage,
    commissions, or other real-world factors.
    """
    
    def __init__(self):
        super().__init__("simple")
    
    def backtest(
        self,
        strategy_name: str,
        historical_data: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> BacktestResult:
        """Run backtest"""
        if not historical_data:
            raise ValueError("No historical data provided")
        
        # Simple backtest: buy on first day, sell on last day
        start_price = historical_data[0]["close"]
        end_price = historical_data[-1]["close"]
        
        trade = BacktestTrade(
            entry_time=datetime.fromisoformat(historical_data[0]["timestamp"]),
            exit_time=datetime.fromisoformat(historical_data[-1]["timestamp"]),
            entry_price=start_price,
            exit_price=end_price,
            size=1.0,
            pnl=end_price - start_price,
            pnl_percent=(end_price - start_price) / start_price
        )
        
        metrics = self.compute_metrics([trade])
        
        # Generate equity curve
        equity_curve = [100.0]
        for i in range(1, len(historical_data)):
            price_change = (historical_data[i]["close"] - historical_data[i-1]["close"]) / historical_data[i-1]["close"]
            equity_curve.append(equity_curve[-1] * (1 + price_change))
        
        return BacktestResult(
            strategy_name=strategy_name,
            start_date=datetime.fromisoformat(historical_data[0]["timestamp"]),
            end_date=datetime.fromisoformat(historical_data[-1]["timestamp"]),
            metrics=metrics,
            trades=[trade],
            equity_curve=equity_curve
        )
    
    def compute_metrics(self, trades: List[BacktestTrade]) -> BacktestMetrics:
        """Compute performance metrics"""
        if not trades:
            return BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        pnls = [t.pnl for t in trades]
        winning = [t.pnl for t in trades if t.pnl > 0]
        losing = [t.pnl for t in trades if t.pnl < 0]
        
        total_pnl = sum(pnls)
        win_rate = len(winning) / len(trades) if trades else 0
        
        # Avoid division by zero
        if losing:
            profit_factor = sum(winning) / abs(sum(losing))
        else:
            profit_factor = float('inf') if winning else 0
        
        return BacktestMetrics(
            total_return=total_pnl,
            annual_return=total_pnl / len(trades) * 252 if trades else 0,
            sharpe_ratio=0.0,  # Simplified
            max_drawdown=0.0,  # Simplified
            win_rate=win_rate,
            profit_factor=profit_factor,
            trades_count=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            avg_win=sum(winning) / len(winning) if winning else 0,
            avg_loss=sum(losing) / len(losing) if losing else 0
        )


# ============================================================================
# Example DRLAgent Implementation
# ============================================================================

class RandomAgent(DRLAgent):
    """
    Random agent that takes random actions.
    
    This is a simple baseline agent for testing and comparison.
    In production, this would be replaced with a trained PPO or other RL agent.
    """
    
    def __init__(self):
        super().__init__("random_agent", "random")
        self.action_history: List[Action] = []
    
    async def predict(self, state: State) -> Action:
        """Predict random action"""
        import random
        
        action_types = ["buy", "sell", "hold"]
        action_type = random.choice(action_types)
        size = random.uniform(0.1, 1.0)
        confidence = random.uniform(0.5, 1.0)
        
        action = Action(
            action_type=action_type,
            size=size,
            confidence=confidence
        )
        
        self.action_history.append(action)
        return action
    
    def train(self, experiences: List[Experience]) -> Dict[str, float]:
        """Train agent (no-op for random agent)"""
        return {"loss": 0.0}
    
    def save_model(self, path: str) -> None:
        """Save model (no-op for random agent)"""
        pass
    
    def load_model(self, path: str) -> None:
        """Load model (no-op for random agent)"""
        pass


__all__ = [
    "MockExchangeConnector",
    "SimpleMovingAverageStrategy",
    "SimpleBacktester",
    "RandomAgent",
]
