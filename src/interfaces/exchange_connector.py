"""
ExchangeConnector interface - for exchange integrations
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Order:
    """Order data class"""
    symbol: str
    side: str  # buy or sell
    type: str  # market, limit, stop
    size: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    leverage: Optional[float] = None

@dataclass
class Trade:
    """Trade data class"""
    id: str
    symbol: str
    side: str
    price: float
    size: float
    fee: float
    timestamp: datetime

@dataclass
class Position:
    """Position data class"""
    id: str
    symbol: str
    side: str
    size: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_percent: float

@dataclass
class Balance:
    """Balance data class"""
    total: float
    available: float
    used: float

class ExchangeConnector(ABC):
    """
    Abstract base class for exchange connectors.
    All exchange implementations must inherit from this class.
    """
    
    def __init__(self, name: str, exchange_type: str):
        """
        Initialize connector
        
        Args:
            name: Exchange name (e.g., 'kalshi', 'polymarket')
            exchange_type: Type of exchange (e.g., 'cex', 'dex', 'prediction_market')
        """
        self.name = name
        self.exchange_type = exchange_type
    
    @abstractmethod
    async def connect(self) -> None:
        """Authenticate with exchange"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from exchange"""
        pass
    
    @abstractmethod
    async def place_order(self, order: Order) -> Trade:
        """
        Place order and return trade
        
        Args:
            order: Order to place
            
        Returns:
            Trade object with execution details
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel order
        
        Args:
            order_id: ID of order to cancel
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get open positions
        
        Returns:
            List of Position objects
        """
        pass
    
    @abstractmethod
    async def close_position(self, position_id: str) -> Trade:
        """
        Close position
        
        Args:
            position_id: ID of position to close
            
        Returns:
            Trade object with closing details
        """
        pass
    
    @abstractmethod
    async def get_balance(self) -> Balance:
        """
        Get account balance
        
        Returns:
            Balance object
        """
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get market data for symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with market data (price, volume, etc.)
        """
        pass
