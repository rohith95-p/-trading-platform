"""
Interface registry for dynamic component loading
"""

from typing import Dict, Type, Any
from .exchange_connector import ExchangeConnector
from .strategy_executor import StrategyExecutor
from .backtester import Backtester
from .drl_agent import DRLAgent

class InterfaceRegistry:
    """Registry for managing interface implementations"""
    
    def __init__(self):
        self.exchanges: Dict[str, Type[ExchangeConnector]] = {}
        self.strategies: Dict[str, Type[StrategyExecutor]] = {}
        self.backtestors: Dict[str, Type[Backtester]] = {}
        self.agents: Dict[str, Type[DRLAgent]] = {}
    
    def register_exchange(self, name: str, connector_class: Type[ExchangeConnector]) -> None:
        """Register exchange connector"""
        self.exchanges[name] = connector_class
    
    def register_strategy(self, name: str, strategy_class: Type[StrategyExecutor]) -> None:
        """Register strategy executor"""
        self.strategies[name] = strategy_class
    
    def register_backtester(self, name: str, backtester_class: Type[Backtester]) -> None:
        """Register backtester"""
        self.backtestors[name] = backtester_class
    
    def register_agent(self, name: str, agent_class: Type[DRLAgent]) -> None:
        """Register DRL agent"""
        self.agents[name] = agent_class
    
    def get_exchange(self, name: str) -> Type[ExchangeConnector]:
        """Get exchange connector class"""
        if name not in self.exchanges:
            raise ValueError(f"Exchange '{name}' not registered")
        return self.exchanges[name]
    
    def get_strategy(self, name: str) -> Type[StrategyExecutor]:
        """Get strategy executor class"""
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not registered")
        return self.strategies[name]
    
    def get_backtester(self, name: str) -> Type[Backtester]:
        """Get backtester class"""
        if name not in self.backtestors:
            raise ValueError(f"Backtester '{name}' not registered")
        return self.backtestors[name]
    
    def get_agent(self, name: str) -> Type[DRLAgent]:
        """Get DRL agent class"""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not registered")
        return self.agents[name]
    
    def list_exchanges(self) -> list:
        """List all registered exchanges"""
        return list(self.exchanges.keys())
    
    def list_strategies(self) -> list:
        """List all registered strategies"""
        return list(self.strategies.keys())
    
    def list_backtestors(self) -> list:
        """List all registered backtestors"""
        return list(self.backtestors.keys())
    
    def list_agents(self) -> list:
        """List all registered agents"""
        return list(self.agents.keys())

# Global registry instance
registry = InterfaceRegistry()
