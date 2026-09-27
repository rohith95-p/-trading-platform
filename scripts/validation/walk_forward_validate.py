"""
Walk-Forward Validation (adapted from VectorBT pattern).

Tests strategy robustness by rolling IS/OOS windows.
A strategy is robust if OOS_PF / IS_PF > 0.5 (efficiency ratio).

Pattern:
- Split data into N folds
- Each fold: train on 70% (IS), test on 30% (OOS)
- Roll forward: fold 1 IS → fold 1 OOS → fold 2 IS → fold 2 OOS ...
- Measure: average efficiency ratio across all folds

If efficiency < 0.5: Strategy is overfit, reject.
If efficiency > 0.7: Strategy is robust, proceed.

Usage:
    python -m scripts.validation.walk_forward_validate
"""

import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtesting.engine import BacktestEngine, EngineConfig
from src.backtesting.data import load_bars
from src.backtesting.costs import CostModel
from src.backtesting.metrics import summarize
from src.strategies.portfolio_v4 import PORTFOLIO_V4


class WalkForwardValidator:
    """
    Rolling window validation with IS/OOS splits.
    
    Measures out-of-sample degradation to detect overfitting.
    """
    
    def __init__(
        self,
        n_folds: int = 6,
        is_ratio: float = 0.70,
        efficiency_threshold: float = 0.50,
    ):
        """
        Args:
            n_folds: Number of train/test folds
            is_ratio: Fraction of each fold used for in-sample (training)
            efficiency_threshold: Minimum OOS_PF / IS_PF ratio to pass
        """
        self.n_folds = n_folds
        self.is_ratio = is_ratio
        self.efficiency_threshold = efficiency_threshold
    
    def validate(
        self,
        strategies: List,
        bars,
        config: EngineConfig,
        cost_model: CostModel,
    ) -> Dict[str, Any]:
        """
        Run walk-forward validation.
        
        Returns:
            {
                'folds': [fold results],
                'avg_efficiency': float,
                'passed': bool,
                'is_avg_pf': float,
                'oos_avg_pf': float,
            }
        """
        print("="*70)
        print("WALK-FORWARD VALIDATION")
        print("="*70)
        print(f"Strategies: {[s.name for s in strategies]}")
        print(f"Folds: {self.n_folds}")
        print(f"IS/OOS split: {self.is_ratio*100:.0f}% / {(1-self.is_ratio)*100:.0f}%")
        print(f"Efficiency threshold: {self.efficiency_threshold:.2f}")
        print()
        
        # Get M15 data length
        m15_len = len(bars.m15)
        
        # Calculate fold size
        # Each fold needs enough data for IS + OOS
        # Leave some data at the end for final OOS test
        usable_len = int(m15_len * 0.90)  # Use 90% of data, reserve 10% for final test
        fold_size = usable_len // (self.n_folds + 1)
        
        print(f"Total M15 bars: {m15_len}")
        print(f"Usable bars: {usable_len}")
        print(f"Bars per fold: {fold_size}")
        print()
        
        fold_results = []
        
        for fold_idx in range(self.n_folds):
            print(f"Fold {fold_idx + 1}/{self.n_folds}")
            print("-" * 70)
            
            # Define IS and OOS windows
            is_start = fold_idx * fold_size
            is_end = is_start + int(fold_size * self.is_ratio)
            oos_start = is_end
            oos_end = oos_start + int(fold_size * (1 - self.is_ratio))
            
            # Ensure we don't exceed data bounds
            if oos_end > m15_len:
                print(f"Fold {fold_idx + 1} exceeds data bounds, skipping")
                continue
            
            # Slice data for IS
            is_bars = self._slice_bars(bars, is_start, is_end)
            is_engine = BacktestEngine(is_bars, cost_model, config)
            
            print(f"  IS window: bars {is_start} to {is_end} ({is_end - is_start} bars)")
            is_result = is_engine.run(strategies)
            is_stats = summarize(is_result.trades, is_result.equity, config.starting_balance).to_dict()
            
            print(f"  IS: n={is_stats['trades']}, PF={is_stats['profit_factor']:.3f}, "
                  f"net=${is_stats['net_pl']:.2f}")
            
            # Slice data for OOS
            oos_bars = self._slice_bars(bars, oos_start, oos_end)
            oos_engine = BacktestEngine(oos_bars, cost_model, config)
            
            print(f"  OOS window: bars {oos_start} to {oos_end} ({oos_end - oos_start} bars)")
            oos_result = oos_engine.run(strategies)
            oos_stats = summarize(oos_result.trades, oos_result.equity, config.starting_balance).to_dict()
            
            print(f"  OOS: n={oos_stats['trades']}, PF={oos_stats['profit_factor']:.3f}, "
                  f"net=${oos_stats['net_pl']:.2f}")
            
            # Calculate efficiency ratio
            if is_stats['profit_factor'] > 0:
                efficiency = oos_stats['profit_factor'] / is_stats['profit_factor']
            else:
                efficiency = 0.0
            
            degradation_pct = (1 - efficiency) * 100
            
            print(f"  Efficiency: {efficiency:.3f} (degradation: {degradation_pct:.1f}%)")
            
            if efficiency < self.efficiency_threshold:
                print(f"  ⚠️  FAIL: Efficiency < {self.efficiency_threshold:.2f}")
            else:
                print(f"  ✓ PASS: Efficiency >= {self.efficiency_threshold:.2f}")
            
            print()
            
            fold_results.append({
                'fold': fold_idx + 1,
                'is_start': is_start,
                'is_end': is_end,
                'oos_start': oos_start,
                'oos_end': oos_end,
                'is_pf': is_stats['profit_factor'],
                'oos_pf': oos_stats['profit_factor'],
                'is_trades': is_stats['trades'],
                'oos_trades': oos_stats['trades'],
                'is_net': is_stats['net_pl'],
                'oos_net': oos_stats['net_pl'],
                'efficiency': efficiency,
                'passed': efficiency >= self.efficiency_threshold,
            })
        
        # Calculate aggregate metrics
        efficiencies = [f['efficiency'] for f in fold_results]
        avg_efficiency = np.mean(efficiencies)
        std_efficiency = np.std(efficiencies)
        
        is_pfs = [f['is_pf'] for f in fold_results]
        oos_pfs = [f['oos_pf'] for f in fold_results]
        avg_is_pf = np.mean(is_pfs)
        avg_oos_pf = np.mean(oos_pfs)
        
        passed_folds = sum(f['passed'] for f in fold_results)
        overall_pass = avg_efficiency >= self.efficiency_threshold
        
        # Summary
        print("="*70)
        print("WALK-FORWARD SUMMARY")
        print("="*70)
        print(f"Average IS PF: {avg_is_pf:.3f}")
        print(f"Average OOS PF: {avg_oos_pf:.3f}")
        print(f"Average Efficiency: {avg_efficiency:.3f} ± {std_efficiency:.3f}")
        print(f"Folds passed: {passed_folds}/{len(fold_results)}")
        print()
        
        if overall_pass:
            print(f"✓ OVERALL: PASS (efficiency {avg_efficiency:.3f} >= {self.efficiency_threshold:.2f})")
        else:
            print(f"✗ OVERALL: FAIL (efficiency {avg_efficiency:.3f} < {self.efficiency_threshold:.2f})")
        
        print()
        print("Interpretation:")
        if avg_efficiency > 0.7:
            print("  Excellent: Strategy is robust and not overfit")
        elif avg_efficiency > 0.5:
            print("  Good: Strategy shows acceptable OOS performance")
        elif avg_efficiency > 0.3:
            print("  Marginal: Strategy degrades significantly OOS")
        else:
            print("  Poor: Strategy is likely overfit to training data")
        
        print()
        
        return {
            'folds': fold_results,
            'avg_efficiency': avg_efficiency,
            'std_efficiency': std_efficiency,
            'passed': overall_pass,
            'is_avg_pf': avg_is_pf,
            'oos_avg_pf': avg_oos_pf,
            'threshold': self.efficiency_threshold,
            'n_folds': len(fold_results),
            'folds_passed': passed_folds,
        }
    
    def _slice_bars(self, bars, start_idx: int, end_idx: int):
        """Create a BarSet slice for the given index range."""
        from src.backtesting.data import BarSet
        
        # Slice M15 (primary timeframe)
        m15_slice = bars.m15[start_idx:end_idx]
        
        # Find corresponding M5/M1/D1 slices by matching timestamps
        m15_start_time = m15_slice['time'][0]
        m15_end_time = m15_slice['time'][-1]
        
        # M5 slice
        m5_slice = None
        if bars.m5 is not None:
            m5_mask = (bars.m5['time'] >= m15_start_time) & (bars.m5['time'] <= m15_end_time)
            m5_slice = bars.m5[m5_mask]
        
        # M1 slice
        m1_slice = None
        if bars.m1 is not None:
            m1_mask = (bars.m1['time'] >= m15_start_time) & (bars.m1['time'] <= m15_end_time)
            m1_slice = bars.m1[m1_mask]
        
        # D1 slice (needs special handling - much fewer bars)
        d1_slice = None
        if bars.d1 is not None:
            # Find D1 bars that overlap with this M15 window
            d1_mask = (bars.d1['time'] <= m15_end_time)
            d1_slice = bars.d1[d1_mask]
            # Keep last 50 D1 bars for indicators
            if len(d1_slice) > 50:
                d1_slice = d1_slice[-50:]
        
        # H4 slice (if exists)
        h4_slice = None
        if hasattr(bars, 'h4') and bars.h4 is not None:
            h4_mask = (bars.h4['time'] >= m15_start_time) & (bars.h4['time'] <= m15_end_time)
            h4_slice = bars.h4[h4_mask]
        
        return BarSet(
            symbol=bars.symbol,
            m15=m15_slice,
            m5=m5_slice,
            m1=m1_slice,
            d1=d1_slice,
            h4=h4_slice if h4_slice is not None else None,
            spec=bars.spec,
            manifests=bars.manifests,
        )


