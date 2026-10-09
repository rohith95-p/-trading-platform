# Ultra Core — Algorithmic Trading System

> **Status: LIVE TRADING** | Last validated: 2026-09-28 | Python 3.11 | MT5 Live | Week 1: Oct 6–10 2026

Ultra Core is a fully automated, backtested, and live-validated algorithmic trading system for **XAUUSDm (Gold)** on MetaTrader 5. It runs a 9-strategy portfolio with a **D1 bias gate, ATR-based stops, and a full risk management stack** on a live demo account.

---

## Validated Performance (Portfolio V5)

| Metric | Value |
|:---|:---|
| **2-Year Net Profit** | +$8,951 (starting $100) |
| **Profit Factor** | 1.82 |
| **Max Drawdown** | 2.77% |
| **Win Rate** | 18.47% |
| **P(ruin) Monte Carlo** | 0.10% |
| **Walk-Forward OOS** | Passed (6-fold) |

---

## Live Trading Results

| Week | Dates | Trades | Net P&L | Balance |
|:---|:---|:---|:---|:---|
| Week 1 | Oct 6–10, 2026 | 6 | +$2.51 | $175.21 |

**Starting balance:** $172.70 (demo) | **Current balance:** $175.21  
**Active config:** `sl_atr_mult=0.5`, `tp_atr_mult=1.5` | D1 BEARISH → SELL only this week

> Live trading began Oct 6, 2026. Tuesday: +$13.14 (4 trades). Wednesday: -$10.63 (dedup bug cost 3 hours of NY session). Thursday: $0.00 (flat market). System running clean after dedup fix deployed.

---

## Architecture

```
ultra_core/
├── src/
│   ├── core/           # Live trading engine (MT5 loop, risk, execution, alerts)
│   ├── strategies/     # All 9 validated strategies + Portfolio V5
│   ├── backtesting/    # Tick-level M1 backtesting engine with ECN costs
│   └── research/       # Feature engineering, candidate library
├── scripts/
│   ├── hourly_monitor.py           # Telegram hourly updates during trading
│   ├── pre_market_check.py         # Daily pre-market checklist
│   ├── daily_stats.py              # Quick account + trade stats
│   ├── end_of_day.py               # End-of-day report generator
│   ├── dedup_monitor.py            # Early warning for dedup bug
│   ├── restart_bot.py              # Quick bot recovery
│   ├── campaign_hypertight.py      # Full 36-strategy sweep
│   ├── campaign_portfolio_sweep.py # Portfolio concurrency sweep
│   └── validation/                 # Full audit suite (PF, DD, ruin, walk-forward)
├── daily_trade_progress/           # Per-day trade reports (live)
├── tests/              # 55 unit tests (config, execution, no-lookahead, strategy)
├── docs/
│   ├── research/       # Research ledger, strategy registry, readiness rating
│   └── plans/          # Daily battle plan, growth path
└── research/           # Historical candidate library, validation ledger
```

---

## The 6 Live Strategies (Portfolio V5)

| Strategy | Edge |
|:---|:---|
| `TREND_PULLBACK` | EMA trend + pullback entry |
| `BB_MR` | Bollinger Band mean reversion |
| `NVMR_NY` | NY VWAP mean reversion |
| `BaseStrategy` | Core execution layer |
| `PDHLR` | Previous day high/low reversal |
| `NY_LIQUIDITY_EXPANSION` | NY volatility expansion |

**Live Risk Config:** `sl_atr_mult=0.5` · `tp_atr_mult=1.5` · `0.02 lots` · `max_concurrent=3`  
**D1 bias gate:** BEARISH → SELL only · BULLISH → BUY only

---

## Risk Controls

- **Daily loss limit:** 6% of balance → stops trading for the day
- **D1 EMA20 bias gate:** blocks counter-trend entries
- **Market hours:** 11:30–21:30 IST only (no overnight, no weekend)
- **News filter:** blocks entries around tier-1 macro events
- **Margin cap:** enforced before every order
- **Telegram alerts:** every trade, every block, every error
- **Kill switch:** create file `STOP` in project root → flatten all positions

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env.local    # fill in MT5 credentials + Telegram token
python -m src.core.main_loop  # start the live bot
```

**Environment variables required:**
- `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

---

## Running Backtests

```bash
# Full 9-strategy portfolio sweep (2yr, concurrency 2-6)
python scripts/campaign_portfolio_sweep.py

# Daily P&L log from your live MT5 balance
python scripts/daily_pnl_log.py

# Walk-forward OOS validation
python scripts/validation/walk_forward_validate.py

# Monte Carlo ruin probability
python scripts/validation/monte_carlo_ruin.py
```

---

## Running Tests

```bash
pytest tests/ -v   # 55 tests: config, execution, no-lookahead, strategy logic
```

---

## Key Design Decisions

1. **0.1 ATR Stop Loss / 1.0 ATR Take Profit**: The 1:10 RRR means you only need to win 9.1% of trades to break even. All 9 strategies naturally exceed this at 12–30% win rates.
2. **M1-level simulation**: The backtester ticks through every 1-minute bar, applying spread+slippage on every tick. No bar-close cheating.
3. **Ambiguous-bar penalty**: When a bar touches both SL and TP in the same minute, the engine assumes SL hit first (worst case). Proven by audit.
4. **No Cent accounts**: The hyper-tight SL model makes standard 0.01 lots viable on $100. Cent accounts are not needed.
5. **Walk-forward validated**: 6-fold rolling OOS validation. The edge is not curve-fitted.

---

## Known Limitations

- **Slippage on news events**: The backtester uses fixed 20-point slippage. During high-impact news (CPI, NFP), real slippage can be 5-10× higher. The daily news filter mitigates but does not eliminate this.
- **PDHLRStrategy** has the highest drawdown (6.35%) and lowest PF (2.59). It is still above the pass bar but should be monitored first in live trading.
- **September 2026 was a brutal month**: 14 losing days, balance hit $103 before recovering to $434. The 1:10 RRR system has long losing streaks by design.
- **Broker minimum stop level**: Verified as 0 on XAUUSDm. If broker changes this, the hyper-tight SL may be rejected at order submission.

---

## Research History

6 months of systematic research documented in:
- `docs/research/RESEARCH_LEDGER.md` — every hypothesis (HYP-001 to HYP-063+)
- `docs/research/STRATEGY_REGISTRY.md` — all strategies ever tested, rated, and classified
- `docs/research/REAL_MONEY_READINESS_RATING_2026-09-06.md` — go/no-go scorecard (92/100 A-grade)
- `research/validation_ledger.json` — machine-readable validation log

---

*Built by Rohith | Powered by MetaTrader 5 | Validated 2026-09-28*
