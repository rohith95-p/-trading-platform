"""
Technical indicators implementation with 20+ indicators.

Implements Phase 1 (8 indicators) and Phase 1.5 (10+ indicators) with vectorized NumPy operations.
All calculations are optimized for performance (<100ms target).
"""

import numpy as np
from typing import List, Dict, Any, Optional


class IndicatorCache:
    """Simple cache for indicator results."""
    def __init__(self):
        self.cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        return self.cache.get(key)
    
    def set(self, key: str, value: Any):
        self.cache[key] = value
    
    def clear(self):
        self.cache.clear()


class TechnicalIndicators:
    """Technical indicators computation with vectorized NumPy operations."""
    
    def __init__(self, cache: Optional[IndicatorCache] = None):
        """Initialize with optional caching."""
        self.cache = cache or IndicatorCache()
    
    # ========================================================================
    # PHASE 1 INDICATORS (8 indicators)
    # ========================================================================
    
    @staticmethod
    def ema(prices: np.ndarray, period: int) -> np.ndarray:
        """Exponential Moving Average - vectorized implementation.
        
        Args:
            prices: Price array
            period: EMA period
            
        Returns:
            EMA values as numpy array
        """
        prices = np.asarray(prices, dtype=float)
        ema = np.full_like(prices, np.nan)
        
        if len(prices) < period:
            return ema
        
        # Initialize with SMA
        ema[period-1] = np.mean(prices[:period])
        
        # Calculate multiplier
        multiplier = 2.0 / (period + 1)
        
        # Vectorized EMA calculation
        for i in range(period, len(prices)):
            ema[i] = prices[i] * multiplier + ema[i-1] * (1 - multiplier)
        
        return ema
    
    @staticmethod
    def rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Relative Strength Index - vectorized implementation.
        
        Args:
            prices: Price array
            period: RSI period (default 14)
            
        Returns:
            RSI values (0-100) as numpy array
        """
        prices = np.asarray(prices, dtype=float)
        rsi_values = np.full_like(prices, np.nan)
        
        if len(prices) < period + 1:
            return rsi_values
        
        # Calculate price changes
        deltas = np.diff(prices)
        
        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Initial average gain/loss
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        # Calculate first RSI
        if avg_loss == 0:
            rsi_values[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_values[period] = 100.0 - (100.0 / (1.0 + rs))
        
        # Wilder's smoothing for subsequent values
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi_values[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i + 1] = 100.0 - (100.0 / (1.0 + rs))
        
        return rsi_values
    
    @staticmethod
    def macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, np.ndarray]:
        """MACD (Moving Average Convergence Divergence).
        
        Args:
            prices: Price array
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)
            
        Returns:
            Dict with 'macd', 'signal', 'histogram' arrays
        """
        prices = np.asarray(prices, dtype=float)
        
        # Calculate fast and slow EMAs
        ema_fast = TechnicalIndicators.ema(prices, fast)
        ema_slow = TechnicalIndicators.ema(prices, slow)
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA of MACD) - only use valid MACD values
        valid_macd = macd_line[~np.isnan(macd_line)]
        signal_line = TechnicalIndicators.ema(valid_macd, signal)
        
        # Pad signal line to match length
        signal_full = np.full_like(macd_line, np.nan)
        valid_start = slow - 1  # Start where MACD becomes valid
        signal_start = valid_start + signal - 1  # Add signal period
        
        if signal_start < len(signal_full) and len(signal_line) > 0:
            # Only copy the valid signal values
            valid_signal = signal_line[~np.isnan(signal_line)]
            end_idx = min(signal_start + len(valid_signal), len(signal_full))
            signal_full[signal_start:end_idx] = valid_signal[:end_idx - signal_start]
        
        # Histogram
        histogram = macd_line - signal_full
        
        return {
            "macd": macd_line,
            "signal": signal_full,
            "histogram": histogram
        }
    
    @staticmethod
    def atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
        """Average True Range - volatility indicator.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            period: ATR period (default 14)
            
        Returns:
            ATR values as numpy array
        """
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        
        atr_values = np.full_like(closes, np.nan)
        
        if len(closes) < 2:
            return atr_values
        
        # Calculate True Range
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        if len(tr) < period:
            return atr_values
        
        # Initial ATR (SMA of TR)
        atr_val = np.mean(tr[:period])
        atr_values[period] = atr_val
        
        # Wilder's smoothing
        for i in range(period, len(tr)):
            atr_val = (atr_val * (period - 1) + tr[i]) / period
            atr_values[i + 1] = atr_val
        
        return atr_values
    
    @staticmethod
    def bbands(prices: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Dict[str, np.ndarray]:
        """Bollinger Bands - volatility bands.
        
        Args:
            prices: Price array
            period: Period for SMA and std dev (default 20)
            std_dev: Number of standard deviations (default 2.0)
            
        Returns:
            Dict with 'upper', 'middle', 'lower' bands
        """
        prices = np.asarray(prices, dtype=float)
        
        upper = np.full_like(prices, np.nan)
        middle = np.full_like(prices, np.nan)
        lower = np.full_like(prices, np.nan)
        
        # Calculate SMA and bands
        for i in range(period - 1, len(prices)):
            window = prices[i - period + 1:i + 1]
            sma = np.mean(window)
            std = np.std(window, ddof=0)
            
            middle[i] = sma
            upper[i] = sma + std_dev * std
            lower[i] = sma - std_dev * std
        
        return {
            "upper": upper,
            "middle": middle,
            "lower": lower
        }
    
    @staticmethod
    def adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
        """Average Directional Index - trend strength indicator.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            period: ADX period (default 14)
            
        Returns:
            ADX values (0-100) as numpy array
        """
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        
        adx_values = np.full_like(closes, np.nan)
        
        if len(closes) < period + 1:
            return adx_values
        
        # Calculate directional movement
        plus_dm = np.maximum(highs[1:] - highs[:-1], 0)
        minus_dm = np.maximum(lows[:-1] - lows[1:], 0)
        
        # Zero out when opposite movement is larger
        plus_dm = np.where((highs[1:] - highs[:-1]) > (lows[:-1] - lows[1:]), plus_dm, 0)
        minus_dm = np.where((lows[:-1] - lows[1:]) > (highs[1:] - highs[:-1]), minus_dm, 0)
        
        # Calculate ATR
        atr_vals = TechnicalIndicators.atr(highs, lows, closes, period)
        
        if len(plus_dm) < period:
            return adx_values
        
        # Initial smoothed DM
        plus_dm_smooth = np.sum(plus_dm[:period])
        minus_dm_smooth = np.sum(minus_dm[:period])
        
        dx_values = []
        
        # Calculate DX
        for i in range(period - 1, len(atr_vals) - 1):
            if i >= period:
                plus_dm_smooth = plus_dm_smooth - (plus_dm_smooth / period) + plus_dm[i]
                minus_dm_smooth = minus_dm_smooth - (minus_dm_smooth / period) + minus_dm[i]
            
            atr_val = atr_vals[i + 1]
            if atr_val > 0:
                plus_di = 100 * plus_dm_smooth / (atr_val * period)
                minus_di = 100 * minus_dm_smooth / (atr_val * period)
                
                di_sum = plus_di + minus_di
                if di_sum > 0:
                    dx = 100 * np.abs(plus_di - minus_di) / di_sum
                    dx_values.append(dx)
                else:
                    dx_values.append(0)
            else:
                dx_values.append(0)
        
        # ADX is smoothed DX
        if len(dx_values) >= period:
            adx_val = np.mean(dx_values[:period])
            adx_values[period * 2 - 1] = adx_val
            
            for i in range(period, len(dx_values)):
                adx_val = (adx_val * (period - 1) + dx_values[i]) / period
                adx_values[period + i] = adx_val
        
        return adx_values
    
    @staticmethod
    def obv(closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        """On Balance Volume - volume-based momentum indicator.
        
        Args:
            closes: Close prices
            volumes: Volume data
            
        Returns:
            OBV values as numpy array
        """
        closes = np.asarray(closes, dtype=float)
        volumes = np.asarray(volumes, dtype=float)
        
        obv_values = np.zeros_like(closes)
        obv_values[0] = volumes[0]
        
        # Vectorized OBV calculation
        price_changes = np.diff(closes)
        volume_direction = np.where(price_changes > 0, volumes[1:], 
                                    np.where(price_changes < 0, -volumes[1:], 0))
        
        obv_values[1:] = volumes[0] + np.cumsum(volume_direction)
        
        return obv_values
    
    @staticmethod
    def vwap(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        """Volume Weighted Average Price.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            volumes: Volume data
            
        Returns:
            VWAP values as numpy array
        """
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        volumes = np.asarray(volumes, dtype=float)
        
        # Typical price
        typical_price = (highs + lows + closes) / 3.0
        
        # Cumulative VWAP
        cum_vol = np.cumsum(volumes)
        cum_tp_vol = np.cumsum(typical_price * volumes)
        
        vwap_values = np.where(cum_vol > 0, cum_tp_vol / cum_vol, np.nan)
        
        return vwap_values

    # ========================================================================
    # PHASE 1.5 INDICATORS (10+ indicators)
    # ========================================================================
    
    @staticmethod
    def stochastic_oscillator(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                             k_period: int = 14, k_smooth: int = 3, d_smooth: int = 3) -> Dict[str, np.ndarray]:
        """Stochastic Oscillator - momentum indicator.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            k_period: Period for %K calculation (default 14)
            k_smooth: Smoothing period for %K (default 3)
            d_smooth: Smoothing period for %D (default 3)
            
        Returns:
            Dict with 'stoch_k' and 'stoch_d' (0-100 range)
        """
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        
        stoch_k = np.full_like(closes, np.nan)
        
        # Calculate raw %K
        for i in range(k_period - 1, len(closes)):
            window_high = np.max(highs[i - k_period + 1:i + 1])
            window_low = np.min(lows[i - k_period + 1:i + 1])
            
            if window_high != window_low:
                stoch_k[i] = 100 * (closes[i] - window_low) / (window_high - window_low)
            else:
                stoch_k[i] = 50.0
        
        # Smooth %K
        stoch_k_smooth = np.full_like(closes, np.nan)
        for i in range(k_period + k_smooth - 2, len(closes)):
            window = stoch_k[i - k_smooth + 1:i + 1]
            if not np.all(np.isnan(window)):
                stoch_k_smooth[i] = np.nanmean(window)
        
        # Calculate %D (SMA of smoothed %K)
        stoch_d = np.full_like(closes, np.nan)
        for i in range(k_period + k_smooth + d_smooth - 3, len(closes)):
            window = stoch_k_smooth[i - d_smooth + 1:i + 1]
            if not np.all(np.isnan(window)):
                stoch_d[i] = np.nanmean(window)
        
        return {
            "stoch_k": stoch_k_smooth,
            "stoch_d": stoch_d
        }
    
    @staticmethod
    def commodity_channel_index(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                                period: int = 20) -> np.ndarray:
        """Commodity Channel Index (CCI) - trend-following indicator.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            period: CCI period (default 20)
            
        Returns:
            CCI values as numpy array
        """
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        
        # Typical price
        typical_price = (highs + lows + closes) / 3.0
        
        cci_values = np.full_like(closes, np.nan)
        
        # Calculate CCI
        for i in range(period - 1, len(closes)):
            window = typical_price[i - period + 1:i + 1]
            sma = np.mean(window)
            mean_deviation = np.mean(np.abs(window - sma))
            
            if mean_deviation > 0:
                cci_values[i] = (typical_price[i] - sma) / (0.015 * mean_deviation)
            else:
                cci_values[i] = 0
        
        return cci_values
    
    @staticmethod
    def williams_percent_r(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                          period: int = 14) -> np.ndarray:
        """Williams %R - momentum indicator.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            period: Period (default 14)
            
        Returns:
            Williams %R values (-100 to 0 range) as numpy array
        """
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        
        willr = np.full_like(closes, np.nan)
        
        # Calculate Williams %R
        for i in range(period - 1, len(closes)):
            window_high = np.max(highs[i - period + 1:i + 1])
            window_low = np.min(lows[i - period + 1:i + 1])
            
            if window_high != window_low:
                willr[i] = -100 * (window_high - closes[i]) / (window_high - window_low)
            else:
                willr[i] = -50.0
        
        return willr
    
    @staticmethod
    def ichimoku_cloud(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                      tenkan_period: int = 9, kijun_period: int = 26, senkou_b_period: int = 52) -> Dict[str, np.ndarray]:
        """Ichimoku Cloud - comprehensive trend/support/resistance indicator.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            tenkan_period: Tenkan-sen period (default 9)
            kijun_period: Kijun-sen period (default 26)
            senkou_b_period: Senkou Span B period (default 52)
            
        Returns:
            Dict with 'tenkan', 'kijun', 'senkou_a', 'senkou_b', 'chikou'
        """
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        
        def midpoint(high, low, period, index):
            if index < period - 1:
                return np.nan
            window_high = np.max(high[index - period + 1:index + 1])
            window_low = np.min(low[index - period + 1:index + 1])
            return (window_high + window_low) / 2.0
        
        # Tenkan-sen (Conversion Line)
        tenkan = np.array([midpoint(highs, lows, tenkan_period, i) for i in range(len(closes))])
        
        # Kijun-sen (Base Line)
        kijun = np.array([midpoint(highs, lows, kijun_period, i) for i in range(len(closes))])
        
        # Senkou Span A (Leading Span A) - shifted forward
        senkou_a = (tenkan + kijun) / 2.0
        
        # Senkou Span B (Leading Span B) - shifted forward
        senkou_b = np.array([midpoint(highs, lows, senkou_b_period, i) for i in range(len(closes))])
        
        # Chikou Span (Lagging Span) - shifted backward
        chikou = closes.copy()
        
        return {
            "tenkan": tenkan,
            "kijun": kijun,
            "senkou_a": senkou_a,
            "senkou_b": senkou_b,
            "chikou": chikou
        }
    
    @staticmethod
    def aroon_indicator(highs: np.ndarray, lows: np.ndarray, period: int = 25) -> Dict[str, np.ndarray]:
        """Aroon Indicator - trend direction indicator.
        
        Args:
            highs: High prices
            lows: Low prices
            period: Aroon period (default 25)
            
        Returns:
            Dict with 'aroon_up' and 'aroon_down' (0-100 range)
        """
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        
        aroon_up = np.full_like(highs, np.nan)
        aroon_down = np.full_like(lows, np.nan)
        
        # Calculate Aroon Up and Down
        for i in range(period, len(highs)):
            window_high = highs[i - period:i + 1]
            window_low = lows[i - period:i + 1]
            
            # Periods since highest high
            periods_since_high = period - np.argmax(window_high)
            aroon_up[i] = 100 * (period - periods_since_high) / period
            
            # Periods since lowest low
            periods_since_low = period - np.argmin(window_low)
            aroon_down[i] = 100 * (period - periods_since_low) / period
        
        return {
            "aroon_up": aroon_up,
            "aroon_down": aroon_down
        }
    
    @staticmethod
    def keltner_channels(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                        period: int = 20, atr_multiplier: float = 2.0) -> Dict[str, np.ndarray]:
        """Keltner Channels - volatility-based bands.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            period: Period for EMA and ATR (default 20)
            atr_multiplier: ATR multiplier (default 2.0)
            
        Returns:
            Dict with 'upper', 'middle', 'lower' bands
        """
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        
        # Middle line (EMA of close)
        middle = TechnicalIndicators.ema(closes, period)
        
        # ATR for channel width
        atr_values = TechnicalIndicators.atr(highs, lows, closes, period)
        
        # Upper and lower bands
        upper = middle + atr_multiplier * atr_values
        lower = middle - atr_multiplier * atr_values
        
        return {
            "upper": upper,
            "middle": middle,
            "lower": lower
        }
    
    @staticmethod
    def money_flow_index(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                        volumes: np.ndarray, period: int = 14) -> np.ndarray:
        """Money Flow Index (MFI) - volume-weighted momentum indicator.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            volumes: Volume data
            period: MFI period (default 14)
            
        Returns:
            MFI values (0-100 range) as numpy array
        """
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        volumes = np.asarray(volumes, dtype=float)
        
        # Typical price
        typical_price = (highs + lows + closes) / 3.0
        
        # Money flow
        money_flow = typical_price * volumes
        
        mfi_values = np.full_like(closes, np.nan)
        
        # Calculate MFI
        for i in range(period, len(closes)):
            # Positive and negative money flow
            positive_flow = 0
            negative_flow = 0
            
            for j in range(i - period + 1, i + 1):
                if typical_price[j] > typical_price[j - 1]:
                    positive_flow += money_flow[j]
                elif typical_price[j] < typical_price[j - 1]:
                    negative_flow += money_flow[j]
            
            if negative_flow > 0:
                money_ratio = positive_flow / negative_flow
                mfi_values[i] = 100 - (100 / (1 + money_ratio))
            else:
                mfi_values[i] = 100.0
        
        return mfi_values
    
    @staticmethod
    def rate_of_change(closes: np.ndarray, period: int = 12) -> np.ndarray:
        """Rate of Change (ROC) - momentum indicator.
        
        Args:
            closes: Close prices
            period: ROC period (default 12)
            
        Returns:
            ROC values (percentage) as numpy array
        """
        closes = np.asarray(closes, dtype=float)
        
        roc_values = np.full_like(closes, np.nan)
        
        # Calculate ROC
        for i in range(period, len(closes)):
            if closes[i - period] != 0:
                roc_values[i] = 100 * (closes[i] - closes[i - period]) / closes[i - period]
            else:
                roc_values[i] = 0
        
        return roc_values
    
    @staticmethod
    def accumulation_distribution(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                                 volumes: np.ndarray) -> np.ndarray:
        """Accumulation/Distribution Line - volume-based indicator.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            volumes: Volume data
            
        Returns:
            A/D Line values as numpy array
        """
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        volumes = np.asarray(volumes, dtype=float)
        
        # Money Flow Multiplier
        mfm = np.where(
            (highs - lows) != 0,
            ((closes - lows) - (highs - closes)) / (highs - lows),
            0
        )
        
        # Money Flow Volume
        mfv = mfm * volumes
        
        # Accumulation/Distribution Line (cumulative)
        ad_line = np.cumsum(mfv)
        
        return ad_line
    
    @staticmethod
    def chaikin_money_flow(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                          volumes: np.ndarray, period: int = 20) -> np.ndarray:
        """Chaikin Money Flow (CMF) - volume-weighted price indicator.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            volumes: Volume data
            period: CMF period (default 20)
            
        Returns:
            CMF values (-1 to 1 range) as numpy array
        """
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        volumes = np.asarray(volumes, dtype=float)
        
        # Money Flow Multiplier
        mfm = np.where(
            (highs - lows) != 0,
            ((closes - lows) - (highs - closes)) / (highs - lows),
            0
        )
        
        # Money Flow Volume
        mfv = mfm * volumes
        
        cmf_values = np.full_like(closes, np.nan)
        
        # Calculate CMF
        for i in range(period - 1, len(closes)):
            sum_mfv = np.sum(mfv[i - period + 1:i + 1])
            sum_volume = np.sum(volumes[i - period + 1:i + 1])
            
            if sum_volume > 0:
                cmf_values[i] = sum_mfv / sum_volume
            else:
                cmf_values[i] = 0
        
        return cmf_values
    
    # ========================================================================
    # ADDITIONAL INDICATORS (to reach 20+)
    # ========================================================================
    
    @staticmethod
    def sma(prices: np.ndarray, period: int) -> np.ndarray:
        """Simple Moving Average.
        
        Args:
            prices: Price array
            period: SMA period
            
        Returns:
            SMA values as numpy array
        """
        prices = np.asarray(prices, dtype=float)
        sma_values = np.full_like(prices, np.nan)
        
        for i in range(period - 1, len(prices)):
            sma_values[i] = np.mean(prices[i - period + 1:i + 1])
        
        return sma_values
    
    @staticmethod
    def stochastic_rsi(closes: np.ndarray, rsi_period: int = 14, stoch_period: int = 14,
                      k_smooth: int = 3, d_smooth: int = 3) -> Dict[str, np.ndarray]:
        """Stochastic RSI - momentum indicator combining RSI and Stochastic.
        
        Args:
            closes: Close prices
            rsi_period: RSI period (default 14)
            stoch_period: Stochastic period (default 14)
            k_smooth: %K smoothing (default 3)
            d_smooth: %D smoothing (default 3)
            
        Returns:
            Dict with 'k' and 'd' values (0-100 range)
        """
        closes = np.asarray(closes, dtype=float)
        
        # Calculate RSI
        rsi_values = TechnicalIndicators.rsi(closes, rsi_period)
        
        # Apply Stochastic to RSI
        stoch_k = np.full_like(closes, np.nan)
        
        for i in range(rsi_period + stoch_period - 1, len(closes)):
            rsi_window = rsi_values[i - stoch_period + 1:i + 1]
            rsi_window = rsi_window[~np.isnan(rsi_window)]
            
            if len(rsi_window) > 0:
                rsi_high = np.max(rsi_window)
                rsi_low = np.min(rsi_window)
                
                if rsi_high != rsi_low:
                    stoch_k[i] = 100 * (rsi_values[i] - rsi_low) / (rsi_high - rsi_low)
                else:
                    stoch_k[i] = 50.0
        
        # Smooth %K
        stoch_k_smooth = TechnicalIndicators.sma(stoch_k[~np.isnan(stoch_k)], k_smooth)
        
        # Calculate %D
        stoch_d = TechnicalIndicators.sma(stoch_k_smooth[~np.isnan(stoch_k_smooth)], d_smooth)
        
        # Pad to original length
        k_full = np.full_like(closes, np.nan)
        d_full = np.full_like(closes, np.nan)
        
        k_start = rsi_period + stoch_period + k_smooth - 2
        if k_start < len(k_full):
            k_full[k_start:k_start + len(stoch_k_smooth)] = stoch_k_smooth
        
        d_start = rsi_period + stoch_period + k_smooth + d_smooth - 3
        if d_start < len(d_full):
            d_full[d_start:d_start + len(stoch_d)] = stoch_d
        
        return {
            "k": k_full,
            "d": d_full
        }
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_latest(self, series: np.ndarray) -> float:
        """Get the latest non-NaN value from a series.
        
        Args:
            series: Numpy array
            
        Returns:
            Latest non-NaN value or NaN if all values are NaN
        """
        series = np.asarray(series)
        valid_values = series[~np.isnan(series)]
        return valid_values[-1] if len(valid_values) > 0 else np.nan
    
    def compute_all(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                   volumes: np.ndarray) -> Dict[str, Any]:
        """Compute all available indicators.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            volumes: Volume data
            
        Returns:
            Dict with all indicator results
        """
        results = {}
        
        # Phase 1 indicators
        results["ema_20"] = self.ema(closes, 20)
        results["ema_50"] = self.ema(closes, 50)
        results["ema_200"] = self.ema(closes, 200)
        results["rsi_14"] = self.rsi(closes, 14)
        results["macd"] = self.macd(closes)
        results["atr_14"] = self.atr(highs, lows, closes, 14)
        results["bbands_20"] = self.bbands(closes, 20, 2.0)
        results["adx_14"] = self.adx(highs, lows, closes, 14)
        results["obv"] = self.obv(closes, volumes)
        results["vwap"] = self.vwap(highs, lows, closes, volumes)
        
        # Phase 1.5 indicators
        results["stochastic"] = self.stochastic_oscillator(highs, lows, closes, 14, 3, 3)
        results["cci_20"] = self.commodity_channel_index(highs, lows, closes, 20)
        results["willr_14"] = self.williams_percent_r(highs, lows, closes, 14)
        results["ichimoku"] = self.ichimoku_cloud(highs, lows, closes, 9, 26, 52)
        results["aroon"] = self.aroon_indicator(highs, lows, 25)
        results["keltner"] = self.keltner_channels(highs, lows, closes, 20, 2.0)
        results["mfi_14"] = self.money_flow_index(highs, lows, closes, volumes, 14)
        results["roc_12"] = self.rate_of_change(closes, 12)
        results["ad"] = self.accumulation_distribution(highs, lows, closes, volumes)
        results["cmf_20"] = self.chaikin_money_flow(highs, lows, closes, volumes, 20)
        
        # Additional indicators
        results["sma_20"] = self.sma(closes, 20)
        
        return results
