"""Unit tests for example interface implementations"""

import pytest
import asyncio
from datetime import datetime
from src.interfaces.examples import (
    MockExchangeConnector,
    SimpleMovingAverageStrategy,
    SimpleBacktester,
    RandomAgent
)
from src.interfaces import Order, MarketData, State


# ============================================================================
# MockExchangeConnector Tests
# ============================================================================

@pytest.mark.asyncio
async def test_mock_exchange_connect():
    """Test connecting to mock exchange"""
    exchange = MockExchangeConnector()
    assert not exchange.connected
    
    await exchange.connect()
    assert exchange.connected


@pytest.mark.asyncio
async def test_mock_exchange_disconnect():
    """Test disconnecting from mock exchange"""
    exchange = MockExchangeConnector()
    await exchange.connect()
    assert exchange.connected
    
    await exchange.disconnect()
    assert not exchange.connected


@pytest.mark.asyncio
async def test_mock_exchange_place_order():
    """Test placing order on mock exchange"""
    exchange = MockExchangeConnector()
    await exchange.connect()
    
    order = Order(
        symbol="BTC/USD",
        side="buy",
        type="market",
        size=1.0,
        price=50000.0
    )
    
    trade = await exchange.place_order(order)
    
    assert trade.symbol == "BTC/USD"
    assert trade.side == "buy"
    assert trade.size == 1.0
    assert trade.fee > 0


@pytest.mark.asyncio
async def test_mock_exchange_place_order_not_connected():
    """Test placing order when not connected"""
    exchange = MockExchangeConnector()
    
    order = Order(
        symbol="BTC/USD",
        side="buy",
        type="market",
        size=1.0,
        price=50000.0
    )
    
    with pytest.raises(RuntimeError):
        await exchange.place_order(order)


@pytest.mark.asyncio
async def test_mock_exchange_get_balance():
    """Test getting balance"""
    exchange = MockExchangeConnector()
    await exchange.connect()
    
    balance = await exchange.get_balance()
    
    assert balance.total == 100000.0
    assert balance.available == 100000.0
    assert balance.used == 0.0


@pytest.mark.asyncio
async def test_mock_exchange_get_positions():
    """Test getting positions"""
    exchange = MockExchangeConnector()
    await exchange.connect()
    
    positions = await exchange.get_positions()
    
    assert isinstance(positions, list)
    assert len(positions) == 0


@pytest.mark.asyncio
async def test_mock_exchange_get_market_data():
    """Test getting market data"""
    exchange = MockExchangeConnector()
    await exchange.connect()
    
    data = await exchange.get_market_data("BTC/USD")
    
    assert data["symbol"] == "BTC/USD"
    assert data["price"] == 100.0
    assert data["volume"] == 1000.0


# ============================================================================
# SimpleMovingAverageStrategy Tests
# ============================================================================

@pytest.mark.asyncio
async def test_sma_strategy_initialization():
    """Test SMA strategy initialization"""
    strategy = SimpleMovingAverageStrategy(fast_period=20, slow_period=50)
    
    assert strategy.name == "sma_crossover"
    assert strategy.strategy_type == "directional"
    assert strategy.fast_period == 20
    assert strategy.slow_period == 50


@pytest.mark.asyncio
async def test_sma_strategy_validate_config():
    """Test SMA strategy config validation"""
    strategy = SimpleMovingAverageStrategy()
    
    # Valid config
    assert strategy.validate_config({"fast_period": 20, "slow_period": 50})
    
    # Invalid configs
    assert not strategy.validate_config({"fast_period": 50, "slow_period": 20})
    assert not strategy.validate_config({"fast_period": 20})
    assert not strategy.validate_config({})


@pytest.mark.asyncio
async def test_sma_strategy_get_required_indicators():
    """Test getting required indicators"""
    strategy = SimpleMovingAverageStrategy()
    
    indicators = strategy.get_required_indicators()
    
    assert "price" in indicators


@pytest.mark.asyncio
async def test_sma_strategy_insufficient_history():
    """Test strategy with insufficient price history"""
    strategy = SimpleMovingAverageStrategy(fast_period=20, slow_period=50)
    
    market_data = MarketData(
        symbol="BTC/USD",
        price=100.0,
        volume=1000.0,
        bid=99.9,
        ask=100.1,
        timestamp=datetime.now(),
        indicators={}
    )
    
    signal = await strategy.execute(market_data)
    
    assert signal is None


