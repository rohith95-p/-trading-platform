"""
ExchangeConnector Interface

Provides a unified abstraction for all exchange integrations, enabling seamless
addition of new exchanges without modifying existing code.

Implements Requirement 1 (Pluggable Architecture) and Requirement 5 (Exchange Connectivity)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class OrderSide(str, Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"


class TimeInForce(str, Enum):
    """Time in force enumeration"""
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill


class ExchangeType(str, Enum):
    """Exchange type enumeration"""
    CEX = "cex"  # Centralized Exchange
    DEX = "dex"  # Decentralized Exchange
    PREDICTION = "prediction"  # Prediction Market
    STOCKS = "stocks"  # Stock Broker


@dataclass
class Market:
    """Market information"""
    symbol: str
    baseAsset: str
    quoteAsset: str
    minOrderSize: float
    maxOrderSize: float
    pricePrecision: int
    sizePrecision: int


@dataclass
class OrderBook:
    """Order book snapshot"""
    symbol: str
    bids: List[tuple]  # List of (price, size) tuples
    asks: List[tuple]  # List of (price, size) tuples
    timestamp: int


@dataclass
class Ticker:
    """Ticker information"""
    symbol: str
    lastPrice: float
    bidPrice: float
    askPrice: float
    volume24h: float
    timestamp: int


@dataclass
class Order:
    """Order specification"""
    symbol: str
    side: OrderSide
    type: OrderType
    size: float
    price: Optional[float] = None
    timeInForce: Optional[TimeInForce] = None
    leverage: Optional[float] = None


@dataclass
class Trade:
    """Executed trade"""
    id: str
    orderId: str
    symbol: str
    side: OrderSide
    price: float
    size: float
    fee: float
    timestamp: int


@dataclass
class Position:
    """Open position"""
    symbol: str
    size: float
    avgPrice: float
    currentPrice: float
    unrealizedPnl: float
    realizedPnl: float


class ExchangeConnector(ABC):
    """
    Abstract base class for exchange connectors.
    
    All exchange implementations must inherit from this class and implement
    all abstract methods.
    """
    
    def __init__(self, name: str, exchange_type: ExchangeType):
        """
        Initialize exchange connector.
        
        Args:
            name: Exchange name (e.g., 'hyperliquid', 'dydx', 'kraken', 'binance')
            exchange_type: Type of exchange (CEX, DEX, prediction, stocks)
        """
        self.name = name
        self.type = exchange_type
        self._connected = False
    
    # Connection management
    
    @abstractmethod
    async def connect(self) -> None:
        """Authenticate and establish connection to exchange"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to exchange"""
        pass
    
    def is_connected(self) -> bool:
        """Check if connected to exchange"""
        return self._connected
    
    # Market data
    
    @abstractmethod
    async def get_markets(self) -> List[Market]:
        """Get list of available markets"""
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str) -> OrderBook:
        """Get order book for symbol"""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get ticker information for symbol"""
        pass
    
    # Trading
    
    @abstractmethod
    async def place_order(self, order: Order) -> Trade:
        """Place order on exchange"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> None:
        """Cancel order on exchange"""
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Position:
        """Get position for symbol"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all open positions"""
        pass
    
    # Account
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance for all assets"""
        pass
