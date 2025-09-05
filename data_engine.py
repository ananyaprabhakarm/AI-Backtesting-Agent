import pandas as pd
import yfinance as yf 

def fetch_historical_data(stock, from_date, to_date, timeframe):
    """
    Fetches real historical stock data from Yahoo Finance.

    Args:
        stock (str): The ticker symbol for the stock (e.g., "AAPL", "NVDA", "SPY").
        from_date (str): The start date in 'YYYY-MM-DD' format.
        to_date (str): The end date in 'YYYY-MM-DD' format.
        timeframe (str): The data interval (e.g., '1d' for daily, '1h' for hourly).

    Returns:
        pd.DataFrame: A DataFrame containing the OHLCV data from Yahoo Finance.
    """
    print(f"--- Fetching real data for {stock} from {from_date} to {to_date} ---")
    try:
        # The core of the new logic: yf.download()
        # It fetches the data and returns it as a pandas DataFrame.
        # Note the parameter name changes: from_date -> start, to_date -> end, timeframe -> interval
        df = yf.download(tickers=stock, start=from_date, end=to_date, interval=timeframe)

        if df.empty:
            print(f"No data found for ticker '{stock}'. It might be an invalid ticker or no data exists for the given date range.")
            return pd.DataFrame()

        # The column names from Yahoo Finance are capitalized (Open, High, Low, Close).
        # We'll convert them to lowercase to match the rest of our project.
        df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Adj Close': 'adj_close',
            'Volume': 'volume'
        }, inplace=True)
        
        # Add the date as a column instead of just the index
        df.reset_index(inplace=True)
        df.rename(columns={'Date': 'date', 'Datetime': 'date'}, inplace=True) # Handles both daily and intraday
        
        # Ensure the date column is in the correct format
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

