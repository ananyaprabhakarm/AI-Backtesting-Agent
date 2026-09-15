import statistics

import pandas as pd
import pytest

from engine.backtest import BacktestResult, Trade
from engine.metrics import (
    calmar_ratio,
    compute_metrics,
    max_drawdown_pct,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
)


def test_max_drawdown_pct():
    equity = pd.Series([100, 120, 90, 110, 80, 130])
    # peak 120 -> trough 80 => -33.33%
    assert max_drawdown_pct(equity) == pytest.approx(-33.3333, rel=1e-3)


def test_max_drawdown_pct_monotonic_increase_is_zero():
    equity = pd.Series([100, 110, 120, 130])
    assert max_drawdown_pct(equity) == pytest.approx(0.0)


def test_sharpe_and_sortino_do_not_nan_on_a_single_return():
    # Two points -> exactly one pct_change return -> sample std is
    # undefined (NaN), not 0. Both ratios must guard on count, not just
    # on `std() == 0`, or this silently returns NaN.
    equity = pd.Series([100.0, 110.0])
    assert sharpe_ratio(equity) == 0.0
    assert sortino_ratio(equity) == 0.0


def test_sortino_ratio_against_independent_computation():
    equity = pd.Series([100, 90, 80, 95, 85, 105])
    returns = equity.pct_change().dropna().tolist()
    downside = [r for r in returns if r < 0]
    expected = statistics.mean(returns) / statistics.stdev(downside)
    assert sortino_ratio(equity, periods_per_year=1) == pytest.approx(expected)


def test_sortino_ratio_no_downside_is_zero():
    equity = pd.Series([100, 110, 120, 130])  # monotonic increase, no negative returns
    assert sortino_ratio(equity) == 0.0


def test_calmar_ratio_hand_computed():
    # total return 1.3x over 4 periods at periods_per_year=4 -> annualized
    # return exponent is exactly 1, so annualized_return = 0.3.
    # Drawdown: peak 1200 -> trough 900 => -25%.
    # calmar = 0.3 / 0.25 = 1.2
    equity = pd.Series([1000, 1200, 900, 1300])
    assert calmar_ratio(equity, initial_capital=1000, periods_per_year=4) == pytest.approx(1.2)


def test_calmar_ratio_zero_drawdown_is_zero():
    equity = pd.Series([1000, 1100, 1200])
    assert calmar_ratio(equity, initial_capital=1000) == 0.0


def test_calmar_ratio_total_wipeout_is_zero():
    equity = pd.Series([1000, 500, 0])
    assert calmar_ratio(equity, initial_capital=1000) == 0.0


def test_profit_factor_hand_computed():
    trades = [
        Trade(entry_date="d", entry_price=10, exit_date="d", exit_price=20, shares=10),   # pnl=100
        Trade(entry_date="d", entry_price=10, exit_date="d", exit_price=5, shares=10),     # pnl=-50
        Trade(entry_date="d", entry_price=10, exit_date="d", exit_price=30, shares=10),    # pnl=200
        Trade(entry_date="d", entry_price=10, exit_date="d", exit_price=7, shares=10),     # pnl=-30
    ]
    assert profit_factor(trades) == pytest.approx(300 / 80)


def test_profit_factor_no_losses_is_infinite():
    trades = [Trade(entry_date="d", entry_price=10, exit_date="d", exit_price=20, shares=10)]
    assert profit_factor(trades) == float('inf')


def test_profit_factor_no_trades_is_zero():
    assert profit_factor([]) == 0.0


def test_compute_metrics_no_trades():
    result = BacktestResult(trades=[], equity_curve=pd.Series([1000, 1000, 1000]),
                             dates=pd.Series(pd.date_range("2024-01-01", periods=3)),
                             initial_capital=1000, final_equity=1000)
    m = compute_metrics(result)
    assert m.num_trades == 0
    assert m.win_rate_pct == 0.0
    assert m.total_return_pct == pytest.approx(0.0)
    assert m.alpha_pct is None


def test_compute_metrics_win_rate_and_return():
    trades = [
        Trade("d1", 10, "d2", 12, 100),   # win, +20%
        Trade("d3", 10, "d4", 9, 100),    # loss, -10%
    ]
    equity = pd.Series([1000, 1200, 1100, 990])
    result = BacktestResult(trades=trades, equity_curve=equity, dates=None,
                             initial_capital=1000, final_equity=990)
    m = compute_metrics(result)
    assert m.num_trades == 2
    assert m.win_rate_pct == pytest.approx(50.0)
    assert m.total_return_pct == pytest.approx(-1.0)
    assert m.avg_trade_return_pct == pytest.approx((20 - 10) / 2)


def test_compute_metrics_alpha_against_benchmark():
    dates = pd.date_range("2024-01-01", periods=3)
    df = pd.DataFrame({"date": dates, "open": [10, 11, 12], "close": [10, 11, 20]})
    trades = [Trade("d1", 10, "d2", 15, 100)]  # strategy trade, unrelated to buy-and-hold math
    equity = pd.Series([1000, 1200, 1500])
    result = BacktestResult(trades=trades, equity_curve=equity, dates=None,
                             initial_capital=1000, final_equity=1500)

    m = compute_metrics(result, df=df)

    strategy_return = 50.0  # (1500/1000 - 1) * 100
    bh_return = (20 / 10 - 1) * 100  # buy at bar0 open (10), mark at last close (20)
    assert m.alpha_pct == pytest.approx(strategy_return - bh_return)
