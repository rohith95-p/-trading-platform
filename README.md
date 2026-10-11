# Ultra Core — Algorithmic Trading Platform

> **Status: DEMO / PAPER-TRADING VALIDATION** | Platform: MetaTrader 5 | Symbol: `XAUUSDm` (Gold Spot CFD) | Python 3.11  
> **Active Portfolio:** Portfolio V5 (6-Leg Core) | **Config Fingerprint:** `17a0b9e6f716de82` | **Enforce Circuit Breakers:** `True`

---

## 1. Executive Summary & Institutional Reality Check

Ultra Core is an automated quantitative trading platform engineered for gold spot CFD trading (`XAUUSDm`) on MetaTrader 5. It integrates a multi-strategy portfolio, intraday time-of-day session regimes, D1 trend filtering, automated tick-level cost simulation, pre-trade risk veto gates, and an external watchdog process.

### Institutional Readiness Verdict: `NOT READY FOR REAL-MONEY` | `PAPER-TRADING & AUDIT VALIDATED`

While historical backtests in coarse environments claimed astronomical returns (e.g., $8,000+ profit and 3.3+ profit factors under a theoretical 0.1 ATR micro-stop), comprehensive forensic audits revealed that **0.1 ATR stop loss (~$0.35 on gold) is physically unviable in live market execution** due to gold spreads ($0.20–$0.30) and slippage consuming over 60% of the stop distance immediately upon entry. Furthermore, coarse 15-minute historical backtests suffered from intra-bar execution artifacts where wicks were not checked on the entry candle.

Under realistic ECN cost models (spread + slippage + commission) and validated tick/minute execution, the live 6-leg Portfolio V5 (`sl_atr_mult=0.5, tp_atr_mult=1.5`) exhibits:
- **Profit Factor:** **1.112** (Long-run 4.2-year validation)
- **Net Profit:** +$3,963.03 (on 4.2 years of historical data)
- **Max Drawdown:** **$1,846.81 (33.88%)** with a duration of **314.9 days**
- **Max Consecutive Losses:** **38 trades**

> [!CAUTION]
> **Account Survival Warning:** A 38-trade consecutive loss streak will wipe out an unconstrained small account (<$200) trading 0.02 lots. The built-in **Sizing Ladder** strictly enforces **0.01 lots and maximum 1 concurrent position** for account balances under $200. Real-money capital must NOT be deployed until paper trading demonstrates live execution alignment and alpha durability.

---

## 2. Validated Performance Baseline

The baseline configuration is hashed and recorded in `research/validation_ledger.json` under fingerprint `17a0b9e6f716de82`. The live engine enforces that this configuration fingerprint matches recorded backtest evidence before initiating execution.

### Multi-Year Ledger Metrics (July 2022 – October 2026)

| Metric | Validated Baseline | Institutional Standard | Status |
|:---|:---|:---|:---|
| **Evaluation Window** | 2022-07-01 → 2026-10-02 (4.2 years) | ≥ 3 years across cycles | PASS |
| **Total Trades** | 9,121 | ≥ 1,000 | PASS |
| **Win Rate** | 28.5% | Dependent on Payoff | Contextual |
| **Profit Factor** | **1.112** | ≥ 1.30 | MARGINAL |
| **Max Drawdown** | 33.88% ($1,846.81) | ≤ 20.0% | ELEVATED |
| **Max Consec. Losses**| 38 trades | ≤ 15 trades | CRITICAL RISK |
| **Monte Carlo P(ruin)**| **48.6%** ($100 bal / $50 floor) | < 1.0% | CRITICAL RISK |
| **Recovery Factor** | 2.15 | ≥ 2.0 | PASS |
| **Sortino Ratio** | 0.104 | ≥ 1.5 | LOW |
| **Omega Ratio** | 1.112 | ≥ 1.30 | MARGINAL |

### Leg-by-Leg Attribution

Forensic analysis of the 6 legs reveals that portfolio alpha is concentrated in 4 core strategies, while 2 legs dilute performance:

