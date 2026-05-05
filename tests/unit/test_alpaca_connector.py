"""
Unit tests for Alpaca Exchange Connector

Tests the AlpacaConnector implementation including:
- Initialization and paper trading enforcement
- Connection management
- Market data retrieval (markets, order book, ticker)
- Order placement (paper trading)
- Position tracking
- Balance management
- Error handling and exponential backoff retries
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.exchanges.alpaca import AlpacaConnector
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
    """Create AlpacaConnector instance for testing"""
    return AlpacaConnector(
        api_key="test_key_id",
        secret_key="test_secret_key",
        paper_trading=True,
    )


def _make_mock_session(json_return=None, status=200):
    """Helper to build a mock aiohttp session"""
    session = MagicMock()
    response = AsyncMock()
    response.status = status
    response.json = AsyncMock(return_value=json_return or {})
    response.text = AsyncMock(return_value="")
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=False)
    session.request = MagicMock(return_value=cm)
    return session, response


# ── Initialization ────────────────────────────────────────────────────────────

class TestAlpacaConnectorInitialization:

    def test_default_paper_trading_enforced(self):
        """paper_trading is always True regardless of argument"""
        c = AlpacaConnector(paper_trading=False)
        assert c.paper_trading is True

    def test_paper_base_url(self):
        """Always uses paper trading endpoint"""
        c = AlpacaConnector()
        assert c.base_url == AlpacaConnector.PAPER_BASE_URL
        assert "paper-api.alpaca.markets" in c.base_url

    def test_exchange_type_is_stocks(self):
        """Exchange type is STOCKS (equities)"""
        from src.core.interfaces import ExchangeType
        c = AlpacaConnector()
        assert c.type == ExchangeType.STOCKS

    def test_initial_paper_balance(self):
        """Paper balance starts at $100k (Alpaca default)"""
        c = AlpacaConnector()
        assert c.paper_balance == 100000.0

    def test_name(self):
        c = AlpacaConnector()
        assert c.name == "alpaca"

    def test_not_connected_initially(self):
        c = AlpacaConnector()
        assert c.is_connected() is False


# ── Connection ────────────────────────────────────────────────────────────────

class TestAlpacaConnectorConnection:

    @pytest.mark.asyncio
    async def test_connect_success(self, connector):
        """Successful connect sets _connected = True"""
        session, response = _make_mock_session({"id": "abc", "status": "ACTIVE"})

        with patch("aiohttp.ClientSession", return_value=session):
            await connector.connect()

        assert connector.is_connected() is True

    @pytest.mark.asyncio
    async def test_connect_failure_closes_session(self, connector):
        """Failed connect closes the session and re-raises"""
        session = MagicMock()
        session.close = AsyncMock()
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(side_effect=Exception("network error"))
        cm.__aexit__ = AsyncMock(return_value=False)
        session.request = MagicMock(return_value=cm)

        with patch("aiohttp.ClientSession", return_value=session):
            with pytest.raises(Exception):
                await connector.connect()

        session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, connector):
        """Disconnect closes session and marks not connected"""
        connector.session = AsyncMock()
        connector._connected = True

        await connector.disconnect()

        assert connector.is_connected() is False
        connector.session.close.assert_called_once()


# ── Market Data ───────────────────────────────────────────────────────────────

class TestAlpacaConnectorMarketData:

    @pytest.mark.asyncio
    async def test_get_markets_returns_tradeable_assets(self, connector):
        """get_markets filters to tradeable assets only"""
        session, response = _make_mock_session([
            {"symbol": "AAPL", "tradable": True, "asset_class": "us_equity"},
            {"symbol": "TSLA", "tradable": True, "asset_class": "us_equity"},
            {"symbol": "DELISTED", "tradable": False, "asset_class": "us_equity"},
        ])
        connector.session = session
        connector._connected = True

        markets = await connector.get_markets()

        assert len(markets) == 2
        symbols = [m.symbol for m in markets]
        assert "AAPL" in symbols
        assert "TSLA" in symbols
        assert "DELISTED" not in symbols

    @pytest.mark.asyncio
    async def test_get_markets_quote_asset_is_usd(self, connector):
        """All stock markets quote in USD"""
        session, response = _make_mock_session([
            {"symbol": "MSFT", "tradable": True},
        ])
        connector.session = session
        connector._connected = True

        markets = await connector.get_markets()

        assert markets[0].quoteAsset == "USD"

    @pytest.mark.asyncio
    async def test_get_order_book(self, connector):
        """get_order_book returns bid/ask from latest quote"""
        session = MagicMock()
        response = AsyncMock()
        response.status = 200
        response.text = AsyncMock(return_value="")
        response.json = AsyncMock(return_value={
            "quote": {"bp": 149.50, "ap": 149.75, "bs": 100, "as": 200}
        })
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=response)
        cm.__aexit__ = AsyncMock(return_value=False)
        session.request = MagicMock(return_value=cm)

        connector.session = session
        connector._connected = True

        order_book = await connector.get_order_book("AAPL")

        assert order_book.symbol == "AAPL"
        assert len(order_book.bids) == 1
        assert len(order_book.asks) == 1
        assert order_book.bids[0][0] == 149.50
        assert order_book.asks[0][0] == 149.75

    @pytest.mark.asyncio
    async def test_get_ticker(self, connector):
        """get_ticker returns last price, bid, ask, volume"""
        call_count = 0
        responses = [
            {"trade": {"p": 150.00}},                          # latest trade
            {"quote": {"bp": 149.90, "ap": 150.10}},           # latest quote
            {"dailyBar": {"v": 50000000}},                     # snapshot
        ]

        session = MagicMock()

        async def fake_json():
            nonlocal call_count
            data = responses[call_count % len(responses)]
            call_count += 1
            return data

        response = AsyncMock()
        response.status = 200
        response.text = AsyncMock(return_value="")
        response.json = fake_json
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=response)
        cm.__aexit__ = AsyncMock(return_value=False)
        session.request = MagicMock(return_value=cm)

        connector.session = session
        connector._connected = True

        ticker = await connector.get_ticker("AAPL")

        assert ticker.symbol == "AAPL"
        assert ticker.lastPrice == 150.00
        assert ticker.bidPrice == 149.90
        assert ticker.askPrice == 150.10
        assert ticker.volume24h == 50000000


# ── Trading ───────────────────────────────────────────────────────────────────

class TestAlpacaConnectorTrading:

    def _setup_ticker_mock(self, connector, last=150.0, bid=149.9, ask=150.1, vol=1000000):
        """Patch get_ticker to return a fixed Ticker"""
        ticker = Ticker(
            symbol="AAPL",
            lastPrice=last,
            bidPrice=bid,
            askPrice=ask,
            volume24h=vol,
            timestamp=int(datetime.now().timestamp() * 1000),
        )
        connector.get_ticker = AsyncMock(return_value=ticker)

    @pytest.mark.asyncio
    async def test_place_market_buy_order(self, connector):
        """Market buy executes at ask price and deducts balance"""
        self._setup_ticker_mock(connector, ask=150.10)
        connector._connected = True

        order = Order(symbol="AAPL", side=OrderSide.BUY, type=OrderType.MARKET, size=10.0)
        initial_balance = connector.paper_balance

        trade = await connector.place_order(order)

        assert trade.symbol == "AAPL"
        assert trade.side == OrderSide.BUY
        assert trade.size == 10.0
        assert trade.price == 150.10
        assert connector.paper_balance < initial_balance

    @pytest.mark.asyncio
    async def test_place_market_sell_order(self, connector):
        """Market sell executes at bid price and increases balance"""
        self._setup_ticker_mock(connector, bid=149.90)
        connector._connected = True

        # Seed a position first
        connector.paper_positions["AAPL"] = Position(
            symbol="AAPL", size=10.0, avgPrice=140.0,
            currentPrice=149.90, unrealizedPnl=99.0, realizedPnl=0,
        )
        initial_balance = connector.paper_balance

        order = Order(symbol="AAPL", side=OrderSide.SELL, type=OrderType.MARKET, size=5.0)
        trade = await connector.place_order(order)

        assert trade.side == OrderSide.SELL
        assert trade.price == 149.90
        assert connector.paper_balance > initial_balance

    @pytest.mark.asyncio
    async def test_place_limit_buy_order(self, connector):
        """Limit buy executes at specified limit price"""
        self._setup_ticker_mock(connector)
        connector._connected = True

        order = Order(
            symbol="AAPL", side=OrderSide.BUY, type=OrderType.LIMIT,
            size=5.0, price=148.00,
        )
        trade = await connector.place_order(order)

        assert trade.price == 148.00

    @pytest.mark.asyncio
    async def test_place_order_insufficient_balance(self, connector):
        """Order fails when cost exceeds paper balance"""
        self._setup_ticker_mock(connector, ask=150.10)
        connector._connected = True
        connector.paper_balance = 100.0  # Very low

        order = Order(symbol="AAPL", side=OrderSide.BUY, type=OrderType.MARKET, size=1000.0)

        with pytest.raises(ValueError, match="Insufficient balance"):
            await connector.place_order(order)

    @pytest.mark.asyncio
    async def test_place_order_invalid_size(self, connector):
        """Order fails with zero or negative size"""
        connector._connected = True

        order = Order(symbol="AAPL", side=OrderSide.BUY, type=OrderType.MARKET, size=0)

        with pytest.raises(ValueError, match="Invalid order size"):
            await connector.place_order(order)

    @pytest.mark.asyncio
    async def test_place_limit_order_invalid_price(self, connector):
        """Limit order fails with non-positive price"""
        connector._connected = True

        order = Order(
            symbol="AAPL", side=OrderSide.BUY, type=OrderType.LIMIT,
            size=5.0, price=-10.0,
        )

        with pytest.raises(ValueError, match="Invalid limit price"):
            await connector.place_order(order)

    @pytest.mark.asyncio
    async def test_cancel_order_is_noop(self, connector):
        """cancel_order is a no-op in paper trading (no exception)"""
        await connector.cancel_order("PAPER-ALPACA-1")  # should not raise

    @pytest.mark.asyncio
    async def test_trade_id_increments(self, connector):
        """Each trade gets a unique incrementing ID"""
        self._setup_ticker_mock(connector)
        connector._connected = True

        order = Order(symbol="AAPL", side=OrderSide.BUY, type=OrderType.MARKET, size=1.0)
        t1 = await connector.place_order(order)
        t2 = await connector.place_order(order)

        assert t1.id != t2.id
        assert "PAPER-ALPACA" in t1.id


# ── Positions ─────────────────────────────────────────────────────────────────

class TestAlpacaConnectorPositions:

    @pytest.mark.asyncio
    async def test_get_position_empty(self, connector):
        """Returns zero position when no trade placed"""
        position = await connector.get_position("AAPL")

        assert position.symbol == "AAPL"
        assert position.size == 0
        assert position.avgPrice == 0

    @pytest.mark.asyncio
    async def test_get_positions_after_buy(self, connector):
        """Position is created after a buy order"""
        ticker = Ticker(
            symbol="AAPL", lastPrice=150.0, bidPrice=149.9, askPrice=150.1,
            volume24h=1000000, timestamp=int(datetime.now().timestamp() * 1000),
        )
        connector.get_ticker = AsyncMock(return_value=ticker)
        connector._connected = True

        order = Order(symbol="AAPL", side=OrderSide.BUY, type=OrderType.MARKET, size=10.0)
        await connector.place_order(order)

        positions = await connector.get_positions()

        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].size == 10.0

    @pytest.mark.asyncio
    async def test_position_avg_price_after_two_buys(self, connector):
        """Average price is correctly weighted after two buys"""
        ticker = Ticker(
            symbol="AAPL", lastPrice=150.0, bidPrice=149.9, askPrice=150.0,
            volume24h=1000000, timestamp=int(datetime.now().timestamp() * 1000),
        )
        connector.get_ticker = AsyncMock(return_value=ticker)
        connector._connected = True

        order1 = Order(symbol="AAPL", side=OrderSide.BUY, type=OrderType.MARKET, size=10.0)
        await connector.place_order(order1)

        ticker2 = Ticker(
            symbol="AAPL", lastPrice=160.0, bidPrice=159.9, askPrice=160.0,
            volume24h=1000000, timestamp=int(datetime.now().timestamp() * 1000),
        )
        connector.get_ticker = AsyncMock(return_value=ticker2)

        order2 = Order(symbol="AAPL", side=OrderSide.BUY, type=OrderType.MARKET, size=10.0)
        await connector.place_order(order2)

        position = await connector.get_position("AAPL")
        assert position.size == 20.0
        # avg = (10*150 + 10*160) / 20 = 155
        assert position.avgPrice == pytest.approx(155.0)

    @pytest.mark.asyncio
    async def test_position_unrealized_pnl(self, connector):
        """Unrealized PnL is positive when price rises after buy"""
        ticker = Ticker(
            symbol="AAPL", lastPrice=150.0, bidPrice=149.9, askPrice=150.0,
            volume24h=1000000, timestamp=int(datetime.now().timestamp() * 1000),
        )
        connector.get_ticker = AsyncMock(return_value=ticker)
        connector._connected = True

        order = Order(symbol="AAPL", side=OrderSide.BUY, type=OrderType.MARKET, size=10.0)
        await connector.place_order(order)

        # Price rises
        ticker_up = Ticker(
            symbol="AAPL", lastPrice=160.0, bidPrice=159.9, askPrice=160.0,
            volume24h=1000000, timestamp=int(datetime.now().timestamp() * 1000),
        )
        connector.get_ticker = AsyncMock(return_value=ticker_up)

        positions = await connector.get_positions()
        assert positions[0].unrealizedPnl > 0


# ── Balance ───────────────────────────────────────────────────────────────────

class TestAlpacaConnectorBalance:

    @pytest.mark.asyncio
    async def test_initial_balance(self, connector):
        """Initial balance is $100k with no positions"""
        balance = await connector.get_balance()

        assert balance["USD"] == 100000.0
        assert balance["total"] == 100000.0
        assert balance["positions_value"] == 0

    @pytest.mark.asyncio
    async def test_balance_decreases_after_buy(self, connector):
        """Balance decreases after buying stock"""
        ticker = Ticker(
            symbol="AAPL", lastPrice=150.0, bidPrice=149.9, askPrice=150.0,
            volume24h=1000000, timestamp=int(datetime.now().timestamp() * 1000),
        )
        connector.get_ticker = AsyncMock(return_value=ticker)
        connector._connected = True

        order = Order(symbol="AAPL", side=OrderSide.BUY, type=OrderType.MARKET, size=100.0)
        await connector.place_order(order)

        balance = await connector.get_balance()
        assert balance["USD"] < 100000.0
        assert balance["positions_value"] > 0


# ── Error Handling & Retries ──────────────────────────────────────────────────

class TestAlpacaConnectorErrorHandling:

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, connector):
        """Request retries on timeout and succeeds on second attempt"""
        connector._connected = True

        success_response = AsyncMock()
        success_response.status = 200
        success_response.text = AsyncMock(return_value="")
        success_response.json = AsyncMock(return_value={"id": "account123"})
        success_cm = AsyncMock()
        success_cm.__aenter__ = AsyncMock(return_value=success_response)
        success_cm.__aexit__ = AsyncMock(return_value=False)

        timeout_cm = AsyncMock()
        timeout_cm.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        timeout_cm.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(side_effect=[timeout_cm, success_cm])
        connector.session = session

        result = await connector._request("GET", "/account")
        assert result == {"id": "account123"}

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_raises(self, connector):
        """Request raises after exhausting all retries"""
        connector._connected = True
        connector.MAX_RETRIES = 2

        timeout_cm = AsyncMock()
        timeout_cm.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        timeout_cm.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(return_value=timeout_cm)
        connector.session = session

        with pytest.raises(asyncio.TimeoutError):
            await connector._request("GET", "/account")

    @pytest.mark.asyncio
    async def test_http_error_triggers_retry(self, connector):
        """Non-200 HTTP response triggers retry"""
        connector._connected = True

        error_response = AsyncMock()
        error_response.status = 500
        error_response.text = AsyncMock(return_value="Internal Server Error")
        error_cm = AsyncMock()
        error_cm.__aenter__ = AsyncMock(return_value=error_response)
        error_cm.__aexit__ = AsyncMock(return_value=False)

        success_response = AsyncMock()
        success_response.status = 200
        success_response.text = AsyncMock(return_value="")
        success_response.json = AsyncMock(return_value={"ok": True})
        success_cm = AsyncMock()
        success_cm.__aenter__ = AsyncMock(return_value=success_response)
        success_cm.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(side_effect=[error_cm, success_cm])
        connector.session = session

        result = await connector._request("GET", "/account")
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_request_without_session_raises(self, connector):
        """Calling _request without connecting raises an exception"""
        connector.session = None

        with pytest.raises(Exception, match="Not connected"):
            await connector._request("GET", "/account")


# ── Auth Headers ──────────────────────────────────────────────────────────────

class TestAlpacaConnectorHeaders:

    def test_headers_include_api_key(self, connector):
        """Auth headers include APCA-API-KEY-ID"""
        headers = connector._build_headers()
        assert headers["APCA-API-KEY-ID"] == "test_key_id"

    def test_headers_include_secret_key(self, connector):
        """Auth headers include APCA-API-SECRET-KEY"""
        headers = connector._build_headers()
        assert headers["APCA-API-SECRET-KEY"] == "test_secret_key"

    def test_headers_without_credentials(self):
        """Headers still valid when no credentials provided"""
        c = AlpacaConnector()
        headers = c._build_headers()
        assert "APCA-API-KEY-ID" not in headers
        assert "APCA-API-SECRET-KEY" not in headers
        assert headers["Accept"] == "application/json"
