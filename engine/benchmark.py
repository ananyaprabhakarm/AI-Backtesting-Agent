"""Buy-and-hold benchmark: what you'd have made just holding the ticker,
for comparison against a strategy's own equity curve. No trading, no
commission/slippage — a single notional buy at the first bar's open.
"""
import pandas as pd


def buy_and_hold_equity_curve(df: pd.DataFrame, initial_capital: float = 10000.0) -> pd.Series:
    if df.empty:
        raise ValueError("No price data to compute a buy-and-hold curve from")

    entry_price = df.iloc[0]['open']
    shares = initial_capital / entry_price if entry_price > 0 else 0.0
    return shares * df['close']


def buy_and_hold_return_pct(df: pd.DataFrame, initial_capital: float = 10000.0) -> float:
    curve = buy_and_hold_equity_curve(df, initial_capital)
    return (curve.iloc[-1] / initial_capital - 1) * 100
