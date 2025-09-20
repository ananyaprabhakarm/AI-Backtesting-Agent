# generated_strategy.py
from data_engine import fetch_historical_data
stock = input("Enter stock ticker (e.g., AAPL, NVDA, SPY): ").strip().upper()
from_date = input("Enter start date (YYYY-MM-DD): ").strip()
to_date = input("Enter end date (YYYY-MM-DD): ").strip()
timeframe = input("Enter timeframe (e.g., 1d for daily, 1h for hourly): ").strip()

def backtest_strategy():
    df = fetch_historical_data(stock, from_date, to_date, timeframe)
    position = None
    signals = []

    for i in range(len(df)):
        row = df.iloc[i]

        if row['close'] > 40:
            if position != 'long':
                print(f"BUY SIGNAL at {row['date']} | Price: {row['close']}")
                position = 'long'
                signals.append(('buy', row['date'], row['close']))
        else:
            if position == 'long':
                print(f"SELL SIGNAL at {row['date']} | Price: {row['close']}")
                position = None
                signals.append(('sell', row['date'], row['close']))

    print("\n=== Backtest Summary ===")
    print(f"Total signals generated: {len(signals)}")

if __name__ == "__main__":
    backtest_strategy()
