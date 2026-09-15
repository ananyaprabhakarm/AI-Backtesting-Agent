"""Run the same rule across several tickers independently and compare.

This is NOT portfolio backtesting — each ticker gets its own isolated
run with its own initial_capital; there's no shared capital, no
correlation modeling, no rebalancing. It's "does this rule work here
too", not "how would a real portfolio holding these together behave".
"""
from dataclasses import dataclass
from typing import List, Optional

from data_engine import fetch_historical_data
from engine.backtest import run_backtest
from engine.conditions import Rule
from engine.metrics import Metrics, compute_metrics


@dataclass
class ScreenResult:
    ticker: str
    metrics: Optional[Metrics] = None
    error: Optional[str] = None


def run_screen(
    tickers: List[str],
    rule: Rule,
    from_date: str,
    to_date: str,
    timeframe: str,
    initial_capital: float = 10000.0,
    position_size_pct: float = 1.0,
    commission_pct: float = 0.0,
    slippage_pct: float = 0.0,
    periods_per_year: int = 252,
) -> List[ScreenResult]:
    results = []
    for raw_ticker in tickers:
        ticker = raw_ticker.strip().upper()
        if not ticker:
            continue
        try:
            df = fetch_historical_data(ticker, from_date, to_date, timeframe)
            if df.empty:
                results.append(ScreenResult(ticker=ticker, error="No data returned for this ticker/date range"))
                continue
            result = run_backtest(
                df, rule,
                initial_capital=initial_capital,
                position_size_pct=position_size_pct,
                commission_pct=commission_pct,
                slippage_pct=slippage_pct,
            )
            metrics = compute_metrics(result, df=df, periods_per_year=periods_per_year)
            results.append(ScreenResult(ticker=ticker, metrics=metrics))
        except Exception as e:
            results.append(ScreenResult(ticker=ticker, error=str(e)))
    return results
