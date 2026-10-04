# 🎯 Elite Risk Metrics - Always Calculated

**Author:** Rohith  
**Date:** 2026-10-03  
**Status:** PERMANENT - These metrics are calculated in EVERY backtest  

---

## 📋 Overview

This document explains the **4 elite non-parametric risk metrics** that are ALWAYS calculated for every strategy and portfolio backtest in this project. These metrics provide superior risk-adjusted performance measurement without assuming normal distributions.

---

## 🔥 The Four Elite Metrics

### 1. **Calmar Ratio** 

```
Calmar Ratio = Annualized Return % / Max Drawdown %
```

**What it measures:** Return per unit of worst-case risk

**Why it matters:**
- NO assumptions about return distribution
- Uses actual worst drawdown, not volatility estimates
- Directly answers: "How much do I make per % I could lose?"
- Simple, intuitive, robust

**Benchmarks:**
- `< 0.5` = Poor (high risk for return)
- `0.5 - 2.0` = Good
- `2.0 - 10.0` = Excellent
- `> 10.0` = Elite
- `> 100` = Legendary

**Example:**
- OLD config: 571% return / 18% DD = **31.62** (Excellent)
- NEW config: 1,925% return / 1.48% DD = **1,300.72** (LEGENDARY!)

**Code location:** `src/backtesting/metrics.py` line ~248

---

### 2. **Omega Ratio**

```
Omega Ratio = Σ(gains above threshold) / Σ(losses below threshold)
```

**What it measures:** Full empirical distribution of returns

**Why it matters:**
- Uses ENTIRE distribution, not just mean & std dev
- No normal distribution assumption
- Captures fat tails and skewness
- When threshold=0: Omega = Profit Factor

**Benchmarks:**
- `< 1.0` = Losing system
- `1.0 - 2.0` = Profitable
- `2.0 - 3.0` = Good
- `> 3.0` = Excellent/Elite

**Example:**
- OLD config: **1.181** (barely profitable)
- NEW config: **3.318** (elite! For every $1 lost, gain $3.32)

**Code location:** `src/backtesting/metrics.py` line ~256

---

### 3. **Sortino Ratio**

```
Sortino Ratio = Mean Trade P&L / Downside StdDev
```

**What it measures:** Return per unit of downside risk ONLY

**Why it matters:**
- Unlike Sharpe, ONLY penalizes losing volatility
- Big winners DON'T increase denominator
- Perfect for strategies with asymmetric payoffs
- Captures the "cut losers short, let winners run" philosophy

**Benchmarks:**
- `< 0.5` = Poor
- `0.5 - 1.0` = Acceptable
- `1.0 - 2.0` = Good
- `> 2.0` = Excellent/Elite

**Example:**
- OLD config: **0.152** (fails! High downside volatility)
- NEW config: **2.120** (elite! Low downside risk)

**Why NEW wins:**
- Avg Loss: $0.52 vs $2.37 (78% smaller!)
- Downside volatility is minimal
- Winners are BIG, losers are TINY

**Code location:** `src/backtesting/metrics.py` line ~263

---

### 4. **Recovery Factor**

```
Recovery Factor = Net P&L / Max Drawdown
```

**What it measures:** How fast you recover from worst drawdown

**Why it matters:**
- Answers: "If I hit max DD, how many DDs of profit do I make?"
- Higher = faster recovery
- Psychological importance (drawdowns hurt!)
- Simple ratio, no distributions

**Benchmarks:**
- `< 3.0` = Poor (slow recovery)
- `3.0 - 10.0` = Good
- `> 10.0` = Excellent
- `> 50.0` = Elite

**Example:**
- OLD config: $2,403 / $405 = **5.93** (good)
- NEW config: $8,090 / $89 = **90.56** (INSANE! Recovers 15x faster)

**Code location:** `src/backtesting/metrics.py` line ~197

---

## 📊 Comparison to Traditional Metrics

| Metric | Assumption | Handles Fat Tails? | Penalizes Upside? | Best For |
|--------|------------|-------------------|-------------------|----------|
| **Sharpe Ratio** | Normal dist | ❌ No | ❌ Yes (bad!) | Academic papers |
| **Calmar Ratio** | ✅ None | ✅ Yes | ✅ No | Real trading |
| **Omega Ratio** | ✅ None | ✅ Yes | ✅ No | Full distribution |
| **Sortino Ratio** | Semi-normal | ✅ Yes | ✅ No | Asymmetric systems |
| **Recovery Factor** | ✅ None | ✅ Yes | ✅ No | DD-sensitive traders |

---

