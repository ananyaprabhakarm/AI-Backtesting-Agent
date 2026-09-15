# AI Backtesting Agent

Turns a plain-English trading rule into a backtest against real historical stock data — with technical indicators, realistic execution (no look-ahead bias, commission, slippage), a buy-and-hold benchmark, a full metrics suite, and multi-ticker screening. Use it from the CLI, from a web UI, or let Gemini interpret rules that plain pattern-matching can't parse.

```
Entry rule: buy when close crosses above sma_20
```

...runs a full backtest and reports total return, win rate, max drawdown, Sharpe/Sortino/Calmar ratios, profit factor, and alpha vs. buy-and-hold — plus writes a standalone, re-runnable copy of the backtest to `generated_strategy.py`.

## Architecture

- [data_engine.py](data_engine.py) — fetches historical OHLCV data from Yahoo Finance via `yfinance`
- [engine/](engine/) — the backtesting engine
  - [conditions.py](engine/conditions.py) — the `Condition`/`Rule` model. **Every rule, however it was parsed, is validated against a strict allowlist of fields, operators, and values before it can run** — this is what makes rule text safe to turn into a backtest rather than a code-injection vector
  - [indicators.py](engine/indicators.py) — SMA, EMA, RSI, MACD, Bollinger Bands, computed on demand
  - [parser_regex.py](engine/parser_regex.py) — deterministic, no-network rule parser
  - [parser_llm.py](engine/parser_llm.py) — Gemini-powered rule parser for phrasing the regex parser can't handle
  - [backtest.py](engine/backtest.py) — the backtest loop: next-bar execution, position sizing, commission, slippage
  - [benchmark.py](engine/benchmark.py) — buy-and-hold equity curve, for comparison against the strategy's own
  - [metrics.py](engine/metrics.py) — total return, win rate, max drawdown, Sharpe/Sortino/Calmar ratios, profit factor, alpha
  - [screen.py](engine/screen.py) — runs one rule across multiple tickers independently and reports per-ticker results
  - [codegen.py](engine/codegen.py) — renders a validated `Rule` into a standalone script that calls the real engine directly (no duplicated logic to drift out of sync)
- [agent.py](agent.py) — CLI entry point
- [app.py](app.py) — Streamlit web UI
- [tests/](tests/) — unit tests for the engine (`pytest tests/`)

## Setup

Requires Python 3.9+.

```bash
git clone https://github.com/ananyaprabhakarm/AI-Backtesting-Agent.git
cd AI-Backtesting-Agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

To enable AI-assisted rule parsing, copy `.env.example` to `.env` and add a [Gemini API key](https://aistudio.google.com/apikey), or export `GEMINI_API_KEY` directly. Without it, the app still works — it just uses the deterministic rule-based parser and AI parsing falls back to it automatically.

## Usage

### CLI

```bash
python agent.py
```

Prompts you for an entry rule, an optional exit rule, whether to use AI parsing, one or more comma-separated tickers, a date range, a timeframe, initial capital, position sizing, commission, and slippage — then prints a full report (or, for multiple tickers, a screen table ranked by return) and saves `generated_strategy.py`.

### Web UI

```bash
streamlit run app.py
```

Configure your strategy in the sidebar and click **Run backtest**. A single ticker shows the price chart with indicator overlays and buy/sell markers, the equity curve overlaid against buy-and-hold, the full metrics suite, and the trade log. Multiple comma-separated tickers instead run an independent screen and show a sortable results table.

### Tests

```bash
pytest tests/
```

## How a backtest executes (no look-ahead bias)

A rule is evaluated against a bar's own (now fully-known) close/high/low/volume, but any resulting entry or exit only **executes at the next bar's open** — never at the same bar's close. Deciding and trading on the same bar's data is a common backtesting mistake: it implicitly assumes you could act on a bar before it finished forming. A signal on the very last bar of the data has no following bar to execute on, so it's simply never executed. If a position is still open when the data ends, it's marked to market at the final close purely for reporting — that valuation isn't a real trade and doesn't carry commission or slippage.

**Commission and slippage** are per-trade, configurable percentages: commission is a fee on top of the trade's notional value (it doesn't reduce share count), and slippage worsens the executed price (higher on buys, lower on sells) versus the bar's raw open. Both apply on entry and exit; `Trade.pnl` is net of commission, while `Trade.return_pct` is the gross price return.

## Supported rule phrasing

**Fields:** `close`, `open`, `high`, `low`, `volume` (also `close price` / `closing price`, etc.)

**Indicators:** `sma_20` / `20 day sma` / `20 day moving average`, `ema_50` / `50 day ema`, `rsi_14` / `14 day rsi`, `macd`, `macd signal`, `upper`/`lower bollinger band` (default period 20)

**Comparisons:** `is above` / `greater than` / `crosses above` (`>`), `is below` / `less than` / `crosses below` (`<`), `is` / `is equal to` (`==`)

**Multiple conditions:** join with `and` or `or` (mixing both in one rule isn't supported — split it into two rules, or use AI parsing)

**Prefixes** (stripped): `buy when`, `sell when`, `exit when`, `enter long when`, `purchase when`

If the regex parser can't understand a rule, check **Use AI (Gemini) to interpret the rule** in the web UI (or answer `y` in the CLI) to have Gemini interpret it instead — its output still passes through the same field/operator allowlist, so it can't produce anything the regex parser couldn't have.

## Multi-ticker screening

Enter more than one comma-separated ticker (CLI or web UI) to run the same rule across all of them. Each ticker gets its own independent backtest with its own starting capital — this is **not** portfolio backtesting (no shared capital, no correlation, no rebalancing). It answers "does this rule work here too", not "how would holding all of these together behave". A ticker with bad data or an invalid symbol is skipped with a clear message rather than failing the whole screen.

## Design notes

- **No code injection surface.** Rule text — from either parser — never gets turned into Python before being validated. It's parsed into `Condition(field, operator, value)` objects, and `Condition` rejects anything outside its field/operator allowlist. Even `codegen.py`, which writes an actual `.py` file, only ever reconstructs the same validated `Rule` object and calls the real backtest engine — it doesn't reimplement the loop, so it can't silently drift out of sync with it.
- **Position sizing** commits a configurable fraction of available cash to each new entry and compounds — win streaks grow position size, losses shrink it.
- **Backtests are long-only, single-position.** An open position at the end of the window is closed at the last bar's price so metrics reflect the full period.

## What's next

This is scaling from a personal script into a real product. Worth discussing before building further:

- **Data provider**: yfinance is fine for prototyping but rate-limits and has gaps. A paid provider (Polygon, Alpaca, Tiingo) is the next step once this needs to be reliable — that requires an account and API keys on your end.
- **Full portfolio backtesting**: today's multi-ticker screen runs each ticker in isolation; shared capital, correlation, and rebalancing across positions is a bigger architectural change.
- **Out-of-sample testing**: a train/test date split to catch strategies that are overfit to one period.
- **More indicators & strategy composition**: stop-loss/take-profit rules, trailing stops.
- **Persistence**: saving strategies and backtest runs somewhere other than a local file (a database) once this has users.
- **Auth & hosting**: if this becomes a hosted web product rather than something run locally.
