import time
import MetaTrader5 as _mt5
from typing import Any
mt5: Any = _mt5
import numpy as np
import logging
import os
from datetime import datetime, timezone

STRICT_SHORT_STOPS = False

def parse_macro_gating_rules():
    global STRICT_SHORT_STOPS
    plan_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "plans", "DAILY_MARKET_ANALYSIS.md")
    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            content = f.read().lower()
            if "bullish macro momentum" in content and "shorts must have strict, tight stops" in content:
                STRICT_SHORT_STOPS = True
                logging.info("Macro Gating Rule Applied: Strict tight stops for SHORT positions enabled.")
    except Exception as e:
        logging.warning(f"Could not parse daily market analysis: {e}")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SYMBOL = "XAUUSDm"
LOT = 0.01
MAGIC_BASE = 2000
MAX_CONCURRENT_TRADES = 2

# Global state to prevent re-entering the same trade over and over on the same day
traded_today = {
    "ATR_KELTNER": None,
    "MACD_EMA200": None,
    "ASIAN_BREAKOUT": None,
    "PDHL_BREAKOUT": None
}

def can_open_new_trade():
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        return False
    return len(positions) < MAX_CONCURRENT_TRADES

def execute_trade(signal, price, sl, tp, strategy_name, magic_id):
    if not can_open_new_trade():
        logging.warning(f"[{strategy_name}] Signal generated but MAX_CONCURRENT_TRADES ({MAX_CONCURRENT_TRADES}) reached. Ignoring.")
        return False
        
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT,
        "type": signal,
        "price": price,
        "sl": sl,
        "tp": tp,
        "magic": magic_id,
        "comment": strategy_name,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    res = mt5.order_send(request)
    if res.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"[{strategy_name}] Trade opened successfully: {res.order} at {price}")
        return True
    else:
        logging.error(f"[{strategy_name}] Order failed: {res.comment} (Code: {res.retcode})")
        return False

# Indicators
def ema(prices, period):
    if len(prices) < period:
        return np.full_like(prices, np.nan)
    ema_vals = np.full_like(prices, np.nan)
    ema_vals[period-1] = np.mean(prices[:period])
    mult = 2.0 / (period + 1)
    for i in range(period, len(prices)):
        ema_vals[i] = prices[i] * mult + ema_vals[i-1] * (1 - mult)
    return ema_vals

def calc_atr(rates, period=14):
    highs = rates['high']
    lows = rates['low']
    closes = rates['close']
    high_low = highs - lows
    if len(closes) > 1:
        high_close = np.abs(highs[1:] - closes[:-1])
        low_close = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(high_low[1:], np.maximum(high_close, low_close))
        tr = np.insert(tr, 0, high_low[0]) # Align lengths
    else:
        tr = high_low
        
    atr = np.full_like(tr, np.nan)
    if len(tr) >= period:
        atr[period-1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr

def macd(prices, fast=12, slow=26, signal=9):
    e_fast = ema(prices, fast)
    e_slow = ema(prices, slow)
    macd_line = e_fast - e_slow
    valid_macd = macd_line[~np.isnan(macd_line)]
    sig_line = ema(valid_macd, signal)
    full_sig = np.full_like(macd_line, np.nan)
    start_idx = slow - 1 + signal - 1
    if start_idx < len(full_sig) and len(sig_line) > 0:
        valid_sig = sig_line[~np.isnan(sig_line)]
        end_idx = min(start_idx + len(valid_sig), len(full_sig))
        full_sig[start_idx:end_idx] = valid_sig[:end_idx-start_idx]
    return macd_line, full_sig

def trailing_stop_logic():
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return
    for pos in positions:
        trail_dist = 2.0
        activation_dist = 3.0
        new_sl = None
        if pos.type == mt5.ORDER_TYPE_BUY:
            if pos.price_current - pos.price_open > activation_dist:
                potential_sl = pos.price_current - trail_dist
                if pos.sl == 0.0 or potential_sl > pos.sl:
                    new_sl = potential_sl
        elif pos.type == mt5.ORDER_TYPE_SELL:
            if pos.price_open - pos.price_current > activation_dist:
                potential_sl = pos.price_current + trail_dist
                if pos.sl == 0.0 or potential_sl < pos.sl:
                    new_sl = potential_sl
                    
        if new_sl is not None:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": pos.ticket,
                "symbol": pos.symbol,
                "sl": new_sl,
                "tp": pos.tp
            }
            res = mt5.order_send(request)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                logging.info(f"Updated Trailing Stop for {pos.ticket} to {new_sl:.3f}")

