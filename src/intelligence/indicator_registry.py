"""
Indicator Registry for managing and computing technical indicators.

Provides a centralized registry for all available indicators (Phase 1 and Phase 1.5).
Supports efficient computation and caching of indicators.
"""
from typing import Dict, List, Any, Optional
import numpy as np
from src.intelligence.indicators import TechnicalIndicators, IndicatorCache


class IndicatorRegistry:
    """Registry for all available technical indicators."""
    
    def __init__(self, cache: Optional[IndicatorCache] = None):
        """Initialize indicator registry with optional caching."""
        self.indicators = TechnicalIndicators(cache=cache)
        self.cache = cache
        
        # Define available indicators with their parameters
        self.available_indicators = {
            # Phase 1 indicators
            "EMA_20": {"method": "ema", "params": {"period": 20}},
            "EMA_50": {"method": "ema", "params": {"period": 50}},
            "EMA_200": {"method": "ema", "params": {"period": 200}},
            "RSI_14": {"method": "rsi", "params": {"period": 14}},
            "MACD": {"method": "macd", "params": {}},
            "ATR_14": {"method": "atr", "params": {"period": 14}},
            "BBANDS_20": {"method": "bbands", "params": {"period": 20, "std_dev": 2.0}},
            "ADX_14": {"method": "adx", "params": {"period": 14}},
            "OBV": {"method": "obv", "params": {}},
            "VWAP": {"method": "vwap", "params": {}},
            
            # Phase 1.5 indicators
            "STOCHASTIC": {"method": "stochastic_oscillator", "params": {"k_period": 14, "k_smooth": 3, "d_smooth": 3}},
            "CCI_20": {"method": "commodity_channel_index", "params": {"period": 20}},
            "WILLR_14": {"method": "williams_percent_r", "params": {"period": 14}},
            "ICHIMOKU": {"method": "ichimoku_cloud", "params": {"tenkan_period": 9, "kijun_period": 26, "senkou_b_period": 52}},
            "AROON": {"method": "aroon_indicator", "params": {"period": 25}},
            "KELTNER": {"method": "keltner_channels", "params": {"period": 20, "atr_multiplier": 2.0}},
            "MFI_14": {"method": "money_flow_index", "params": {"period": 14}},
            "ROC_12": {"method": "rate_of_change", "params": {"period": 12}},
            "AD": {"method": "accumulation_distribution", "params": {}},
            "CMF_20": {"method": "chaikin_money_flow", "params": {"period": 20}},
        }
    
    def get_available_indicators(self) -> List[str]:
        """Get list of all available indicator names."""
        return list(self.available_indicators.keys())
    
    def compute(
        self,
        indicator_name: str,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: Optional[np.ndarray] = None,
    ) -> Any:
        """Compute a single indicator by name."""
        if indicator_name not in self.available_indicators:
            raise ValueError(f"Unknown indicator: {indicator_name}")
        
        indicator_config = self.available_indicators[indicator_name]
        method_name = indicator_config["method"]
        params = indicator_config["params"]
        
        # Get the method from TechnicalIndicators (use class method, not instance)
        method = getattr(TechnicalIndicators, method_name)
        
        # Build arguments based on indicator type
        if method_name == "obv":
            # OBV(closes, volumes)
            if volumes is None:
                raise ValueError(f"Indicator {indicator_name} requires volumes")
            return method(closes, volumes, **params)
        elif method_name == "vwap":
            # VWAP(highs, lows, closes, volumes)
            if volumes is None:
                raise ValueError(f"Indicator {indicator_name} requires volumes")
            return method(highs, lows, closes, volumes, **params)
        elif method_name in ["money_flow_index", "accumulation_distribution", "chaikin_money_flow"]:
            # These need highs, lows, closes, volumes
            if volumes is None:
                raise ValueError(f"Indicator {indicator_name} requires volumes")
            return method(highs, lows, closes, volumes, **params)
        elif method_name == "aroon_indicator":
            # Aroon(highs, lows, period)
            return method(highs, lows, **params)
        elif method_name in ["atr", "adx", "stochastic_oscillator", "commodity_channel_index", 
                             "williams_percent_r", "ichimoku_cloud", "keltner_channels"]:
            # These need highs, lows, closes
            return method(highs, lows, closes, **params)
        elif method_name in ["ema", "rsi", "rate_of_change"]:
            # These only need closes
            return method(closes, **params)
        elif method_name in ["macd", "bbands"]:
            # These only need closes
            return method(closes, **params)
        else:
            raise ValueError(f"Unknown method: {method_name}")
    
    def compute_multiple(
        self,
        indicator_names: List[str],
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """Compute multiple indicators efficiently."""
        results = {}
        for indicator_name in indicator_names:
            try:
                results[indicator_name] = self.compute(
                    indicator_name, highs, lows, closes, volumes
                )
            except Exception as e:
                results[indicator_name] = {"error": str(e)}
        return results
    
    def compute_all(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
    ) -> Dict[str, Any]:
        """Compute all available indicators."""
        return self.indicators.compute_all(highs, lows, closes, volumes)
