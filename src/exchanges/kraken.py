"""
Kraken Exchange Connector

Implements ExchangeConnector interface for Kraken spot and margin trading.
Supports market orders, limit orders with up to 5x leverage.
Handles Kraken's rate limiting (15 API calls per second).

Implements Requirements 3 (Kraken Exchange Connector)
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
from urllib.parse import urlencode
import base64

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


class KrakenConnector(ExchangeConnector):
    """
    Kraken exchange connector for spot and margin trading.
    
    Features:
    - Market orders, limit orders
    - Up to 5x leverage (configurable per user)
    - Rate limiting handling (15 API calls per second)
    - Position management
    - Real-time market data
    - Comprehensive error handling and retries
    """
    
    # API endpoints
    BASE_URL = "https://api.kraken.com"
    
    # Rate limiting (15 calls per second)
    RATE_LIMIT = 15
    RATE_LIMIT_WINDOW = 1.0  # seconds
    
    # Retries
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    
    def __init__(
        self,
        api_key: str,
        secret: str,
        max_leverage: float = 5.0,
    ):
        """
        Initialize Kraken connector.
        
        Args:
            api_key: Kraken API key
            secret: Kraken API secret
            max_leverage: Maximum leverage allowed (default 5x)
        """
        super().__init__("kraken", ExchangeType.CEX)
        self.api_key = api_key
        self.secret = secret
        self.max_leverage = max_leverage
        self.base_url = self.BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self.last_request_time = 0.0
        self.request_count = 0
    
    async def connect(self) -> None:
        """Authenticate and establish connection to Kraken"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Start rate limiter
            asyncio.create_task(self._rate_limiter())
            
            # Test connection by fetching markets
            markets = await self.get_markets()
            if markets:
                self._connected = True
                logger.info(f"Connected to Kraken ({self.base_url})")
            else:
                raise Exception("Failed to fetch markets")
        except Exception as e:
            logger.error(f"Failed to connect to Kraken: {e}")
            if self.session:
                await self.session.close()
            raise
    
    async def disconnect(self) -> None:
        """Close connection to Kraken"""
        if self.session:
            await self.session.close()
            self._connected = False
            logger.info("Disconnected from Kraken")
    
    async def get_markets(self) -> List[Market]:
        """Get list of available markets on Kraken"""
        try:
            response = await self._request("GET", "/0/public/AssetPairs")
            markets = []
            
            for pair_name, pair_data in response.get("result", {}).items():
                market = Market(
                    symbol=pair_name,
                    baseAsset=pair_data.get("base", ""),
                    quoteAsset=pair_data.get("quote", ""),
                    minOrderSize=float(pair_data.get("ordermin", 0.001)),
                    maxOrderSize=float(pair_data.get("ordermax", 1000000)),
                    pricePrecision=int(pair_data.get("priceprecision", 8)),
                    sizePrecision=int(pair_data.get("lot_decimals", 8)),
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
                "/0/public/Depth",
                {"pair": symbol},
            )
            
            result = response.get("result", {})
            book_data = result.get(symbol, {})
            
            bids = [
                (float(bid[0]), float(bid[1]))
                for bid in book_data.get("bids", [])
            ]
            asks = [
                (float(ask[0]), float(ask[1]))
                for ask in book_data.get("asks", [])
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
                "/0/public/Ticker",
                {"pair": symbol},
            )
            
            result = response.get("result", {})
            ticker_data = result.get(symbol, {})
            
            return Ticker(
                symbol=symbol,
                lastPrice=float(ticker_data.get("c", [0])[0]),
                bidPrice=float(ticker_data.get("b", [0])[0]),
                askPrice=float(ticker_data.get("a", [0])[0]),
                volume24h=float(ticker_data.get("v", [0])[1]),
                timestamp=int(datetime.now().timestamp() * 1000),
            )
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            raise
    
    async def place_order(self, order: Order) -> Trade:
        """
        Place order on Kraken.
        
        Validates leverage before placing order.
        """
        try:
            # Validate leverage
            leverage = order.leverage or 1.0
            if leverage > self.max_leverage:
                raise ValueError(
                    f"Leverage {leverage} exceeds maximum {self.max_leverage}"
                )
            
            # Prepare order payload
            payload = {
                "pair": order.symbol,
                "type": order.side.value,
                "ordertype": order.type.value,
                "volume": str(order.size),
                "leverage": str(int(leverage)),
            }
            
            if order.type == OrderType.LIMIT and order.price:
                payload["price"] = str(order.price)
            
            if order.timeInForce:
                payload["timeinforce"] = order.timeInForce.value
            
            response = await self._request("POST", "/0/private/AddOrder", payload)
            
            result = response.get("result", {})
            
            # Extract trade information from response
            trade = Trade(
                id=result.get("txid", [""])[0],
                orderId=result.get("descr", {}).get("order", ""),
                symbol=order.symbol,
                side=order.side,
                price=order.price or 0,
                size=order.size,
                fee=0,  # Kraken returns fee separately
                timestamp=int(datetime.now().timestamp() * 1000),
            )
            
            logger.info(f"Order placed on Kraken: {trade}")
            return trade
        except Exception as e:
            logger.error(f"Failed to place order on Kraken: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> None:
        """Cancel order on Kraken"""
        try:
            payload = {"txid": order_id}
            
            await self._request("POST", "/0/private/CancelOrder", payload)
            logger.info(f"Order cancelled on Kraken: {order_id}")
        except Exception as e:
            logger.error(f"Failed to cancel order on Kraken: {e}")
            raise
    
    async def get_position(self, symbol: str) -> Position:
        """Get position for symbol"""
        try:
            positions = await self.get_positions()
            for position in positions:
                if position.symbol == symbol:
                    return position
            
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
            response = await self._request("POST", "/0/private/OpenPositions")
            positions = []
            
            for pos_id, pos_data in response.get("result", {}).items():
                position = Position(
                    symbol=pos_data.get("pair", ""),
                    size=float(pos_data.get("vol", 0)),
                    avgPrice=float(pos_data.get("cost", 0)) / float(pos_data.get("vol", 1)),
                    currentPrice=float(pos_data.get("value", 0)) / float(pos_data.get("vol", 1)),
                    unrealizedPnl=float(pos_data.get("net", 0)),
                    realizedPnl=0,
                )
                positions.append(position)
            
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance for all assets"""
        try:
            response = await self._request("POST", "/0/private/Balance")
            
            balance = {}
            for asset, amount in response.get("result", {}).items():
                balance[asset] = float(amount)
            
            return balance
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise
    
    # Private methods
    
    async def _rate_limiter(self) -> None:
        """Rate limiter to enforce 15 calls per second"""
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
        Make HTTP request to Kraken API with rate limiting and retry logic.
        
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
                raise Exception("Not connected to Kraken")
            
            # Wait for rate limiter
            while self.request_count >= self.RATE_LIMIT:
                await asyncio.sleep(0.01)
            
            url = f"{self.base_url}{endpoint}"
            headers = {}
            
            if method == "POST":
                headers = self._get_headers(endpoint, params or {})
            
            async with self.session.request(
                method,
                url,
                params=params if method == "GET" else None,
                data=params if method == "POST" else None,
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
                logger.warning(f"Request timeout, retrying ({retry_count + 1}/{self.MAX_RETRIES})")
                await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                return await self._request(method, endpoint, params, retry_count + 1)
            else:
                raise
        except Exception as e:
            if retry_count < self.MAX_RETRIES:
                logger.warning(f"Request failed, retrying ({retry_count + 1}/{self.MAX_RETRIES}): {e}")
                await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                return await self._request(method, endpoint, params, retry_count + 1)
            else:
                raise
    
    def _get_headers(self, endpoint: str, params: Dict) -> Dict[str, str]:
        """Get request headers with authentication for private endpoints"""
        nonce = str(int(time.time() * 1000))
        params["nonce"] = nonce
        
        postdata = urlencode(params)
        encoded = (str(params.get("nonce")) + postdata).encode()
        message = hashlib.sha256(encoded).digest()
        
        signature = hmac.new(
            base64.b64decode(self.secret),
            endpoint.encode() + message,
            hashlib.sha512,
        )
        
        return {
            "API-Sign": base64.b64encode(signature.digest()).decode(),
            "API-Key": self.api_key,
        }
