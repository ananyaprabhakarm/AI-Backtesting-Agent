"""Streamlit web UI for the AI Backtesting Agent.

Run with: streamlit run app.py
"""
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from data_engine import fetch_historical_data
from engine.backtest import run_backtest
from engine.benchmark import buy_and_hold_equity_curve
from engine.metrics import compute_metrics
from engine.parser_regex import parse_rule
from engine.screen import run_screen

st.set_page_config(page_title="AI Backtesting Agent", layout="wide")
st.title("AI Backtesting Agent")
st.caption("Turn a plain-English trading rule into a backtest against real historical data.")

with st.sidebar:
    st.header("Strategy")
    entry_text = st.text_input("Entry rule", "buy when close crosses above sma_20")
    exit_text = st.text_input("Exit rule (optional)", "")
    use_ai = st.checkbox(
        "Use AI (Gemini) to interpret the rule",
        value=False,
        help="Requires GEMINI_API_KEY to be set. Falls back to the built-in rule-based parser on failure.",
    )

    st.header("Data")
    tickers_input = st.text_input("Ticker(s), comma-separated", "AAPL")
    start_date = st.date_input("Start date", date.today() - timedelta(days=365))
    end_date = st.date_input("End date", date.today())
    timeframe = st.selectbox("Timeframe", ["1d", "1h", "1wk"], index=0)

    st.header("Position sizing & costs")
    initial_capital = st.number_input("Initial capital", min_value=100.0, value=10000.0, step=100.0)
    position_size_pct = st.slider("Position size (% of capital per trade)", 1, 100, 100) / 100
    commission_pct = st.number_input("Commission per trade (%)", min_value=0.0, max_value=5.0, value=0.1, step=0.01) / 100
    slippage_pct = st.number_input("Slippage per trade (%)", min_value=0.0, max_value=5.0, value=0.05, step=0.01) / 100

    run_clicked = st.button("Run backtest", type="primary")


def parse_rule_text(entry_text, exit_text, use_ai):
    if use_ai:
        try:
            from engine.parser_llm import parse_rule_with_llm
            return parse_rule_with_llm(entry_text, exit_text), None
        except Exception as e:
            return parse_rule(entry_text, exit_text), f"AI parsing unavailable ({e}); used rule-based parsing instead."
    return parse_rule(entry_text, exit_text), None


def format_profit_factor(pf):
    return "∞" if pf == float('inf') else f"{pf:.2f}"


