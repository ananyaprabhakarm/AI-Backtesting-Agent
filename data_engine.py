import pandas as pd
import numpy as np

def fetch_historicaldata(stock, from_date, to_date, timeframe):
    date_range = pd.date_range(start=from_date, end=to_date, freq=timeframe)
    
    data = {
        "stock": [stock] * len(date_range),
        "date": date_range.date,
        "timestamp": date_range,
        "open": np.random.uniform(100, 200, len(date_range)),
        "high": np.random.uniform(200, 300, len(date_range)),
        "low": np.random.uniform(50, 100, len(date_range)),
        "close": np.random.uniform(100, 200, len(date_range)),
        "volume": np.random.randint(1000, 10000, len(date_range))
    }
    
    return pd.DataFrame(data)

if __name__ == "__main__":
    df = fetch_historicaldata("AAPL", "2023-01-01", "2023-01-10", "D")
    print(df)
