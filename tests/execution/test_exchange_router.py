"""
Unit tests for Exchange Router

Tests cover:
- Connector registration
- Order routing
- Market data retrieval
- Position management
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.execution.exchange_router import (
    ExchangeRouter,
    get_exchange_router,
    initialize_exchange_router,
)
from src.core.interfaces import (
    ExchangeConnector,
    ExchangeType,
    Order,
    OrderSide,
    OrderType,
)


@pytest.fixture
def router():
    """Create an exchange router instance for testing"""
    return ExchangeRouter()


@pytest.fixture
def mock_connector():
    """Create a mock exchange connector"""
    connector = MagicMock(spec=ExchangeConnector)
    connector.name = "test_exchange"
    connector.type = ExchangeType.CEX
    connector.is_connected.return_value = True
    return connector


def test_register_connector(router, mock_connector):
    """Test registering a connector"""
    router.register_connector("test", mock_connector)
    
    assert "test" in router.connectors
    assert router.connectors["test"] == mock_connector


def test_get_connector(router, mock_connector):
    """Test retrieving a connector"""
    router.register_connector("test", mock_connector)
    
    connector = router.get_connector("test")
    
    assert connector == mock_connector


def test_get_connector_not_found(router):
    """Test retrieving a non-existent connector"""
    with pytest.raises(ValueError, match="Unknown exchange"):
        router.get_connector("nonexistent")


def test_get_connector_case_insensitive(router, mock_connector):
    """Test connector retrieval is case-insensitive"""
    router.register_connector("TEST", mock_connector)
    
    connector = router.get_connector("test")
    
    assert connector == mock_connector


@pytest.mark.asyncio
async def test_connect_all(router, mock_connector):
    """Test connecting all connectors"""
    mock_connector.connect = AsyncMock()
    router.register_connector("test", mock_connector)
    
    await router.connect_all()
    
    mock_connector.connect.assert_called_once()


@pytest.mark.asyncio
async def test_disconnect_all(router, mock_connector):
    """Test disconnecting all connectors"""
    mock_connector.disconnect = AsyncMock()
    router.register_connector("test", mock_connector)
    
    await router.disconnect_all()
    
    mock_connector.disconnect.assert_called_once()


def test_get_connected_exchanges(router, mock_connector):
    """Test getting list of connected exchanges"""
    mock_connector.is_connected.return_value = True
    router.register_connector("test1", mock_connector)
    
    mock_connector2 = MagicMock(spec=ExchangeConnector)
    mock_connector2.is_connected.return_value = False
    router.register_connector("test2", mock_connector2)
    
    connected = router.get_connected_exchanges()
    
    assert "test1" in connected
    assert "test2" not in connected


@pytest.mark.asyncio
async def test_get_markets(router, mock_connector):
    """Test getting markets from exchange"""
    mock_markets = [MagicMock(symbol="BTC-USD")]
    mock_connector.get_markets = AsyncMock(return_value=mock_markets)
    router.register_connector("test", mock_connector)
    
    markets = await router.get_markets("test")
    
    assert markets == mock_markets
    mock_connector.get_markets.assert_called_once()


@pytest.mark.asyncio
async def test_get_order_book(router, mock_connector):
    """Test getting order book from exchange"""
    mock_book = MagicMock(symbol="BTC-USD")
    mock_connector.get_order_book = AsyncMock(return_value=mock_book)
    router.register_connector("test", mock_connector)
    
    book = await router.get_order_book("test", "BTC-USD")
    
    assert book == mock_book
    mock_connector.get_order_book.assert_called_once_with("BTC-USD")


@pytest.mark.asyncio
async def test_get_ticker(router, mock_connector):
    """Test getting ticker from exchange"""
    mock_ticker = MagicMock(symbol="BTC-USD")
    mock_connector.get_ticker = AsyncMock(return_value=mock_ticker)
    router.register_connector("test", mock_connector)
    
    ticker = await router.get_ticker("test", "BTC-USD")
    
    assert ticker == mock_ticker
    mock_connector.get_ticker.assert_called_once_with("BTC-USD")


@pytest.mark.asyncio
async def test_place_order(router, mock_connector):
    """Test placing order on exchange"""
    order = Order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        size=1.0,
    )
    
    mock_trade = MagicMock(id="trade_123")
    mock_connector.place_order = AsyncMock(return_value=mock_trade)
    router.register_connector("test", mock_connector)
    
    trade = await router.place_order("test", order)
    
    assert trade == mock_trade
    mock_connector.place_order.assert_called_once_with(order)


@pytest.mark.asyncio
async def test_place_order_unknown_exchange(router):
    """Test placing order on unknown exchange"""
    order = Order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        size=1.0,
    )
    
    with pytest.raises(ValueError, match="Unknown exchange"):
        await router.place_order("unknown", order)


@pytest.mark.asyncio
async def test_cancel_order(router, mock_connector):
    """Test cancelling order on exchange"""
    mock_connector.cancel_order = AsyncMock()
    router.register_connector("test", mock_connector)
    
    await router.cancel_order("test", "order_123")
    
    mock_connector.cancel_order.assert_called_once_with("order_123")


@pytest.mark.asyncio
async def test_get_position(router, mock_connector):
    """Test getting position from exchange"""
    mock_position = MagicMock(symbol="BTC-USD")
    mock_connector.get_position = AsyncMock(return_value=mock_position)
    router.register_connector("test", mock_connector)
    
    position = await router.get_position("test", "BTC-USD")
    
    assert position == mock_position
    mock_connector.get_position.assert_called_once_with("BTC-USD")


@pytest.mark.asyncio
async def test_get_positions(router, mock_connector):
    """Test getting all positions from exchange"""
    mock_positions = [MagicMock(symbol="BTC-USD")]
    mock_connector.get_positions = AsyncMock(return_value=mock_positions)
    router.register_connector("test", mock_connector)
    
    positions = await router.get_positions("test")
    
    assert positions == mock_positions
    mock_connector.get_positions.assert_called_once()


@pytest.mark.asyncio
async def test_get_balance(router, mock_connector):
    """Test getting balance from exchange"""
    mock_balance = {"USDC": 10000, "BTC": 0.5}
    mock_connector.get_balance = AsyncMock(return_value=mock_balance)
    router.register_connector("test", mock_connector)
    
    balance = await router.get_balance("test")
    
    assert balance == mock_balance
    mock_connector.get_balance.assert_called_once()


def test_list_exchanges(router, mock_connector):
    """Test listing all exchanges"""
    mock_connector.is_connected.return_value = True
    router.register_connector("test1", mock_connector)
    
    mock_connector2 = MagicMock(spec=ExchangeConnector)
    mock_connector2.type = ExchangeType.DEX
    mock_connector2.is_connected.return_value = False
    router.register_connector("test2", mock_connector2)
    
    exchanges = router.list_exchanges()
    
    assert len(exchanges) == 2
    assert exchanges[0]["name"] == "test1"
    assert exchanges[0]["connected"] is True
    assert exchanges[1]["name"] == "test2"
    assert exchanges[1]["connected"] is False


def test_get_exchange_router():
    """Test getting global exchange router instance"""
    router1 = get_exchange_router()
    router2 = get_exchange_router()
    
    assert router1 is router2


def test_initialize_exchange_router():
    """Test initializing exchange router with connectors"""
    config = {
        "hyperliquid_config": {
            "api_key": "test_key",
            "secret": "test_secret",
            "testnet": True,
        },
        "kraken_config": {
            "api_key": "test_key",
            "secret": "test_secret",
        },
    }
    
    router = initialize_exchange_router(**config)
    
    assert "hyperliquid" in router.connectors
    assert "kraken" in router.connectors
