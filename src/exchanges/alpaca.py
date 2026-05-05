"""
Alpaca Exchange Connector

Implements ExchangeConnector interface for Alpaca stock broker.
Uses Alpaca's paper trading API endpoint exclusively.
Handles equities (stocks) trading with paper money only.

Implements Requirement 5 (Exchange Connectivity - Alpaca)
"""

import aiohttp
import asyncio
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime

from src.core.interfaces import (
    ExchangeConnector,
    ExchangeType,
    Market,
    OrderBook,
    Ticker,
    Order,
    Trade,
    Position,
    OrderSide,
    OrderType,
)

logger = logging.getLogger(__name__)


class AlpacaConnector(ExchangeConnector):
    """
    Alpaca stock broker connector.

    Features:
    - Paper trading mode only (Alpaca paper trading API endpoint)
    - Stock market data access (equities)
    - Order execution simulation via paper API
    - Position tracking
    - Rate limiting handling
    - Exponential backoff retries (max 3 attempts)

    Note: This connector always uses the Alpaca paper trading endpoint
    (https://paper-api.alpaca.markets/v2) and will never execute real trades.
    """

    # API endpoints — paper trading only
    PAPER_BASE_URL = "https://paper-api.alpaca.markets/v2"
    DATA_BASE_URL = "https://data.alpaca.markets/v2"

    # Rate limiting (Alpaca allows 200 req/min for free tier)
    RATE_LIMIT = 3  # requests per second (conservative)
    RATE_LIMIT_WINDOW = 1.0  # seconds

    # Retries with exponential backoff
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0  # seconds

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper_trading: bool = True,
    ):
        """
        Initialize Alpaca connector.

        Args:
            api_key: Alpaca API key ID (APCA-API-KEY-ID)
            secret_key: Alpaca secret key (APCA-API-SECRET-KEY)
            paper_trading: Always True — real trading is not supported
        """
        super().__init__("alpaca", ExchangeType.STOCKS)
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper_trading = True  # Always enforce paper trading
        self.base_url = self.PAPER_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_count = 0
        self.last_request_time = 0.0

        # Paper trading state
        self.paper_positions: Dict[str, Position] = {}
        self.paper_balance = 100000.0  # Alpaca paper accounts start with $100k
        self.paper_trades: List[Trade] = []
        self.next_trade_id = 1

        if not paper_trading:
            logger.warning(
                "AlpacaConnector always operates in paper trading mode. "
                "Real trading is not supported. Using paper-api.alpaca.markets."
            )

    async def connect(self) -> None:
        """Authenticate and establish connection to Alpaca paper trading API"""
        try:
            self.session = aiohttp.ClientSession()

            # Start rate limiter background task
            asyncio.create_task(self._rate_limiter())

            # Test connection by fetching account info
            account = await self._request("GET", "/account")
            if account:
                self._connected = True
                logger.info(
                    f"Connected to Alpaca paper trading API ({self.base_url})"
                )
            else:
                raise Exception("Failed to fetch account from Alpaca paper API")
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            if self.session:
                await self.session.close()
            raise

    async def disconnect(self) -> None:
        """Close connection to Alpaca"""
        if self.session:
            await self.session.close()
            self._connected = False
            logger.info("Disconnected from Alpaca")

    async def get_markets(self) -> List[Market]:
        """Get list of tradeable assets (stocks) on Alpaca"""
        try:
            response = await self._request(
                "GET", "/assets", {"status": "active", "asset_class": "us_equity"}
            )

            markets = []
            for asset in response if isinstance(response, list) else []:
                if not asset.get("tradable", False):
                    continue
                market = Market(
                    symbol=asset.get("symbol", ""),
                    baseAsset=asset.get("symbol", ""),
                    quoteAsset="USD",
                    minOrderSize=1.0,
                    maxOrderSize=1000000.0,
                    pricePrecision=2,
                    sizePrecision=0,
                )
                markets.append(market)

            return markets
        except Exception as e:
            logger.error(f"Failed to get markets from Alpaca: {e}")
            raise

    async def get_order_book(self, symbol: str) -> OrderBook:
        """Get order book (quotes) for a stock symbol"""
        try:
            response = await self._data_request(
                "GET", f"/stocks/{symbol}/quotes/latest"
            )

            quote = response.get("quote", {})
            bid_price = float(quote.get("bp", 0))
            ask_price = float(quote.get("ap", 0))
            bid_size = float(quote.get("bs", 0))
            ask_size = float(quote.get("as", 0))

            bids = [(bid_price, bid_size)] if bid_price > 0 else []
            asks = [(ask_price, ask_size)] if ask_price > 0 else []

            return OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=int(datetime.now().timestamp() * 1000),
            )
        except Exception as e:
            logger.error(f"Failed to get order book for {symbol}: {e}")
            raise

    async def get_ticker(self, symbol: str) -> Ticker:
        """Get ticker information for a stock symbol"""
        try:
            response = await self._data_request(
                "GET", f"/stocks/{symbol}/trades/latest"
            )

            trade_data = response.get("trade", {})
            last_price = float(trade_data.get("p", 0))

            # Fetch latest quote for bid/ask
            quote_response = await self._data_request(
                "GET", f"/stocks/{symbol}/quotes/latest"
            )
            quote = quote_response.get("quote", {})
            bid_price = float(quote.get("bp", last_price))
            ask_price = float(quote.get("ap", last_price))

            # Fetch snapshot for volume
            snapshot_response = await self._data_request(
                "GET", f"/stocks/{symbol}/snapshot"
            )
            snapshot = snapshot_response.get("snapshot", snapshot_response)
            daily_bar = snapshot.get("dailyBar", {})
            volume = float(daily_bar.get("v", 0))

            return Ticker(
                symbol=symbol,
                lastPrice=last_price,
                bidPrice=bid_price,
                askPrice=ask_price,
                volume24h=volume,
                timestamp=int(datetime.now().timestamp() * 1000),
            )
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            raise

    async def place_order(self, order: Order) -> Trade:
        """
        Place order on Alpaca (PAPER TRADING ONLY).

        Simulates order execution using current market prices.
        """
        try:
            self._validate_order(order)

            ticker = await self.get_ticker(order.symbol)

            if order.type == OrderType.MARKET:
                execution_price = (
                    ticker.askPrice if order.side == OrderSide.BUY else ticker.bidPrice
                )
            elif order.type == OrderType.LIMIT:
                if order.price is None:
                    raise ValueError("Limit order requires a price")
                execution_price = order.price
            else:
                raise ValueError(f"Unsupported order type: {order.type}")

            cost = execution_price * order.size
            fee = cost * 0.0  # Alpaca is commission-free; simulate 0 fee
            total_cost = cost + fee

            if order.side == OrderSide.BUY and total_cost > self.paper_balance:
                raise ValueError(
                    f"Insufficient balance: {self.paper_balance:.2f} < {total_cost:.2f}"
                )

            trade_id = f"PAPER-ALPACA-{self.next_trade_id}"
            self.next_trade_id += 1

            trade = Trade(
                id=trade_id,
                orderId=trade_id,
                symbol=order.symbol,
                side=order.side,
                price=execution_price,
                size=order.size,
                fee=fee,
                timestamp=int(datetime.now().timestamp() * 1000),
            )

            if order.side == OrderSide.BUY:
                self.paper_balance -= total_cost
            else:
                self.paper_balance += cost - fee

            await self._update_position(trade)
            self.paper_trades.append(trade)

            logger.info(f"Paper trade executed on Alpaca: {trade}")
            return trade
        except Exception as e:
            logger.error(f"Failed to place order on Alpaca: {e}")
            raise

    async def cancel_order(self, order_id: str) -> None:
        """Cancel order (paper trading — no-op)"""
        logger.info(f"Paper trading: Order {order_id} cancellation simulated on Alpaca")

    async def get_position(self, symbol: str) -> Position:
        """Get position for a stock symbol"""
        try:
            if symbol in self.paper_positions:
                return self.paper_positions[symbol]

            return Position(
                symbol=symbol,
                size=0,
                avgPrice=0,
                currentPrice=0,
                unrealizedPnl=0,
                realizedPnl=0,
            )
        except Exception as e:
            logger.error(f"Failed to get position for {symbol}: {e}")
            raise

    async def get_positions(self) -> List[Position]:
        """Get all open positions"""
        try:
            positions = []
            for symbol, position in self.paper_positions.items():
                if position.size != 0:
                    try:
                        ticker = await self.get_ticker(symbol)
                        position.currentPrice = ticker.lastPrice
                        position.unrealizedPnl = (
                            (position.currentPrice - position.avgPrice) * position.size
                        )
                        positions.append(position)
                    except Exception as e:
                        logger.warning(f"Failed to update position price for {symbol}: {e}")
                        positions.append(position)
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise

    async def get_balance(self) -> Dict[str, float]:
        """Get account balance (paper trading)"""
        try:
            positions_value = sum(
                pos.size * pos.currentPrice for pos in self.paper_positions.values()
            )
            return {
                "USD": self.paper_balance,
                "total": self.paper_balance + positions_value,
                "positions_value": positions_value,
            }
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise

    # ── Private helpers ──────────────────────────────────────────────────────

    def _validate_order(self, order: Order) -> None:
        """Validate order parameters for stock trading"""
        if order.size <= 0:
            raise ValueError(f"Invalid order size: {order.size}")

        if order.type == OrderType.LIMIT:
            if order.price is None:
                raise ValueError("Limit order requires a price")
            if order.price <= 0:
                raise ValueError(f"Invalid limit price: {order.price} (must be > 0)")

    def _build_headers(self) -> Dict[str, str]:
        """Build Alpaca authentication headers"""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["APCA-API-KEY-ID"] = self.api_key
        if self.secret_key:
            headers["APCA-API-SECRET-KEY"] = self.secret_key
        return headers

    async def _update_position(self, trade: Trade) -> None:
        """Update paper position based on executed trade"""
        symbol = trade.symbol

        if symbol not in self.paper_positions:
            self.paper_positions[symbol] = Position(
                symbol=symbol,
                size=0,
                avgPrice=0,
                currentPrice=trade.price,
                unrealizedPnl=0,
                realizedPnl=0,
            )

        position = self.paper_positions[symbol]

        if trade.side == OrderSide.BUY:
            new_size = position.size + trade.size
            if new_size > 0:
                position.avgPrice = (
                    (position.avgPrice * position.size + trade.price * trade.size) / new_size
                )
            position.size = new_size
        else:
            position.size -= trade.size
            if position.size < 0:
                logger.warning(f"Position for {symbol} went negative: {position.size}")
                position.size = 0

        position.currentPrice = trade.price
        position.unrealizedPnl = (position.currentPrice - position.avgPrice) * position.size

    async def _rate_limiter(self) -> None:
        """Background task to enforce API rate limits"""
        while True:
            try:
                current_time = time.time()
                time_since_last = current_time - self.last_request_time

                if time_since_last >= self.RATE_LIMIT_WINDOW:
                    self.request_count = 0
                    self.last_request_time = current_time

                if self.request_count >= self.RATE_LIMIT:
                    sleep_time = self.RATE_LIMIT_WINDOW - time_since_last
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Rate limiter error: {e}")
                await asyncio.sleep(0.1)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        retry_count: int = 0,
    ) -> Dict:
        """
        Make HTTP request to Alpaca paper trading API with rate limiting and
        exponential backoff retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path
            params: Query params (GET) or body (POST)
            retry_count: Current retry attempt number

        Returns:
            Parsed JSON response dict or list
        """
        return await self._do_request(
            self.base_url, method, endpoint, params, retry_count
        )

    async def _data_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        retry_count: int = 0,
    ) -> Dict:
        """Make HTTP request to Alpaca market data API"""
        return await self._do_request(
            self.DATA_BASE_URL, method, endpoint, params, retry_count
        )

    async def _do_request(
        self,
        base_url: str,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        retry_count: int = 0,
    ) -> Dict:
        """Internal request handler shared by trading and data APIs"""
        try:
            if not self.session:
                raise Exception("Not connected to Alpaca")

            # Wait if rate limit reached
            while self.request_count >= self.RATE_LIMIT:
                await asyncio.sleep(0.01)

            self.request_count += 1

            url = f"{base_url}{endpoint}"
            headers = self._build_headers()

            async with self.session.request(
                method,
                url,
                params=params if method == "GET" else None,
                json=params if method in ("POST", "PATCH") else None,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status in (200, 201, 204):
                    if response.status == 204:
                        return {}
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")

        except asyncio.TimeoutError:
            if retry_count < self.MAX_RETRIES:
                delay = self.RETRY_BASE_DELAY * (2 ** retry_count)
                logger.warning(
                    f"Request timeout, retrying in {delay:.1f}s "
                    f"({retry_count + 1}/{self.MAX_RETRIES})"
                )
                await asyncio.sleep(delay)
                return await self._do_request(
                    base_url, method, endpoint, params, retry_count + 1
                )
            raise

        except Exception as e:
            if retry_count < self.MAX_RETRIES:
                delay = self.RETRY_BASE_DELAY * (2 ** retry_count)
                logger.warning(
                    f"Request failed, retrying in {delay:.1f}s "
                    f"({retry_count + 1}/{self.MAX_RETRIES}): {e}"
                )
                await asyncio.sleep(delay)
                return await self._do_request(
                    base_url, method, endpoint, params, retry_count + 1
                )
            raise
