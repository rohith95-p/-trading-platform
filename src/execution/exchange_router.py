"""
Exchange router - routes orders to appropriate exchange
"""

from typing import Dict, Any
from src.interfaces import ExchangeConnector
from src.interfaces.registry import registry

class ExchangeRouter:
    """Route orders to appropriate exchange"""
    
    def __init__(self):
        self.connectors: Dict[str, ExchangeConnector] = {}
    
    def register_connector(self, name: str, connector: ExchangeConnector) -> None:
        """Register exchange connector"""
        self.connectors[name] = connector
    
    async def route_order(self, exchange: str, order: Any) -> Any:
        """
        Route order to exchange
        
        Args:
            exchange: Exchange name
            order: Order object
            
        Returns:
            Trade result
        """
        if exchange not in self.connectors:
            raise ValueError(f"Exchange '{exchange}' not registered")
        
        connector = self.connectors[exchange]
        return await connector.place_order(order)
    
    def list_exchanges(self) -> list:
        """List available exchanges"""
        return list(self.connectors.keys())
