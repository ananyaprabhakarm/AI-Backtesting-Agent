import pandas as pd
import pytest

from engine.backtest import run_backtest
from engine.parser_regex import parse_rule


def make_df(closes):
    dates = pd.date_range("2024-01-01", periods=len(closes))
    return pd.DataFrame({
        "date": dates, "close": closes, "open": closes, "high": closes, "low": closes,
        "volume": [1000] * len(closes),
    })


def test_backtest_matches_hand_calculation():
    closes = [10, 10, 10, 11, 12, 13, 12, 11, 10, 11, 12, 13, 14, 13, 12]
    df = make_df(closes)
    rule = parse_rule("buy when close is above 3 day sma")

    result = run_backtest(df, rule, initial_capital=1000, position_size_pct=1.0)

    assert len(result.trades) == 2
    t1, t2 = result.trades
    assert (t1.entry_date, t1.entry_price, t1.exit_date, t1.exit_price) == (
        pd.Timestamp("2024-01-04"), 11, pd.Timestamp("2024-01-07"), 12,
    )
    assert t1.pnl == pytest.approx(1000 / 11 * (12 - 11))

    cash_after_t1 = 1000 / t1.entry_price * t1.exit_price
    expected_final = cash_after_t1 / t2.entry_price * t2.exit_price
    assert result.final_equity == pytest.approx(expected_final, rel=1e-6)


def test_backtest_closes_open_position_at_last_bar():
    closes = [10, 11, 12, 13, 14]
    df = make_df(closes)
    rule = parse_rule("buy when close is above 9")

    result = run_backtest(df, rule, initial_capital=1000, position_size_pct=1.0)

    assert len(result.trades) == 1
    assert result.trades[0].exit_date == pd.Timestamp("2024-01-05")
    assert result.final_equity == pytest.approx(1000 / 10 * 14)


def test_explicit_exit_rule_used_over_implicit_negation():
    # With only the entry rule, the implicit exit ("not (close > 9)") wouldn't
    # trigger until close drops back to 9 (day index 3). The explicit exit rule
    # here (close > 11.5) fires earlier, at day index 2 — proving it's the
    # explicit rule being used, not a silent fallback to negating entry.
    closes = [10, 11, 12, 9]
    df = make_df(closes)
    rule = parse_rule("buy when close is above 9", "sell when close is above 11.5")

    result = run_backtest(df, rule, initial_capital=1000, position_size_pct=1.0)

    assert len(result.trades) == 1
    assert result.trades[0].exit_date == pd.Timestamp("2024-01-03")
    assert result.trades[0].exit_price == 12


def test_empty_dataframe_raises():
    rule = parse_rule("buy when close is above 40")
    with pytest.raises(ValueError):
        run_backtest(pd.DataFrame(), rule)


@pytest.mark.parametrize("bad_pct", [0, -0.5, 1.5])
def test_invalid_position_size_raises(bad_pct):
    rule = parse_rule("buy when close is above 40")
    df = make_df([10, 11])
    with pytest.raises(ValueError):
        run_backtest(df, rule, position_size_pct=bad_pct)