| Strategy | Magic | Session (IST) | Trades | Win Rate | Net P&L | Profit Factor | Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `BB_MEAN_REVERSION_V5` | 5002 | 17:30–21:30 | 1,442 | 31.4% | **+$1,921.25** | **1.317** | **Core Alpha** |
| `TREND_PULLBACK_V5` | 5001 | 11:30–21:30 | 4,584 | 27.7% | **+$1,427.19** | **1.089** | Positive |
| `FVG_NY_TIGHT_V5` | 5005 | 17:30–21:30 | 2,196 | 28.9% | **+$1,139.63** | **1.125** | Positive |
| `NVMR_TARGET_10_V5` | 5003 | 00:00–24:00 | 69 | 30.4% | **+$131.39** | **1.456** | High Payoff |
| `NY_LIQUIDITY_EXPANSION_V5` | 5009 | 17:30–21:30 | 209 | 31.1% | **-$39.08** | **0.953** | Negative |
| `PDHLR_STRATEGY_V5` | 5008 | 00:00–24:00 | 621 | 25.4% | **-$617.35** | **0.795** | Severe Drag |

---

## 3. Architecture & Core Subsystems

```
ultra_core/
├── src/
│   ├── core/                   # Production engine orchestration
│   │   ├── main_loop.py        # Core execution loop & Highlander signal arbiter
│   │   ├── risk_manager.py     # ATR stop calculation, session multipliers, daily limits
│   │   ├── execution_handler.py# MT5 order routing & 6-layer PreTradeVeto gate
│   │   ├── sizing_ladder.py    # Balance-based position sizing & exposure caps
│   │   ├── risk_rules.py       # Circuit breakers & streak monitors (ENFORCE=True)
│   │   ├── market_hours.py     # Session filters & weekend flattening
│   │   ├── news_filter.py      # Tier-1 macroeconomic blackout filter (±15m)
│   │   ├── resilience.py       # Lockfile, heartbeat, kill-switch, state persistence
│   │   ├── validation_ledger.py# SystemConfig SHA-256 fingerprint validation
│   │   └── alerts.py           # Telegram bot & webhook dispatch
│   ├── strategies/             # Strategy implementations
│   │   ├── portfolio_v5_6_leg.py # Active 6-leg portfolio definition
│   │   ├── grid_strategies.py  # TrendPullback & BBMeanReversion
│   │   ├── bible_strategies.py # NVMR & PDHLR (repaired date math)
│   │   └── ny_liquidity_expansion.py
│   └── backtesting/            # Realistic simulation engine
│       ├── engine.py           # Multi-timeframe backtester with ECN costs
│       ├── costs.py            # Spread, commission, and slippage models
│       └── data.py             # MT5-native bar caching & SHA-256 provenance
├── scripts/
│   ├── watchdog.py             # Process keep-alive & hang detector (psutil)
│   ├── check_account.py        # Account & open position diagnostic
│   ├── validation/             # Quantitative validation suite
│   │   ├── monte_carlo_ruin.py # Resampled bootstrap ruin analysis
│   │   ├── walk_forward_validate.py # Rolling IS/OOS efficiency testing
│   │   ├── validate_current_portfolio.py # 3-gate compliance runner
│   │   └── full_metrics_report.py
│   └── archive/                # Preserved historical research & one-off scripts
├── tests/                      # Unit & regression test suite
└── research/                   # Historical data manifests & validation ledger
```

---

## 4. Key Engineering Fixes & Structural Alignment

1. **Highlander Conviction Arbiter Alignment**:
   `src/core/main_loop.py` and `src/backtesting/engine.py` were using legacy portfolio keys in `rank_order`. Both now map all active portfolio strategies (`NVMR_TARGET_10_V5`, `BB_MEAN_REVERSION_V5`, `FVG_NY_TIGHT_V5`, `TREND_PULLBACK_V5`, `PDHLR_STRATEGY_V5`, `NY_LIQUIDITY_EXPANSION_V5`, and aliases), correctly executing only the highest risk-adjusted conviction signal per candle.

2. **Candle Deduplication Clock Independence**:
   Replaced local system epoch eviction with broker-candle timestamp math (`signal_candle - 7200`), completely eliminating clock drift and premature signal re-firing.

