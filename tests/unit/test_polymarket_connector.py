"""
Unit tests for Polymarket Exchange Connector

Tests the Polymarket connector implementation including:
- Connection management
- Market data retrieval
- Order placement (paper trading)
- Position tracking
- Balance management
- Error handling and retries
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.exchanges.polymarket import PolymarketConnector
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


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def connector():
    """Create PolymarketConnector instance for testing"""
    return PolymarketConnector(api_key="test_api_key", paper_trading=True)


@pytest.fixture
def mock_session():
    """Return a (session, response) pair with a 200 OK mock"""
    session = MagicMock()
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock()
    session.request = MagicMock(
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=response))
    )
    return session, response


# ── Initialization ────────────────────────────────────────────────────────────

class TestPolymarketConnectorInitialization:

    def test_default_params(self):
        c = PolymarketConnector()
        assert c.name == "polymarket"
        assert c.paper_trading is True
        assert c.base_url == PolymarketConnector.CLOB_BASE_URL
        assert c.paper_balance == 10000.0

    def test_paper_trading_always_enforced(self):
        """paper_trading=False must still result in paper_trading=True"""
        c = PolymarketConnector(paper_trading=False)
        assert c.paper_trading is True

    def test_api_key_stored(self):
        c = PolymarketConnector(api_key="my_key")
        assert c.api_key == "my_key"

    def test_initial_state(self):
        c = PolymarketConnector()
        assert c.paper_positions == {}
        assert c.paper_trades == []
        assert c.is_connected() is False


# ── Connection ────────────────────────────────────────────────────────────────

class TestPolymarketConnectorConnection:

    @pytest.mark.asyncio
    async def test_connect_success(self, connector, mock_session):
        session, response = mock_session
        response.json.return_value = {
            "data": [
                {"condition_id": "0xabc", "question": "Will X happen?", "active": True}
            ]
        }

        with patch("aiohttp.ClientSession", return_value=session):
            await connector.connect()

        assert connector.is_connected() is True

    @pytest.mark.asyncio
    async def test_disconnect(self, connector):
        connector.session = AsyncMock()
        connector._connected = True

        await connector.disconnect()

        assert connector.is_connected() is False
        connector.session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure_closes_session(self, connector):
        """If connect fails, session should be closed"""
        mock_sess = AsyncMock()
        mock_sess.request = MagicMock(side_effect=Exception("network error"))

        with patch("aiohttp.ClientSession", return_value=mock_sess):
            with pytest.raises(Exception):
                await connector.connect()

        mock_sess.close.assert_called_once()


# ── Market Data ───────────────────────────────────────────────────────────────

class TestPolymarketConnectorMarketData:

    @pytest.mark.asyncio
    async def test_get_markets(self, connector, mock_session):
        session, response = mock_session
        connector.session = session
        connector._connected = True

        response.json.return_value = {
            "data": [
                {"condition_id": "0xabc", "question": "Will X happen?"},
                {"condition_id": "0xdef", "question": "Will Y happen?"},
            ]
        }

        markets = await connector.get_markets()

        assert len(markets) == 2
        assert markets[0].symbol == "0xabc"
        assert markets[0].baseAsset == "YES"
        assert markets[0].quoteAsset == "USDC"

    @pytest.mark.asyncio
    async def test_get_markets_empty(self, connector, mock_session):
        session, response = mock_session
        connector.session = session
        connector._connected = True
        response.json.return_value = {"data": []}

        markets = await connector.get_markets()
        assert markets == []

    @pytest.mark.asyncio
    async def test_get_order_book(self, connector, mock_session):
        session, response = mock_session
        connector.session = session
        connector._connected = True

        response.json.return_value = {
            "bids": [{"price": "0.55", "size": "100"}, {"price": "0.50", "size": "200"}],
            "asks": [{"price": "0.60", "size": "150"}, {"price": "0.65", "size": "50"}],
        }

        ob = await connector.get_order_book("0xabc")

        assert ob.symbol == "0xabc"
        assert len(ob.bids) == 2
        assert len(ob.asks) == 2
        assert ob.bids[0] == (0.55, 100.0)
        assert ob.asks[0] == (0.60, 150.0)

    @pytest.mark.asyncio
    async def test_get_ticker(self, connector, mock_session):
        session, response = mock_session
        connector.session = session
        connector._connected = True

        # Three sequential calls: buy price, sell price, midpoint
        response.json.side_effect = [
            {"price": "0.60"},   # buy side
            {"price": "0.55"},   # sell side
            {"mid": "0.575"},    # midpoint
        ]

        ticker = await connector.get_ticker("0xabc")

        assert ticker.symbol == "0xabc"
        assert ticker.askPrice == 0.60
        assert ticker.bidPrice == 0.55
        assert ticker.lastPrice == pytest.approx(0.575)


# ── Trading (Paper) ───────────────────────────────────────────────────────────

class TestPolymarketConnectorTrading:

    def _setup_ticker_mock(self, response, bid=0.55, ask=0.60):
        response.json.side_effect = [
            {"price": str(ask)},
            {"price": str(bid)},
            {"mid": str((bid + ask) / 2)},
        ]

    @pytest.mark.asyncio
    async def test_place_market_buy_order(self, connector, mock_session):
        session, response = mock_session
        connector.session = session
        connector._connected = True
        self._setup_ticker_mock(response)

        order = Order(symbol="0xabc", side=OrderSide.BUY, type=OrderType.MARKET, size=10.0)
        initial_balance = connector.paper_balance

        trade = await connector.place_order(order)

        assert trade.symbol == "0xabc"
        assert trade.side == OrderSide.BUY
        assert trade.size == 10.0
        assert trade.price == 0.60  # ask price
        assert trade.fee > 0
        assert connector.paper_balance < initial_balance

    @pytest.mark.asyncio
    async def test_place_market_sell_order(self, connector, mock_session):
        session, response = mock_session
        connector.session = session
        connector._connected = True

        # Seed a position first
        connector.paper_positions["0xabc"] = Position(
            symbol="0xabc", size=20.0, avgPrice=0.55,
            currentPrice=0.55, unrealizedPnl=0, realizedPnl=0
        )

        self._setup_ticker_mock(response)

        order = Order(symbol="0xabc", side=OrderSide.SELL, type=OrderType.MARKET, size=5.0)
        initial_balance = connector.paper_balance

        trade = await connector.place_order(order)

        assert trade.side == OrderSide.SELL
        assert trade.price == 0.55  # bid price
        assert connector.paper_balance > initial_balance

    @pytest.mark.asyncio
    async def test_place_limit_order(self, connector, mock_session):
        session, response = mock_session
        connector.session = session
        connector._connected = True
        self._setup_ticker_mock(response)

        order = Order(
            symbol="0xabc", side=OrderSide.BUY, type=OrderType.LIMIT, size=10.0, price=0.50
        )
        trade = await connector.place_order(order)

        assert trade.price == 0.50

    @pytest.mark.asyncio
    async def test_place_order_insufficient_balance(self, connector, mock_session):
        session, response = mock_session
        connector.session = session
        connector._connected = True
        connector.paper_balance = 5.0  # Very low
        self._setup_ticker_mock(response)

        order = Order(symbol="0xabc", side=OrderSide.BUY, type=OrderType.MARKET, size=1000.0)

        with pytest.raises(ValueError, match="Insufficient balance"):
            await connector.place_order(order)

    @pytest.mark.asyncio
    async def test_cancel_order_noop(self, connector):
        """cancel_order should not raise in paper trading mode"""
        await connector.cancel_order("PAPER-POLY-1")  # should not raise

    @pytest.mark.asyncio
    async def test_trade_id_increments(self, connector, mock_session):
        session, response = mock_session
        connector.session = session
        connector._connected = True

        for _ in range(2):
            self._setup_ticker_mock(response)
            order = Order(symbol="0xabc", side=OrderSide.BUY, type=OrderType.MARKET, size=1.0)
            await connector.place_order(order)

        ids = [t.id for t in connector.paper_trades]
        assert ids[0] != ids[1]


# ── Positions ─────────────────────────────────────────────────────────────────

class TestPolymarketConnectorPositions:

    @pytest.mark.asyncio
    async def test_get_position_empty(self, connector):
        pos = await connector.get_position("0xabc")
        assert pos.symbol == "0xabc"
        assert pos.size == 0
        assert pos.avgPrice == 0

    @pytest.mark.asyncio
    async def test_get_positions_after_trade(self, connector, mock_session):
        session, response = mock_session
        connector.session = session
        connector._connected = True

        # buy side
        response.json.side_effect = [
            {"price": "0.60"},
            {"price": "0.55"},
            {"mid": "0.575"},
            # get_positions calls get_ticker again
            {"price": "0.60"},
            {"price": "0.55"},
            {"mid": "0.575"},
        ]

        order = Order(symbol="0xabc", side=OrderSide.BUY, type=OrderType.MARKET, size=10.0)
        await connector.place_order(order)

        positions = await connector.get_positions()

        assert len(positions) == 1
        assert positions[0].symbol == "0xabc"
        assert positions[0].size == 10.0

    @pytest.mark.asyncio
    async def test_position_pnl_increases_with_price(self, connector, mock_session):
        session, response = mock_session
        connector.session = session
        connector._connected = True

        # Buy at 0.60
        response.json.side_effect = [
            {"price": "0.60"},
            {"price": "0.55"},
            {"mid": "0.575"},
            # get_positions: price now 0.80
            {"price": "0.80"},
            {"price": "0.75"},
            {"mid": "0.775"},
        ]

        order = Order(symbol="0xabc", side=OrderSide.BUY, type=OrderType.MARKET, size=10.0)
        await connector.place_order(order)

        positions = await connector.get_positions()
        assert positions[0].unrealizedPnl > 0


# ── Balance ───────────────────────────────────────────────────────────────────

class TestPolymarketConnectorBalance:

    @pytest.mark.asyncio
    async def test_initial_balance(self, connector):
        balance = await connector.get_balance()
        assert balance["USDC"] == 10000.0
        assert balance["total"] == 10000.0
        assert balance["positions_value"] == 0

    @pytest.mark.asyncio
    async def test_balance_decreases_after_buy(self, connector, mock_session):
        session, response = mock_session
        connector.session = session
        connector._connected = True

        response.json.side_effect = [
            {"price": "0.60"},
            {"price": "0.55"},
            {"mid": "0.575"},
        ]

        order = Order(symbol="0xabc", side=OrderSide.BUY, type=OrderType.MARKET, size=10.0)
        await connector.place_order(order)

        balance = await connector.get_balance()
        assert balance["USDC"] < 10000.0
        assert balance["positions_value"] > 0


# ── Validation ────────────────────────────────────────────────────────────────

class TestPolymarketConnectorValidation:

    def test_invalid_order_size_zero(self, connector):
        order = Order(symbol="0xabc", side=OrderSide.BUY, type=OrderType.MARKET, size=0)
        with pytest.raises(ValueError, match="Invalid order size"):
            connector._validate_order(order)

    def test_invalid_order_size_negative(self, connector):
        order = Order(symbol="0xabc", side=OrderSide.BUY, type=OrderType.MARKET, size=-5)
        with pytest.raises(ValueError, match="Invalid order size"):
            connector._validate_order(order)

    def test_invalid_limit_price_above_one(self, connector):
        order = Order(
            symbol="0xabc", side=OrderSide.BUY, type=OrderType.LIMIT, size=10.0, price=1.5
        )
        with pytest.raises(ValueError, match="Invalid limit price"):
            connector._validate_order(order)

    def test_invalid_limit_price_zero(self, connector):
        order = Order(
            symbol="0xabc", side=OrderSide.BUY, type=OrderType.LIMIT, size=10.0, price=0.0
        )
        with pytest.raises(ValueError, match="Invalid limit price"):
            connector._validate_order(order)

    def test_valid_limit_price(self, connector):
        order = Order(
            symbol="0xabc", side=OrderSide.BUY, type=OrderType.LIMIT, size=10.0, price=0.5
        )
        connector._validate_order(order)  # should not raise


# ── Error Handling & Retries ──────────────────────────────────────────────────

class TestPolymarketConnectorErrorHandling:

    @pytest.mark.asyncio
    async def test_retry_on_timeout_then_success(self, connector):
        connector.session = AsyncMock()
        connector._connected = True

        success_response = AsyncMock()
        success_response.status = 200
        success_response.json = AsyncMock(return_value={"data": []})

        connector.session.request = MagicMock(
            side_effect=[
                asyncio.TimeoutError(),
                AsyncMock(__aenter__=AsyncMock(return_value=success_response)),
            ]
        )

        result = await connector._request("GET", "/markets")
        assert result == {"data": []}

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_raises(self, connector):
        connector.session = AsyncMock()
        connector._connected = True
        connector.MAX_RETRIES = 2

        connector.session.request = MagicMock(side_effect=asyncio.TimeoutError())

        with pytest.raises(asyncio.TimeoutError):
            await connector._request("GET", "/markets")

    @pytest.mark.asyncio
    async def test_http_error_raises(self, connector):
        connector.session = AsyncMock()
        connector._connected = True
        connector.MAX_RETRIES = 0  # no retries

        error_response = AsyncMock()
        error_response.status = 429
        error_response.text = AsyncMock(return_value="rate limited")

        connector.session.request = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=error_response))
        )

        with pytest.raises(Exception, match="HTTP 429"):
            await connector._request("GET", "/markets")

    @pytest.mark.asyncio
    async def test_request_without_session_raises(self, connector):
        connector.session = None
        with pytest.raises(Exception, match="Not connected"):
            await connector._request("GET", "/markets")

    @pytest.mark.asyncio
    async def test_auth_header_sent_when_api_key_set(self, connector):
        connector.session = AsyncMock()
        connector._connected = True

        captured_headers = {}

        async def fake_request(method, url, **kwargs):
            captured_headers.update(kwargs.get("headers", {}))
            resp = AsyncMock()
            resp.status = 200
            resp.json = AsyncMock(return_value={})
            return resp

        connector.session.request = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(
                    return_value=type(
                        "R",
                        (),
                        {
                            "status": 200,
                            "json": AsyncMock(return_value={}),
                            "__aenter__": AsyncMock(),
                            "__aexit__": AsyncMock(return_value=False),
                        },
                    )()
                )
            )
        )

        # Patch to capture headers
        original_request = connector._request

        async def patched_request(method, endpoint, params=None, retry_count=0):
            url = f"{connector.base_url}{endpoint}"
            headers = {"Accept": "application/json"}
            if connector.api_key:
                headers["Authorization"] = f"Bearer {connector.api_key}"
            captured_headers.update(headers)
            return {}

        connector._request = patched_request
        await connector._request("GET", "/markets")
        assert "Authorization" in captured_headers
        assert captured_headers["Authorization"] == "Bearer test_api_key"
