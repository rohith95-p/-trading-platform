"""
XAUUSD Monday Trading Engine — Configuration & Strategy Parameters
================================================================
Capital: $100 | Target: $130 | Max Drawdown: $15
Broker: Exness (Demo) | Symbol: XAUUSDm | Leverage: 1:200

This module defines all the trading parameters, strategy configurations,
and risk management rules for Monday August 25, 2026 XAUUSD trading.
"""

# ============================================================
# ACCOUNT CONFIGURATION
# ============================================================

ACCOUNT_CONFIG = {
    "initial_capital": 100.0,
    "target_balance": 130.0,
    "target_profit": 30.0,
    "max_drawdown_dollars": 15.0,
    "max_drawdown_percent": 15.0,
    "stop_trading_balance": 85.0,
    "leverage": 200,
    "currency": "USD",
}

SYMBOL_CONFIG = {
    "primary_symbol": "XAUUSDm",       # Exness Standard Gold
    "alt_symbol": "XAUUSD247m",         # 24/7 Gold (if available)
    "pip_value": 0.01,                  # Per pip per 0.01 lot
    "min_lot": 0.01,
    "max_lot": 0.05,                    # Safety cap for $100 account
    "default_lot": 0.01,
    "spread_typical_pips": 20,          # ~20 pips typical spread on Exness Gold
    "contract_size": 100,               # 1 lot = 100 oz
}


# ============================================================
# RISK MANAGEMENT RULES
# ============================================================

RISK_RULES = {
    "max_risk_per_trade_dollars": 5.0,
    "max_risk_per_trade_percent": 5.0,
    "max_concurrent_trades": 2,
    "max_trades_per_day": 8,
    "max_consecutive_losses_before_break": 2,
    "break_duration_minutes": 30,
    "close_all_by_ist": "23:00",        # Close everything by 11 PM IST
    "no_trade_first_minutes": 30,       # Don't trade first 30 min of Asian open
    "reduce_size_at_balance": 90.0,     # Reduce lot size if balance drops to $90
    "stop_trading_at_balance": 85.0,    # Hard stop if balance drops to $85
    
    # Anomaly / Edge Case Rules (Confirmed via /grill-me)
    "require_hard_sl_tp": True,         # ALWAYS attach SL/TP to broker order in case of disconnect
    "ignore_spread_spikes": True,       # Take breakout trades even if spread is high to avoid missing move
    "require_monday_test_trade": True,  # MUST execute a 0.01 lot manual test trade at 1:30 PM IST before running bot
}


# ============================================================
# MARKET INTELLIGENCE — August 25, 2026
# ============================================================

MARKET_INTEL = {
    "gold_last_price": 4590.0,          # Approximate Friday close
    "gold_weekly_change_pct": 5.0,      # +5% last week
    "gold_monthly_change_pct": 14.0,    # +14% in August
    "gold_trend": "STRONGLY_BULLISH",
    
    "dxy_level": 98.80,
    "dxy_trend": "BEARISH",             # Bearish DXY = Bullish Gold
    "dxy_monthly_change_pct": -2.28,
    
    "treasury_10y_yield": 4.74,
    "treasury_trend": "RISING",         # But buybacks compressing
    
    "silver_price": 69.50,
    "gold_silver_ratio": 66.0,
    
    "geopolitical_risk": "HIGH",        # Iran sanctions, Strait of Hormuz
    "central_bank_buying": "RECORD",    # 288.9 tonnes Q2, China 21mo streak
    
    "jackson_hole_date": "2026-08-27",  # Wed-Fri, speech Thu Aug 28
    "major_news_monday": False,         # No major releases Monday
    
    "directional_bias": "BULLISH",
    "confidence": 0.75,                 # 75% confidence in bullish bias
}


# ============================================================
# KEY PRICE LEVELS
# ============================================================

KEY_LEVELS = {
    "resistance_3": 4721.0,     # Extended target
    "resistance_2": 4650.0,     # Weekly high / psychological
    "resistance_1": 4631.0,     # Immediate resistance (Friday high)
    "friday_close":  4590.0,    # Reference point
    "support_1":     4550.0,    # First support / FVG zone
    "support_2":     4514.0,    # 200-day SMA (CRITICAL)
    "support_3":     4465.0,    # Strong demand zone
    "support_4":     4379.0,    # 100-day SMA (worst case)
}


