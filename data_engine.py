import pandas as pd
import numpy as np

def fetch_historicaldata(stock, from_date, to_date, timeframe):
    """
    Fetches historical data for a given stock within a date range and timeframe.
    Returns a Pandas DataFrame with columns: stock, date, timestamp, open, high, low, close, volume.
    """
    # Generate a date range based on the timeframe
    date_range = pd.date_range(start=from_date, end=to_date, freq=timeframe)
    
    # Generate dummy data
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
    
    # Create and return the DataFrame
    return pd.DataFrame(data)

# Example usage
if __name__ == "__main__":
    df = fetch_historicaldata("NIFTY", "2023-01-01", "2023-01-10", "D")
    print(df)