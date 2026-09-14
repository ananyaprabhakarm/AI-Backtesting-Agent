"""Streamlit web UI for the AI Backtesting Agent.

Run with: streamlit run app.py
"""
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_engine import fetch_historical_data
from engine.backtest import run_backtest
from engine.metrics import compute_metrics
from engine.parser_regex import parse_rule

st.set_page_config(page_title="AI Backtesting Agent", layout="wide")
st.title("AI Backtesting Agent")
st.caption("Turn a plain-English trading rule into a backtest against real historical data.")

with st.sidebar:
    st.header("Strategy")
    entry_text = st.text_input("Entry rule", "buy when close crosses above sma_20")
    exit_text = st.text_input("Exit rule (optional)", "")
    use_ai = st.checkbox(
        "Use AI (Claude) to interpret the rule",
        value=False,
        help="Requires ANTHROPIC_API_KEY to be set. Falls back to the built-in rule-based parser on failure.",
    )

    st.header("Data")
    ticker = st.text_input("Ticker", "AAPL")
    start_date = st.date_input("Start date", date.today() - timedelta(days=365))
    end_date = st.date_input("End date", date.today())
    timeframe = st.selectbox("Timeframe", ["1d", "1h", "1wk"], index=0)

    st.header("Position sizing")
    initial_capital = st.number_input("Initial capital", min_value=100.0, value=10000.0, step=100.0)
    position_size_pct = st.slider("Position size (% of capital per trade)", 1, 100, 100) / 100

    run_clicked = st.button("Run backtest", type="primary")


def parse_rule_text(entry_text, exit_text, use_ai):
    if use_ai:
        try:
            from engine.parser_llm import parse_rule_with_llm
            return parse_rule_with_llm(entry_text, exit_text), None
        except Exception as e:
            return parse_rule(entry_text, exit_text), f"AI parsing unavailable ({e}); used rule-based parsing instead."
    return parse_rule(entry_text, exit_text), None


if run_clicked:
    try:
        rule, ai_warning = parse_rule_text(entry_text, exit_text, use_ai)
        if ai_warning:
            st.warning(ai_warning)

        with st.spinner(f"Fetching {ticker} data..."):
            df = fetch_historical_data(ticker.strip().upper(), str(start_date), str(end_date), timeframe)

        if df.empty:
            st.error(f"No data found for '{ticker}' in that date range.")
        else:
            result = run_backtest(df, rule, initial_capital=initial_capital, position_size_pct=position_size_pct)
            metrics = compute_metrics(result)

            cols = st.columns(6)
            cols[0].metric("Total return", f"{metrics.total_return_pct:.2f}%")
            cols[1].metric("Trades", metrics.num_trades)
            cols[2].metric("Win rate", f"{metrics.win_rate_pct:.2f}%")
            cols[3].metric("Avg trade return", f"{metrics.avg_trade_return_pct:.2f}%")
            cols[4].metric("Max drawdown", f"{metrics.max_drawdown_pct:.2f}%")
            cols[5].metric("Sharpe ratio", f"{metrics.sharpe_ratio:.2f}")

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
            price_fig.update_layout(title=f"{ticker.upper()} price", height=420, margin=dict(t=40, b=20))
            st.plotly_chart(price_fig)

            equity_fig = go.Figure()
            equity_fig.add_trace(go.Scatter(x=df["date"], y=result.equity_curve, name="Equity", line=dict(color="#54A24B")))
            equity_fig.update_layout(title="Equity curve", height=320, margin=dict(t=40, b=20))
            st.plotly_chart(equity_fig)

            if result.trades:
                trade_rows = [{
                    "Entry date": t.entry_date, "Entry price": round(t.entry_price, 2),
                    "Exit date": t.exit_date, "Exit price": round(t.exit_price, 2),
                    "Shares": round(t.shares, 4), "P&L": round(t.pnl, 2), "Return %": round(t.return_pct, 2),
                } for t in result.trades]
                st.subheader("Trade log")
                st.dataframe(pd.DataFrame(trade_rows), width='stretch')
            else:
                st.info("No trades were triggered for this rule over the selected period.")
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Set your strategy in the sidebar and click **Run backtest**.")
