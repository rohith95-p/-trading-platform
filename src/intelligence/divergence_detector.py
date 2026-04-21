"""
Indicator Divergence Detection for identifying potential trend reversals.

Detects bullish and bearish divergences for RSI, MACD, and Stochastic indicators
with configurable sensitivity levels and confidence scoring.
"""
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
import numpy as np

log = logging.getLogger(__name__)


class DivergenceSensitivity(Enum):
    """Divergence detection sensitivity levels."""
    STRICT = "strict"
    NORMAL = "normal"
    LOOSE = "loose"


class DivergenceType(Enum):
    """Types of divergences."""
    BULLISH = "bullish"
    BEARISH = "bearish"


class Divergence:
    """Represents a detected divergence."""
    
    def __init__(
        self,
        divergence_type: DivergenceType,
        indicator: str,
        price_index: int,
        indicator_index: int,
        price_value: float,
        indicator_value: float,
        confidence: float,
        magnitude: float,
        touches: int,
    ):
        self.type = divergence_type
        self.indicator = indicator
        self.price_index = price_index
        self.indicator_index = indicator_index
        self.price_value = price_value
        self.indicator_value = indicator_value
        self.confidence = confidence
        self.magnitude = magnitude
        self.touches = touches
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "indicator": self.indicator,
            "price_index": self.price_index,
            "indicator_index": self.indicator_index,
            "price_value": self.price_value,
            "indicator_value": self.indicator_value,
            "confidence": self.confidence,
            "magnitude": self.magnitude,
            "touches": self.touches,
        }


