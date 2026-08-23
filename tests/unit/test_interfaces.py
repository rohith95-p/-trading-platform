"""Unit tests for interfaces"""

import pytest
from datetime import datetime
from src.interfaces import (
    ExchangeConnector, StrategyExecutor, Backtester, DRLAgent,
    Order, Trade, Position, Balance,
    Signal, MarketData,
    BacktestTrade, BacktestMetrics, BacktestResult,
    State, Action, Experience
)
from src.interfaces.registry import registry


# ============================================================================
# ExchangeConnector Tests
# ============================================================================

def test_exchange_connector_is_abstract():
    """Test that ExchangeConnector is abstract"""
    with pytest.raises(TypeError):
        ExchangeConnector("test", "cex")


def test_exchange_connector_order_dataclass():
    """Test Order dataclass"""
    order = Order(
        symbol="BTC/USD",
        side="buy",
        type="limit",
        size=1.0,
        price=50000.0
    )
    assert order.symbol == "BTC/USD"
    assert order.side == "buy"
    assert order.type == "limit"
    assert order.size == 1.0
    assert order.price == 50000.0


def test_exchange_connector_trade_dataclass():
    """Test Trade dataclass"""
    now = datetime.now()
    trade = Trade(
        id="trade_123",
        symbol="BTC/USD",
        side="buy",
        price=50000.0,
        size=1.0,
        fee=10.0,
        timestamp=now
    )
    assert trade.id == "trade_123"
    assert trade.symbol == "BTC/USD"
    assert trade.side == "buy"
    assert trade.price == 50000.0
    assert trade.size == 1.0
    assert trade.fee == 10.0
    assert trade.timestamp == now


def test_exchange_connector_position_dataclass():
    """Test Position dataclass"""
    position = Position(
        id="pos_123",
        symbol="BTC/USD",
        side="long",
        size=1.0,
        entry_price=50000.0,
        current_price=51000.0,
        pnl=1000.0,
        pnl_percent=2.0
    )
    assert position.id == "pos_123"
    assert position.symbol == "BTC/USD"
    assert position.side == "long"
    assert position.size == 1.0
    assert position.pnl == 1000.0
    assert position.pnl_percent == 2.0


def test_exchange_connector_balance_dataclass():
    """Test Balance dataclass"""
    balance = Balance(
        total=100000.0,
        available=80000.0,
        used=20000.0
    )
    assert balance.total == 100000.0
    assert balance.available == 80000.0
    assert balance.used == 20000.0


def test_exchange_connector_mock_implementation():
    """Test mock ExchangeConnector implementation"""
    class MockExchange(ExchangeConnector):
        async def connect(self): pass
        async def disconnect(self): pass
        async def place_order(self, order): 
            return Trade("1", order.symbol, order.side, 100.0, order.size, 1.0, datetime.now())
        async def cancel_order(self, order_id): 
            return True
        async def get_positions(self): 
            return []
        async def close_position(self, position_id): 
            return Trade("1", "BTC/USD", "sell", 100.0, 1.0, 1.0, datetime.now())
        async def get_balance(self): 
            return Balance(100000.0, 80000.0, 20000.0)
        async def get_market_data(self, symbol): 
            return {"price": 100.0, "volume": 1000.0}
    
    exchange = MockExchange("mock", "cex")
    assert exchange.name == "mock"
    assert exchange.exchange_type == "cex"


# ============================================================================
# StrategyExecutor Tests
# ============================================================================

def test_strategy_executor_is_abstract():
    """Test that StrategyExecutor is abstract"""
    with pytest.raises(TypeError):
        StrategyExecutor("test", "directional")


def test_strategy_executor_signal_dataclass():
    """Test Signal dataclass"""
    now = datetime.now()
    signal = Signal(
        asset="BTC",
        direction="buy",
        confidence=0.85,
        rationale="Price above 50-day MA",
        timestamp=now
    )
    assert signal.asset == "BTC"
    assert signal.direction == "buy"
    assert signal.confidence == 0.85
    assert signal.rationale == "Price above 50-day MA"
    assert signal.timestamp == now


