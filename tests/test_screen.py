import pandas as pd
import pytest

import engine.screen as screen_module
from engine.parser_regex import parse_rule
from engine.screen import run_screen


def make_df(closes):
    dates = pd.date_range("2024-01-01", periods=len(closes))
    return pd.DataFrame({
        "date": dates, "close": closes, "open": closes, "high": closes, "low": closes,
        "volume": [1000] * len(closes),
    })


def fake_fetch(ticker, from_date, to_date, timeframe):
    if ticker == "GOOD":
        return make_df([10, 11, 12, 13, 14])
    if ticker == "EMPTY":
        return pd.DataFrame()
    if ticker == "BROKEN":
        raise RuntimeError("simulated data provider failure")
    raise AssertionError(f"unexpected ticker in test: {ticker}")


def test_screen_handles_good_empty_and_broken_tickers(monkeypatch):
    monkeypatch.setattr(screen_module, "fetch_historical_data", fake_fetch)
    rule = parse_rule("buy when close is above 9")

    results = run_screen(["good", " EMPTY ", "broken"], rule, "2024-01-01", "2024-01-10", "1d")

    by_ticker = {r.ticker: r for r in results}
    assert set(by_ticker) == {"GOOD", "EMPTY", "BROKEN"}

    assert by_ticker["GOOD"].metrics is not None
    assert by_ticker["GOOD"].error is None
    assert by_ticker["GOOD"].metrics.num_trades >= 0  # completed without raising

    assert by_ticker["EMPTY"].metrics is None
    assert "No data" in by_ticker["EMPTY"].error

    assert by_ticker["BROKEN"].metrics is None
    assert "simulated data provider failure" in by_ticker["BROKEN"].error


def test_screen_one_bad_ticker_does_not_stop_the_rest(monkeypatch):
    monkeypatch.setattr(screen_module, "fetch_historical_data", fake_fetch)
    rule = parse_rule("buy when close is above 9")

    results = run_screen(["broken", "good"], rule, "2024-01-01", "2024-01-10", "1d")

    assert len(results) == 2
    assert results[0].ticker == "BROKEN" and results[0].error is not None
    assert results[1].ticker == "GOOD" and results[1].metrics is not None


def test_screen_skips_blank_ticker_entries(monkeypatch):
    monkeypatch.setattr(screen_module, "fetch_historical_data", fake_fetch)
    rule = parse_rule("buy when close is above 9")

    results = run_screen(["good", "", "  "], rule, "2024-01-01", "2024-01-10", "1d")

    assert len(results) == 1
    assert results[0].ticker == "GOOD"
