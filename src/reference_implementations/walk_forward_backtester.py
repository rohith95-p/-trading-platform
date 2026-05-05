"""
SOURCE: git repos/Fiduciary-Sentinel-Core - Copy/backtest/engine.py
PURPOSE: Walk-forward validation backtesting engine.
         Tests PPO agent on rolling out-of-sample windows to prevent overfitting.

Walk-forward methodology:
  Train (12 months) → Validate (3 months, pick best model) → Test (3 months, record performance)
  Slide window forward by test_months and repeat.

This is more rigorous than simple train/test split because:
- Each test window is truly out-of-sample
- Model selection happens on validation, not test data
- Captures regime changes over time

Our backtester (src/backtesting/pandas_backtester.py) uses a simpler approach.
This walk-forward engine is for PPO agent evaluation specifically.

Usage:
    engine = WalkForwardBacktester(ticker="BTC-USD", initial_capital=10000)
    results_df, portfolio_curve_df = engine.run_walk_forward(
        train_months=12, val_months=3, test_months=3
    )
    print(results_df)  # Per-window returns
    print(f"Total return: {results_df['Return_Pct'].sum():.2f}%")
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple


class WalkForwardBacktester:
    """
    Walk-forward validation for PPO trading agents.

    Requires:
    - A trained PPO model (stable-baselines3 compatible)
    - Historical OHLCV data
    - TradingEnvironment compatible with the model
    """

    def __init__(self, ticker: str = "BTC-USD", initial_capital: float = 10000.0,
                 historical_data: Optional[dict] = None):
        self.ticker = ticker
        self.initial_capital = initial_capital
        self.historical_data = historical_data
        self.df_full = None

        if historical_data:
            self.df_full = historical_data.get("stock")

    def run_walk_forward(self, model, env_class,
                         train_months: int = 12,
                         val_months: int = 3,
                         test_months: int = 3) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Execute walk-forward validation.

        Args:
            model: Trained PPO model (stable-baselines3 compatible)
            env_class: TradingEnvironment class to instantiate per window
            train_months: Training window size in months
            val_months: Validation window size in months
            test_months: Test window size in months (also the step size)

        Returns:
            (results_df, portfolio_curve_df)
            results_df: Per-window {Start, End, Return_Pct, Ending_Capital}
            portfolio_curve_df: {Date, Portfolio_Value} for full equity curve
        """
        if self.df_full is None:
            raise ValueError("No historical data loaded.")

        df_len = len(self.df_full)
        days_per_month = 30 if any(c in self.ticker for c in ["BTC", "ETH"]) else 21

        train_len = train_months * days_per_month
        val_len = val_months * days_per_month
        test_len = test_months * days_per_month

        current_idx = train_len + val_len
        results = []
        portfolio_curve = []
        current_capital = self.initial_capital

        while current_idx + test_len < df_len:
            test_end_idx = current_idx + test_len
            test_df = self.df_full.iloc[current_idx: test_end_idx]

            start_date = test_df.index[0]
            end_date = test_df.index[-1]
            print(f"[WALK-FORWARD] Testing: {start_date.date()} → {end_date.date()}")

            # Create test environment for this window
            test_data = {
                "stock": test_df,
                "sp500": self.historical_data.get("sp500", pd.DataFrame()),
                "interest_rate": self.historical_data.get("interest_rate", pd.Series()),
            }
            test_env = env_class(ticker=self.ticker, initial_balance=current_capital,
                                 historical_data=test_data)

            obs, _ = test_env.reset()
            test_env.current_step = 0
            test_env.max_steps = len(test_df) - 1

            done = False
            info = {"portfolio_value": current_capital}

            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = test_env.step(action)
                done = terminated or truncated
                portfolio_curve.append({
                    "Date": test_df.index[min(test_env.current_step, len(test_df) - 1)],
                    "Portfolio_Value": info["portfolio_value"],
                })

            final_value = info["portfolio_value"]
            return_pct = (final_value - current_capital) / current_capital * 100
            print(f"[WALK-FORWARD] Return: {return_pct:.2f}% | Capital: ${final_value:.2f}")

            results.append({
                "Start": start_date,
                "End": end_date,
                "Return_Pct": return_pct,
                "Ending_Capital": final_value,
            })

            current_capital = final_value
            current_idx += test_len

        return pd.DataFrame(results), pd.DataFrame(portfolio_curve)

    @staticmethod
    def compute_summary_stats(results_df: pd.DataFrame) -> dict:
        """Compute summary statistics from walk-forward results."""
        if results_df.empty:
            return {}
        returns = results_df["Return_Pct"].values
        return {
            "total_return_pct": returns.sum(),
            "avg_window_return_pct": returns.mean(),
            "win_rate": (returns > 0).mean(),
            "sharpe_ratio": returns.mean() / returns.std() * np.sqrt(12) if returns.std() > 0 else 0,
            "max_drawdown_pct": results_df["Ending_Capital"].pct_change().min() * 100,
            "n_windows": len(results_df),
        }
