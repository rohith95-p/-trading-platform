"""
DRLAgent interface - for reinforcement learning agents
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

@dataclass
class State:
    """Agent state"""
    price: float
    indicators: Dict[str, float]
    position: float
    balance: float
    timestamp: int

@dataclass
class Action:
    """Agent action"""
    action_type: str  # buy, sell, hold
    size: float
    confidence: float

@dataclass
class Experience:
    """Training experience"""
    state: State
    action: Action
    reward: float
    next_state: State
    done: bool

class DRLAgent(ABC):
    """
    Abstract base class for DRL agents.
    All DRL agent implementations must inherit from this class.
    """
    
    def __init__(self, name: str, agent_type: str):
        """
        Initialize agent
        
        Args:
            name: Agent name
            agent_type: Type of agent (e.g., 'ppo', 'a2c', 'sac')
        """
        self.name = name
        self.agent_type = agent_type
    
    @abstractmethod
    async def predict(self, state: State) -> Action:
        """
        Predict action given state
        
        Args:
            state: Current state
            
        Returns:
            Action object
        """
        pass
    
    @abstractmethod
    def train(self, experiences: List[Experience]) -> Dict[str, float]:
        """
        Train agent on experiences
        
        Args:
            experiences: List of experiences
            
        Returns:
            Dictionary with training metrics
        """
        pass
    
    @abstractmethod
    def save_model(self, path: str) -> None:
        """
        Save model to disk
        
        Args:
            path: Path to save model
        """
        pass
    
    @abstractmethod
    def load_model(self, path: str) -> None:
        """
        Load model from disk
        
        Args:
            path: Path to load model from
        """
        pass
