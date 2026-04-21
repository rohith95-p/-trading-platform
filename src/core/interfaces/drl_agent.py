"""
DRL Agent Interface

Enables pluggable reinforcement learning agents with consistent prediction and training APIs.

Implements Requirement 1 (Pluggable Architecture) and Requirement 7 (PPO Reinforcement Learning Agent)
"""

from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any


class DRLAgent(ABC):
    """Abstract base class for Deep Reinforcement Learning agents"""
    
    def __init__(self, name: str, algorithm: str):
        """
        Initialize DRL agent
        
        Args:
            name: Name of the agent
            algorithm: Algorithm type ('PPO', 'A2C', 'SAC', etc.)
        """
        self.name = name
        self.algorithm = algorithm
    
    @abstractmethod
    def predict(self, state: np.ndarray) -> int:
        """
        Predict action from state
        
        Args:
            state: Current market state as numpy array
            
        Returns:
            action: 0 (hold), 1 (buy), 2 (sell)
        """
        pass
    
    @abstractmethod
    def train(self, env: Any, total_timesteps: int) -> None:
        """
        Train agent on environment
        
        Args:
            env: Training environment
            total_timesteps: Total number of timesteps to train
        """
        pass
    
    @abstractmethod
    def save(self, path: str) -> None:
        """
        Save model weights
        
        Args:
            path: File path to save model
        """
        pass
    
    @abstractmethod
    def load(self, path: str) -> None:
        """
        Load model weights
        
        Args:
            path: File path to load model from
        """
        pass