def main():
    """Run walk-forward validation on current portfolio."""
    
    # Load data
    print("Loading data...")
    bars = load_bars(symbol="XAUUSDm", timeframes=("M15", "M5", "M1", "D1"))
    from src.backtesting.costs import SCENARIOS
    cost_model = SCENARIOS["realistic_ecn"]
    
    # Configuration matching live system
    config = EngineConfig(
        symbol="XAUUSDm",
        starting_balance=100.0,
        fixed_lots=0.01,
        sizing_mode="fixed",
        max_concurrent=1,
        max_same_direction=1,
        enable_trailing=True,
        enable_pyramiding=False,
        enable_d1_bias_gate=False,
        direction_gate="d1_ema20",
        daily_loss_limit_mode="balance_pct",
        daily_loss_limit_pct=0.06,
        dedup_per_candle=True,
    )
    
    # Strategies
    strategies = [cls() for cls in PORTFOLIO_V4]
    
    # Run walk-forward validation
    validator = WalkForwardValidator(
        n_folds=6,
        is_ratio=0.70,
        efficiency_threshold=0.50,
    )
    
    results = validator.validate(strategies, bars, config, cost_model)
    
    # Save results
    output_path = Path("research/validation/walk_forward_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to: {output_path}")
    print()
    
    # Return exit code
    return 0 if results['passed'] else 1


if __name__ == "__main__":
    sys.exit(main())