# Strategy 1: ATR Keltner Breakout (15m)
def run_atr_keltner():
    global traded_today
    now = datetime.now(timezone.utc).date()
    if traded_today["ATR_KELTNER"] == now: return
    
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 100)
    if rates is None or len(rates) < 100: return
    
    closes = rates['close']
    ema20 = ema(closes, 20)
    atr = calc_atr(rates, 14)
    
    p_close = closes[-3]
    c_close = closes[-2]
    
    p_kc_up = ema20[-3] + (2 * atr[-3])
    p_kc_lo = ema20[-3] - (2 * atr[-3])
    c_kc_up = ema20[-2] + (2 * atr[-2])
    c_kc_lo = ema20[-2] - (2 * atr[-2])
    
    signal = None
    if p_close <= p_kc_up and c_close > c_kc_up:
        signal = mt5.ORDER_TYPE_BUY
    elif p_close >= p_kc_lo and c_close < c_kc_lo:
        signal = mt5.ORDER_TYPE_SELL
        
    if signal is not None:
        price = mt5.symbol_info_tick(SYMBOL).ask if signal == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(SYMBOL).bid
        curr_atr = atr[-1]
        sl_dist = 2.0 * curr_atr
        if signal == mt5.ORDER_TYPE_SELL and STRICT_SHORT_STOPS:
            sl_dist = 1.0 * curr_atr
            
        tp_dist = sl_dist * 2.0
        sl = price - sl_dist if signal == mt5.ORDER_TYPE_BUY else price + sl_dist
        tp = price + tp_dist if signal == mt5.ORDER_TYPE_BUY else price - tp_dist
        
        if sl_dist > 12.00:
            logging.warning(f"[ATR_KELTNER] Trade skipped: M5 ATR risk (${sl_dist:.2f}) exceeds $12 cap.")
            print(f"[{now.strftime('%H:%M:%S')}] SKIPPED: ATR_KELTNER risk ${sl_dist:.2f} > $12")
            return
        
        if execute_trade(signal, price, sl, tp, "ATR_KELTNER", MAGIC_BASE + 1):
            traded_today["ATR_KELTNER"] = now

# Strategy 2: MACD Cross + EMA200 (1H)
def run_macd_ema200():
    global traded_today
    now = datetime.now(timezone.utc).date()
    if traded_today["MACD_EMA200"] == now: return
    
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 300)
    if rates is None or len(rates) < 300: return
    
    closes = rates['close']
    ema200 = ema(closes, 200)
    macd_line, sig_line = macd(closes)
    
    c_close = closes[-2]
    c_ema200 = ema200[-2]
    p_macd = macd_line[-3]
    p_sig = sig_line[-3]
    c_macd = macd_line[-2]
    c_sig = sig_line[-2]
    
    signal = None
    if c_close > c_ema200 and p_macd <= p_sig and c_macd > c_sig:
        signal = mt5.ORDER_TYPE_BUY
    elif c_close < c_ema200 and p_macd >= p_sig and c_macd < c_sig:
        signal = mt5.ORDER_TYPE_SELL
        
    if signal is not None:
        price = mt5.symbol_info_tick(SYMBOL).ask if signal == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(SYMBOL).bid
        atr = calc_atr(rates, 14)[-1]
        sl_dist = 2.0 * atr
        if signal == mt5.ORDER_TYPE_SELL and STRICT_SHORT_STOPS:
            sl_dist = 1.0 * atr
            
        tp_dist = sl_dist * 1.5
        sl = price - sl_dist if signal == mt5.ORDER_TYPE_BUY else price + sl_dist
        tp = price + tp_dist if signal == mt5.ORDER_TYPE_BUY else price - tp_dist
        
        if sl_dist > 12.00:
            logging.warning(f"[MACD_EMA200] Trade skipped: M5 ATR risk (${sl_dist:.2f}) exceeds $12 cap.")
            print(f"[{now.strftime('%H:%M:%S')}] SKIPPED: MACD_EMA200 risk ${sl_dist:.2f} > $12")
            return
        
        if execute_trade(signal, price, sl, tp, "MACD_EMA200", MAGIC_BASE + 2):
            traded_today["MACD_EMA200"] = now