3. **PDHLR Previous-Day Boundary Repair**:
   Corrected integer floor division in `bible_strategies.py` to calculate IST day boundaries (`((cur_ts + 19800) // 86400) * 86400 - 19800`), eliminating a 24-to-48-hour lookback distortion during evening trading hours.

4. **News Filter Macroeconomic Calendar Correction**:
   Corrected hardcoded tier-1 event dates from weekend dates to actual weekday release schedules (NFP, CPI, PCE, GDP, FOMC). Enhanced `is_near_news_event` with strict UTC datetime comparison and added operator override schema at `docs/plans/news_calendar.json`.

5. **Cross-Platform Watchdog & Process Keep-Alive**:
   Replaced deprecated Windows `wmic` subprocess calls with `psutil` process iteration, ensuring robust monitoring on Windows 11, Windows Server, and Linux environments.

6. **Position Sizing & Capital Protection**:
   `ExecutionHandler` strictly applies `SizingLadder.get_sizing(balance)`. For small balances ($100–$200), lots are hard-capped at 0.01 with at most 1 concurrent position.

7. **Secrets Isolation & Security Hardening**:
   Sanitized `check_account.py` to read credentials from environment variables (`MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`). Ensured `.env.local` remains strictly ignored by Git while providing `.env.example`.

8. **Headless & Cross-Platform CI/CD Testing**:
   Added a lightweight `MetaTrader5` fallback stub in `tests/conftest.py` so test suites pass reliably across Linux CI runners, developer laptops, and headless virtual environments.

---

## 5. Risk Controls & Safety Mechanisms

- **Circuit Breakers (`src/core/risk_rules.py`)**: `ENFORCE = True`. Daily loss limit of 6% immediately halts trading for the day. Consecutive loss limits trigger automatic cool-down periods.
- **Sizing Ladder (`src/core/sizing_ladder.py`)**: Dynamically scales lot sizes from balance. Trading completely halts if balance falls below the $50 hard floor.
- **D1 EMA20 Bias Gate**: Daily candle trend filter prevents opening trades against the macro trend.
- **Session Trading Windows**: Restricts entries to validated liquid hours (11:30–21:30 IST) and enforces Friday evening weekend flattening.
- **News Blackout Window**: Blocks entries ±15 minutes around tier-1 US releases (NFP, CPI, PCE, GDP, FOMC).
- **Hard Kill Switch**: Creating a file named `STOP` in the root repository directory immediately flattens all open positions and safely shuts down the orchestrator.

---

## 6. Setup & Operational Runbook

### Prerequisites
- Python 3.11+
- MetaTrader 5 Terminal installed with an active demo account (`XAUUSDm` symbol available).

### Installation

```bash
# 1. Clone repository
git clone https://github.com/rohith95-p/-trading-platform.git
cd -trading-platform

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env.local
# Edit .env.local with your MT5 account number, password, server, and Telegram token
```

### Running Validation Tests

```bash
# Run unit and regression suite (56 tests)
pytest tests/ -v

# Run walk-forward out-of-sample validation
python -m scripts.validation.walk_forward_validate

# Run Monte Carlo ruin probability simulation
python -m scripts.validation.monte_carlo_ruin

# Run full portfolio metrics report
python -m scripts.validation.full_metrics_report
```

### Launching the Trading Engine

```bash
# Terminal 1: Launch main orchestrator
python -m src.core.main_loop

# Terminal 2: Launch resilience watchdog
python -m scripts.watchdog
```

---

## 7. Operational Guidelines & Verification

1. **Check Live Fingerprint**:
   On startup, `main_loop.py` prints `CONFIG VALIDATED: fingerprint 17a0b9e6f716de82`. If any configuration parameter or strategy multiplier is modified without updating `validation_ledger.json`, the bot safely refuses to trade.
2. **Emergency Flatten**:
   To immediately close all open trades and halt the system:
   ```bash
   echo. > STOP
   ```
3. **Daily Monitoring**:
   Monitor the daily P&L report sent to Telegram and verify that daily losses never exceed 6% of equity.
