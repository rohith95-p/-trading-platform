"""
Unit tests for Kalshi Exchange Connector

Tests the Kalshi connector implementation including:
- Connection management
- Market data retrieval
- Order placement (paper trading)
- Position tracking
- Error handling
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.exchanges.kalshi import KalshiConnector
from src.core.interfaces import (
    Order,
    OrderSide,
    OrderType,
    Market,
    OrderBook,
    Ticker,
    Trade,
    Position,
)


@pytest.fixture
def kalshi_connector():
    """Create Kalshi connector instance for testing"""
    return KalshiConnector(
        api_key="test_api_key",
        private_key="test_private_key",
        demo=True,
        paper_trading=True,
    )


@pytest.fixture
def mock_session():
    """Create mock aiohttp session"""
    session = MagicMock()
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock()
    session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=response)))
    return session, response


class TestKalshiConnectorInitialization:
    """Test connector initialization"""
    
    def test_init_default_params(self):
        """Test initialization with default parameters"""
        connector = KalshiConnector()
        
        assert connector.name == "kalshi"
        assert connector.demo is True
        assert connector.paper_trading is True
        assert connector.base_url == KalshiConnector.DEMO_BASE_URL
        assert connector.paper_balance == 10000.0
    
    def test_init_prod_mode(self):
        """Test initialization in production mode"""
        connector = KalshiConnector(demo=False)
        
        assert connector.base_url == KalshiConnector.PROD_BASE_URL
        assert connector.paper_trading is True  # Always enforced
    
    def test_init_always_paper_trading(self):
        """Test that paper trading is always enforced"""
        connector = KalshiConnector(paper_trading=False)
        
        assert connector.paper_trading is True


class TestKalshiConnectorConnection:
    """Test connection management"""
    
    @pytest.mark.asyncio
    async def test_connect_success(self, kalshi_connector, mock_session):
        """Test successful connection"""
        session, response = mock_session
        response.json.return_value = {
            "events": [
                {
                    "event_ticker": "TEST",
                    "title": "Test Event",
                    "category": "test",
                    "markets": [
                        {
                            "ticker": "TEST-YES",
                            "title": "Test Market",
                            "yes_bid": 45,
                            "yes_ask": 55,
                            "volume": 1000,
                            "close_time": "2024-12-31T23:59:59Z",
                        }
                    ],
                }
            ]
        }
        
        with patch("aiohttp.ClientSession", return_value=session):
            await kalshi_connector.connect()
        
        assert kalshi_connector.is_connected() is True
    
    @pytest.mark.asyncio
    async def test_disconnect(self, kalshi_connector):
        """Test disconnection"""
        kalshi_connector.session = AsyncMock()
        kalshi_connector._connected = True
        
        await kalshi_connector.disconnect()
        
        assert kalshi_connector.is_connected() is False
        kalshi_connector.session.close.assert_called_once()


class TestKalshiConnectorMarketData:
    """Test market data retrieval"""
    
    @pytest.mark.asyncio
    async def test_get_markets(self, kalshi_connector, mock_session):
        """Test getting list of markets"""
        session, response = mock_session
        kalshi_connector.session = session
        kalshi_connector._connected = True
        
        response.json.return_value = {
            "events": [
                {
                    "event_ticker": "ELECTION",
                    "title": "2024 Election",
                    "category": "politics",
                    "markets": [
                        {
                            "ticker": "PRES-2024",
                            "title": "Presidential Winner",
                            "yes_bid": 45,
                            "yes_ask": 55,
                            "volume": 10000,
                            "close_time": "2024-11-05T23:59:59Z",
                        }
                    ],
                }
            ]
        }
        
        markets = await kalshi_connector.get_markets()
        
        assert len(markets) == 1
        assert markets[0].symbol == "PRES-2024"
        assert markets[0].baseAsset == "YES"
        assert markets[0].quoteAsset == "USD"
    
    @pytest.mark.asyncio
    async def test_get_order_book(self, kalshi_connector, mock_session):
        """Test getting order book"""
        session, response = mock_session
        kalshi_connector.session = session
        kalshi_connector._connected = True
        
        response.json.return_value = {
            "orderbook": {
                "yes": [[50, 100], [45, 200]],
                "no": [[50, 100], [55, 200]],
            }
        }
        
        order_book = await kalshi_connector.get_order_book("TEST-YES")
        
        assert order_book.symbol == "TEST-YES"
        assert len(order_book.bids) == 2
        assert len(order_book.asks) == 2
        assert order_book.bids[0][0] == 0.50  # Price in dollars
        assert order_book.bids[0][1] == 100.0  # Size
    
    @pytest.mark.asyncio
    async def test_get_ticker(self, kalshi_connector, mock_session):
        """Test getting ticker"""
        session, response = mock_session
        kalshi_connector.session = session
        kalshi_connector._connected = True
        
        response.json.return_value = {
            "market": {
                "ticker": "TEST-YES",
                "title": "Test Market",
                "yes_bid": 45,
                "yes_ask": 55,
                "volume": 1000,
                "close_time": "2024-12-31T23:59:59Z",
            }
        }
        
        ticker = await kalshi_connector.get_ticker("TEST-YES")
        
        assert ticker.symbol == "TEST-YES"
        assert ticker.bidPrice == 0.45
        assert ticker.askPrice == 0.55
        assert ticker.lastPrice == 0.50  # Mid price
        assert ticker.volume24h == 1000.0


class TestKalshiConnectorTrading:
    """Test trading operations (paper trading)"""
    
    @pytest.mark.asyncio
    async def test_place_market_buy_order(self, kalshi_connector, mock_session):
        """Test placing market buy order"""
        session, response = mock_session
        kalshi_connector.session = session
        kalshi_connector._connected = True
        
        # Mock ticker response
        response.json.return_value = {
            "market": {
                "ticker": "TEST-YES",
                "title": "Test Market",
                "yes_bid": 45,
                "yes_ask": 55,
                "volume": 1000,
            }
        }
        
        order = Order(
            symbol="TEST-YES",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            size=10.0,
        )
        
        initial_balance = kalshi_connector.paper_balance
        trade = await kalshi_connector.place_order(order)
        
        assert trade.symbol == "TEST-YES"
        assert trade.side == OrderSide.BUY
        assert trade.size == 10.0
        assert trade.price == 0.55  # Ask price for buy
        assert trade.fee > 0
        assert kalshi_connector.paper_balance < initial_balance
    
    @pytest.mark.asyncio
    async def test_place_limit_order(self, kalshi_connector, mock_session):
        """Test placing limit order"""
        session, response = mock_session
        kalshi_connector.session = session
        kalshi_connector._connected = True
        
        response.json.return_value = {
            "market": {
                "ticker": "TEST-YES",
                "yes_bid": 45,
                "yes_ask": 55,
                "volume": 1000,
            }
        }
        
        order = Order(
            symbol="TEST-YES",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            size=10.0,
            price=0.50,
        )
        
        trade = await kalshi_connector.place_order(order)
        
        assert trade.price == 0.50  # Limit price
    
    @pytest.mark.asyncio
    async def test_place_order_insufficient_balance(self, kalshi_connector, mock_session):
        """Test placing order with insufficient balance"""
        session, response = mock_session
        kalshi_connector.session = session
        kalshi_connector._connected = True
        kalshi_connector.paper_balance = 10.0  # Low balance
        
        response.json.return_value = {
            "market": {
                "ticker": "TEST-YES",
                "yes_bid": 45,
                "yes_ask": 55,
                "volume": 1000,
            }
        }
        
        order = Order(
            symbol="TEST-YES",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            size=1000.0,  # Too large
        )
        
        with pytest.raises(ValueError, match="Insufficient balance"):
            await kalshi_connector.place_order(order)
    
    @pytest.mark.asyncio
    async def test_place_order_invalid_price(self, kalshi_connector, mock_session):
        """Test placing order with invalid price"""
        session, response = mock_session
        kalshi_connector.session = session
        kalshi_connector._connected = True
        
        order = Order(
            symbol="TEST-YES",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            size=10.0,
            price=1.5,  # Invalid for prediction market
        )
        
        with pytest.raises(ValueError, match="Invalid limit price"):
            await kalshi_connector.place_order(order)


class TestKalshiConnectorPositions:
    """Test position management"""
    
    @pytest.mark.asyncio
    async def test_get_position_empty(self, kalshi_connector):
        """Test getting position when none exists"""
        position = await kalshi_connector.get_position("TEST-YES")
        
        assert position.symbol == "TEST-YES"
        assert position.size == 0
        assert position.avgPrice == 0
    
    @pytest.mark.asyncio
    async def test_get_positions_after_trade(self, kalshi_connector, mock_session):
        """Test getting positions after placing trade"""
        session, response = mock_session
        kalshi_connector.session = session
        kalshi_connector._connected = True
        
        response.json.return_value = {
            "market": {
                "ticker": "TEST-YES",
                "yes_bid": 45,
                "yes_ask": 55,
                "volume": 1000,
            }
        }
        
        # Place buy order
        order = Order(
            symbol="TEST-YES",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            size=10.0,
        )
        await kalshi_connector.place_order(order)
        
        # Get positions
        positions = await kalshi_connector.get_positions()
        
        assert len(positions) == 1
        assert positions[0].symbol == "TEST-YES"
        assert positions[0].size == 10.0
    
    @pytest.mark.asyncio
    async def test_position_pnl_calculation(self, kalshi_connector, mock_session):
        """Test position P&L calculation"""
        session, response = mock_session
        kalshi_connector.session = session
        kalshi_connector._connected = True
        
        # Mock initial buy
        response.json.return_value = {
            "market": {
                "ticker": "TEST-YES",
                "yes_bid": 45,
                "yes_ask": 55,
                "volume": 1000,
            }
        }
        
        order = Order(
            symbol="TEST-YES",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            size=10.0,
        )
        await kalshi_connector.place_order(order)
        
        # Mock price increase
        response.json.return_value = {
            "market": {
                "ticker": "TEST-YES",
                "yes_bid": 65,
                "yes_ask": 75,
                "volume": 1000,
            }
        }
        
        positions = await kalshi_connector.get_positions()
        
        assert positions[0].unrealizedPnl > 0  # Profit


class TestKalshiConnectorBalance:
    """Test balance management"""
    
    @pytest.mark.asyncio
    async def test_get_balance_initial(self, kalshi_connector):
        """Test getting initial balance"""
        balance = await kalshi_connector.get_balance()
        
        assert balance["USD"] == 10000.0
        assert balance["total"] == 10000.0
        assert balance["positions_value"] == 0
    
    @pytest.mark.asyncio
    async def test_get_balance_after_trade(self, kalshi_connector, mock_session):
        """Test getting balance after trade"""
        session, response = mock_session
        kalshi_connector.session = session
        kalshi_connector._connected = True
        
        response.json.return_value = {
            "market": {
                "ticker": "TEST-YES",
                "yes_bid": 45,
                "yes_ask": 55,
                "volume": 1000,
            }
        }
        
        order = Order(
            symbol="TEST-YES",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            size=10.0,
        )
        await kalshi_connector.place_order(order)
        
        balance = await kalshi_connector.get_balance()
        
        assert balance["USD"] < 10000.0  # Balance decreased
        assert balance["positions_value"] > 0  # Has position value


class TestKalshiConnectorErrorHandling:
    """Test error handling and retries"""
    
    @pytest.mark.asyncio
    async def test_request_retry_on_timeout(self, kalshi_connector):
        """Test request retry on timeout"""
        kalshi_connector.session = AsyncMock()
        kalshi_connector._connected = True
        
        # Mock timeout then success
        response_mock = AsyncMock()
        response_mock.status = 200
        response_mock.json = AsyncMock(return_value={"events": []})
        
        kalshi_connector.session.request = MagicMock(
            side_effect=[
                asyncio.TimeoutError(),
                AsyncMock(__aenter__=AsyncMock(return_value=response_mock)),
            ]
        )
        
        result = await kalshi_connector._request("GET", "/events")
        
        assert result == {"events": []}
    
    @pytest.mark.asyncio
    async def test_request_max_retries_exceeded(self, kalshi_connector):
        """Test request fails after max retries"""
        kalshi_connector.session = AsyncMock()
        kalshi_connector._connected = True
        kalshi_connector.MAX_RETRIES = 2
        
        kalshi_connector.session.request = MagicMock(
            side_effect=asyncio.TimeoutError()
        )
        
        with pytest.raises(asyncio.TimeoutError):
            await kalshi_connector._request("GET", "/events")


class TestKalshiConnectorValidation:
    """Test order validation"""
    
    def test_validate_order_invalid_size(self, kalshi_connector):
        """Test validation rejects invalid size"""
        order = Order(
            symbol="TEST-YES",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            size=0,  # Invalid
        )
        
        with pytest.raises(ValueError, match="Invalid order size"):
            kalshi_connector._validate_order(order)
    
    def test_validate_order_invalid_limit_price(self, kalshi_connector):
        """Test validation rejects invalid limit price"""
        order = Order(
            symbol="TEST-YES",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            size=10.0,
            price=2.0,  # Invalid for prediction market
        )
        
        with pytest.raises(ValueError, match="Invalid limit price"):
            kalshi_connector._validate_order(order)
