"""
Binance Exchange Connector

Implements ExchangeConnector interface for Binance spot and futures trading.
Supports market orders, limit orders, stop-loss orders with up to 125x leverage.
Handles Binance's rate limiting (1200 weight per minute).

Implements Requirements 4 (Binance Exchange Connector)
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


class BinanceConnector(ExchangeConnector):
    """
    Binance exchange connector for spot and futures trading.
    
    Features:
    - Market orders, limit orders, stop-loss orders
    - Up to 125x leverage for futures (configurable per user)
    - Spot and futures trading
    - Rate limiting handling (1200 weight per minute)
    - Position management
    - Real-time market data
    - Comprehensive error handling and retries
    """
    
    # API endpoints
    SPOT_BASE_URL = "https://api.binance.com"
    FUTURES_BASE_URL = "https://fapi.binance.com"
    
    # Rate limiting (1200 weight per minute)
    RATE_LIMIT_WEIGHT = 1200
    RATE_LIMIT_WINDOW = 60.0  # seconds
    
    # Retries
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    
    def __init__(
        self,
        api_key: str,
        secret: str,
        max_leverage: float = 125.0,
        trading_mode: str = "spot",  # 'spot' or 'futures'
    ):
        """
        Initialize Binance connector.
        
        Args:
            api_key: Binance API key
            secret: Binance API secret
            max_leverage: Maximum leverage allowed (default 125x for futures)
            trading_mode: Trading mode ('spot' or 'futures')
        """
        super().__init__("binance", ExchangeType.CEX)
        self.api_key = api_key
        self.secret = secret
        self.max_leverage = max_leverage
        self.trading_mode = trading_mode
        self.base_url = (
            self.FUTURES_BASE_URL if trading_mode == "futures" else self.SPOT_BASE_URL
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self.weight_used = 0
        self.weight_reset_time = time.time()
    
    async def connect(self) -> None:
        """Authenticate and establish connection to Binance"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection by fetching markets
            markets = await self.get_markets()
            if markets:
                self._connected = True
                logger.info(
                    f"Connected to Binance ({self.trading_mode}) ({self.base_url})"
                )
            else:
                raise Exception("Failed to fetch markets")
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            if self.session:
                await self.session.close()
            raise
    
    async def disconnect(self) -> None:
        """Close connection to Binance"""
        if self.session:
            await self.session.close()
            self._connected = False
            logger.info("Disconnected from Binance")
    
    async def get_markets(self) -> List[Market]:
        """Get list of available markets on Binance"""
        try:
            endpoint = "/fapi/v1/exchangeInfo" if self.trading_mode == "futures" else "/api/v3/exchangeInfo"
            response = await self._request("GET", endpoint)
            markets = []
            
            for symbol_data in response.get("symbols", []):
                if symbol_data.get("status") != "TRADING":
                    continue
                
                market = Market(
                    symbol=symbol_data["symbol"],
                    baseAsset=symbol_data.get("baseAsset", ""),
                    quoteAsset=symbol_data.get("quoteAsset", ""),
                    minOrderSize=float(
                        next(
                            (f["minQty"] for f in symbol_data.get("filters", []) if f["filterType"] == "LOT_SIZE"),
                            0.001,
                        )
                    ),
                    maxOrderSize=float(
                        next(
                            (f["maxQty"] for f in symbol_data.get("filters", []) if f["filterType"] == "LOT_SIZE"),
                            1000000,
                        )
                    ),
                    pricePrecision=symbol_data.get("pricePrecision", 8),
                    sizePrecision=symbol_data.get("quantityPrecision", 8),
                )
                markets.append(market)
            
            return markets
        except Exception as e:
            logger.error(f"Failed to get markets: {e}")
            raise
    
    async def get_order_book(self, symbol: str) -> OrderBook:
        """Get order book for symbol"""
        try:
            endpoint = "/fapi/v1/depth" if self.trading_mode == "futures" else "/api/v3/depth"
            response = await self._request(
                "GET",
                endpoint,
                {"symbol": symbol, "limit": 20},
            )
            
            bids = [
                (float(bid[0]), float(bid[1]))
                for bid in response.get("bids", [])
            ]
            asks = [
                (float(ask[0]), float(ask[1]))
                for ask in response.get("asks", [])
            ]
            
            return OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=response.get("E", int(datetime.now().timestamp() * 1000)),
            )
        except Exception as e:
            logger.error(f"Failed to get order book for {symbol}: {e}")
            raise
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get ticker information for symbol"""
        try:
            endpoint = "/fapi/v1/ticker/24hr" if self.trading_mode == "futures" else "/api/v3/ticker/24hr"
            response = await self._request(
                "GET",
                endpoint,
                {"symbol": symbol},
            )
            
            return Ticker(
                symbol=symbol,
                lastPrice=float(response["lastPrice"]),
                bidPrice=float(response["bidPrice"]),
                askPrice=float(response["askPrice"]),
                volume24h=float(response.get("volume", 0)),
                timestamp=response.get("time", int(datetime.now().timestamp() * 1000)),
            )
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            raise
    
    async def place_order(self, order: Order) -> Trade:
        """
        Place order on Binance.
        
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
            endpoint = "/fapi/v1/order" if self.trading_mode == "futures" else "/api/v3/order"
            payload = {
                "symbol": order.symbol,
                "side": order.side.value.upper(),
                "type": order.type.value.upper(),
                "quantity": str(order.size),
                "timestamp": int(time.time() * 1000),
            }
            
            if order.type == OrderType.LIMIT and order.price:
                payload["price"] = str(order.price)
                payload["timeInForce"] = order.timeInForce.value if order.timeInForce else "GTC"
            
            if self.trading_mode == "futures" and leverage > 1:
                payload["leverage"] = str(int(leverage))
            
            response = await self._request("POST", endpoint, payload)
            
            # Extract trade information from response
            trade = Trade(
                id=str(response.get("orderId", "")),
                orderId=str(response.get("orderId", "")),
                symbol=order.symbol,
                side=order.side,
                price=float(response.get("price", order.price or 0)),
                size=float(response.get("origQty", order.size)),
                fee=0,  # Binance returns fee separately
                timestamp=response.get("transactTime", int(datetime.now().timestamp() * 1000)),
            )
            
            logger.info(f"Order placed on Binance: {trade}")
            return trade
        except Exception as e:
            logger.error(f"Failed to place order on Binance: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> None:
        """Cancel order on Binance"""
        try:
            endpoint = "/fapi/v1/order" if self.trading_mode == "futures" else "/api/v3/order"
            payload = {
                "orderId": order_id,
                "timestamp": int(time.time() * 1000),
            }
            
            await self._request("DELETE", endpoint, payload)
            logger.info(f"Order cancelled on Binance: {order_id}")
        except Exception as e:
            logger.error(f"Failed to cancel order on Binance: {e}")
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
            if self.trading_mode == "futures":
                response = await self._request(
                    "GET",
                    "/fapi/v2/positionRisk",
                    {"timestamp": int(time.time() * 1000)},
                )
                positions = []
                
                for pos_data in response:
                    if float(pos_data.get("positionAmt", 0)) != 0:
                        position = Position(
                            symbol=pos_data["symbol"],
                            size=float(pos_data["positionAmt"]),
                            avgPrice=float(pos_data.get("entryPrice", 0)),
                            currentPrice=float(pos_data.get("markPrice", 0)),
                            unrealizedPnl=float(pos_data.get("unRealizedProfit", 0)),
                            realizedPnl=0,
                        )
                        positions.append(position)
                
                return positions
            else:
                # Spot trading doesn't have positions in the same way
                return []
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance for all assets"""
        try:
            if self.trading_mode == "futures":
                response = await self._request(
                    "GET",
                    "/fapi/v2/account",
                    {"timestamp": int(time.time() * 1000)},
                )
                
                balance = {}
                for asset_data in response.get("assets", []):
                    balance[asset_data["asset"]] = float(asset_data.get("walletBalance", 0))
                
                return balance
            else:
                response = await self._request(
                    "GET",
                    "/api/v3/account",
                    {"timestamp": int(time.time() * 1000)},
                )
                
                balance = {}
                for asset_data in response.get("balances", []):
                    balance[asset_data["asset"]] = float(asset_data.get("free", 0))
                
                return balance
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise
    
    # Private methods
    
    # Endpoints that require HMAC signature regardless of HTTP method
    PRIVATE_ENDPOINTS = {
        "/fapi/v1/order",
        "/fapi/v2/account",
        "/fapi/v2/positionRisk",
        "/api/v3/order",
        "/api/v3/account",
        "/api/v3/openOrders",
        "/api/v3/allOrders",
        "/api/v3/myTrades",
    }

    def _sign_params(self, params: Dict) -> Dict:
        """Add HMAC-SHA256 signature to a params dict. Mutates and returns it."""
        params.setdefault("timestamp", int(time.time() * 1000))
        query_string = urlencode(params)
        signature = hmac.new(
            self.secret.encode(),
            query_string.encode(),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        retry_count: int = 0,
        signed: bool = False,
    ) -> Dict:
        """
        Make HTTP request to Binance API with rate limiting and retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            params: Request parameters
            retry_count: Current retry attempt
            signed: Force signing even if not in PRIVATE_ENDPOINTS list

        Returns:
            Response JSON
        """
        try:
            if not self.session:
                raise Exception("Not connected to Binance")

            # Check rate limit
            current_time = time.time()
            if current_time - self.weight_reset_time >= self.RATE_LIMIT_WINDOW:
                self.weight_used = 0
                self.weight_reset_time = current_time

            estimated_weight = 1
            if self.weight_used + estimated_weight > self.RATE_LIMIT_WEIGHT:
                sleep_time = self.RATE_LIMIT_WINDOW - (current_time - self.weight_reset_time)
                if sleep_time > 0:
                    logger.warning(f"Rate limit approaching, sleeping {sleep_time}s")
                    await asyncio.sleep(sleep_time)
                    self.weight_used = 0
                    self.weight_reset_time = time.time()

            url = f"{self.base_url}{endpoint}"
            headers: Dict = {}
            params = params or {}

            # Determine if this request needs a signature
            needs_signing = (
                signed
                or method in ("POST", "DELETE")
                or endpoint in self.PRIVATE_ENDPOINTS
            )

            if needs_signing:
                self._sign_params(params)
                headers["X-MBX-APIKEY"] = self.api_key

            async with self.session.request(
                method,
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                # Update weight used from Binance response header
                weight_header = response.headers.get("X-MBX-Used-Weight-1M") \
                    or response.headers.get("X-MBX-Used-Weight", "1")
                self.weight_used += int(weight_header)

                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")

        except asyncio.TimeoutError:
            if retry_count < self.MAX_RETRIES:
                logger.warning(f"Request timeout, retrying ({retry_count + 1}/{self.MAX_RETRIES})")
                await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                return await self._request(method, endpoint, params, retry_count + 1, signed)
            else:
                raise
        except Exception as e:
            if retry_count < self.MAX_RETRIES:
                logger.warning(f"Request failed, retrying ({retry_count + 1}/{self.MAX_RETRIES}): {e}")
                await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                return await self._request(method, endpoint, params, retry_count + 1, signed)
            else:
                raise
