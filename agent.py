"""CLI entry point: turn a plain-English rule into a backtest report.

Also writes generated_strategy.py — a standalone, re-runnable copy of
the same backtest — for transparency and sharing.
"""
from dotenv import load_dotenv

load_dotenv()

from data_engine import fetch_historical_data
from engine.benchmark import buy_and_hold_return_pct
from engine.codegen import generate_script
from engine.backtest import run_backtest
from engine.metrics import compute_metrics
from engine.parser_regex import parse_rule
from engine.screen import run_screen


def parse_rule_text(entry_text, exit_text, use_ai):
    if use_ai:
        try:
            from engine.parser_llm import parse_rule_with_llm
            return parse_rule_with_llm(entry_text, exit_text)
        except Exception as e:
            print(f"AI parsing unavailable ({e}); falling back to rule-based parsing.")
    return parse_rule(entry_text, exit_text)


def print_report(result, metrics, df):
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
    print(f"Sortino ratio:     {metrics.sortino_ratio:.2f}")
    print(f"Calmar ratio:      {metrics.calmar_ratio:.2f}")
    pf = "inf" if metrics.profit_factor == float('inf') else f"{metrics.profit_factor:.2f}"
    print(f"Profit factor:     {pf}")

    bh_return = buy_and_hold_return_pct(df, result.initial_capital)
    print(f"\nBuy & hold return: {bh_return:.2f}%")
    print(f"Alpha vs buy&hold: {metrics.alpha_pct:.2f}%")


def print_screen_table(screen_results):
    header = f"{'Ticker':<8} {'Trades':>6} {'Return%':>9} {'WinRate%':>9} {'MaxDD%':>8} {'Sharpe':>7} {'Alpha%':>8}"
    print(header)
    print("-" * len(header))

    ranked = sorted(
        (r for r in screen_results if r.metrics is not None),
        key=lambda r: r.metrics.total_return_pct,
        reverse=True,
    )
    for r in ranked:
        m = r.metrics
        alpha = f"{m.alpha_pct:.2f}" if m.alpha_pct is not None else "n/a"
        print(f"{r.ticker:<8} {m.num_trades:>6} {m.total_return_pct:>9.2f} {m.win_rate_pct:>9.2f} "
              f"{m.max_drawdown_pct:>8.2f} {m.sharpe_ratio:>7.2f} {alpha:>8}")

    failed = [r for r in screen_results if r.error is not None]
    if failed:
        print("\nSkipped:")
        for r in failed:
            print(f"  {r.ticker}: {r.error}")


def main():
    try:
        entry_text = input("Enter your entry rule (e.g. 'buy when close crosses above sma_20'): ").strip()
        exit_text = input("Enter an exit rule (optional, press Enter to exit on the opposite condition): ").strip()
        use_ai = input("Use AI (Gemini) to interpret the rule? [y/N]: ").strip().lower() == "y"

        rule = parse_rule_text(entry_text, exit_text, use_ai)

        tickers_input = input("Enter stock ticker(s), comma-separated (e.g., AAPL, NVDA, SPY): ").strip()
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        from_date = input("Enter start date (YYYY-MM-DD): ").strip()
        to_date = input("Enter end date (YYYY-MM-DD): ").strip()
        timeframe = input("Enter timeframe (e.g., 1d for daily, 1h for hourly): ").strip()

        capital_input = input("Initial capital [10000]: ").strip()
        initial_capital = float(capital_input) if capital_input else 10000.0

        size_input = input("Position size as % of capital per trade [100]: ").strip()
        position_size_pct = (float(size_input) if size_input else 100.0) / 100

        commission_input = input("Commission per trade, % [0.1]: ").strip()
        commission_pct = (float(commission_input) if commission_input else 0.1) / 100

        slippage_input = input("Slippage per trade, % [0.05]: ").strip()
        slippage_pct = (float(slippage_input) if slippage_input else 0.05) / 100

        if len(tickers) > 1:
            screen_results = run_screen(
                tickers, rule, from_date, to_date, timeframe,
                initial_capital=initial_capital, position_size_pct=position_size_pct,
                commission_pct=commission_pct, slippage_pct=slippage_pct,
            )
            print_screen_table(screen_results)
        elif len(tickers) == 1:
            df = fetch_historical_data(tickers[0], from_date, to_date, timeframe)
            if df.empty:
                return
            result = run_backtest(
                df, rule, initial_capital=initial_capital, position_size_pct=position_size_pct,
                commission_pct=commission_pct, slippage_pct=slippage_pct,
            )
            metrics = compute_metrics(result, df=df)
            print_report(result, metrics, df)
        else:
            print("No tickers entered.")
            return

        script = generate_script(
            rule, initial_capital=initial_capital, position_size_pct=position_size_pct,
            commission_pct=commission_pct, slippage_pct=slippage_pct,
        )
        with open("generated_strategy.py", "w") as f:
            f.write(script)
        print("\nStrategy also saved to generated_strategy.py")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
