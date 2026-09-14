"""Performance metrics computed from a BacktestResult."""
from dataclasses import dataclass

import numpy as np

from engine.backtest import BacktestResult


@dataclass
class Metrics:
    total_return_pct: float
    num_trades: int
    win_rate_pct: float
    avg_trade_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float


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
    if returns.empty or returns.std() == 0:
        return 0.0
    period_rf = risk_free_rate / periods_per_year
    excess = returns - period_rf
    return float((excess.mean() / returns.std()) * np.sqrt(periods_per_year))


def compute_metrics(result: BacktestResult, periods_per_year: int = 252) -> Metrics:
    total_return = (result.final_equity / result.initial_capital - 1) * 100 if result.initial_capital else 0.0

    num_trades = len(result.trades)
    if num_trades:
        wins = sum(1 for t in result.trades if t.pnl > 0)
        win_rate = wins / num_trades * 100
        avg_trade_return = sum(t.return_pct for t in result.trades) / num_trades
    else:
        win_rate = 0.0
        avg_trade_return = 0.0

    return Metrics(
        total_return_pct=total_return,
        num_trades=num_trades,
        win_rate_pct=win_rate,
        avg_trade_return_pct=avg_trade_return,
        max_drawdown_pct=max_drawdown_pct(result.equity_curve),
        sharpe_ratio=sharpe_ratio(result.equity_curve, periods_per_year=periods_per_year),
    )