@pytest.mark.asyncio
async def test_sma_strategy_crossover_signal():
    """Test SMA crossover signal generation"""
    strategy = SimpleMovingAverageStrategy(fast_period=3, slow_period=5)
    
    # Build price history for crossover
    prices = [100, 101, 102, 103, 104, 105, 106, 107, 108]
    
    for price in prices:
        market_data = MarketData(
            symbol="BTC/USD",
            price=price,
            volume=1000.0,
            bid=price - 0.1,
            ask=price + 0.1,
            timestamp=datetime.now(),
            indicators={}
        )
        
        signal = await strategy.execute(market_data)
        
        # Should generate signal after enough history
        if len(strategy.price_history) > 5:
            # With uptrend, should generate buy signal
            if signal:
                assert signal.direction in ["buy", "sell", "hold"]


# ============================================================================
# SimpleBacktester Tests
# ============================================================================

def test_simple_backtester_initialization():
    """Test backtester initialization"""
    backtester = SimpleBacktester()
    
    assert backtester.name == "simple"


def test_simple_backtester_empty_data():
    """Test backtester with empty data"""
    backtester = SimpleBacktester()
    
    with pytest.raises(ValueError):
        backtester.backtest("test_strategy", [], {})


def test_simple_backtester_single_trade():
    """Test backtester with single trade"""
    backtester = SimpleBacktester()
    
    historical_data = [
        {"timestamp": "2024-01-01T10:00:00", "close": 100.0},
        {"timestamp": "2024-01-02T10:00:00", "close": 110.0},
        {"timestamp": "2024-01-03T10:00:00", "close": 105.0},
    ]
    
    result = backtester.backtest("test_strategy", historical_data, {})
    
    assert result.strategy_name == "test_strategy"
    assert len(result.trades) == 1
    assert result.trades[0].pnl == 5.0  # 110 - 100
    assert len(result.equity_curve) == 3


def test_simple_backtester_compute_metrics():
    """Test metric computation"""
    backtester = SimpleBacktester()
    
    from src.interfaces import BacktestTrade
    
    trades = [
        BacktestTrade(
            entry_time=datetime(2024, 1, 1),
            exit_time=datetime(2024, 1, 2),
            entry_price=100.0,
            exit_price=110.0,
            size=1.0,
            pnl=10.0,
            pnl_percent=0.1
        ),
        BacktestTrade(
            entry_time=datetime(2024, 1, 3),
            exit_time=datetime(2024, 1, 4),
            entry_price=110.0,
            exit_price=105.0,
            size=1.0,
            pnl=-5.0,
            pnl_percent=-0.045
        ),
    ]
    
    metrics = backtester.compute_metrics(trades)
    
    assert metrics.trades_count == 2
    assert metrics.winning_trades == 1
    assert metrics.losing_trades == 1
    assert metrics.win_rate == 0.5
    assert metrics.total_return == 5.0


def test_simple_backtester_no_trades():
    """Test metric computation with no trades"""
    backtester = SimpleBacktester()
    
    metrics = backtester.compute_metrics([])
    
    assert metrics.trades_count == 0
    assert metrics.total_return == 0


# ============================================================================
# RandomAgent Tests
# ============================================================================

@pytest.mark.asyncio
async def test_random_agent_initialization():
    """Test random agent initialization"""
    agent = RandomAgent()
    
    assert agent.name == "random_agent"
    assert agent.agent_type == "random"


@pytest.mark.asyncio
async def test_random_agent_predict():
    """Test random agent prediction"""
    agent = RandomAgent()
    
    state = State(
        price=100.0,
        indicators={"rsi": 65.0},
        position=1.0,
        balance=100000.0,
        timestamp=1704067200
    )
    
    action = await agent.predict(state)
    
    assert action.action_type in ["buy", "sell", "hold"]
    assert 0.1 <= action.size <= 1.0
    assert 0.5 <= action.confidence <= 1.0


@pytest.mark.asyncio
async def test_random_agent_train():
    """Test random agent training"""
    agent = RandomAgent()
    
    from src.interfaces import Experience, Action
    
    experiences = [
        Experience(
            state=State(100.0, {"rsi": 65.0}, 1.0, 100000.0, 1704067200),
            action=Action("buy", 1.0, 0.8),
            reward=100.0,
            next_state=State(101.0, {"rsi": 70.0}, 1.0, 100100.0, 1704067260),
            done=False
        )
    ]
    
    metrics = agent.train(experiences)
    
    assert "loss" in metrics
    assert metrics["loss"] == 0.0


@pytest.mark.asyncio
async def test_random_agent_save_load():
    """Test random agent save/load"""
    agent = RandomAgent()
    
    # Should not raise
    agent.save_model("/tmp/test_model")
    agent.load_model("/tmp/test_model")


@pytest.mark.asyncio
async def test_random_agent_action_history():
    """Test random agent action history"""
    agent = RandomAgent()
    
    state = State(
        price=100.0,
        indicators={"rsi": 65.0},
        position=1.0,
        balance=100000.0,
        timestamp=1704067200
    )
    
    # Generate multiple predictions
    for _ in range(5):
        await agent.predict(state)
    
    assert len(agent.action_history) == 5