def render_single_ticker(rule, ticker, df):
    result = run_backtest(
        df, rule, initial_capital=initial_capital, position_size_pct=position_size_pct,
        commission_pct=commission_pct, slippage_pct=slippage_pct,
    )
    metrics = compute_metrics(result, df=df)

    row1 = st.columns(6)
    row1[0].metric("Total return", f"{metrics.total_return_pct:.2f}%")
    row1[1].metric("Trades", metrics.num_trades)
    row1[2].metric("Win rate", f"{metrics.win_rate_pct:.2f}%")
    row1[3].metric("Avg trade return", f"{metrics.avg_trade_return_pct:.2f}%")
    row1[4].metric("Max drawdown", f"{metrics.max_drawdown_pct:.2f}%")
    row1[5].metric("Sharpe ratio", f"{metrics.sharpe_ratio:.2f}")

    row2 = st.columns(4)
    row2[0].metric("Sortino ratio", f"{metrics.sortino_ratio:.2f}")
    row2[1].metric("Calmar ratio", f"{metrics.calmar_ratio:.2f}")
    row2[2].metric("Profit factor", format_profit_factor(metrics.profit_factor))
    alpha_display = f"{metrics.alpha_pct:.2f}%" if metrics.alpha_pct is not None else "n/a"
    row2[3].metric("Alpha vs buy & hold", alpha_display)

    price_fig = go.Figure()
    price_fig.add_trace(go.Scatter(x=df["date"], y=df["close"], name="Close", line=dict(color="#4C78A8")))
    for indicator in sorted(rule.indicators_needed()):
        if indicator in df.columns:
            price_fig.add_trace(go.Scatter(x=df["date"], y=df[indicator], name=indicator))

    buy_x = [t.entry_date for t in result.trades]
    buy_y = [t.entry_price for t in result.trades]
    sell_x = [t.exit_date for t in result.trades]
    sell_y = [t.exit_price for t in result.trades]
    price_fig.add_trace(go.Scatter(x=buy_x, y=buy_y, mode="markers", name="Buy",
                                    marker=dict(symbol="triangle-up", color="green", size=11)))
    price_fig.add_trace(go.Scatter(x=sell_x, y=sell_y, mode="markers", name="Sell",
                                    marker=dict(symbol="triangle-down", color="red", size=11)))
    price_fig.update_layout(title=f"{ticker} price", height=420, margin=dict(t=40, b=20))
    st.plotly_chart(price_fig)

    bh_curve = buy_and_hold_equity_curve(df, initial_capital)
    equity_fig = go.Figure()
    equity_fig.add_trace(go.Scatter(x=df["date"], y=result.equity_curve, name="Strategy", line=dict(color="#54A24B")))
    equity_fig.add_trace(go.Scatter(x=df["date"], y=bh_curve, name="Buy & hold", line=dict(color="#B279A2", dash="dot")))
    equity_fig.update_layout(title="Equity curve vs. buy & hold", height=320, margin=dict(t=40, b=20))
    st.plotly_chart(equity_fig)

    if result.trades:
        trade_rows = [{
            "Entry date": t.entry_date, "Entry price": round(t.entry_price, 2),
            "Exit date": t.exit_date, "Exit price": round(t.exit_price, 2),
            "Shares": round(t.shares, 4), "P&L": round(t.pnl, 2), "Return %": round(t.return_pct, 2),
            "Commission": round(t.commission_paid, 2),
        } for t in result.trades]
        st.subheader("Trade log")
        st.dataframe(pd.DataFrame(trade_rows), width='stretch')
    else:
        st.info("No trades were triggered for this rule over the selected period.")


def render_screen(rule, tickers):
    with st.spinner(f"Running the rule across {len(tickers)} tickers..."):
        results = run_screen(
            tickers, rule, str(start_date), str(end_date), timeframe,
            initial_capital=initial_capital, position_size_pct=position_size_pct,
            commission_pct=commission_pct, slippage_pct=slippage_pct,
        )

    rows = []
    for r in results:
        if r.metrics is None:
            rows.append({"Ticker": r.ticker, "Status": f"skipped — {r.error}"})
            continue
        m = r.metrics
        rows.append({
            "Ticker": r.ticker, "Status": "ok",
            "Trades": m.num_trades, "Return %": round(m.total_return_pct, 2),
            "Win rate %": round(m.win_rate_pct, 2), "Avg trade %": round(m.avg_trade_return_pct, 2),
            "Max drawdown %": round(m.max_drawdown_pct, 2), "Sharpe": round(m.sharpe_ratio, 2),
            "Sortino": round(m.sortino_ratio, 2), "Calmar": round(m.calmar_ratio, 2),
            "Profit factor": format_profit_factor(m.profit_factor),
            "Alpha %": round(m.alpha_pct, 2) if m.alpha_pct is not None else None,
        })

    st.subheader(f"Screen results ({len(tickers)} tickers)")
    st.caption("Each ticker is backtested independently with its own capital — this is not portfolio backtesting.")
    df_results = pd.DataFrame(rows)
    if "Return %" in df_results.columns:
        df_results = df_results.sort_values(by="Return %", ascending=False, na_position="last")
    st.dataframe(df_results, width='stretch')


if run_clicked:
    try:
        rule, ai_warning = parse_rule_text(entry_text, exit_text, use_ai)
        if ai_warning:
            st.warning(ai_warning)

        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        if not tickers:
            st.error("Enter at least one ticker.")
        elif len(tickers) == 1:
            ticker = tickers[0]
            with st.spinner(f"Fetching {ticker} data..."):
                df = fetch_historical_data(ticker, str(start_date), str(end_date), timeframe)
            if df.empty:
                st.error(f"No data found for '{ticker}' in that date range.")
            else:
                render_single_ticker(rule, ticker, df)
        else:
            render_screen(rule, tickers)
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Set your strategy in the sidebar and click **Run backtest**. Enter multiple comma-separated tickers to run a screen instead of a single detailed backtest.")
