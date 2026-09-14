import pandas as pd
import pytest

from engine.backtest import BacktestResult, Trade
from engine.metrics import compute_metrics, max_drawdown_pct


def test_max_drawdown_pct():
    equity = pd.Series([100, 120, 90, 110, 80, 130])
    # peak 120 -> trough 80 => -33.33%
    assert max_drawdown_pct(equity) == pytest.approx(-33.3333, rel=1e-3)


def test_max_drawdown_pct_monotonic_increase_is_zero():
    equity = pd.Series([100, 110, 120, 130])
    assert max_drawdown_pct(equity) == pytest.approx(0.0)


def test_compute_metrics_no_trades():
    result = BacktestResult(trades=[], equity_curve=pd.Series([1000, 1000, 1000]),
                             dates=pd.Series(pd.date_range("2024-01-01", periods=3)),
                             initial_capital=1000, final_equity=1000)
    m = compute_metrics(result)
    assert m.num_trades == 0
    assert m.win_rate_pct == 0.0
    assert m.total_return_pct == pytest.approx(0.0)


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