# ============================================================
# STRATEGY CONFIGURATIONS
# ============================================================

STRATEGIES = {
    "asian_breakout": {
        "name": "Asian Session Range Breakout",
        "strategy_number": 13,
        "priority": "HIGH",
        "session": "LONDON_OPEN",           # Execute at London open
        "timeframe_entry": "M15",
        "timeframe_bias": "H1",
        "setup": {
            "range_start_gmt": "00:00",
            "range_end_gmt": "08:00",
            "breakout_window_gmt": "08:00-10:00",
            "confirmation": "candle_body_close_outside_range",
            "filter": "skip_if_range_gt_50_dollars",
        },
        "entry_long": "Candle body close above Asian High",
        "entry_short": "Candle body close below Asian Low",
        "stop_loss": "Opposite side of Asian range",
        "take_profit_rr": 2.0,
        "lot_size": 0.01,
        "max_risk": 5.0,
    },
    
    "ema_crossover": {
        "name": "Multi-TF EMA Crossover",
        "strategy_number": 16,
        "priority": "HIGH",
        "session": "LONDON",
        "timeframe_entry": "M15",
        "timeframe_bias": "H1",
        "indicators": {
            "ema_fast": 9,
            "ema_slow": 21,
            "ema_trend": 200,
        },
        "entry_long": "Price > 200 EMA AND 9 EMA crosses above 21 EMA",
        "entry_short": "Price < 200 EMA AND 9 EMA crosses below 21 EMA",
        "stop_loss": "Below recent swing low or 2x ATR(14)",
        "take_profit_rr": 1.5,
        "lot_size": 0.01,
        "max_risk": 5.0,
    },
    
    "fibonacci_pullback": {
        "name": "Fibonacci Golden Pocket Pullback",
        "strategy_number": 6,
        "priority": "MEDIUM",
        "session": "LONDON_NY",
        "timeframe_entry": "H1",
        "timeframe_bias": "H4",
        "setup": {
            "key_levels": [0.382, 0.500, 0.618, 0.786],
            "golden_pocket": [0.618, 0.786],
            "confirmation": "bullish_engulfing_or_pin_bar",
            "confluence": "must_align_with_sr_or_ema",
        },
        "entry_long": "Price pulls back to 61.8%-78.6% zone + bullish confirmation",
        "stop_loss": "Below 78.6% level or recent swing low",
        "take_profit_1": "0% level (previous swing high)",
        "take_profit_2": "127.2% extension",
        "lot_size": 0.01,
        "max_risk": 5.0,
    },
    
    "bollinger_squeeze": {
        "name": "Bollinger Band Squeeze Breakout",
        "strategy_number": 7,
        "priority": "MEDIUM",
        "session": "LONDON_NY",
        "timeframe_entry": "M15",
        "timeframe_bias": "H1",
        "indicators": {
            "bb_period": 20,
            "bb_std": 2.0,
            "rsi_period": 14,
        },
        "entry": "After squeeze, candle closes outside band + RSI confirms direction",
        "stop_loss": "Opposite band or middle band (20 SMA)",
        "take_profit_rr": 1.5,
        "lot_size": 0.01,
        "max_risk": 5.0,
    },
    
    "pin_bar_key_level": {
        "name": "Pin Bar / Engulfing at Key Level",
        "strategy_number": 17,
        "priority": "OPPORTUNISTIC",
        "session": "ANY",
        "timeframe_entry": "H4",
        "timeframe_bias": "D1",
        "key_levels_to_watch": [4514, 4550, 4580, 4600, 4631, 4650],
        "entry": "Pin bar or engulfing at key level, aligned with trend",
        "stop_loss": "Beyond pattern wick (10-20 pips past the wick tip)",
        "take_profit_rr": 2.0,
        "lot_size": 0.01,
        "max_risk": 5.0,
    },
}


# ============================================================
# SESSION SCHEDULE (IST — Indian Standard Time)
# ============================================================

SESSION_SCHEDULE = {
    "asian_open_ist": "05:30",
    "asian_close_ist": "13:30",
    "london_open_ist": "13:30",
    "london_close_ist": "21:30",
    "ny_open_ist": "18:30",
    "ny_close_ist": "02:30",    # Next day
    "london_ny_overlap_ist": "18:30-21:30",  # PRIME TIME
    "stop_trading_ist": "23:00",
}


# ============================================================
# EMERGENCY PROTOCOLS
# ============================================================

EMERGENCY_RULES = {
    "balance_90": {
        "action": "Reduce lot size to minimum (0.01), max 1 trade at a time",
        "lot_size": 0.01,
        "max_concurrent": 1,
    },
    "balance_85": {
        "action": "STOP TRADING immediately. Capital preservation mode.",
        "lot_size": 0,
        "max_concurrent": 0,
    },
    "consecutive_losses_2": {
        "action": "30-minute break. Re-assess directional bias.",
        "break_minutes": 30,
    },
    "gap_down_30_plus": {
        "action": "DO NOT trade first 2 hours. Wait for direction.",
        "wait_hours": 2,
    },
    "hawkish_fed_surprise": {
        "action": "Close ALL long positions immediately.",
    },
}


# ============================================================
# PROFIT SCENARIOS
# ============================================================

PROFIT_SCENARIOS = {
    "best_case": {
        "winners": 3, "losers": 0,
        "avg_win": 10.0, "avg_loss": 0,
        "total_profit": 30.0,
    },
    "good_case": {
        "winners": 4, "losers": 1,
        "avg_win": 9.0, "avg_loss": 5.0,
        "total_profit": 31.0,
    },
    "realistic_case": {
        "winners": 5, "losers": 2,
        "avg_win": 8.0, "avg_loss": 5.0,
        "total_profit": 30.0,
    },
    "conservative_case": {
        "winners": 3, "losers": 1,
        "avg_win": 12.0, "avg_loss": 5.0,
        "total_profit": 31.0,
    },
}


def print_battle_plan():
    """Print the complete battle plan summary."""
    print("=" * 60)
    print("  XAUUSD MONDAY BATTLE PLAN — August 25, 2026")
    print("=" * 60)
    print(f"\n  Capital: ${ACCOUNT_CONFIG['initial_capital']}")
    print(f"  Target:  ${ACCOUNT_CONFIG['target_balance']} (+${ACCOUNT_CONFIG['target_profit']})")
    print(f"  Max Loss: ${RISK_RULES['stop_trading_at_balance']} (stop at ${RISK_RULES['stop_trading_at_balance']})")
    print(f"\n  Bias:    {MARKET_INTEL['directional_bias']}")
    print(f"  Confidence: {MARKET_INTEL['confidence']*100:.0f}%")
    print(f"  Gold:    ~${MARKET_INTEL['gold_last_price']}")
    print(f"  DXY:     {MARKET_INTEL['dxy_level']} ({MARKET_INTEL['dxy_trend']})")
    
    print(f"\n  KEY LEVELS:")
    for name, price in KEY_LEVELS.items():
        marker = " <<<" if name == "friday_close" else ""
        print(f"    {name:15s}: ${price:.0f}{marker}")
    
    print(f"\n  STRATEGIES ({len(STRATEGIES)} setups):")
    for key, strat in STRATEGIES.items():
        print(f"    [{strat['priority']:13s}] {strat['name']}")
    
    print(f"\n  SESSIONS (IST):")
    print(f"    Asian:      {SESSION_SCHEDULE['asian_open_ist']} - {SESSION_SCHEDULE['asian_close_ist']}")
    print(f"    London:     {SESSION_SCHEDULE['london_open_ist']} - {SESSION_SCHEDULE['london_close_ist']}")
    print(f"    NY:         {SESSION_SCHEDULE['ny_open_ist']} - {SESSION_SCHEDULE['ny_close_ist']}")
    print(f"    PRIME TIME: {SESSION_SCHEDULE['london_ny_overlap_ist']}")
    print(f"    STOP:       {SESSION_SCHEDULE['stop_trading_ist']}")
    
    print("\n" + "=" * 60)
    print("  STATUS: READY FOR MONDAY")
    print("=" * 60)


if __name__ == "__main__":
    print_battle_plan()
