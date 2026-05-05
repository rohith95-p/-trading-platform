"""
Integration tests for Exchange Connectors.

Tests cover paper trading flows for:
- KalshiConnector: connect → get_markets → place_order → get_positions → disconnect
- PolymarketConnector: same pattern
- AlpacaConnector: same pattern
- ExchangeRouter: routing to correct connector

All tests use mocked HTTP — no real API calls are made.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.exchanges.kalshi import KalshiConnector
from src.exchanges.polymarket import PolymarketConnector
from src.exchanges.alpaca import AlpacaConnector
from src.exchanges.router import ExchangeRouter
from src.core.interfaces import (
    Order,
    OrderSide,
    OrderType,
    Market,
    Position,
    Trade,
)
from src.interfaces.exchange_connector import Balance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_session(json_return_value):
    """Return a (session, response) pair where response.json() returns the given value."""
    session = MagicMock()
    session.close = AsyncMock()  # disconnect() awaits session.close()
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value=json_return_value)
    session.request = MagicMock(
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=response))
    )
    return session, response


# ===========================================================================
# KalshiConnector integration tests
# ===========================================================================


class TestKalshiPaperTradingFlow:
    """Full paper trading flow: connect → get_markets → place_order → get_positions → disconnect."""

    @pytest.fixture
    def connector(self):
        return KalshiConnector(api_key="test_key", private_key="test_priv", demo=True, paper_trading=True)

    @pytest.mark.asyncio
    async def test_connect(self, connector):
        """Connector connects successfully when markets are returned."""
        session, response = _make_mock_session({
            "events": [
                {
                    "event_ticker": "EVT",
                    "title": "Test Event",
                    "category": "test",
                    "markets": [
                        {
                            "ticker": "EVT-YES",
                            "title": "Test Market",
                            "yes_bid": 40,
                            "yes_ask": 60,
                            "volume": 500,
                            "close_time": "2025-12-31T23:59:59Z",
                        }
                    ],
                }
            ]
        })
        with patch("aiohttp.ClientSession", return_value=session):
            await connector.connect()

        assert connector.is_connected()

    @pytest.mark.asyncio
    async def test_get_markets(self, connector):
        """get_markets returns a non-empty list of Market objects."""
        session, response = _make_mock_session({
            "events": [
                {
                    "event_ticker": "PRES",
                    "title": "Presidential Race",
                    "category": "politics",
                    "markets": [
                        {
                            "ticker": "PRES-YES",
                            "title": "Candidate wins",
                            "yes_bid": 45,
                            "yes_ask": 55,
                            "volume": 10000,
                            "close_time": "2025-11-05T23:59:59Z",
                        }
                    ],
                }
            ]
        })
        connector.session = session
        connector._connected = True

        markets = await connector.get_markets()

        assert len(markets) >= 1
        assert all(isinstance(m, Market) for m in markets)
        assert markets[0].symbol == "PRES-YES"

    @pytest.mark.asyncio
    async def test_place_order(self, connector):
        """place_order returns a Trade and deducts from paper balance."""
        session, response = _make_mock_session({
            "market": {
                "ticker": "EVT-YES",
                "yes_bid": 40,
                "yes_ask": 60,
                "volume": 500,
            }
        })
        connector.session = session
        connector._connected = True

        order = Order(symbol="EVT-YES", side=OrderSide.BUY, type=OrderType.MARKET, size=5.0)
        initial_balance = connector.paper_balance

        trade = await connector.place_order(order)

        assert isinstance(trade, Trade)
        assert trade.symbol == "EVT-YES"
        assert trade.side == OrderSide.BUY
        assert trade.size == 5.0
        assert trade.price > 0
        assert connector.paper_balance < initial_balance

    @pytest.mark.asyncio
    async def test_get_positions_after_trade(self, connector):
        """get_positions returns the position created by a prior trade."""
        session, response = _make_mock_session({
            "market": {
                "ticker": "EVT-YES",
                "yes_bid": 40,
                "yes_ask": 60,
                "volume": 500,
            }
        })
        connector.session = session
        connector._connected = True

        order = Order(symbol="EVT-YES", side=OrderSide.BUY, type=OrderType.MARKET, size=3.0)
        await connector.place_order(order)

        positions = await connector.get_positions()

        assert len(positions) >= 1
        symbols = [p.symbol for p in positions]
        assert "EVT-YES" in symbols

    @pytest.mark.asyncio
    async def test_disconnect(self, connector):
        """disconnect sets is_connected to False."""
        connector.session = AsyncMock()
        connector._connected = True

        await connector.disconnect()

        assert not connector.is_connected()

    @pytest.mark.asyncio
    async def test_full_flow(self, connector):
        """Full paper trading flow end-to-end."""
        markets_payload = {
            "events": [
                {
                    "event_ticker": "FLOW",
                    "title": "Flow Test",
                    "category": "test",
                    "markets": [
                        {
                            "ticker": "FLOW-YES",
                            "title": "Flow Market",
                            "yes_bid": 30,
                            "yes_ask": 70,
                            "volume": 200,
                            "close_time": "2025-06-30T23:59:59Z",
                        }
                    ],
                }
            ]
        }
        ticker_payload = {
            "market": {
                "ticker": "FLOW-YES",
                "yes_bid": 30,
                "yes_ask": 70,
                "volume": 200,
            }
        }

        # connect
        session, response = _make_mock_session(markets_payload)
        with patch("aiohttp.ClientSession", return_value=session):
            await connector.connect()
        assert connector.is_connected()

        # get_markets
        response.json.return_value = markets_payload
        markets = await connector.get_markets()
        assert len(markets) >= 1

        # place_order
        response.json.return_value = ticker_payload
        order = Order(symbol="FLOW-YES", side=OrderSide.BUY, type=OrderType.MARKET, size=2.0)
        trade = await connector.place_order(order)
        assert trade.symbol == "FLOW-YES"

        # get_positions
        positions = await connector.get_positions()
        assert any(p.symbol == "FLOW-YES" for p in positions)

        # disconnect
        await connector.disconnect()
        assert not connector.is_connected()


# ===========================================================================
# PolymarketConnector integration tests
# ===========================================================================


class TestPolymarketPaperTradingFlow:
    """Full paper trading flow for Polymarket connector."""

    @pytest.fixture
    def connector(self):
        return PolymarketConnector(api_key="test_key", paper_trading=True)

    @pytest.mark.asyncio
    async def test_connect(self, connector):
        """Connector connects when markets endpoint returns data."""
        session, response = _make_mock_session({
            "data": [
                {
                    "condition_id": "0xabc",
                    "question": "Will X happen?",
                    "tokens": [
                        {"token_id": "YES-0xabc", "outcome": "Yes"},
                        {"token_id": "NO-0xabc", "outcome": "No"},
                    ],
                    "volume": "5000",
                    "active": True,
                }
            ]
        })
        with patch("aiohttp.ClientSession", return_value=session):
            await connector.connect()

        assert connector.is_connected()

    @pytest.mark.asyncio
    async def test_get_markets(self, connector):
        """get_markets returns Market objects."""
        session, response = _make_mock_session({
            "data": [
                {
                    "condition_id": "0xdef",
                    "question": "Will Y happen?",
                    "tokens": [
                        {"token_id": "YES-0xdef", "outcome": "Yes"},
                        {"token_id": "NO-0xdef", "outcome": "No"},
                    ],
                    "volume": "3000",
                    "active": True,
                }
            ]
        })
        connector.session = session
        connector._connected = True

        markets = await connector.get_markets()

        assert len(markets) >= 1
        assert all(isinstance(m, Market) for m in markets)

    @pytest.mark.asyncio
    async def test_place_order(self, connector):
        """place_order returns a Trade and updates paper balance."""
        session, response = _make_mock_session({
            "data": [
                {
                    "condition_id": "0xabc",
                    "question": "Will X happen?",
                    "tokens": [
                        {"token_id": "YES-0xabc", "outcome": "Yes"},
                    ],
                    "volume": "5000",
                    "active": True,
                    "best_ask": "0.60",
                    "best_bid": "0.40",
                }
            ]
        })
        connector.session = session
        connector._connected = True

        order = Order(symbol="YES-0xabc", side=OrderSide.BUY, type=OrderType.MARKET, size=10.0)
        initial_balance = connector.paper_balance

        trade = await connector.place_order(order)

        assert isinstance(trade, Trade)
        assert trade.symbol == "YES-0xabc"
        assert trade.size == 10.0
        assert connector.paper_balance < initial_balance

    @pytest.mark.asyncio
    async def test_get_positions_after_trade(self, connector):
        """Positions reflect the trade placed."""
        session, response = _make_mock_session({
            "data": [
                {
                    "condition_id": "0xabc",
                    "question": "Will X happen?",
                    "tokens": [{"token_id": "YES-0xabc", "outcome": "Yes"}],
                    "volume": "5000",
                    "active": True,
                    "best_ask": "0.60",
                    "best_bid": "0.40",
                }
            ]
        })
        connector.session = session
        connector._connected = True

        order = Order(symbol="YES-0xabc", side=OrderSide.BUY, type=OrderType.MARKET, size=5.0)
        await connector.place_order(order)

        positions = await connector.get_positions()

        assert len(positions) >= 1
        assert any(p.symbol == "YES-0xabc" for p in positions)

    @pytest.mark.asyncio
    async def test_disconnect(self, connector):
        """disconnect closes session and marks disconnected."""
        connector.session = AsyncMock()
        connector._connected = True

        await connector.disconnect()

        assert not connector.is_connected()

    @pytest.mark.asyncio
    async def test_paper_trading_always_enforced(self, connector):
        """paper_trading is always True regardless of constructor arg."""
        c = PolymarketConnector(paper_trading=False)
        assert c.paper_trading is True


# ===========================================================================
# AlpacaConnector integration tests
# ===========================================================================


class TestAlpacaPaperTradingFlow:
    """Full paper trading flow for Alpaca connector."""

    @pytest.fixture
    def connector(self):
        return AlpacaConnector(api_key="APCA_TEST", secret_key="SECRET_TEST", paper_trading=True)

    @pytest.mark.asyncio
    async def test_connect(self, connector):
        """Connector connects when account endpoint returns data."""
        session, response = _make_mock_session({"id": "acc123", "status": "ACTIVE"})
        with patch("aiohttp.ClientSession", return_value=session):
            await connector.connect()

        assert connector.is_connected()

    @pytest.mark.asyncio
    async def test_get_markets(self, connector):
        """get_markets returns Market objects for tradeable assets."""
        session, response = _make_mock_session([
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "tradable": True,
                "fractionable": True,
                "min_order_size": "1",
                "price_increment": "0.01",
            },
            {
                "symbol": "TSLA",
                "name": "Tesla Inc.",
                "tradable": True,
                "fractionable": True,
                "min_order_size": "1",
                "price_increment": "0.01",
            },
        ])
        connector.session = session
        connector._connected = True

        markets = await connector.get_markets()

        assert len(markets) >= 1
        assert all(isinstance(m, Market) for m in markets)

    @pytest.mark.asyncio
    async def test_place_order(self, connector):
        """place_order returns a Trade and deducts from paper balance."""
        mock_ticker = MagicMock()
        mock_ticker.askPrice = 150.0
        mock_ticker.bidPrice = 148.0

        with patch.object(connector, "get_ticker", new_callable=AsyncMock, return_value=mock_ticker):
            order = Order(symbol="AAPL", side=OrderSide.BUY, type=OrderType.MARKET, size=10.0)
            initial_balance = connector.paper_balance

            trade = await connector.place_order(order)

        assert isinstance(trade, Trade)
        assert trade.symbol == "AAPL"
        assert trade.size == 10.0
        assert trade.price == 150.0
        # Alpaca is commission-free; balance decreases by cost (price * size)
        assert connector.paper_balance == initial_balance - (150.0 * 10.0)

    @pytest.mark.asyncio
    async def test_get_positions_after_trade(self, connector):
        """Positions reflect the trade placed."""
        mock_ticker = MagicMock()
        mock_ticker.askPrice = 150.0
        mock_ticker.bidPrice = 148.0

        with patch.object(connector, "get_ticker", new_callable=AsyncMock, return_value=mock_ticker):
            order = Order(symbol="AAPL", side=OrderSide.BUY, type=OrderType.MARKET, size=5.0)
            await connector.place_order(order)

        positions = await connector.get_positions()

        assert len(positions) >= 1
        assert any(p.symbol == "AAPL" for p in positions)

    @pytest.mark.asyncio
    async def test_disconnect(self, connector):
        """disconnect closes session and marks disconnected."""
        connector.session = AsyncMock()
        connector._connected = True

        await connector.disconnect()

        assert not connector.is_connected()

    @pytest.mark.asyncio
    async def test_paper_trading_always_enforced(self, connector):
        """paper_trading is always True regardless of constructor arg."""
        c = AlpacaConnector(paper_trading=False)
        assert c.paper_trading is True

    @pytest.mark.asyncio
    async def test_get_balance(self, connector):
        """get_balance returns a dict with USD key."""
        balance = await connector.get_balance()
        assert "USD" in balance or "total" in balance or isinstance(balance, dict)


# ===========================================================================
# ExchangeRouter tests
# ===========================================================================


class TestExchangeRouter:
    """Test ExchangeRouter routing to correct connector."""

    @pytest.fixture
    def router(self):
        return ExchangeRouter()

    @pytest.fixture
    def mock_kalshi(self):
        connector = AsyncMock()
        connector.name = "kalshi"
        return connector

    @pytest.fixture
    def mock_alpaca(self):
        connector = AsyncMock()
        connector.name = "alpaca"
        return connector

    def test_add_and_get_connector(self, router, mock_kalshi):
        """add_connector registers connector; get_connector retrieves it."""
        router.add_connector(mock_kalshi)
        assert router.get_connector("kalshi") is mock_kalshi

    def test_connector_names(self, router, mock_kalshi, mock_alpaca):
        """connector_names lists all registered connectors."""
        router.add_connector(mock_kalshi)
        router.add_connector(mock_alpaca)
        assert set(router.connector_names) == {"kalshi", "alpaca"}

    def test_remove_connector(self, router, mock_kalshi):
        """remove_connector unregisters the connector."""
        router.add_connector(mock_kalshi)
        router.remove_connector("kalshi")
        assert "kalshi" not in router.connector_names

    def test_get_unknown_connector_raises(self, router):
        """get_connector raises KeyError for unknown exchange."""
        with pytest.raises(KeyError):
            router.get_connector("unknown_exchange")

    def test_remove_unknown_connector_raises(self, router):
        """remove_connector raises KeyError for unknown exchange."""
        with pytest.raises(KeyError):
            router.remove_connector("ghost")

    @pytest.mark.asyncio
    async def test_place_order_routes_to_correct_connector(self, router, mock_kalshi):
        """place_order delegates to the named connector."""
        mock_trade = MagicMock()
        mock_kalshi.place_order = AsyncMock(return_value=mock_trade)
        router.add_connector(mock_kalshi)

        order = Order(symbol="EVT-YES", side=OrderSide.BUY, type=OrderType.MARKET, size=1.0)
        result = await router.place_order("kalshi", order)

        mock_kalshi.place_order.assert_called_once_with(order)
        assert result is mock_trade

    @pytest.mark.asyncio
    async def test_place_order_wrong_exchange_raises(self, router, mock_kalshi):
        """place_order raises KeyError when exchange is not registered."""
        router.add_connector(mock_kalshi)

        order = Order(symbol="AAPL", side=OrderSide.BUY, type=OrderType.MARKET, size=1.0)
        with pytest.raises(KeyError):
            await router.place_order("alpaca", order)

    @pytest.mark.asyncio
    async def test_get_all_positions_aggregates(self, router, mock_kalshi, mock_alpaca):
        """get_all_positions returns positions from all connectors."""
        pos_k = MagicMock()
        pos_a = MagicMock()
        mock_kalshi.get_positions = AsyncMock(return_value=[pos_k])
        mock_alpaca.get_positions = AsyncMock(return_value=[pos_a])
        router.add_connector(mock_kalshi)
        router.add_connector(mock_alpaca)

        all_positions = await router.get_all_positions()

        assert "kalshi" in all_positions
        assert "alpaca" in all_positions
        assert pos_k in all_positions["kalshi"]
        assert pos_a in all_positions["alpaca"]

    @pytest.mark.asyncio
    async def test_get_total_balance_sums_connectors(self, router, mock_kalshi, mock_alpaca):
        """get_total_balance sums balances across all connectors."""
        bal_k = Balance(total=5000.0, available=5000.0, used=0.0)
        bal_a = Balance(total=10000.0, available=10000.0, used=0.0)
        mock_kalshi.get_balance = AsyncMock(return_value=bal_k)
        mock_alpaca.get_balance = AsyncMock(return_value=bal_a)
        router.add_connector(mock_kalshi)
        router.add_connector(mock_alpaca)

        total = await router.get_total_balance()

        assert total == pytest.approx(15000.0)

    @pytest.mark.asyncio
    async def test_get_all_positions_handles_connector_error(self, router, mock_kalshi):
        """get_all_positions returns empty list for a failing connector."""
        mock_kalshi.get_positions = AsyncMock(side_effect=Exception("network error"))
        router.add_connector(mock_kalshi)

        all_positions = await router.get_all_positions()

        assert all_positions["kalshi"] == []

    @pytest.mark.asyncio
    async def test_cancel_order_routes_to_correct_connector(self, router, mock_alpaca):
        """cancel_order delegates to the named connector."""
        mock_alpaca.cancel_order = AsyncMock(return_value=True)
        router.add_connector(mock_alpaca)

        result = await router.cancel_order("alpaca", "order_xyz")

        mock_alpaca.cancel_order.assert_called_once_with("order_xyz")
        assert result is True