# Strategy 3: Asian Range Breakout (15m)
def run_asian_breakout():
    global traded_today
    now_utc = datetime.now(timezone.utc)
    if traded_today["ASIAN_BREAKOUT"] == now_utc.date(): return
    
    if not (8 <= now_utc.hour < 10): return
        
    today_00 = datetime(now_utc.year, now_utc.month, now_utc.day, 0, 0, 0, tzinfo=timezone.utc)
    today_08 = datetime(now_utc.year, now_utc.month, now_utc.day, 8, 0, 0, tzinfo=timezone.utc)
    
    rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M5, today_00, today_08)
    if rates is None or len(rates) == 0: return
        
    asian_high = float(np.max(rates['high']))
    asian_low = float(np.min(rates['low']))
    asian_range = asian_high - asian_low
    if asian_range > 50.0: return
        
    current_rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 3)
    if current_rates is None or len(current_rates) < 3: return
    
    p_close = current_rates[-3]['close']
    c_close = current_rates[-2]['close']
    
    signal = None
    sl = None
    if p_close <= asian_high and c_close > asian_high:
        signal = mt5.ORDER_TYPE_BUY
        sl = asian_low if asian_range <= 25.0 else asian_low + (asian_range / 2)
    elif p_close >= asian_low and c_close < asian_low:
        signal = mt5.ORDER_TYPE_SELL
        sl = asian_high if asian_range <= 25.0 else asian_high - (asian_range / 2)
        
    if signal is not None:
        price = mt5.symbol_info_tick(SYMBOL).ask if signal == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(SYMBOL).bid
        risk = abs(price - sl)
        tp = price + (risk * 2.0) if signal == mt5.ORDER_TYPE_BUY else price - (risk * 2.0)
        
        if risk > 12.00:
            logging.warning(f"[ASIAN_BREAKOUT] Trade skipped: Structural risk (${risk:.2f}) exceeds $12 cap.")
            print(f"[{now_utc.strftime('%H:%M:%S')}] SKIPPED: ASIAN_BREAKOUT risk ${risk:.2f} > $12")
            return
        
        if execute_trade(signal, price, sl, tp, "ASIAN_BREAKOUT", MAGIC_BASE + 3):
            traded_today["ASIAN_BREAKOUT"] = now_utc.date()

# Strategy 4: Previous Day High/Low Breakout (1H)
def run_pdhl_breakout():
    global traded_today
    now_utc = datetime.now(timezone.utc)
    if traded_today["PDHL_BREAKOUT"] == now_utc.date(): return
    
    d1_rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_D1, 0, 3)
    if d1_rates is None or len(d1_rates) < 3: return
    prev_day = d1_rates[-2]
    pd_hi = prev_day['high']
    pd_lo = prev_day['low']
    
    h1_rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 50)
    if h1_rates is None or len(h1_rates) < 50: return
    p_close = h1_rates[-3]['close']
    c_close = h1_rates[-2]['close']
    
    signal = None
    if p_close <= pd_hi and c_close > pd_hi:
        signal = mt5.ORDER_TYPE_BUY
    elif p_close >= pd_lo and c_close < pd_lo:
        signal = mt5.ORDER_TYPE_SELL
        
    if signal is not None:
        price = mt5.symbol_info_tick(SYMBOL).ask if signal == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(SYMBOL).bid
        atr = calc_atr(h1_rates, 14)[-1]
        sl_dist = 2.0 * atr
        if signal == mt5.ORDER_TYPE_SELL and STRICT_SHORT_STOPS:
            sl_dist = 1.0 * atr
            
        tp_dist = sl_dist * 2.0
        sl = price - sl_dist if signal == mt5.ORDER_TYPE_BUY else price + sl_dist
        tp = price + tp_dist if signal == mt5.ORDER_TYPE_BUY else price - tp_dist
        
        if sl_dist > 12.00:
            logging.warning(f"[PDHL_BREAKOUT] Trade skipped: M5 ATR risk (${sl_dist:.2f}) exceeds $12 cap.")
            print(f"[{now_utc.strftime('%H:%M:%S')}] SKIPPED: PDHL_BREAKOUT risk ${sl_dist:.2f} > $12")
            return
        
        if execute_trade(signal, price, sl, tp, "PDHL_BREAKOUT", MAGIC_BASE + 4):
            traded_today["PDHL_BREAKOUT"] = now_utc.date()

if __name__ == "__main__":
    if not mt5.initialize():
        logging.error("MT5 initialize failed")
        exit()
    
    parse_macro_gating_rules()
    
    logging.info("Multi-Strategy Institutional Engine Started.")
    logging.info(f"Loaded: ATR_KELTNER, MACD_EMA200, ASIAN_BREAKOUT, PDHL_BREAKOUT. Max Trades: {MAX_CONCURRENT_TRADES}")
    
    while True:
        try:
            trailing_stop_logic()
            run_atr_keltner()
            run_macd_ema200()
            run_asian_breakout()
            run_pdhl_breakout()
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        time.sleep(60)
