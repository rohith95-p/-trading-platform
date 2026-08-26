"""
DataFetcher -- Centralised MT5 data access layer.

Fetches:
  - M15 OHLCV for strategy signals
  - D1 OHLCV for daily ATR drawdown cap
  - M5 tick_volume for volume confirmation
  - Live tick data (ask/bid/spread)
"""

import logging
import numpy as np
import MetaTrader5 as _mt5
from typing import Any, Optional, cast
from datetime import datetime, timezone, timedelta

mt5: Any = _mt5
log = logging.getLogger(__name__)

# IST offset
IST = timezone(timedelta(hours=5, minutes=30))


class DataFetcher:
    """Fetches OHLCV data and tick info from MetaTrader 5."""

    def __init__(self, symbol: str = "XAUUSDm"):
        self.symbol = symbol

    # ------------------------------------------------------------------
    # Rate fetchers
    # ------------------------------------------------------------------

    def get_rates(self, timeframe: int, count: int) -> Optional[np.ndarray]:
        """Fetch the latest `count` candles for the given timeframe."""
        rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, count)
        if rates is None or len(rates) < count:
            log.debug(f"get_rates({timeframe}, {count}): insufficient data")
            return None
        return cast(np.ndarray, rates)

    def get_m5_rates(self, count: int = 100) -> Optional[np.ndarray]:
        """Fetch M5 candles (used for volume confirmation)."""
        return self.get_rates(mt5.TIMEFRAME_M5, count)

    def get_m15_rates(self, count: int = 100) -> Optional[np.ndarray]:
        """Fetch M15 candles (primary strategy timeframe)."""
        return self.get_rates(mt5.TIMEFRAME_M15, count)

    def get_d1_rates(self, count: int = 20) -> Optional[np.ndarray]:
        """Fetch D1 candles (used for daily ATR drawdown cap)."""
        return self.get_rates(mt5.TIMEFRAME_D1, count)

    def get_rates_range(
        self, timeframe: int, start: datetime, end: datetime
    ) -> Optional[np.ndarray]:
        """Fetch candles between two UTC datetimes."""
        rates = mt5.copy_rates_range(self.symbol, timeframe, start, end)
        if rates is None or len(rates) == 0:
            return None
        return cast(np.ndarray, rates)

    # ------------------------------------------------------------------
    # Tick / price
    # ------------------------------------------------------------------

    def get_tick(self):
        """Return the latest tick (ask, bid, etc.)."""
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            log.warning(f"symbol_info_tick({self.symbol}) returned None")
        return tick

    def get_ask(self) -> Optional[float]:
        tick = self.get_tick()
        return tick.ask if tick else None

    def get_bid(self) -> Optional[float]:
        tick = self.get_tick()
        return tick.bid if tick else None

    def get_spread(self) -> Optional[int]:
        """Return the current spread in points."""
        info = mt5.symbol_info(self.symbol)
        return info.spread if info else None

    # ------------------------------------------------------------------
    # Positions & History
    # ------------------------------------------------------------------

    def get_positions(self) -> list:
        """Return open positions for the symbol, or empty list."""
        positions = mt5.positions_get(symbol=self.symbol)
        return list(positions) if positions else []

    def get_todays_closed_pl(self) -> float:
        """Sum the P/L of all deals closed today (IST midnight to now)."""
        now_ist = datetime.now(IST)
        midnight_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        midnight_utc = midnight_ist.astimezone(timezone.utc)

        deals = mt5.history_deals_get(midnight_utc, datetime.now(timezone.utc))
        if deals is None:
            return 0.0

        total_pl = 0.0
        for deal in deals:
            # entry=1 means closing a position (exit deal)
            if deal.entry == 1 and deal.symbol == self.symbol:
                total_pl += deal.profit
        return total_pl
