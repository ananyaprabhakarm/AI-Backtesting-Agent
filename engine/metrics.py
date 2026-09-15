"""Performance metrics computed from a BacktestResult."""
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from engine.backtest import BacktestResult
from engine.benchmark import buy_and_hold_return_pct


@dataclass
class Metrics:
    total_return_pct: float
    num_trades: int
    win_rate_pct: float
    avg_trade_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    profit_factor: float
    alpha_pct: Optional[float] = None  # strategy return minus buy-and-hold return; None if no benchmark df was given


def max_drawdown_pct(equity_curve) -> float:
    if len(equity_curve) == 0:
        return 0.0
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    return float(drawdown.min() * 100)


def sharpe_ratio(equity_curve, periods_per_year: int = 252, risk_free_rate: float = 0.0) -> float:
    if len(equity_curve) < 2:
        return 0.0
    returns = equity_curve.pct_change().dropna()
    # A single-element sample std is NaN, not 0 — guard on count, not just
    # the `== 0` check, or a very short curve silently returns NaN.
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    period_rf = risk_free_rate / periods_per_year
    excess = returns - period_rf
    return float((excess.mean() / returns.std()) * np.sqrt(periods_per_year))


def sortino_ratio(equity_curve, periods_per_year: int = 252, risk_free_rate: float = 0.0) -> float:
    """Like Sharpe, but only downside volatility (returns below the
    risk-free rate) counts against the strategy — upside swings don't
    penalize it the way they do in the Sharpe ratio's plain std dev."""
    if len(equity_curve) < 2:
        return 0.0
    returns = equity_curve.pct_change().dropna()
    if len(returns) < 2:
        return 0.0
    period_rf = risk_free_rate / periods_per_year
    excess = returns - period_rf
    downside = excess[excess < 0]
    if len(downside) < 2 or downside.std() == 0:
        return 0.0
    return float((excess.mean() / downside.std()) * np.sqrt(periods_per_year))


def calmar_ratio(equity_curve, initial_capital: float, periods_per_year: int = 252) -> float:
    """Annualized return divided by max drawdown magnitude."""
    if len(equity_curve) < 2 or initial_capital <= 0:
        return 0.0
    num_periods = len(equity_curve)
    total_return_ratio = equity_curve.iloc[-1] / initial_capital
    if total_return_ratio <= 0:
        return 0.0  # a total wipeout has no sensible annualized rate — treat as undefined
    annualized_return = total_return_ratio ** (periods_per_year / num_periods) - 1
    mdd_fraction = abs(max_drawdown_pct(equity_curve)) / 100
    if mdd_fraction == 0:
        return 0.0
    return float(annualized_return / mdd_fraction)


def profit_factor(trades) -> float:
    """Gross profit from winners divided by gross loss from losers.
    Returns float('inf') if there are winners and no losers at all."""
    gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = sum(-t.pnl for t in trades if t.pnl < 0)
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def compute_metrics(result: BacktestResult, df: Optional[pd.DataFrame] = None, periods_per_year: int = 252) -> Metrics:
    total_return = (result.final_equity / result.initial_capital - 1) * 100 if result.initial_capital else 0.0

    num_trades = len(result.trades)
    if num_trades:
        wins = sum(1 for t in result.trades if t.pnl > 0)
        win_rate = wins / num_trades * 100
        avg_trade_return = sum(t.return_pct for t in result.trades) / num_trades
    else:
        win_rate = 0.0
        avg_trade_return = 0.0

    alpha_pct = None
    if df is not None:
        alpha_pct = total_return - buy_and_hold_return_pct(df, result.initial_capital)

    return Metrics(
        total_return_pct=total_return,
        num_trades=num_trades,
        win_rate_pct=win_rate,
        avg_trade_return_pct=avg_trade_return,
        max_drawdown_pct=max_drawdown_pct(result.equity_curve),
        sharpe_ratio=sharpe_ratio(result.equity_curve, periods_per_year=periods_per_year),
        sortino_ratio=sortino_ratio(result.equity_curve, periods_per_year=periods_per_year),
        calmar_ratio=calmar_ratio(result.equity_curve, result.initial_capital, periods_per_year=periods_per_year),
        profit_factor=profit_factor(result.trades),
        alpha_pct=alpha_pct,
    )