def test_strategy_executor_market_data_dataclass():
    """Test MarketData dataclass"""
    now = datetime.now()
    market_data = MarketData(
        symbol="BTC/USD",
        price=50000.0,
        volume=1000.0,
        bid=49999.0,
        ask=50001.0,
        timestamp=now,
        indicators={"rsi": 65.0, "macd": 100.0}
    )
    assert market_data.symbol == "BTC/USD"
    assert market_data.price == 50000.0
    assert market_data.volume == 1000.0
    assert market_data.bid == 49999.0
    assert market_data.ask == 50001.0
    assert market_data.indicators["rsi"] == 65.0


def test_strategy_executor_mock_implementation():
    """Test mock StrategyExecutor implementation"""
    class MockStrategy(StrategyExecutor):
        async def execute(self, market_data):
            if market_data.price > 50000:
                return Signal("BTC", "buy", 0.8, "Price high", datetime.now())
            return None
        
        def validate_config(self, config):
            return "threshold" in config
        
        def get_required_indicators(self):
            return ["rsi", "macd"]
    
    strategy = MockStrategy("mock_strategy", "directional")
    assert strategy.name == "mock_strategy"
    assert strategy.strategy_type == "directional"
    assert strategy.get_required_indicators() == ["rsi", "macd"]
    assert strategy.validate_config({"threshold": 50000})
    assert not strategy.validate_config({})


# ============================================================================
# Backtester Tests
# ============================================================================

def test_backtester_is_abstract():
    """Test that Backtester is abstract"""
    with pytest.raises(TypeError):
        Backtester("test")


def test_backtester_trade_dataclass():
    """Test BacktestTrade dataclass"""
    entry_time = datetime(2024, 1, 1, 10, 0, 0)
    exit_time = datetime(2024, 1, 1, 11, 0, 0)
    trade = BacktestTrade(
        entry_time=entry_time,
        exit_time=exit_time,
        entry_price=50000.0,
        exit_price=51000.0,
        size=1.0,
        pnl=1000.0,
        pnl_percent=2.0
    )
    assert trade.entry_price == 50000.0
    assert trade.exit_price == 51000.0
    assert trade.pnl == 1000.0
    assert trade.pnl_percent == 2.0


def test_backtester_metrics_dataclass():
    """Test BacktestMetrics dataclass"""
    metrics = BacktestMetrics(
        total_return=0.15,
        annual_return=0.20,
        sharpe_ratio=1.5,
        max_drawdown=-0.10,
        win_rate=0.60,
        profit_factor=2.0,
        trades_count=100,
        winning_trades=60,
        losing_trades=40,
        avg_win=500.0,
        avg_loss=-250.0
    )
    assert metrics.total_return == 0.15
    assert metrics.sharpe_ratio == 1.5
    assert metrics.max_drawdown == -0.10
    assert metrics.win_rate == 0.60
    assert metrics.profit_factor == 2.0


def test_backtester_result_dataclass():
    """Test BacktestResult dataclass"""
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    metrics = BacktestMetrics(0.15, 0.20, 1.5, -0.10, 0.60, 2.0, 100, 60, 40, 500.0, -250.0)
    trades = []
    equity_curve = [100.0, 101.0, 102.0]
    
    result = BacktestResult(
        strategy_name="test_strategy",
        start_date=start_date,
        end_date=end_date,
        metrics=metrics,
        trades=trades,
        equity_curve=equity_curve
    )
    assert result.strategy_name == "test_strategy"
    assert result.start_date == start_date
    assert result.end_date == end_date
    assert result.metrics.total_return == 0.15


def test_backtester_mock_implementation():
    """Test mock Backtester implementation"""
    class MockBacktester(Backtester):
        def backtest(self, strategy_name, historical_data, config):
            metrics = BacktestMetrics(0.15, 0.20, 1.5, -0.10, 0.60, 2.0, 100, 60, 40, 500.0, -250.0)
            return BacktestResult(
                strategy_name=strategy_name,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                metrics=metrics,
                trades=[],
                equity_curve=[100.0, 101.0, 102.0]
            )
        
        def compute_metrics(self, trades):
            return BacktestMetrics(0.15, 0.20, 1.5, -0.10, 0.60, 2.0, 100, 60, 40, 500.0, -250.0)
    
    backtester = MockBacktester("mock_backtester")
    assert backtester.name == "mock_backtester"


# ============================================================================
# DRLAgent Tests
# ============================================================================

def test_drl_agent_is_abstract():
    """Test that DRLAgent is abstract"""
    with pytest.raises(TypeError):
        DRLAgent("test", "ppo")


