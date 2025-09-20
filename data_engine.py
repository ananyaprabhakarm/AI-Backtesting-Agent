import pandas as pd
import yfinance as yf 

def fetch_historical_data(stock, from_date, to_date, timeframe):
    
    try:    
        df = yf.download(tickers=stock, start=from_date, end=to_date, interval=timeframe)

        if df.empty:
            print(f"No data found for ticker '{stock}'. It might be an invalid ticker or no data exists for the given date range.")
            return pd.DataFrame()

        df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Adj Close': 'adj_close',
            'Volume': 'volume'
        }, inplace=True)
        
        df.reset_index(inplace=True)
        df.rename(columns={'Date': 'date', 'Datetime': 'date'}, inplace=True) # Handles both daily and intraday
        

        df['date'] = pd.to_datetime(df['date'])


        print("Data fetched successfully.")
        return df

    except Exception as e:
        print(f"An error occurred while fetching data: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    nvda_df = fetch_historical_data(stock="NVDA", from_date="2024-01-01", to_date="2024-02-01", timeframe="1d")
    
    if not nvda_df.empty:
        print("\n--- Sample of NVDA Data ---")
        print(nvda_df.head())

