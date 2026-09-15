import pandas as pd
import pytest

from engine.backtest import run_backtest
from engine.parser_regex import parse_rule


def make_df(closes):
    """OHLC fixture where open == high == low == close per bar. Fine for
    tests that don't care about the open/close distinction."""
    dates = pd.date_range("2024-01-01", periods=len(closes))
    return pd.DataFrame({
        "date": dates, "close": closes, "open": closes, "high": closes, "low": closes,
        "volume": [1000] * len(closes),
    })


def make_ohlc_df(bars):
    """bars: list of (open, close) tuples — for tests that need the two to
    differ, to prove execution actually uses the *next* bar's open."""
    dates = pd.date_range("2024-01-01", periods=len(bars))
    opens = [b[0] for b in bars]
    closes = [b[1] for b in bars]
    highs = [max(o, c) for o, c in bars]
    lows = [min(o, c) for o, c in bars]
    return pd.DataFrame({
        "date": dates, "open": opens, "close": closes, "high": highs, "low": lows,
        "volume": [1000] * len(bars),
    })


def test_entry_executes_at_next_bar_open_not_signal_bar_close():
    # Bar 0's close (10) triggers the signal. Bar 1's open (50) and close
    # (51) are both deliberately different from it and from each other, so
    # whichever price shows up in the trade proves which bar/field was used.
    df = make_ohlc_df([(10, 10), (50, 51)])
    rule = parse_rule("buy when close is above 9")

    result = run_backtest(df, rule, initial_capital=1000, position_size_pct=1.0)

    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.entry_date == pd.Timestamp("2024-01-02")  # bar 1, not bar 0
    assert t.entry_price == 50  # bar 1's open, not bar 0's close (10) or bar 1's close (51)


def test_signal_on_last_bar_is_never_executed():
    # Signal fires on the very last bar (nothing to buy at "close is above 9"
    # until the final close of 10) — there's no bar after it to execute at,
    # so no trade should be recorded at all.
    df = make_df([5, 6, 7, 10])
    rule = parse_rule("buy when close is above 9")

    result = run_backtest(df, rule, initial_capital=1000, position_size_pct=1.0)

    assert result.trades == []
    assert result.final_equity == 1000


def test_backtest_matches_hand_calculation():
    # buy/implicit-sell on "close is above 10", traced bar by bar:
    #   i0 close=11>10 -> signal, enters at bar1's open (12)
    #   i1 close=12>10 -> stays in
    #   i2 close=9<=10 -> exit signal, executes at bar3's open (13)
    #   i3 close=13>10 -> re-entry signal, executes at bar4's open (9)
    #   i4 close=9<=10 -> exit signal, executes at bar5's open (8)
    #   i5 close=8<=10 -> no new signal; backtest ends flat
    closes = [11, 12, 9, 13, 9, 8]
    df = make_df(closes)
    rule = parse_rule("buy when close is above 10")

    result = run_backtest(df, rule, initial_capital=1000, position_size_pct=1.0)

    assert len(result.trades) == 2
    t1, t2 = result.trades
    assert (t1.entry_date, t1.entry_price, t1.exit_date, t1.exit_price) == (
        pd.Timestamp("2024-01-02"), 12, pd.Timestamp("2024-01-04"), 13,
    )
    assert t1.pnl == pytest.approx(1000 / 12 * (13 - 12))

    cash_after_t1 = 1000 / 12 * 13
    assert (t2.entry_date, t2.entry_price, t2.exit_date, t2.exit_price) == (
        pd.Timestamp("2024-01-05"), 9, pd.Timestamp("2024-01-06"), 8,
    )
    expected_t2_pnl = cash_after_t1 / 9 * (8 - 9)
    assert t2.pnl == pytest.approx(expected_t2_pnl)
    assert result.final_equity == pytest.approx(cash_after_t1 / 9 * 8)


def test_backtest_closes_open_position_at_last_bar():
    # Entry signal at bar0 (close=9, not >9, no signal yet), fires at bar1
    # (close=11>9), executes at bar2's open (12). Stays in for the rest —
    # still open when data ends, so it's marked to market at the final close.
    closes = [9, 11, 12, 13, 14]
    df = make_df(closes)
    rule = parse_rule("buy when close is above 9")

    result = run_backtest(df, rule, initial_capital=1000, position_size_pct=1.0)

    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.entry_date == pd.Timestamp("2024-01-03")
    assert t.entry_price == 12
    assert t.exit_date == pd.Timestamp("2024-01-05")
    assert t.exit_price == 14
    assert t.commission_paid == 0.0
    assert result.final_equity == pytest.approx(1000 / 12 * 14)