def test_drl_agent_state_dataclass():
    """Test State dataclass"""
    state = State(
        price=50000.0,
        indicators={"rsi": 65.0, "macd": 100.0},
        position=1.0,
        balance=100000.0,
        timestamp=1704067200
    )
    assert state.price == 50000.0
    assert state.position == 1.0
    assert state.balance == 100000.0
    assert state.indicators["rsi"] == 65.0


def test_drl_agent_action_dataclass():
    """Test Action dataclass"""
    action = Action(
        action_type="buy",
        size=1.0,
        confidence=0.85
    )
    assert action.action_type == "buy"
    assert action.size == 1.0
    assert action.confidence == 0.85


def test_drl_agent_experience_dataclass():
    """Test Experience dataclass"""
    state = State(50000.0, {"rsi": 65.0}, 1.0, 100000.0, 1704067200)
    action = Action("buy", 1.0, 0.85)
    next_state = State(51000.0, {"rsi": 70.0}, 1.0, 101000.0, 1704067260)
    
    experience = Experience(
        state=state,
        action=action,
        reward=1000.0,
        next_state=next_state,
        done=False
    )
    assert experience.state.price == 50000.0
    assert experience.action.action_type == "buy"
    assert experience.reward == 1000.0
    assert experience.done is False


def test_drl_agent_mock_implementation():
    """Test mock DRLAgent implementation"""
    class MockAgent(DRLAgent):
        async def predict(self, state):
            return Action("buy", 1.0, 0.8)
        
        def train(self, experiences):
            return {"loss": 0.1}
        
        def save_model(self, path):
            pass
        
        def load_model(self, path):
            pass
    
    agent = MockAgent("mock_agent", "ppo")
    assert agent.name == "mock_agent"
    assert agent.agent_type == "ppo"


# ============================================================================
# Registry Tests
# ============================================================================

def test_registry_exchange_registration():
    """Test exchange registration"""
    class MockExchange(ExchangeConnector):
        async def connect(self): pass
        async def disconnect(self): pass
        async def place_order(self, order): pass
        async def cancel_order(self, order_id): pass
        async def get_positions(self): pass
        async def close_position(self, position_id): pass
        async def get_balance(self): pass
        async def get_market_data(self, symbol): pass
    
    registry.register_exchange("mock_exchange", MockExchange)
    assert "mock_exchange" in registry.list_exchanges()
    assert registry.get_exchange("mock_exchange") == MockExchange


def test_registry_strategy_registration():
    """Test strategy registration"""
    class MockStrategy(StrategyExecutor):
        async def execute(self, market_data): pass
        def validate_config(self, config): pass
        def get_required_indicators(self): pass
    
    registry.register_strategy("mock_strategy", MockStrategy)
    assert "mock_strategy" in registry.list_strategies()
    assert registry.get_strategy("mock_strategy") == MockStrategy


def test_registry_backtester_registration():
    """Test backtester registration"""
    class MockBacktester(Backtester):
        def backtest(self, strategy_name, historical_data, config): pass
        def compute_metrics(self, trades): pass
    
    registry.register_backtester("mock_backtester", MockBacktester)
    assert "mock_backtester" in registry.list_backtestors()
    assert registry.get_backtester("mock_backtester") == MockBacktester


def test_registry_agent_registration():
    """Test agent registration"""
    class MockAgent(DRLAgent):
        async def predict(self, state): pass
        def train(self, experiences): pass
        def save_model(self, path): pass
        def load_model(self, path): pass
    
    registry.register_agent("mock_agent", MockAgent)
    assert "mock_agent" in registry.list_agents()
    assert registry.get_agent("mock_agent") == MockAgent


def test_registry_unregistered_exchange():
    """Test getting unregistered exchange"""
    with pytest.raises(ValueError):
        registry.get_exchange("nonexistent_exchange")


def test_registry_unregistered_strategy():
    """Test getting unregistered strategy"""
    with pytest.raises(ValueError):
        registry.get_strategy("nonexistent_strategy")


def test_registry_unregistered_backtester():
    """Test getting unregistered backtester"""
    with pytest.raises(ValueError):
        registry.get_backtester("nonexistent_backtester")


def test_registry_unregistered_agent():
    """Test getting unregistered agent"""
    with pytest.raises(ValueError):
        registry.get_agent("nonexistent_agent")
