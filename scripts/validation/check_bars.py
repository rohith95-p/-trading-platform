import json
from src.backtesting.data import load_bars
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def ts_to_str(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M:%S')

def main():
    bars = load_bars("XAUUSDm")
    m1 = bars.m1
    
    # Target time: 2026-08-03 13:30:00 IST
    # Let's find timestamps between 13:30 and 14:00 IST
    start_dt = datetime.strptime("2026-08-03 19:00:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
    end_dt = datetime.strptime("2026-08-03 19:30:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
    
    start_ts = int(start_dt.astimezone(timezone.utc).timestamp())
    end_ts = int(end_dt.astimezone(timezone.utc).timestamp())
    
    m1_slice = m1[(m1["time"] >= start_ts) & (m1["time"] <= end_ts)]
    
    print("M1 bars from 13:30 to 14:00 IST:")
    for b in m1_slice:
        print(f"[{ts_to_str(b['time'])}] O: {b['open']} H: {b['high']} L: {b['low']} C: {b['close']}")
        
if __name__ == "__main__":
    main()
