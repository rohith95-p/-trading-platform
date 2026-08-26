---
name: xauusd-trading-prep
description: Pre-trade market analysis workflow and position sizing for XAUUSD (Gold) trading on MetaTrader 5 via Exness. Use when the user asks to prepare for Gold trading, analyze Gold market conditions, or create a trading plan.
---

# XAUUSD Trading Preparation Skill

## When to Activate
- User asks to prepare for XAUUSD / Gold trading
- User asks to analyze Gold market conditions
- User asks to create a trading plan for Gold
- User asks to check what's moving Gold

## The "Tomorrow's Plan" Daily Workflow
When the user asks for "tomorrow's plan" or a daily plan, you must execute the "Global Macro Tracker" workflow:
1. Fetch 5-day closing prices for the following 6 assets using Yahoo Finance (yfinance):
   - Gold (GC=F), Silver (SI=F), DXY (DX-Y.NYB), 10Y Yield (^TNX), Crude Oil (CL=F), VIX (^VIX).
2. Generate or update `c:\projects\ultra_core\docs\plans\DAILY_MARKET_ANALYSIS.md` containing the macro correlations and findings.
3. Generate or update `c:\projects\ultra_core\docs\plans\DAILY_BATTLE_PLAN.md` with the mathematical strategy setups for both buy and sell directions based on Smart Money Concepts (SMC) and macro gating.

## Pre-Trade Market Research Checklist

Always research ALL of the following before creating a trading plan:

### 1. Gold Price & Trend
- Current price, weekly/monthly performance
- Trend direction on D1, H4, H1
- Position relative to key moving averages (50, 200 EMA/SMA)

### 2. DXY (US Dollar Index)
- Current level and trend (INVERSE correlation with Gold)
- A falling DXY = bullish Gold
- A rising DXY = bearish Gold

### 3. US Treasury Yields (10-Year)
- Current yield and trend (generally INVERSE correlation)
- Treasury buybacks or auctions that could compress yields

### 4. Economic Calendar
- Check for: CPI, NFP, FOMC, PCE, PPI, GDP releases
- Check for: Jackson Hole, Fed speeches, G7/G20 summits
- Monday = usually low-news day (good for technical trading)

### 5. Geopolitical Factors
- Middle East tensions (Iran, oil, Strait of Hormuz)
- Trade wars, sanctions, military conflicts
- Safe-haven demand spikes

### 6. Central Bank Gold Demand
- China (PBoC) buying streak
- Global central bank quarterly purchases
- Reserve diversification trends

### 7. Silver (XAGUSD) Confirmation
- Silver price and trend (confirms precious metals strength)
- Gold/Silver ratio (above 80 = silver undervalued, below 50 = gold undervalued)

### 8. Key Support/Resistance Levels
- Search for technical analysis with H4/Daily levels
- Identify: R1/R2/R3 resistance, S1/S2/S3 support
- Note: 200-day SMA, round numbers ($X,X00), weekly highs/lows

### 9. Session Timing (IST)
- Asian: 05:30 - 13:30 IST
- London: 13:30 - 21:30 IST (PRIME for Gold)
- New York: 18:30 - 02:30 IST
- London-NY Overlap: 18:30 - 21:30 IST (HIGHEST volatility)
- Stop trading by: 23:00 IST (for small accounts)

## Position Sizing & Institutional Risk Management

### Exness Symbol Convention
- Gold symbol: **XAUUSDm** (Standard accounts: 0.01 lot = 1 ounce)
- For strict $5 risk limits, users MUST use a **Cent Account** (`XAUUSDc`).

### The Volatility (ATR) Reality vs Account Size
Institutions use Average True Range (ATR) to place stop losses outside of market noise. 
- On a 15m timeframe, Gold's ATR often requires a $20-$30 stop loss distance. 
- With a minimum 0.01 lot size on a Standard account, this equals a **$20-$30 monetary risk per trade**.
- Trying to force a fixed $5 stop loss on Gold (50 pips) results in an extremely poor win rate (~37%) due to being stopped out by random volatility. 

| Account Size | Broker Type | Max Lot | Est. Risk/Trade (ATR) | Verdict |
|---|---|---|---|---|
| $100 | Standard (m) | 0.01 | ~$25 (25%) | **High Risk** |
| $100 | Cent (c) | 0.10 | ~$5 (5%) | **Optimal** |
| $500 | Standard (m) | 0.01 | ~$25 (5%) | **Optimal** |

**Rule of Thumb:** Never use fixed dollar amount stops on volatile assets. Size the position based on the required ATR stop.

## Strategy Selection by Market Condition

### Trending Market (use these)
1. Multi-TF EMA Ribbon (9/21/55/200) — Strategy #16
2. ATR Chandelier Trailing Stop — Strategy #11
3. Supertrend + EMA Filter — Strategy #18

### Range-Bound Market (use these)
1. Bollinger Band Squeeze Breakout — Strategy #7
2. Pivot Point Reversal — Strategy #10
3. Stochastic RSI Divergence — Strategy #12

### Session-Based (always applicable)
1. Asian Session Range Breakout — Strategy #13
2. London Session Breakout — Strategy #2
3. Opening Range Breakout (ORB 30) — Strategy #22

### High-Confluence (best for small accounts)
1. Fibonacci Golden Pocket Pullback — Strategy #6
2. Pin Bar / Engulfing at Key Levels — Strategy #17
3. Supply & Demand Zone Trading — Strategy #5

## Emergency Rules (Non-Negotiable)
1. **Always set a stop loss** — Gold moves $30-50 in minutes
2. **2 consecutive losses → 30 min break**
3. **Account drops 15% → STOP trading for the day**
4. **No trading during high-impact news release moment** (wait 2-5 min after)
5. **Close all positions before sleeping** on small accounts

## Learned Rules
1. **Timeframe Compression Rule for Small Accounts:** When trading Gold with <$200, NEVER use timeframes higher than M5 (5-minute) for ATR-based momentum strategies. The H1/M15 ATR distances create unacceptable dollar risks at minimum lot sizes. Always scale down to M5 to compress the ATR and keep dollar risk within a $12 cap limit.
