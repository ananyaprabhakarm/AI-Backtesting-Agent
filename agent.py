"""CLI entry point: turn a plain-English rule into a backtest report.

Also writes generated_strategy.py — a standalone, re-runnable copy of
the same backtest — for transparency and sharing.
"""
from data_engine import fetch_historical_data
from engine.codegen import generate_script
from engine.backtest import run_backtest
from engine.metrics import compute_metrics
from engine.parser_regex import parse_rule


def parse_rule_text(entry_text, exit_text, use_ai):
    if use_ai:
        try:
            from engine.parser_llm import parse_rule_with_llm
            return parse_rule_with_llm(entry_text, exit_text)
        except Exception as e:
            print(f"AI parsing unavailable ({e}); falling back to rule-based parsing.")
    return parse_rule(entry_text, exit_text)


def print_report(result, metrics):
    for t in result.trades:
        print(f"BUY  {t.entry_date} @ {t.entry_price:.2f}  ->  SELL {t.exit_date} @ {t.exit_price:.2f}  "
              f"| P&L: {t.pnl:.2f} ({t.return_pct:.2f}%)")

    print("\n=== Backtest Summary ===")
    print(f"Total trades:      {metrics.num_trades}")
    print(f"Total return:      {metrics.total_return_pct:.2f}%")
    print(f"Win rate:          {metrics.win_rate_pct:.2f}%")
    print(f"Avg trade return:  {metrics.avg_trade_return_pct:.2f}%")
    print(f"Max drawdown:      {metrics.max_drawdown_pct:.2f}%")
    print(f"Sharpe ratio:      {metrics.sharpe_ratio:.2f}")


def main():
    try:
        entry_text = input("Enter your entry rule (e.g. 'buy when close crosses above sma_20'): ").strip()
        exit_text = input("Enter an exit rule (optional, press Enter to exit on the opposite condition): ").strip()
        use_ai = input("Use AI (Claude) to interpret the rule? [y/N]: ").strip().lower() == "y"

        rule = parse_rule_text(entry_text, exit_text, use_ai)

        stock = input("Enter stock ticker (e.g., AAPL, NVDA, SPY): ").strip().upper()
        from_date = input("Enter start date (YYYY-MM-DD): ").strip()
        to_date = input("Enter end date (YYYY-MM-DD): ").strip()
        timeframe = input("Enter timeframe (e.g., 1d for daily, 1h for hourly): ").strip()

        capital_input = input("Initial capital [10000]: ").strip()
        initial_capital = float(capital_input) if capital_input else 10000.0

        size_input = input("Position size as % of capital per trade [100]: ").strip()
        position_size_pct = (float(size_input) if size_input else 100.0) / 100

        df = fetch_historical_data(stock, from_date, to_date, timeframe)
        if df.empty:
            return

        result = run_backtest(df, rule, initial_capital=initial_capital, position_size_pct=position_size_pct)
        metrics = compute_metrics(result)
        print_report(result, metrics)

        script = generate_script(rule, initial_capital=initial_capital, position_size_pct=position_size_pct)
        with open("generated_strategy.py", "w") as f:
            f.write(script)
        print("\nStrategy also saved to generated_strategy.py")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