def test_forced_close_at_end_carries_entry_commission_but_no_exit_commission():
    # Same shape as above, but with commission on. The forced close at the
    # end is a valuation for reporting, not an executed sell order, so it
    # shouldn't charge a second (exit) commission — only the entry's.
    closes = [9, 11, 12, 13, 14]
    df = make_df(closes)
    rule = parse_rule("buy when close is above 9")

    result = run_backtest(df, rule, initial_capital=1000, position_size_pct=1.0, commission_pct=0.01)

    assert len(result.trades) == 1
    t = result.trades[0]
    entry_cost = (1000 / 12) * 12
    expected_entry_commission = entry_cost * 0.01
    assert t.commission_paid == pytest.approx(expected_entry_commission)


def test_explicit_exit_rule_executes_at_next_open_not_signal_close():
    # Explicit exit signal fires at bar2 (close=12 > 11.5) and executes at
    # bar3's open. Bar3's open (8.5) and close (8.0) are made to differ so
    # the recorded exit price proves the real trade path (uses open) fired,
    # not the end-of-data forced-close fallback (which would use close).
    df = make_ohlc_df([(10, 10), (11, 11), (12, 12), (8.5, 8.0)])
    rule = parse_rule("buy when close is above 9", "sell when close is above 11.5")

    result = run_backtest(df, rule, initial_capital=1000, position_size_pct=1.0)

    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.entry_date == pd.Timestamp("2024-01-02")
    assert t.entry_price == 11
    assert t.exit_date == pd.Timestamp("2024-01-04")
    assert t.exit_price == 8.5
    assert result.final_equity == pytest.approx((1000 / 11) * 8.5)


def test_commission_reduces_pnl_by_exact_amount():
    df = make_ohlc_df([(10, 10), (20, 5), (2, 2)])
    rule = parse_rule("buy when close is above 9")  # implicit exit on close <= 9

    baseline = run_backtest(df, rule, initial_capital=1000, position_size_pct=0.5)
    with_commission = run_backtest(df, rule, initial_capital=1000, position_size_pct=0.5, commission_pct=0.01)

    assert len(baseline.trades) == len(with_commission.trades) == 1
    shares = (1000 * 0.5) / 20  # allocation / entry price (open of bar 1) — unaffected by commission
    entry_commission = (shares * 20) * 0.01
    exit_commission = (shares * 2) * 0.01
    expected_commission = entry_commission + exit_commission

    assert with_commission.trades[0].shares == pytest.approx(baseline.trades[0].shares)
    assert with_commission.trades[0].commission_paid == pytest.approx(expected_commission)
    assert with_commission.trades[0].pnl == pytest.approx(baseline.trades[0].pnl - expected_commission)


def test_slippage_worsens_executed_price_and_reduces_pnl():
    df = make_ohlc_df([(10, 10), (20, 5), (2, 2)])
    rule = parse_rule("buy when close is above 9")

    baseline = run_backtest(df, rule, initial_capital=1000, position_size_pct=0.5)
    with_slippage = run_backtest(df, rule, initial_capital=1000, position_size_pct=0.5, slippage_pct=0.01)

    expected_entry_price = 20 * 1.01
    expected_exit_price = 2 * 0.99
    expected_shares = (1000 * 0.5) / expected_entry_price
    expected_pnl = (expected_exit_price - expected_entry_price) * expected_shares

    t = with_slippage.trades[0]
    assert t.entry_price == pytest.approx(expected_entry_price)
    assert t.exit_price == pytest.approx(expected_exit_price)
    assert t.pnl == pytest.approx(expected_pnl)
    assert t.pnl < baseline.trades[0].pnl


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


@pytest.mark.parametrize("bad_pct", [-0.01, 1, 1.5])
def test_invalid_commission_raises(bad_pct):
    rule = parse_rule("buy when close is above 40")
    df = make_df([10, 11])
    with pytest.raises(ValueError):
        run_backtest(df, rule, commission_pct=bad_pct)


@pytest.mark.parametrize("bad_pct", [-0.01, 1, 1.5])
def test_invalid_slippage_raises(bad_pct):
    rule = parse_rule("buy when close is above 40")
    df = make_df([10, 11])
    with pytest.raises(ValueError):
        run_backtest(df, rule, slippage_pct=bad_pct)
