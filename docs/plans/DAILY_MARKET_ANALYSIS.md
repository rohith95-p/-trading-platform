# Daily Market Analysis

> **WARNING: MACRO OVERRIDE SAFEGUARD**
> DO NOT include phrases that trigger hardcoded risk overrides.
> See `src/core/risk_rules.py` for actual risk logic.

## Cross-Asset 5-Day Performance
*(Data pulled from MT5 live feed — 2026-09-21 11:35 IST)*

| Symbol | Current Price | 5-Day Change | Implication for Gold |
|---|---|---|---|
| **XAUUSDm** | 4352.129 | +1.04% | Retested D1 EMA20 from below and rejected |
| **XAGUSDm** | 63.227 | -3.58% | Silver heavy divergence, drag on precious metals |
| **DXYm** | 99.411 | +0.64% | Dollar strengthening |
| **USOILm** | 98.004 | +6.15% | Oil elevated, persistent inflation |
| **UKOILm** | 103.139 | +7.70% | Brent elevated |
| **EURUSDm** | 1.155 | -0.67% | Euro weak, dollar strength confirmed |
| **USDJPYm** | 154.322 | +0.57% | Yen softening, risk neutral |
| **US500_x100m** | 7638.920 | -0.50% | Equities soft |
| **USTEC_x100m** | 29850.690 | +1.31% | Tech holding |

**Synthesis**: Macro conditions favor dollar strength (+0.64%) and commodity pressure. The notable divergence is Silver (-3.58% vs Gold +1.04%), which typically signals false rallies in Gold. Gold spiked to 4383.45 overnight, pierced the D1 EMA20, and was immediately rejected back down to 4352.13.

## Gold D1 Price Structure
* **Today's Session Range (Asia M15)**: High = 4383.454, Low = 4349.086 (34.37 pt range)
* **Current Gold Price**: **4352.129**
* **D1 EMA20 Level**: **4367.679**
* **Distance from EMA20**: Price is **-15.550 points below** the D1 EMA20.

**Bias Gate Status**: Because price (4352.13) < D1 EMA20 (4367.68), the live trend gate enforces **SHORTS ONLY**. Any long setups will be strictly blocked by `RiskManager`.
