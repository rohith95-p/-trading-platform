"""
Polymarket Exchange Connector

Implements ExchangeConnector interface for Polymarket prediction markets.
Uses Polymarket's CLOB (Central Limit Order Book) API.
Supports paper trading mode only (no real money trading).

Implements Requirement 5 (Exchange Connectivity - Polymarket)
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


class PolymarketConnector(ExchangeConnector):
    """
    Polymarket prediction market connector.

    Features:
    - Paper trading mode only (simulated orders)
    - Market data access via CLOB API
    - Order execution simulation
    - Position tracking
    - Rate limiting handling
    - Exponential backoff retries (max 3 attempts)

    Note: This connector enforces paper trading mode and will not execute
    real trades even if API keys are provided.
    """

    # API endpoints
    CLOB_BASE_URL = "https://clob.polymarket.com"

    # Rate limiting
    RATE_LIMIT = 10  # requests per second
    RATE_LIMIT_WINDOW = 1.0  # seconds

    # Retries
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0  # seconds (exponential backoff base)

    def __init__(
        self,
        api_key: Optional[str] = None,
        paper_trading: bool = True,
    ):
        """
        Initialize Polymarket connector.

        Args:
            api_key: Polymarket API key (optional for public data)
            paper_trading: Force paper trading mode (default True, always enforced)
        """
        super().__init__("polymarket", ExchangeType.PREDICTION)
        self.api_key = api_key
        self.paper_trading = True  # Always enforce paper trading
        self.base_url = self.CLOB_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_count = 0
        self.last_request_time = 0.0

        # Paper trading state
        self.paper_positions: Dict[str, Position] = {}
        self.paper_balance = 10000.0  # Start with $10k paper money
        self.paper_trades: List[Trade] = []
        self.next_trade_id = 1

        if not paper_trading:
            logger.warning(
                "Polymarket connector always operates in paper trading mode. "
                "Real trading is not supported."
            )

    async def connect(self) -> None:
        """Authenticate and establish connection to Polymarket CLOB API"""
        try:
            self.session = aiohttp.ClientSession()

            # Start rate limiter background task
            asyncio.create_task(self._rate_limiter())

            # Test connection by fetching markets
            markets = await self.get_markets()
            if markets is not None:
                self._connected = True
                logger.info(
                    f"Connected to Polymarket CLOB API ({self.base_url}) in PAPER TRADING mode"
                )
            else:
                raise Exception("Failed to fetch markets from Polymarket")
        except Exception as e:
            logger.error(f"Failed to connect to Polymarket: {e}")
            if self.session:
                await self.session.close()
            raise

    async def disconnect(self) -> None:
        """Close connection to Polymarket"""
        if self.session:
            await self.session.close()
            self._connected = False
            logger.info("Disconnected from Polymarket")

    async def get_markets(self) -> List[Market]:
        """Get list of available markets on Polymarket"""
        try:
            response = await self._request("GET", "/markets", {"active": "true", "limit": "100"})

            markets = []
            for market_data in response.get("data", []):
                market = Market(
                    symbol=market_data.get("condition_id", ""),
                    baseAsset="YES",
                    quoteAsset="USDC",
                    minOrderSize=1.0,
                    maxOrderSize=100000.0,
                    pricePrecision=4,
                    sizePrecision=0,
                )
                markets.append(market)

            return markets
        except Exception as e:
            logger.error(f"Failed to get markets from Polymarket: {e}")
            raise

    async def get_order_book(self, symbol: str) -> OrderBook:
        """Get order book for a market token ID"""
        try:
            response = await self._request("GET", f"/book", {"token_id": symbol})

            bids_raw = response.get("bids", [])
            asks_raw = response.get("asks", [])

            bids = [
                (float(entry.get("price", 0)), float(entry.get("size", 0)))
                for entry in bids_raw
            ]
            asks = [
                (float(entry.get("price", 0)), float(entry.get("size", 0)))
                for entry in asks_raw
            ]

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
        """Get ticker information for a market token ID"""
        try:
            response = await self._request("GET", f"/price", {"token_id": symbol, "side": "buy"})
            buy_price = float(response.get("price", 0.5))

            response_sell = await self._request(
                "GET", f"/price", {"token_id": symbol, "side": "sell"}
            )
            sell_price = float(response_sell.get("price", 0.5))

            last_price = (buy_price + sell_price) / 2

            # Fetch midpoint for volume
            mid_response = await self._request("GET", f"/midpoint", {"token_id": symbol})
            volume = float(mid_response.get("mid", last_price))

            return Ticker(
                symbol=symbol,
                lastPrice=last_price,
                bidPrice=sell_price,
                askPrice=buy_price,
                volume24h=0.0,  # CLOB API doesn't expose 24h volume per token directly
                timestamp=int(datetime.now().timestamp() * 1000),
            )
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            raise

    async def place_order(self, order: Order) -> Trade:
        """
        Place order on Polymarket (PAPER TRADING ONLY).

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
            fee = cost * 0.01  # 1% fee simulation
            total_cost = cost + fee

            if order.side == OrderSide.BUY and total_cost > self.paper_balance:
                raise ValueError(
                    f"Insufficient balance: {self.paper_balance:.2f} < {total_cost:.2f}"
                )

            trade_id = f"PAPER-POLY-{self.next_trade_id}"
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

            logger.info(f"Paper trade executed on Polymarket: {trade}")
            return trade
        except Exception as e:
            logger.error(f"Failed to place order on Polymarket: {e}")
            raise

    async def cancel_order(self, order_id: str) -> None:
        """Cancel order (paper trading — no-op)"""
        logger.info(f"Paper trading: Order {order_id} cancellation simulated on Polymarket")

    async def get_position(self, symbol: str) -> Position:
        """Get position for a market token"""
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
                "USDC": self.paper_balance,
                "total": self.paper_balance + positions_value,
                "positions_value": positions_value,
            }
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise

    # ── Private helpers ──────────────────────────────────────────────────────

    def _validate_order(self, order: Order) -> None:
        """Validate order parameters"""
        if order.size <= 0:
            raise ValueError(f"Invalid order size: {order.size}")

        if order.type == OrderType.LIMIT and order.price is not None:
            if order.price <= 0 or order.price > 1:
                raise ValueError(
                    f"Invalid limit price for prediction market: {order.price} "
                    "(must be between 0 and 1)"
                )

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
        Make HTTP request to Polymarket CLOB API with rate limiting and
        exponential backoff retry logic.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path
            params: Query params (GET) or body (POST)
            retry_count: Current retry attempt number

        Returns:
            Parsed JSON response dict
        """
        try:
            if not self.session:
                raise Exception("Not connected to Polymarket")

            # Wait if rate limit reached
            while self.request_count >= self.RATE_LIMIT:
                await asyncio.sleep(0.01)

            self.request_count += 1

            url = f"{self.base_url}{endpoint}"
            headers = {"Accept": "application/json"}

            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with self.session.request(
                method,
                url,
                params=params if method == "GET" else None,
                json=params if method == "POST" else None,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
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
                return await self._request(method, endpoint, params, retry_count + 1)
            raise

        except Exception as e:
            if retry_count < self.MAX_RETRIES:
                delay = self.RETRY_BASE_DELAY * (2 ** retry_count)
                logger.warning(
                    f"Request failed, retrying in {delay:.1f}s "
                    f"({retry_count + 1}/{self.MAX_RETRIES}): {e}"
                )
                await asyncio.sleep(delay)
                return await self._request(method, endpoint, params, retry_count + 1)
            raise
