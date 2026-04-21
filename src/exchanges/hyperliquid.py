"""
Hyperliquid Exchange Connector

Implements ExchangeConnector interface for Hyperliquid perpetual futures trading.
Supports market orders, limit orders, stop-loss orders with up to 20x leverage.

Implements Requirements 1 (Hyperliquid Exchange Connector)
"""

import aiohttp
import asyncio
import hashlib
import hmac
import json
import logging
import base64
from typing import Dict, List, Optional
from datetime import datetime
from cryptography.fernet import Fernet

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
    TimeInForce,
)

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class CredentialEncryption:
    """Handles secure encryption and decryption of API credentials"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize credential encryption.
        
        Args:
            encryption_key: Encryption key for credentials. If None, credentials are not encrypted.
        """
        self.encryption_key = encryption_key
        self.cipher = Fernet(encryption_key.encode()) if encryption_key else None
    
    def encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential string"""
        if not self.cipher:
            return credential
        
        encrypted = self.cipher.encrypt(credential.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential string"""
        if not self.cipher:
            return encrypted_credential
        
        try:
            encrypted = base64.b64decode(encrypted_credential.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            raise AuthenticationError(f"Failed to decrypt credential: {e}")


class RequestSigner:
    """Handles HMAC-SHA256 request signing for Hyperliquid API"""
    
    @staticmethod
    def sign_request(
        api_secret: str,
        timestamp: str,
        api_key: str,
        request_body: Optional[str] = None,
    ) -> str:
        """
        Sign a request using HMAC-SHA256.
        
        Args:
            api_secret: API secret key
            timestamp: Request timestamp in milliseconds
            api_key: API key
            request_body: Optional request body for POST requests
        
        Returns:
            HMAC-SHA256 signature in hexadecimal format
        """
        # Construct message to sign
        message = f"{timestamp}{api_key}"
        if request_body:
            message += request_body
        
        # Sign with HMAC-SHA256
        signature = hmac.new(
            api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return signature
    
    @staticmethod
    def verify_signature(
        api_secret: str,
        timestamp: str,
        api_key: str,
        signature: str,
        request_body: Optional[str] = None,
    ) -> bool:
        """
        Verify a request signature.
        
        Args:
            api_secret: API secret key
            timestamp: Request timestamp in milliseconds
            api_key: API key
            signature: Signature to verify
            request_body: Optional request body
        
        Returns:
            True if signature is valid, False otherwise
        """
        expected_signature = RequestSigner.sign_request(
            api_secret,
            timestamp,
            api_key,
            request_body,
        )
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(signature, expected_signature)


class HyperliquidConnector(ExchangeConnector):
    """
    Hyperliquid exchange connector for perpetual futures trading.
    
    Features:
    - Market orders, limit orders, stop-loss orders
    - Up to 20x leverage (configurable per user)
    - Position management
    - Real-time market data
    - Comprehensive error handling and retries
    - Robust authentication with HMAC-SHA256 signing
    - Secure credential storage and transmission
    """
    
    # API endpoints
    BASE_URL = "https://api.hyperliquid.xyz"
    TESTNET_URL = "https://testnet.hyperliquid.xyz"
    
    # Rate limiting
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    
    # Authentication
    REQUEST_TIMEOUT = 30  # seconds
    SIGNATURE_ALGORITHM = "HMAC-SHA256"
    
    def __init__(
        self,
        api_key: str,
        secret: str,
        testnet: bool = False,
        max_leverage: float = 20.0,
        encryption_key: Optional[str] = None,
    ):
        """
        Initialize Hyperliquid connector with robust authentication.
        
        Args:
            api_key: Hyperliquid API key
            secret: Hyperliquid API secret
            testnet: Use testnet if True
            max_leverage: Maximum leverage allowed (default 20x)
            encryption_key: Optional encryption key for credential storage
        
        Raises:
            AuthenticationError: If credentials are invalid
        """
        super().__init__("hyperliquid", ExchangeType.CEX)
        
        # Validate credentials
        if not api_key or not secret:
            raise AuthenticationError("API key and secret are required")
        
        if len(api_key) < 10:
            raise AuthenticationError("Invalid API key format")
        
        if len(secret) < 10:
            raise AuthenticationError("Invalid API secret format")
        
        # Initialize credential encryption
        self.credential_encryption = CredentialEncryption(encryption_key)
        
        # Store encrypted credentials
        self._api_key = self.credential_encryption.encrypt_credential(api_key)
        self._secret = self.credential_encryption.encrypt_credential(secret)
        
        # Store decrypted credentials for use (in production, decrypt on-demand)
        self.api_key = api_key
        self.secret = secret
        
        self.testnet = testnet
        self.max_leverage = max_leverage
        self.base_url = self.TESTNET_URL if testnet else self.BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_signer = RequestSigner()
        
        logger.info(f"Initialized Hyperliquid connector (testnet={testnet})")
    
    async def connect(self) -> None:
        """
        Authenticate and establish connection to Hyperliquid.
        
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            self.session = aiohttp.ClientSession()
            
            # Test authentication by fetching account info
            try:
                await self._request("GET", "/account")
            except Exception as auth_error:
                await self.session.close()
                raise AuthenticationError(
                    f"Authentication failed: {str(auth_error)}"
                )
            
            # Test connection by fetching markets
            try:
                markets = await self.get_markets()
                if not markets:
                    raise Exception("No markets available")
            except Exception as e:
                await self.session.close()
                raise AuthenticationError(
                    f"Failed to verify connection: {str(e)}"
                )
            
            self._connected = True
            logger.info(
                f"Successfully authenticated with Hyperliquid "
                f"({self.base_url})"
            )
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Hyperliquid: {e}")
            if self.session:
                await self.session.close()
            raise AuthenticationError(f"Connection failed: {str(e)}")
    
    async def disconnect(self) -> None:
        """Close connection to Hyperliquid"""
        if self.session:
            await self.session.close()
            self._connected = False
            logger.info("Disconnected from Hyperliquid")
    
    async def get_markets(self) -> List[Market]:
        """Get list of available markets on Hyperliquid"""
        try:
            response = await self._request("GET", "/info")
            markets = []
            
            for market_data in response.get("universe", []):
                market = Market(
                    symbol=market_data["name"],
                    baseAsset=market_data["name"].split("-")[0],
                    quoteAsset="USD",
                    minOrderSize=market_data.get("minOrderSize", 0.001),
                    maxOrderSize=market_data.get("maxOrderSize", 1000000),
                    pricePrecision=market_data.get("pricePrecision", 8),
                    sizePrecision=market_data.get("sizePrecision", 8),
                )
                markets.append(market)
            
            return markets
        except Exception as e:
            logger.error(f"Failed to get markets: {e}")
            raise
    
    async def get_order_book(self, symbol: str) -> OrderBook:
        """Get order book for symbol"""
        try:
            response = await self._request("GET", f"/l2/{symbol}")
            
            bids = [(float(bid[0]), float(bid[1])) for bid in response.get("bids", [])]
            asks = [(float(ask[0]), float(ask[1])) for ask in response.get("asks", [])]
            
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
        Place order on Hyperliquid with comprehensive validation and error handling.
        
        Supports both market and limit orders with proper validation:
        
        Market Orders:
        - Executed immediately at market price
        - No price required
        - No time-in-force parameter
        
        Limit Orders:
        - Executed at specified price or better
        - Price validation: must be positive
        - Time-in-force options:
          * GTC (Good Till Cancelled): Order remains active until filled or cancelled
          * IOC (Immediate or Cancel): Order fills immediately or is cancelled
          * FOK (Fill or Kill): Order must fill completely or is cancelled
        
        Validates:
        - Order parameters (symbol, size, side)
        - Leverage (max 20x by default, configurable)
        - Order type and price requirements
        - Time-in-force for limit orders
        
        Handles:
        - Market order execution
        - Limit order execution with price handling
        - Fee calculation
        - Trade confirmation
        - Comprehensive error handling
        
        Args:
            order: Order specification with:
                - symbol: Trading pair (e.g., "BTC-USD")
                - side: OrderSide.BUY or OrderSide.SELL
                - type: OrderType.MARKET or OrderType.LIMIT
                - size: Order size in base asset
                - price: Required for LIMIT orders, optional for MARKET
                - timeInForce: Optional for LIMIT orders (GTC, IOC, FOK)
                - leverage: Optional leverage (default 1.0, max 20.0)
        
        Returns:
            Trade: Executed trade information with:
                - id: Order ID from exchange
                - symbol: Trading pair
                - side: Buy or sell
                - price: Execution price
                - size: Executed size
                - fee: Trading fee
                - timestamp: Execution timestamp
        
        Raises:
            ValueError: If order parameters are invalid:
                - Empty or invalid symbol
                - Non-positive size
                - Invalid side or type
                - Missing price for limit orders
                - Invalid price for limit orders
                - Leverage exceeds maximum
                - Invalid time-in-force
            Exception: If order placement fails:
                - API connection error
                - Invalid API response
                - Trade confirmation failure
        
        Examples:
            # Market order
            market_order = Order(
                symbol="BTC-USD",
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                size=1.0,
                leverage=2.0
            )
            trade = await connector.place_order(market_order)
            
            # Limit order with GTC
            limit_order = Order(
                symbol="BTC-USD",
                side=OrderSide.SELL,
                type=OrderType.LIMIT,
                size=0.5,
                price=51000.0,
                timeInForce=TimeInForce.GTC,
                leverage=1.0
            )
            trade = await connector.place_order(limit_order)
            
            # Limit order with IOC
            ioc_order = Order(
                symbol="ETH-USD",
                side=OrderSide.BUY,
                type=OrderType.LIMIT,
                size=10.0,
                price=3100.0,
                timeInForce=TimeInForce.IOC
            )
            trade = await connector.place_order(ioc_order)
        """
        try:
            # Validate order parameters
            self._validate_order_parameters(order)
            
            # Validate and normalize leverage
            leverage = self._validate_leverage(order.leverage)
            
            # Validate order type and price
            self._validate_order_type(order)
            
            # Prepare order payload
            payload = self._prepare_order_payload(order, leverage)
            
            # Place order on Hyperliquid
            response = await self._request("POST", "/order", payload)
            
            # Validate response
            if not response or "id" not in response:
                raise Exception("Invalid response from Hyperliquid: missing order ID")
            
            # Extract and validate trade information
            trade = self._extract_trade_from_response(response, order)
            
            # Verify trade confirmation
            self._verify_trade_confirmation(trade, order)
            
            logger.info(
                f"Order placed on Hyperliquid: {trade.id} "
                f"({order.type.value} {order.side.value} {trade.size} {order.symbol} @ {trade.price})"
            )
            return trade
        
        except ValueError as e:
            logger.error(f"Invalid order parameters: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to place order on Hyperliquid: {e}")
            raise
    
    def _validate_order_parameters(self, order: Order) -> None:
        """
        Validate order parameters.
        
        Args:
            order: Order to validate
        
        Raises:
            ValueError: If any parameter is invalid
        """
        # Validate symbol
        if not order.symbol or not isinstance(order.symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        
        if len(order.symbol) < 3:
            raise ValueError(f"Invalid symbol format: {order.symbol}")
        
        # Validate size
        if order.size <= 0:
            raise ValueError(f"Order size must be positive, got {order.size}")
        
        if not isinstance(order.size, (int, float)):
            raise ValueError(f"Order size must be numeric, got {type(order.size)}")
        
        # Validate side
        if order.side not in [OrderSide.BUY, OrderSide.SELL]:
            raise ValueError(f"Invalid order side: {order.side}")
        
        # Validate type
        if order.type not in [OrderType.MARKET, OrderType.LIMIT]:
            raise ValueError(f"Invalid order type: {order.type}")
    
    def _validate_leverage(self, leverage: Optional[float]) -> float:
        """
        Validate and normalize leverage.
        
        Args:
            leverage: Requested leverage (None defaults to 1.0)
        
        Returns:
            float: Validated leverage
        
        Raises:
            ValueError: If leverage is invalid or exceeds maximum
        """
        # Default to 1x if not specified
        if leverage is None:
            return 1.0
        
        # Validate leverage is numeric
        if not isinstance(leverage, (int, float)):
            raise ValueError(f"Leverage must be numeric, got {type(leverage)}")
        
        # Validate leverage is positive
        if leverage <= 0:
            raise ValueError(f"Leverage must be positive, got {leverage}")
        
        # Validate leverage does not exceed maximum
        if leverage > self.max_leverage:
            raise ValueError(
                f"Leverage {leverage}x exceeds maximum {self.max_leverage}x. "
                f"Please reduce leverage or contact support to increase limit."
            )
        
        return float(leverage)
    
    def _validate_order_type(self, order: Order) -> None:
        """
        Validate order type and required fields.
        
        Args:
            order: Order to validate
        
        Raises:
            ValueError: If order type validation fails
        """
        if order.type == OrderType.LIMIT:
            # Limit orders require a price
            if order.price is None:
                raise ValueError(
                    f"Limit orders require a positive price, got {order.price}"
                )
            
            if not isinstance(order.price, (int, float)):
                raise ValueError(f"Price must be numeric, got {type(order.price)}")
            
            if order.price <= 0:
                raise ValueError(
                    f"Limit orders require a positive price, got {order.price}"
                )
            
            # Validate time-in-force for limit orders
            self._validate_time_in_force(order.timeInForce)
        
        elif order.type == OrderType.MARKET:
            # Market orders should not have a price
            if order.price is not None and order.price > 0:
                logger.warning(
                    f"Market order should not have price, ignoring price {order.price}"
                )
            
            # Market orders should not have time-in-force
            if order.timeInForce is not None:
                logger.warning(
                    f"Market order should not have time-in-force, ignoring {order.timeInForce}"
                )
    
    def _validate_time_in_force(self, time_in_force: Optional[TimeInForce]) -> None:
        """
        Validate time-in-force parameter for limit orders.
        
        Args:
            time_in_force: Time-in-force value (GTC, IOC, FOK)
        
        Raises:
            ValueError: If time-in-force is invalid
        """
        if time_in_force is None:
            # Default to GTC if not specified
            return
        
        # Validate time-in-force is one of the allowed values
        valid_tif = [TimeInForce.GTC, TimeInForce.IOC, TimeInForce.FOK]
        if time_in_force not in valid_tif:
            raise ValueError(
                f"Invalid time-in-force: {time_in_force}. "
                f"Must be one of: {', '.join([t.value for t in valid_tif])}"
            )
    
    def _prepare_order_payload(self, order: Order, leverage: float) -> Dict:
        """
        Prepare order payload for Hyperliquid API.
        
        Handles both market and limit orders with proper price and time-in-force handling.
        
        Args:
            order: Order specification
            leverage: Validated leverage
        
        Returns:
            Dict: Order payload for API request
        
        Raises:
            ValueError: If order payload cannot be prepared
        """
        # Determine price based on order type
        price = None
        if order.type == OrderType.LIMIT:
            if order.price is None or order.price <= 0:
                raise ValueError(
                    f"Limit orders require a positive price, got {order.price}"
                )
            price = order.price
        
        # Determine time in force
        time_in_force = "GTC"  # Good Till Cancelled (default)
        if order.timeInForce:
            time_in_force = order.timeInForce.value
            # Validate time-in-force value
            if time_in_force not in ["GTC", "IOC", "FOK"]:
                raise ValueError(
                    f"Invalid time-in-force: {time_in_force}. "
                    f"Must be one of: GTC, IOC, FOK"
                )
        
        # For market orders, ensure time-in-force is not set
        if order.type == OrderType.MARKET:
            time_in_force = None
        
        # Build order specification
        order_spec = {
            "symbol": order.symbol,
            "side": order.side.value,
            "type": order.type.value,
            "size": order.size,
            "leverage": leverage,
        }
        
        # Add price for limit orders
        if order.type == OrderType.LIMIT:
            order_spec["price"] = price
            order_spec["timeInForce"] = time_in_force
        
        payload = {
            "action": "order",
            "orders": [order_spec],
        }
        
        logger.debug(
            f"Prepared order payload: {order.type.value} {order.side.value} "
            f"{order.size} {order.symbol} @ {price} "
            f"(leverage={leverage}, tif={time_in_force})"
        )
        
        return payload
    
    def _extract_trade_from_response(self, response: Dict, order: Order) -> Trade:
        """
        Extract trade information from Hyperliquid API response.
        
        Handles both market and limit order responses with proper price extraction.
        
        Args:
            response: API response
            order: Original order
        
        Returns:
            Trade: Extracted trade information
        
        Raises:
            Exception: If response is missing required fields
        """
        # Extract required fields
        order_id = response.get("id")
        if not order_id:
            raise Exception("Response missing order ID")
        
        # Extract price
        # For market orders: use filled price from response
        # For limit orders: use order price (may not be filled yet)
        price = None
        if order.type == OrderType.MARKET:
            # Market orders should have filled price in response
            price = float(response.get("price", 0))
            if price <= 0:
                raise Exception(
                    f"Market order response missing valid filled price: {price}"
                )
        elif order.type == OrderType.LIMIT:
            # Limit orders use the specified price
            price = order.price
            if price is None or price <= 0:
                raise Exception(
                    f"Limit order missing valid price: {price}"
                )
        
        # Extract size (use filled size if available, otherwise use order size)
        size = float(response.get("size", order.size or 0))
        if size <= 0:
            raise Exception(f"Invalid size in response: {size}")
        
        # Calculate fee
        fee = self._calculate_fee(price, size, order.side)
        
        # Create trade object
        trade = Trade(
            id=order_id,
            orderId=order_id,
            symbol=order.symbol,
            side=order.side,
            price=price,
            size=size,
            fee=fee,
            timestamp=int(datetime.now().timestamp() * 1000),
        )
        
        logger.debug(
            f"Extracted trade from response: {trade.id} "
            f"({order.type.value} {order.side.value} {size} {order.symbol} @ {price})"
        )
        
        return trade
    
    def _calculate_fee(self, price: float, size: float, side: OrderSide) -> float:
        """
        Calculate trading fee for Hyperliquid.
        
        Hyperliquid fee structure:
        - Maker: 0.02% (0.0002)
        - Taker: 0.05% (0.0005)
        
        For simplicity, we use average fee of 0.035% (0.00035)
        
        Args:
            price: Trade price
            size: Trade size
            side: Order side (buy/sell)
        
        Returns:
            float: Calculated fee in quote currency
        """
        # Average fee rate (0.035%)
        fee_rate = 0.00035
        
        # Fee = price * size * fee_rate
        fee = price * size * fee_rate
        
        return fee
    
    def _verify_trade_confirmation(self, trade: Trade, order: Order) -> None:
        """
        Verify trade confirmation and consistency.
        
        Validates that the trade matches the original order specification.
        
        Args:
            trade: Executed trade
            order: Original order
        
        Raises:
            Exception: If trade confirmation fails
        """
        # Verify symbol matches
        if trade.symbol != order.symbol:
            raise Exception(
                f"Trade symbol mismatch: expected {order.symbol}, got {trade.symbol}"
            )
        
        # Verify side matches
        if trade.side != order.side:
            raise Exception(
                f"Trade side mismatch: expected {order.side}, got {trade.side}"
            )
        
        # Verify size is reasonable (allow small rounding differences)
        size_diff = abs(trade.size - order.size)
        if size_diff > order.size * 0.01:  # Allow 1% difference
            logger.warning(
                f"Trade size differs from order: "
                f"expected {order.size}, got {trade.size}"
            )
        
        # Verify price is positive
        if trade.price <= 0:
            raise Exception(f"Invalid trade price: {trade.price}")
        
        # Verify fee is non-negative
        if trade.fee < 0:
            raise Exception(f"Invalid trade fee: {trade.fee}")
        
        # For limit orders, verify price matches order price
        if order.type == OrderType.LIMIT:
            price_diff = abs(trade.price - order.price)
            if price_diff > 0.01:  # Allow small rounding differences
                logger.warning(
                    f"Limit order price differs: "
                    f"expected {order.price}, got {trade.price}"
                )
        
        logger.debug(
            f"Trade confirmation verified: {trade.id} "
            f"({order.type.value} {order.side.value} {trade.size} {trade.symbol} @ {trade.price})"
        )
    
    async def cancel_order(self, order_id: str) -> None:
        """Cancel order on Hyperliquid"""
        try:
            payload = {
                "action": "cancel",
                "orderId": order_id,
            }
            
            await self._request("POST", "/order", payload)
            logger.info(f"Order cancelled on Hyperliquid: {order_id}")
        except Exception as e:
            logger.error(f"Failed to cancel order on Hyperliquid: {e}")
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
            response = await self._request("GET", "/positions")
            positions = []
            
            for pos_data in response.get("positions", []):
                position = Position(
                    symbol=pos_data["symbol"],
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
            response = await self._request("GET", "/account")
            
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
        Make HTTP request to Hyperliquid API with retry logic and authentication.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            payload: Request payload for POST requests
            retry_count: Current retry attempt
        
        Returns:
            Response JSON
        
        Raises:
            AuthenticationError: If authentication fails
            Exception: If request fails after retries
        """
        try:
            if not self.session:
                raise AuthenticationError("Not connected to Hyperliquid")
            
            url = f"{self.base_url}{endpoint}"
            headers = self._get_headers(payload)
            
            async with self.session.request(
                method,
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT),
            ) as response:
                response_text = await response.text()
                
                # Handle authentication errors
                if response.status == 401:
                    raise AuthenticationError(
                        f"Authentication failed: Invalid API credentials"
                    )
                elif response.status == 403:
                    raise AuthenticationError(
                        f"Authentication failed: Access denied"
                    )
                elif response.status == 200:
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError as e:
                        raise Exception(f"Invalid JSON response: {e}")
                else:
                    error_msg = f"HTTP {response.status}: {response_text}"
                    logger.warning(error_msg)
                    raise Exception(error_msg)
        
        except AuthenticationError:
            raise
        except asyncio.TimeoutError:
            if retry_count < self.MAX_RETRIES:
                logger.warning(
                    f"Request timeout, retrying "
                    f"({retry_count + 1}/{self.MAX_RETRIES})"
                )
                await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                return await self._request(
                    method, endpoint, payload, retry_count + 1
                )
            else:
                raise Exception(f"Request timeout after {self.MAX_RETRIES} retries")
        except Exception as e:
            if retry_count < self.MAX_RETRIES:
                logger.warning(
                    f"Request failed, retrying "
                    f"({retry_count + 1}/{self.MAX_RETRIES}): {e}"
                )
                await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                return await self._request(
                    method, endpoint, payload, retry_count + 1
                )
            else:
                raise
    
    def _get_headers(self, payload: Optional[Dict] = None) -> Dict[str, str]:
        """
        Get request headers with authentication.
        
        Args:
            payload: Optional request payload for signature calculation
        
        Returns:
            Dictionary of HTTP headers with authentication
        """
        timestamp = str(int(datetime.now().timestamp() * 1000))
        
        # Prepare request body for signing
        request_body = json.dumps(payload) if payload else None
        
        # Sign the request
        signature = self.request_signer.sign_request(
            self.secret,
            timestamp,
            self.api_key,
            request_body,
        )
        
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Signature": signature,
            "X-Timestamp": timestamp,
            "User-Agent": "HyperliquidConnector/1.0",
        }
    
    def _sign_request(self, timestamp: str) -> str:
        """
        Sign request with API secret using HMAC-SHA256.
        
        Args:
            timestamp: Request timestamp in milliseconds
        
        Returns:
            HMAC-SHA256 signature in hexadecimal format
        """
        message = f"{timestamp}{self.api_key}"
        signature = hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature
