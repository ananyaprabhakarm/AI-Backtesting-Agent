"""Core backtest loop.

Signal vs. execution timing: a rule is evaluated against bar i's own
(now fully-known) OHLCV data, but any resulting entry/exit only
executes at bar i+1's open — never at bar i's own close. Evaluating a
condition on a bar and then trading at that same bar's close is a
look-ahead bias (it assumes you could act on information — that bar's
high/low/volume — before the bar has actually finished forming). A
signal generated on the final bar has no following bar to execute on
and is therefore never executed; it's simply dropped.

Separately, if a position is still open when the data ends, it's
marked to market at the final bar's close purely for reporting (so
metrics reflect the whole window) — that valuation close does not
count as a signal-triggered trade and, deliberately, does not carry
commission/slippage (see run_backtest's docstring).
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
    commission_paid: float = 0.0

    @property
    def pnl(self) -> float:
        """Realized profit, net of commission. Entry/exit prices already
        include slippage, so this is the trader's actual take-home P&L."""
        return (self.exit_price - self.entry_price) * self.shares - self.commission_paid

    @property
    def return_pct(self) -> float:
        """Gross price return (entry/exit prices include slippage, but this
        is not commission-adjusted — it answers "how did the price move",
        not "what did I net". See pnl for the net dollar figure."""
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
    commission_pct: float = 0.0,
    slippage_pct: float = 0.0,
) -> BacktestResult:
    """Run a single-position long-only backtest.

    position_size_pct is the fraction (0, 1] of available cash committed
    to each new position. commission_pct and slippage_pct are per-trade
    fractions (e.g. 0.001 for 0.1%): commission is a fee on top of the
    trade's notional value (deducted from cash, doesn't change share
    count), and slippage worsens the executed price (higher on buys,
    lower on sells) — both apply on entry and exit.

    A rule is evaluated using bar i's data; if it fires, the trade
    executes at bar i+1's open (see module docstring) — so the earliest
    possible entry is at bar 1, and a signal on the last bar is never
    executed. If a position is still open when the loop ends, it's
    closed at the last bar's close for reporting purposes only, with no
    commission/slippage applied (it's a valuation, not an order).
    """
    if not 0 < position_size_pct <= 1:
        raise ValueError("position_size_pct must be between 0 (exclusive) and 1 (inclusive)")
    if not 0 <= commission_pct < 1:
        raise ValueError("commission_pct must be between 0 (inclusive) and 1 (exclusive)")
    if not 0 <= slippage_pct < 1:
        raise ValueError("slippage_pct must be between 0 (inclusive) and 1 (exclusive)")
    if df.empty:
        raise ValueError("No price data to backtest")

    df = compute_indicators(df, rule.indicators_needed())

    cash = initial_capital
    shares = 0.0
    entry_date = entry_price = None
    entry_commission = 0.0
    pending_entry = False
    pending_exit = False
    trades: List[Trade] = []
    equity_curve = []

    for i in range(len(df)):
        row = df.iloc[i]

        # Execute whatever was signaled on the previous bar, at this bar's open.
        if pending_entry and shares == 0:
            price = row['open'] * (1 + slippage_pct)
            if price > 0:
                allocation = cash * position_size_pct
                shares = allocation / price
                cost = shares * price
                entry_commission = cost * commission_pct
                cash -= cost + entry_commission
                entry_date, entry_price = row['date'], price
        pending_entry = False

        if pending_exit and shares > 0:
            price = row['open'] * (1 - slippage_pct)
            proceeds = shares * price
            exit_commission = proceeds * commission_pct
            cash += proceeds - exit_commission
            trades.append(Trade(
                entry_date, entry_price, row['date'], price, shares,
                commission_paid=entry_commission + exit_commission,
            ))
            shares = 0.0
            entry_date = entry_price = None
            entry_commission = 0.0
        pending_exit = False

        # Evaluate this bar's now-fully-known data for a signal to act on next bar.
        in_position = shares > 0
        if not in_position:
            if rule.entry.evaluate(row):
                pending_entry = True
        else:
            should_exit = rule.exit.evaluate(row) if rule.exit is not None else not rule.entry.evaluate(row)
            if should_exit:
                pending_exit = True

        equity_curve.append(cash + shares * row['close'])

    # Any position still open at the end is marked to market at the last
    # close for reporting — not an executed trade, so no commission/slippage.
    if shares > 0:
        last_row = df.iloc[-1]
        price = last_row['close']
        cash += shares * price
        trades.append(Trade(entry_date, entry_price, last_row['date'], price, shares, commission_paid=entry_commission))
        shares = 0.0
        equity_curve[-1] = cash

    return BacktestResult(
        trades=trades,
        equity_curve=pd.Series(equity_curve, index=df.index),
        dates=df['date'],
        initial_capital=initial_capital,
        final_equity=equity_curve[-1] if equity_curve else initial_capital,
    )
