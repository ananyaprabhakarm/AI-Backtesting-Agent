import pandas as pd
import pytest

from engine.benchmark import buy_and_hold_equity_curve, buy_and_hold_return_pct


def make_df(opens, closes):
    dates = pd.date_range("2024-01-01", periods=len(opens))
    return pd.DataFrame({"date": dates, "open": opens, "close": closes})


def test_buy_and_hold_buys_at_first_open_and_marks_to_close():
    df = make_df(opens=[10, 11, 12], closes=[10.5, 11.5, 20])
    curve = buy_and_hold_equity_curve(df, initial_capital=1000)

    shares = 1000 / 10  # first bar's open
    assert curve.tolist() == pytest.approx([shares * 10.5, shares * 11.5, shares * 20])


def test_buy_and_hold_return_pct():
    df = make_df(opens=[10, 11, 12], closes=[10.5, 11.5, 20])
    assert buy_and_hold_return_pct(df, initial_capital=1000) == pytest.approx((20 / 10 - 1) * 100)


def test_empty_dataframe_raises():
    with pytest.raises(ValueError):
        buy_and_hold_equity_curve(pd.DataFrame())
