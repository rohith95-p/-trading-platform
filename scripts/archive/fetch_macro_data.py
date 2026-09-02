import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_5_day_data(tickers):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10) # Get 10 days to ensure we have 5 trading days
    
    data = yf.download(tickers, start=start_date, end=end_date)['Close']
    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)
    
    # Get last 5 trading days
    data = data.tail(5)
    return data

if __name__ == "__main__":
    tickers = ["GC=F", "SI=F", "DX-Y.NYB", "^TNX", "CL=F", "^VIX"]
    data = get_5_day_data(tickers)
    print("5-Day Closing Prices:")
    print(data)
