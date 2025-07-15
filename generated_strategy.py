# generated_strategy.py
from data_engine import fetch_historicaldata

def backtest_strategy():
    df = fetch_historicaldata()
    position = None
    signals = []

    for i in range(len(df)):
        row = df.iloc[i]

        if close < open:
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
