"""
StrategyExecutor interface - for strategy implementations
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Signal:
    """Trading signal"""
    asset: str
    direction: str  # buy, sell, hold
    confidence: float  # 0-1
    rationale: str
    timestamp: datetime

@dataclass
class MarketData:
    """Market data for strategy"""
    symbol: str
    price: float
    volume: float
    bid: float
    ask: float
    timestamp: datetime
    indicators: Dict[str, Any]

class StrategyExecutor(ABC):
    """
    Abstract base class for strategy executors.
    All strategy implementations must inherit from this class.
    """
    
    def __init__(self, name: str, strategy_type: str):
        """
        Initialize strategy
        
        Args:
            name: Strategy name
            strategy_type: Type of strategy (e.g., 'directional', 'grid', 'market_making')
        """
        self.name = name
        self.strategy_type = strategy_type
    
    @abstractmethod
    async def execute(self, market_data: MarketData) -> Optional[Signal]:
        """
        Execute strategy and return signal
        
        Args:
            market_data: Current market data
            
        Returns:
            Signal object or None if no signal
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate strategy configuration
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_required_indicators(self) -> list:
        """
        Get list of required indicators
        
        Returns:
            List of indicator names
        """
        pass