## 🔧 Implementation

### Where Calculated

**Primary:** `src/backtesting/metrics.py` in `summarize()` function

**Lines:**
- Calmar: ~248-254
- Omega: ~256-261
- Sortino: ~263-266
- Recovery Factor: ~197

### How to Access

```python
from src.backtesting.engine import BacktestEngine
from src.backtesting.metrics import summarize

result = engine.run(strategies)
stats = summarize(result.trades, result.equity, start_balance)

# Access metrics
print(f"Calmar: {stats.calmar_ratio}")
print(f"Omega: {stats.omega_ratio}")
print(f"Sortino: {stats.sortino_ratio}")
print(f"Recovery: {stats.recovery_factor}")
```

### In JSON Reports

All metrics are automatically saved in `core_metrics` section of backtest JSON reports:

```json
{
  "core_metrics": {
    "profit_factor": 3.318,
    "expectancy": 1.0078,
    "calmar_ratio": 1300.72,
    "omega_ratio": 3.318,
    "sortino_ratio": 2.120,
    "recovery_factor": 90.56
  }
}
```

---

## ✅ Validation Gates

These metrics are included in standard validation:

```python
validation_gates = {
    "Profit Factor > 1.3": stats.profit_factor > 1.3,
    "Calmar Ratio > 0.5": stats.calmar_ratio > 0.5,
    "Omega Ratio > 1.0": stats.omega_ratio > 1.0,
    "Sortino Ratio > 1.0": stats.sortino_ratio > 1.0,
    "Recovery Factor > 3.0": stats.recovery_factor > 3.0,
}
```

---

## 📚 References

1. **Calmar Ratio**
   - Young, T. W. (1991). "Calmar Ratio: A Smoother Tool"
   - Uses max DD instead of standard deviation

2. **Omega Ratio**
   - Keating, C. & Shadwick, W. F. (2002). "A Universal Performance Measure"
   - Journal of Performance Measurement
   - Full distribution analysis without parametric assumptions

3. **Sortino Ratio**
   - Sortino, F. & Price, L. (1994). "Performance Measurement in a Downside Risk Framework"
   - Journal of Investing
   - Downside deviation only, not total volatility

4. **Recovery Factor**
   - Practical ratio used by professional traders
   - Measures psychological resilience of a system

---

## 🚨 Important Notes

### For Future Developers / AI Taking Over:

1. **NEVER REMOVE THESE METRICS**
   - They are fundamental to system validation
   - They catch issues that PF/Expectancy miss
   - They are distribution-free (robust!)

2. **ALWAYS CALCULATE IN BACKTESTS**
   - Every strategy test MUST include these
   - Portfolio tests MUST include these
   - Live monitoring SHOULD track these

3. **USE FOR DECISIONS**
   - Don't deploy if Calmar < 0.5
   - Don't deploy if Sortino < 1.0
   - Don't deploy if Recovery < 3.0
   - These gates exist for a reason!

4. **PREFER OVER SHARPE**
   - XAUUSD returns are NOT normal
   - Fat tails, skewness everywhere
   - Sharpe will lie to you
   - These metrics won't

---

## 🎯 Quick Reference Card

```
┌──────────────────────────────────────────────────────────┐
│  ELITE RISK METRICS - QUICK REFERENCE                    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Calmar Ratio  = Return / Max DD %                       │
│     Target: > 0.5  (Ours: 1,300.72 🔥)                  │
│                                                          │
│  Omega Ratio   = Gains / Losses (full distribution)      │
│     Target: > 1.0  (Ours: 3.318 ⭐)                     │
│                                                          │
│  Sortino Ratio = Mean / Downside StdDev                  │
│     Target: > 1.0  (Ours: 2.120 ⭐)                     │
│                                                          │
│  Recovery Factor = P&L / Max DD                          │
│     Target: > 3.0  (Ours: 90.56 🔥)                     │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  ALL calculated in: src/backtesting/metrics.py          │
│  ALL saved in: reports/*.json                            │
│  ALL distribution-free (no normal assumption)            │
└──────────────────────────────────────────────────────────┘
```

---

## 🎓 Conclusion

These four metrics provide a complete, robust picture of risk-adjusted performance without relying on fragile assumptions about return distributions. They are calculated automatically in every backtest and should be reviewed before deploying any strategy.

**Remember:** A high Profit Factor with a failing Calmar or Sortino means you're taking excessive risk for your returns. These metrics keep you honest.

---

**Last Updated:** 2026-10-03  
**By:** Rohith  
**Status:** PERMANENT DOCUMENTATION  
