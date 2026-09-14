"""Core backtest loop: walks the price series bar-by-bar, evaluates the
rule's entry/exit conditions, and tracks a single long position with
simple position sizing (a fraction of available cash per entry).
"""
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from engine.conditions import Rule
from engine.indicators import compute_indicators


@dataclass
class Trade:
    entry_date: object
    entry_price: float
    exit_date: object
    exit_price: float
    shares: float

    @property
    def pnl(self) -> float:
        return (self.exit_price - self.entry_price) * self.shares

    @property
    def return_pct(self) -> float:
        return (self.exit_price / self.entry_price - 1) * 100


@dataclass
class BacktestResult:
    trades: List[Trade] = field(default_factory=list)
    equity_curve: Optional[pd.Series] = None
    dates: Optional[pd.Series] = None
    initial_capital: float = 0.0
    final_equity: float = 0.0


def run_backtest(
    df: pd.DataFrame,
    rule: Rule,
    initial_capital: float = 10000.0,
    position_size_pct: float = 1.0,
) -> BacktestResult:
    """Run a single-position long-only backtest.

    position_size_pct is the fraction (0, 1] of available cash committed
    to each new position.
    """
    if not 0 < position_size_pct <= 1:
        raise ValueError("position_size_pct must be between 0 (exclusive) and 1 (inclusive)")
    if df.empty:
        raise ValueError("No price data to backtest")

    df = compute_indicators(df, rule.indicators_needed())

    cash = initial_capital
    shares = 0.0
    entry_date = None
    entry_price = None
    trades: List[Trade] = []
    equity_curve = []

    for i in range(len(df)):
        row = df.iloc[i]
        in_position = shares > 0

        if not in_position:
            if rule.entry.evaluate(row):
                allocation = cash * position_size_pct
                price = row['close']
                if price > 0:
                    shares = allocation / price
                    cash -= shares * price
                    entry_date = row['date']
                    entry_price = price
        else:
            should_exit = rule.exit.evaluate(row) if rule.exit is not None else not rule.entry.evaluate(row)
            if should_exit:
                price = row['close']
                cash += shares * price
                trades.append(Trade(entry_date, entry_price, row['date'], price, shares))
                shares = 0.0
                entry_date = entry_price = None

        equity_curve.append(cash + shares * row['close'])

    # Close any still-open position at the last bar's price so metrics
    # reflect the full backtest window rather than ignoring an open trade.
    if shares > 0:
        last_row = df.iloc[-1]
        price = last_row['close']
        cash += shares * price
        trades.append(Trade(entry_date, entry_price, last_row['date'], price, shares))
        shares = 0.0
        equity_curve[-1] = cash

    return BacktestResult(
        trades=trades,
        equity_curve=pd.Series(equity_curve, index=df.index),
        dates=df['date'],
        initial_capital=initial_capital,
        final_equity=equity_curve[-1] if equity_curve else initial_capital,
    )
