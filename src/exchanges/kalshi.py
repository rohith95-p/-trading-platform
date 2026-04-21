"""
Kalshi Exchange Connector

Implements ExchangeConnector interface for Kalshi prediction markets.
Supports paper trading mode only (no real money trading).
Handles Kalshi's API rate limiting and provides comprehensive error handling.

Implements Requirement 5 (Exchange Connectivity - Kalshi)
"""

import aiohttp
import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal

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


class KalshiConnector(ExchangeConnector):
    """
    Kalshi prediction market connector.
    
    Features:
    - Paper trading mode only (simulated orders)
    - Market data access (events, markets, orderbooks)
    - Order execution simulation
    - Position tracking
    - Rate limiting handling
    - Comprehensive error handling and retries
    
    Note: This connector enforces paper trading mode and will not execute
    real trades even if API keys are provided.
    """
    
    # API endpoints
    PROD_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
    DEMO_BASE_URL = "https://demo-api.kalshi.co/trade-api/v2"
    
    # Rate limiting (conservative estimate)
    RATE_LIMIT = 10  # requests per second
    RATE_LIMIT_WINDOW = 1.0  # seconds
    
    # Retries
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        private_key: Optional[str] = None,
        demo: bool = True,
        paper_trading: bool = True,
    ):
        """
        Initialize Kalshi connector.
        
        Args:
            api_key: Kalshi API key (optional for public data)
            private_key: Kalshi private key (optional for public data)
            demo: Use demo API endpoint (default True)
            paper_trading: Force paper trading mode (default True, always enforced)
        """
        super().__init__("kalshi", ExchangeType.PREDICTION)
        self.api_key = api_key
        self.private_key = private_key
        self.demo = demo
        self.paper_trading = True  # Always enforce paper trading
        self.base_url = self.DEMO_BASE_URL if demo else self.PROD_BASE_URL
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
                "Kalshi connector always operates in paper trading mode. "
                "Real trading is not supported."
            )
    
    async def connect(self) -> None:
        """Authenticate and establish connection to Kalshi"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Start rate limiter
            asyncio.create_task(self._rate_limiter())
            
            # Test connection by fetching markets
            markets = await self.get_markets()
            if markets:
                self._connected = True
                logger.info(
                    f"Connected to Kalshi ({self.base_url}) in PAPER TRADING mode"
                )
            else:
                raise Exception("Failed to fetch markets")
        except Exception as e:
            logger.error(f"Failed to connect to Kalshi: {e}")
            if self.session:
                await self.session.close()
            raise
    
    async def disconnect(self) -> None:
        """Close connection to Kalshi"""
        if self.session:
            await self.session.close()
            self._connected = False
            logger.info("Disconnected from Kalshi")
    
    async def get_markets(self) -> List[Market]:
        """Get list of available markets on Kalshi"""
        try:
            response = await self._request(
                "GET",
                "/events",
                {"status": "open", "limit": "100"},
            )
            
            markets = []
            for event in response.get("events", []):
                for market_data in event.get("markets", []):
                    # Calculate mid price from bid/ask
                    yes_bid = market_data.get("yes_bid", 0)
                    yes_ask = market_data.get("yes_ask", 100)
                    mid_price = (yes_bid + yes_ask) / 2 / 100  # Convert cents to dollars
                    
                    market = Market(
                        symbol=market_data.get("ticker", ""),
                        baseAsset="YES",
                        quoteAsset="USD",
                        minOrderSize=1.0,  # Minimum 1 contract
                        maxOrderSize=10000.0,  # Maximum 10k contracts
                        pricePrecision=2,
                        sizePrecision=0,
                    )
                    markets.append(market)
            
            return markets
        except Exception as e:
            logger.error(f"Failed to get markets: {e}")
            raise
    
    async def get_order_book(self, symbol: str) -> OrderBook:
        """Get order book for symbol"""
        try:
            response = await self._request(
                "GET",
                f"/markets/{symbol}/orderbook",
            )
            
            orderbook_data = response.get("orderbook", {})
            
            # Parse yes side (bids)
            yes_orders = orderbook_data.get("yes", [])
            bids = [
                (float(price) / 100, float(size))
                for price, size in yes_orders
            ]
            
            # Parse no side (asks - inverse of yes)
            no_orders = orderbook_data.get("no", [])
            asks = [
                (1.0 - float(price) / 100, float(size))
                for price, size in no_orders
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
        """Get ticker information for symbol"""
        try:
            response = await self._request(
                "GET",
                f"/markets/{symbol}",
            )
            
            market_data = response.get("market", {})
            
            yes_bid = market_data.get("yes_bid", 0) / 100
            yes_ask = market_data.get("yes_ask", 100) / 100
            last_price = (yes_bid + yes_ask) / 2
            volume = market_data.get("volume", 0)
            
            return Ticker(
                symbol=symbol,
                lastPrice=last_price,
                bidPrice=yes_bid,
                askPrice=yes_ask,
                volume24h=float(volume),
                timestamp=int(datetime.now().timestamp() * 1000),
            )
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            raise
    
    async def place_order(self, order: Order) -> Trade:
        """
        Place order on Kalshi (PAPER TRADING ONLY).
        
        Simulates order execution using current market prices.
        """
        try:
            # Validate order
            self._validate_order(order)
            
            # Get current market price
            ticker = await self.get_ticker(order.symbol)
            
            # Determine execution price based on order type and side
            if order.type == OrderType.MARKET:
                # Market orders execute at ask (buy) or bid (sell)
                execution_price = (
                    ticker.askPrice if order.side == OrderSide.BUY
                    else ticker.bidPrice
                )
            elif order.type == OrderType.LIMIT:
                # Limit orders execute at limit price (if valid)
                if order.price is None:
                    raise ValueError("Limit order requires price")
                execution_price = order.price
            else:
                raise ValueError(f"Unsupported order type: {order.type}")
            
            # Calculate cost
            cost = execution_price * order.size
            fee = cost * 0.01  # 1% fee simulation
            total_cost = cost + fee
            
            # Check balance
            if order.side == OrderSide.BUY and total_cost > self.paper_balance:
                raise ValueError(
                    f"Insufficient balance: {self.paper_balance:.2f} < {total_cost:.2f}"
                )
            
            # Execute trade
            trade_id = f"PAPER-{self.next_trade_id}"
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
            
            # Update paper balance
            if order.side == OrderSide.BUY:
                self.paper_balance -= total_cost
            else:
                self.paper_balance += cost - fee
            
            # Update position
            await self._update_position(trade)
            
            # Store trade
            self.paper_trades.append(trade)
            
            logger.info(f"Paper trade executed on Kalshi: {trade}")
            return trade
        except Exception as e:
            logger.error(f"Failed to place order on Kalshi: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> None:
        """Cancel order on Kalshi (paper trading - no-op)"""
        logger.info(f"Paper trading: Order {order_id} cancellation simulated")
    
    async def get_position(self, symbol: str) -> Position:
        """Get position for symbol"""
        try:
            if symbol in self.paper_positions:
                return self.paper_positions[symbol]
            
            # Return zero position if not found
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
            # Update current prices for all positions
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
                        logger.warning(f"Failed to update position for {symbol}: {e}")
                        positions.append(position)
            
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance (paper trading)"""
        try:
            # Calculate total value (balance + positions)
            positions_value = sum(
                pos.size * pos.currentPrice
                for pos in self.paper_positions.values()
            )
            
            return {
                "USD": self.paper_balance,
                "total": self.paper_balance + positions_value,
                "positions_value": positions_value,
            }
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise
    
    # Private methods
    
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
        """Update position based on trade"""
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
            # Add to position
            new_size = position.size + trade.size
            position.avgPrice = (
                (position.avgPrice * position.size + trade.price * trade.size) / new_size
            )
            position.size = new_size
        else:
            # Reduce position
            position.size -= trade.size
            if position.size < 0:
                logger.warning(f"Position for {symbol} went negative: {position.size}")
                position.size = 0
        
        position.currentPrice = trade.price
        position.unrealizedPnl = (position.currentPrice - position.avgPrice) * position.size
    
    async def _rate_limiter(self) -> None:
        """Rate limiter to enforce API rate limits"""
        while True:
            try:
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                
                if time_since_last >= self.RATE_LIMIT_WINDOW:
                    self.request_count = 0
                    self.last_request_time = current_time
                
                if self.request_count < self.RATE_LIMIT:
                    self.request_count += 1
                else:
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
        Make HTTP request to Kalshi API with rate limiting and retry logic.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            params: Request parameters
            retry_count: Current retry attempt
        
        Returns:
            Response JSON
        """
        try:
            if not self.session:
                raise Exception("Not connected to Kalshi")
            
            # Wait for rate limiter
            while self.request_count >= self.RATE_LIMIT:
                await asyncio.sleep(0.01)
            
            url = f"{self.base_url}{endpoint}"
            headers = {"Accept": "application/json"}
            
            # Add authentication if available
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
                logger.warning(
                    f"Request timeout, retrying ({retry_count + 1}/{self.MAX_RETRIES})"
                )
                await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                return await self._request(method, endpoint, params, retry_count + 1)
            else:
                raise
        except Exception as e:
            if retry_count < self.MAX_RETRIES:
                logger.warning(
                    f"Request failed, retrying ({retry_count + 1}/{self.MAX_RETRIES}): {e}"
                )
                await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                return await self._request(method, endpoint, params, retry_count + 1)
            else:
                raise
