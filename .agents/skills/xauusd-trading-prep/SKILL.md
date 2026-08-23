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

## Position Sizing for Small Accounts ($100-$500)

### Exness Symbol Convention
- Gold symbol: **XAUUSDm** (note lowercase "m" suffix for Standard accounts)
- 24/7 Gold: **XAUUSD247m**

### Lot Size Rules
| Account Size | Max Lot | Max Risk/Trade | Max Daily Loss |
|---|---|---|---|
| $100 | 0.01 | $5 (5%) | $15 (15%) |
| $200 | 0.02 | $10 (5%) | $30 (15%) |
| $500 | 0.05 | $25 (5%) | $75 (15%) |

### With 1:200 Leverage (Exness)
- 0.01 lots XAUUSD = ~$23 margin at $4,600/oz
- Per $1 gold movement at 0.01 lots = $0.01 profit/loss
- To risk $5: set stop loss ~500 pips ($5) away with 0.01 lots

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
