"""
Pandas-based vectorized backtester
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from src.interfaces import Backtester
from src.interfaces.backtester import BacktestResult, BacktestMetrics, BacktestTrade
from src.backtesting.metrics import (
    compute_sharpe_ratio,
    compute_max_drawdown,
    compute_win_rate,
    compute_profit_factor,
    compute_annual_return,
)


class PandasBacktester(Backtester):
    """Vectorized backtester using pandas.

    Args:
        fee_rate: Round-trip fee as a fraction of trade value (default 0.001 = 0.1%).
        slippage_rate: One-way slippage as a fraction of price (default 0.0005 = 0.05%).
        timeframe: Data timeframe string, e.g. '1d', '1h', '15m' (default '1d').
    """

    def __init__(
        self,
        fee_rate: float = 0.001,
        slippage_rate: float = 0.0005,
        timeframe: str = "1d",
    ):
        super().__init__("pandas")
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self.timeframe = timeframe

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_slippage(self, price: float, is_buy: bool) -> float:
        """Return price adjusted for slippage."""
        if is_buy:
            return price * (1.0 + self.slippage_rate)
        return price * (1.0 - self.slippage_rate)

    def _apply_fee(self, trade_value: float) -> float:
        """Return fee amount for a given trade value."""
        return abs(trade_value) * self.fee_rate

    def _generate_signals(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.Series:
        """Resolve user-supplied signals or build a simple SMA crossover signal."""
        configured_signals = config.get("signals")
        if configured_signals is not None:
            if len(configured_signals) != len(df):
                raise ValueError("signals length must match historical_data length")

            signals = pd.Series(configured_signals, index=df.index, dtype=float).fillna(0.0)
            return signals.clip(lower=-1, upper=1).astype(int)

        fast_window = int(config.get("fast_window", 10))
        slow_window = int(config.get("slow_window", 30))
        if fast_window < 1 or slow_window < 1:
            raise ValueError("fast_window and slow_window must be positive")
        if fast_window >= slow_window:
            raise ValueError("fast_window must be smaller than slow_window")

        fast_ma = df["close"].rolling(window=fast_window, min_periods=fast_window).mean()
        slow_ma = df["close"].rolling(window=slow_window, min_periods=slow_window).mean()
        signal = (fast_ma > slow_ma).astype(int)
        signal[(fast_ma.isna()) | (slow_ma.isna())] = 0
        return signal

    # ------------------------------------------------------------------
    # Backtester interface
    # ------------------------------------------------------------------

    def backtest(
        self,
        strategy_name: str,
        historical_data: List[Dict[str, Any]],
        config: Dict[str, Any],
    ) -> BacktestResult:
        """Run a vectorized backtest.

        Args:
            strategy_name: Name of the strategy.
            historical_data: List of OHLCV dicts with keys:
                datetime, open, high, low, close, volume.
            config: Optional configuration dict. Supports explicit `signals` or
                SMA crossover settings (`fast_window`, `slow_window`).

        Returns:
            BacktestResult with metrics, trade log, and equity curve.
        """
        df = pd.DataFrame(historical_data)
        df["datetime"] = pd.to_datetime(df["datetime"], format="mixed", dayfirst=False)
        df = df.sort_values("datetime").reset_index(drop=True)

        df["signal"] = self._generate_signals(df, config)

        # --- Vectorized returns ---
        df["returns"] = df["close"].pct_change().fillna(0.0)
        df["strategy_returns"] = df["signal"].shift(1).fillna(0) * df["returns"]

        # --- Equity curve ---
        df["cumulative_returns"] = (1.0 + df["strategy_returns"]).cumprod()
        equity_curve: List[float] = df["cumulative_returns"].tolist()

        # --- Trade-by-trade log with fee/slippage ---
        trades: List[BacktestTrade] = []
        in_position = False
        entry_price = 0.0
        entry_time: datetime = df["datetime"].iloc[0]

        for _, row in df.iterrows():
            if row["signal"] == 1 and not in_position:
                in_position = True
                entry_price = self._apply_slippage(float(row["close"]), is_buy=True)
                entry_time = row["datetime"]

            elif row["signal"] == 0 and in_position:
                in_position = False
                exit_price = self._apply_slippage(float(row["close"]), is_buy=False)
                size = 1.0
                gross_pnl = (exit_price - entry_price) * size
                fee = self._apply_fee(entry_price * size) + self._apply_fee(exit_price * size)
                net_pnl = gross_pnl - fee
                pnl_percent = (net_pnl / entry_price) * 100.0 if entry_price != 0 else 0.0

                trades.append(
                    BacktestTrade(
                        entry_time=entry_time,
                        exit_time=row["datetime"],
                        entry_price=entry_price,
                        exit_price=exit_price,
                        size=size,
                        pnl=net_pnl,
                        pnl_percent=pnl_percent,
                    )
                )

        metrics = self.compute_metrics(trades)

        return BacktestResult(
            strategy_name=strategy_name,
            start_date=df["datetime"].iloc[0],
            end_date=df["datetime"].iloc[-1],
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
        )

    def compute_metrics(self, trades: List[BacktestTrade]) -> BacktestMetrics:
        """Compute performance metrics from a list of trades."""
        if not trades:
            return BacktestMetrics(
                total_return=0.0,
                annual_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                trades_count=0,
                winning_trades=0,
                losing_trades=0,
                avg_win=0.0,
                avg_loss=0.0,
            )

        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl < 0]

        total_return = sum(t.pnl for t in trades)
        avg_win = sum(t.pnl for t in winning) / len(winning) if winning else 0.0
        avg_loss = abs(sum(t.pnl for t in losing) / len(losing)) if losing else 0.0

        # Use standalone metrics helpers
        pct_returns = [t.pnl_percent / 100.0 for t in trades]
        sharpe = compute_sharpe_ratio(pct_returns)

        # Equity curve from cumulative pnl for drawdown
        equity: List[float] = []
        running = 0.0
        for t in trades:
            running += t.pnl
            equity.append(running)
        max_dd = compute_max_drawdown(equity)

        win_rate = compute_win_rate(trades)
        profit_factor = compute_profit_factor(trades)

        # Approximate n_days from trade timestamps
        n_days = max(
            (trades[-1].exit_time - trades[0].entry_time).days, 1
        ) if len(trades) > 1 else 1
        annual_ret = compute_annual_return(
            total_return / max(abs(trades[0].entry_price), 1.0), n_days
        )

        return BacktestMetrics(
            total_return=total_return,
            annual_return=annual_ret,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            win_rate=win_rate,
            profit_factor=profit_factor,
            trades_count=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            avg_win=avg_win,
            avg_loss=avg_loss,
        )
