"""
dYdX Exchange Connector

Implements ExchangeConnector interface for dYdX decentralized derivatives trading.
Supports market orders, limit orders with up to 20x leverage.
Handles blockchain network congestion with exponential backoff retries.

Implements Requirements 2 (dYdX Exchange Connector)
"""

import aiohttp
import asyncio
import hashlib
import hmac
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from eth_account import Account
from eth_account.messages import encode_defunct

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


class dYdXConnector(ExchangeConnector):
    """
    dYdX exchange connector for decentralized derivatives trading.
    
    Features:
    - Market orders, limit orders
    - Up to 20x leverage (configurable per user)
    - Wallet-based authentication with signing key
    - Blockchain network congestion handling
    - Position management
    - Real-time market data
    """
    
    # API endpoints
    BASE_URL = "https://api.dydx.trade"
    TESTNET_URL = "https://testnet.dydx.trade"
    
    # Rate limiting and retries
    MAX_RETRIES = 5
    RETRY_DELAY = 1.0  # seconds
    BLOCKCHAIN_CONFIRMATION_TIMEOUT = 60  # seconds
    
    def __init__(
        self,
        wallet_address: str,
        signing_key: str,
        testnet: bool = False,
        max_leverage: float = 20.0,
    ):
        """
        Initialize dYdX connector.
        
        Args:
            wallet_address: Ethereum wallet address
            signing_key: Private key for signing transactions
            testnet: Use testnet if True
            max_leverage: Maximum leverage allowed (default 20x)
        """
        super().__init__("dydx", ExchangeType.DEX)
        self.wallet_address = wallet_address
        self.signing_key = signing_key
        self.testnet = testnet
        self.max_leverage = max_leverage
        self.base_url = self.TESTNET_URL if testnet else self.BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.account = Account.from_key(signing_key)
    
    async def connect(self) -> None:
        """Authenticate and establish connection to dYdX"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection by fetching markets
            markets = await self.get_markets()
            if markets:
                self._connected = True
                logger.info(f"Connected to dYdX ({self.base_url})")
            else:
                raise Exception("Failed to fetch markets")
        except Exception as e:
            logger.error(f"Failed to connect to dYdX: {e}")
            if self.session:
                await self.session.close()
            raise
    
    async def disconnect(self) -> None:
        """Close connection to dYdX"""
        if self.session:
            await self.session.close()
            self._connected = False
            logger.info("Disconnected from dYdX")
    
    async def get_markets(self) -> List[Market]:
        """Get list of available markets on dYdX"""
        try:
            response = await self._request("GET", "/markets")
            markets = []
            
            for market_data in response.get("markets", []):
                market = Market(
                    symbol=market_data["id"],
                    baseAsset=market_data["id"].split("-")[0],
                    quoteAsset="USD",
                    minOrderSize=float(market_data.get("minOrderSize", 0.001)),
                    maxOrderSize=float(market_data.get("maxOrderSize", 1000000)),
                    pricePrecision=int(market_data.get("pricePrecision", 8)),
                    sizePrecision=int(market_data.get("sizePrecision", 8)),
                )
                markets.append(market)
            
            return markets
        except Exception as e:
            logger.error(f"Failed to get markets: {e}")
            raise
    
    async def get_order_book(self, symbol: str) -> OrderBook:
        """Get order book for symbol"""
        try:
            response = await self._request("GET", f"/orderbook/{symbol}")
            
            bids = [
                (float(bid["price"]), float(bid["size"]))
                for bid in response.get("bids", [])
            ]
            asks = [
                (float(ask["price"]), float(ask["size"]))
                for ask in response.get("asks", [])
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
            response = await self._request("GET", f"/ticker/{symbol}")
            
            return Ticker(
                symbol=symbol,
                lastPrice=float(response["lastPrice"]),
                bidPrice=float(response["bid"]),
                askPrice=float(response["ask"]),
                volume24h=float(response.get("volume24h", 0)),
                timestamp=int(datetime.now().timestamp() * 1000),
            )
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            raise
    
    async def place_order(self, order: Order) -> Trade:
        """
        Place order on dYdX.
        
        Validates leverage before placing order.
        Handles blockchain confirmation.
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
                "market": order.symbol,
                "side": order.side.value,
                "type": order.type.value,
                "size": str(order.size),
                "price": str(order.price) if order.type == OrderType.LIMIT else None,
                "timeInForce": order.timeInForce.value if order.timeInForce else "GTC",
                "leverage": str(leverage),
                "wallet": self.wallet_address,
            }
            
            # Sign the order
            signature = self._sign_order(payload)
            payload["signature"] = signature
            
            response = await self._request("POST", "/orders", payload)
            
            # Wait for blockchain confirmation
            tx_hash = response.get("txHash")
            if tx_hash:
                await self._wait_for_confirmation(tx_hash)
            
            # Extract trade information from response
            trade = Trade(
                id=response.get("id", ""),
                orderId=response.get("orderId", ""),
                symbol=order.symbol,
                side=order.side,
                price=float(response.get("price", 0)),
                size=float(response.get("size", 0)),
                fee=float(response.get("fee", 0)),
                timestamp=int(datetime.now().timestamp() * 1000),
            )
            
            logger.info(f"Order placed on dYdX: {trade}")
            return trade
        except Exception as e:
            logger.error(f"Failed to place order on dYdX: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> None:
        """Cancel order on dYdX"""
        try:
            payload = {
                "orderId": order_id,
                "wallet": self.wallet_address,
            }
            
            # Sign the cancellation
            signature = self._sign_order(payload)
            payload["signature"] = signature
            
            response = await self._request("POST", "/orders/cancel", payload)
            
            # Wait for blockchain confirmation
            tx_hash = response.get("txHash")
            if tx_hash:
                await self._wait_for_confirmation(tx_hash)
            
            logger.info(f"Order cancelled on dYdX: {order_id}")
        except Exception as e:
            logger.error(f"Failed to cancel order on dYdX: {e}")
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
            response = await self._request(
                "GET",
                f"/accounts/{self.wallet_address}/positions",
            )
            positions = []
            
            for pos_data in response.get("positions", []):
                position = Position(
                    symbol=pos_data["market"],
                    size=float(pos_data["size"]),
                    avgPrice=float(pos_data.get("avgPrice", 0)),
                    currentPrice=float(pos_data.get("currentPrice", 0)),
                    unrealizedPnl=float(pos_data.get("unrealizedPnl", 0)),
                    realizedPnl=float(pos_data.get("realizedPnl", 0)),
                )
                positions.append(position)
            
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance for all assets"""
        try:
            response = await self._request(
                "GET",
                f"/accounts/{self.wallet_address}",
            )
            
            balance = {}
            for asset_data in response.get("balances", []):
                balance[asset_data["asset"]] = float(asset_data["balance"])
            
            return balance
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise
    
    # Private methods
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict] = None,
        retry_count: int = 0,
    ) -> Dict:
        """
        Make HTTP request to dYdX API with exponential backoff retry logic.
        
        Handles blockchain network congestion with exponential backoff.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            payload: Request payload for POST requests
            retry_count: Current retry attempt
        
        Returns:
            Response JSON
        """
        try:
            if not self.session:
                raise Exception("Not connected to dYdX")
            
            url = f"{self.base_url}{endpoint}"
            headers = {"Content-Type": "application/json"}
            
            async with self.session.request(
                method,
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:  # Rate limited
                    if retry_count < self.MAX_RETRIES:
                        delay = self.RETRY_DELAY * (2 ** retry_count)  # Exponential backoff
                        logger.warning(
                            f"Rate limited, retrying in {delay}s "
                            f"({retry_count + 1}/{self.MAX_RETRIES})"
                        )
                        await asyncio.sleep(delay)
                        return await self._request(method, endpoint, payload, retry_count + 1)
                    else:
                        raise Exception("Max retries exceeded due to rate limiting")
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
        
        except asyncio.TimeoutError:
            if retry_count < self.MAX_RETRIES:
                delay = self.RETRY_DELAY * (2 ** retry_count)
                logger.warning(
                    f"Request timeout, retrying in {delay}s "
                    f"({retry_count + 1}/{self.MAX_RETRIES})"
                )
                await asyncio.sleep(delay)
                return await self._request(method, endpoint, payload, retry_count + 1)
            else:
                raise
        except Exception as e:
            if retry_count < self.MAX_RETRIES:
                delay = self.RETRY_DELAY * (2 ** retry_count)
                logger.warning(
                    f"Request failed, retrying in {delay}s "
                    f"({retry_count + 1}/{self.MAX_RETRIES}): {e}"
                )
                await asyncio.sleep(delay)
                return await self._request(method, endpoint, payload, retry_count + 1)
            else:
                raise
    
    def _sign_order(self, payload: Dict) -> str:
        """Sign order with wallet private key"""
        message_str = json.dumps(payload, sort_keys=True)
        message = encode_defunct(text=message_str)
        signed_message = self.account.sign_message(message)
        return signed_message.signature.hex()
    
    async def _wait_for_confirmation(
        self,
        tx_hash: str,
        timeout: int = BLOCKCHAIN_CONFIRMATION_TIMEOUT,
    ) -> None:
        """
        Wait for blockchain transaction confirmation.
        
        Args:
            tx_hash: Transaction hash
            timeout: Timeout in seconds
        """
        start_time = datetime.now()
        
        while True:
            try:
                response = await self._request("GET", f"/transactions/{tx_hash}")
                
                if response.get("status") == "confirmed":
                    logger.info(f"Transaction confirmed: {tx_hash}")
                    return
                
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    raise Exception(f"Transaction confirmation timeout: {tx_hash}")
                
                await asyncio.sleep(2)
            except Exception as e:
                logger.warning(f"Error checking transaction status: {e}")
                await asyncio.sleep(2)