class DivergenceDetector:
    """Detects indicator divergences for trading signals."""
    
    def __init__(self, sensitivity: str = "normal"):
        """Initialize divergence detector.
        
        Args:
            sensitivity: "strict", "normal", or "loose"
        """
        self.sensitivity = DivergenceSensitivity(sensitivity)
        
        # Lookback periods for each sensitivity
        self.lookback_periods = {
            DivergenceSensitivity.STRICT: 5,
            DivergenceSensitivity.NORMAL: 10,
            DivergenceSensitivity.LOOSE: 20,
        }
        
        self.lookback = self.lookback_periods[self.sensitivity]
    
    def detect_bullish_divergence(
        self,
        prices: np.ndarray,
        indicator: np.ndarray,
        indicator_name: str = "RSI",
    ) -> List[Divergence]:
        """Detect bullish divergence (price lower low, indicator higher low).
        
        Args:
            prices: Price array
            indicator: Indicator values array
            indicator_name: Name of indicator (for logging)
        
        Returns:
            List of detected bullish divergences
        """
        divergences = []
        
        if len(prices) < self.lookback + 2 or len(indicator) < self.lookback + 2:
            return divergences
        
        # Find local lows in price
        for i in range(self.lookback, len(prices) - 1):
            # Check if this is a local low
            if prices[i] < prices[i - 1] and prices[i] < prices[i + 1]:
                # Look back for previous local low
                prev_low_idx = None
                for j in range(i - self.lookback, i):
                    if prices[j] < prices[j - 1] and prices[j] < prices[j + 1]:
                        prev_low_idx = j
                
                if prev_low_idx is None:
                    continue
                
                # Check if price made lower low but indicator made higher low
                if (prices[i] < prices[prev_low_idx] and 
                    not np.isnan(indicator[i]) and not np.isnan(indicator[prev_low_idx]) and
                    indicator[i] > indicator[prev_low_idx]):
                    
                    # Calculate confidence
                    magnitude = prices[prev_low_idx] - prices[i]
                    indicator_magnitude = indicator[i] - indicator[prev_low_idx]
                    touches = self._count_touches(prices, prices[i], prev_low_idx, i)
                    confidence = self._calculate_confidence(magnitude, indicator_magnitude, touches)
                    
                    divergence = Divergence(
                        divergence_type=DivergenceType.BULLISH,
                        indicator=indicator_name,
                        price_index=i,
                        indicator_index=i,
                        price_value=prices[i],
                        indicator_value=indicator[i],
                        confidence=confidence,
                        magnitude=magnitude,
                        touches=touches,
                    )
                    divergences.append(divergence)
        
        return divergences
    
    def detect_bearish_divergence(
        self,
        prices: np.ndarray,
        indicator: np.ndarray,
        indicator_name: str = "RSI",
    ) -> List[Divergence]:
        """Detect bearish divergence (price higher high, indicator lower high).
        
        Args:
            prices: Price array
            indicator: Indicator values array
            indicator_name: Name of indicator (for logging)
        
        Returns:
            List of detected bearish divergences
        """
        divergences = []
        
        if len(prices) < self.lookback + 2 or len(indicator) < self.lookback + 2:
            return divergences
        
        # Find local highs in price
        for i in range(self.lookback, len(prices) - 1):
            # Check if this is a local high
            if prices[i] > prices[i - 1] and prices[i] > prices[i + 1]:
                # Look back for previous local high
                prev_high_idx = None
                for j in range(i - self.lookback, i):
                    if prices[j] > prices[j - 1] and prices[j] > prices[j + 1]:
                        prev_high_idx = j
                
                if prev_high_idx is None:
                    continue
                
                # Check if price made higher high but indicator made lower high
                if (prices[i] > prices[prev_high_idx] and 
                    not np.isnan(indicator[i]) and not np.isnan(indicator[prev_high_idx]) and
                    indicator[i] < indicator[prev_high_idx]):
                    
                    # Calculate confidence
                    magnitude = prices[i] - prices[prev_high_idx]
                    indicator_magnitude = indicator[prev_high_idx] - indicator[i]
                    touches = self._count_touches(prices, prices[i], prev_high_idx, i)
                    confidence = self._calculate_confidence(magnitude, indicator_magnitude, touches)
                    
                    divergence = Divergence(
                        divergence_type=DivergenceType.BEARISH,
                        indicator=indicator_name,
                        price_index=i,
                        indicator_index=i,
                        price_value=prices[i],
                        indicator_value=indicator[i],
                        confidence=confidence,
                        magnitude=magnitude,
                        touches=touches,
                    )
                    divergences.append(divergence)
        
        return divergences
    
    def _count_touches(self, prices: np.ndarray, level: float, start_idx: int, end_idx: int) -> int:
        """Count how many times price touches a level."""
        touches = 0
        tolerance = level * 0.001  # 0.1% tolerance
        
        for i in range(start_idx, end_idx + 1):
            if abs(prices[i] - level) < tolerance:
                touches += 1
        
        return touches
    
    def _calculate_confidence(self, magnitude: float, indicator_magnitude: float, touches: int) -> float:
        """Calculate divergence confidence score (0-1).
        
        Based on:
        - Magnitude of price move
        - Magnitude of indicator move
        - Number of touches at the level
        """
        if magnitude == 0:
            return 0.0
        
        # Normalize magnitudes
        magnitude_score = min(magnitude / 100, 1.0)  # Assume 100 is significant
        indicator_score = min(indicator_magnitude / 50, 1.0)  # Assume 50 is significant
        touches_score = min(touches / 5, 1.0)  # Assume 5 touches is significant
        
        # Weighted average
        confidence = (magnitude_score * 0.4 + indicator_score * 0.4 + touches_score * 0.2)
        
        return min(confidence, 1.0)
    
    def detect_all_divergences(
        self,
        prices: np.ndarray,
        rsi: np.ndarray,
        macd: np.ndarray,
        stochastic_k: np.ndarray,
    ) -> Dict[str, List[Divergence]]:
        """Detect all divergences for RSI, MACD, and Stochastic.
        
        Args:
            prices: Price array
            rsi: RSI indicator values
            macd: MACD line values
            stochastic_k: Stochastic %K values
        
        Returns:
            Dict mapping indicator name -> list of divergences
        """
        all_divergences = {}
        
        # RSI divergences
        all_divergences["RSI_bullish"] = self.detect_bullish_divergence(prices, rsi, "RSI")
        all_divergences["RSI_bearish"] = self.detect_bearish_divergence(prices, rsi, "RSI")
        
        # MACD divergences
        all_divergences["MACD_bullish"] = self.detect_bullish_divergence(prices, macd, "MACD")
        all_divergences["MACD_bearish"] = self.detect_bearish_divergence(prices, macd, "MACD")
        
        # Stochastic divergences
        all_divergences["STOCH_bullish"] = self.detect_bullish_divergence(prices, stochastic_k, "STOCHASTIC")
        all_divergences["STOCH_bearish"] = self.detect_bearish_divergence(prices, stochastic_k, "STOCHASTIC")
        
        return all_divergences
    
    def generate_signals(
        self,
        divergences: Dict[str, List[Divergence]],
        min_confidence: float = 0.5,
    ) -> List[Dict]:
        """Generate trading signals from divergences.
        
        Args:
            divergences: Dict of detected divergences
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of trading signals
        """
        signals = []
        
        for div_type, div_list in divergences.items():
            for divergence in div_list:
                if divergence.confidence >= min_confidence:
                    signal = {
                        "type": "divergence",
                        "direction": "bullish" if divergence.type == DivergenceType.BULLISH else "bearish",
                        "indicator": divergence.indicator,
                        "confidence": divergence.confidence,
                        "price": divergence.price_value,
                        "indicator_value": divergence.indicator_value,
                        "magnitude": divergence.magnitude,
                    }
                    signals.append(signal)
        
        # Sort by confidence (highest first)
        signals.sort(key=lambda x: x["confidence"], reverse=True)
        
        return signals
    
    def set_sensitivity(self, sensitivity: str) -> None:
        """Change divergence detection sensitivity.
        
        Args:
            sensitivity: "strict", "normal", or "loose"
        """
        self.sensitivity = DivergenceSensitivity(sensitivity)
        self.lookback = self.lookback_periods[self.sensitivity]
        log.info(f"Divergence sensitivity set to {sensitivity} (lookback: {self.lookback})")
