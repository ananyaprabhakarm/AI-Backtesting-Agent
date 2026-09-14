# AI Backtesting Agent

Turns a plain-English trading rule into a backtest against real historical stock data — with technical indicators, position sizing, and performance metrics. Use it from the CLI, from a web UI, or let Gemini interpret rules that plain pattern-matching can't parse.

```
Entry rule: buy when close crosses above sma_20
```

...runs a full backtest and reports total return, win rate, max drawdown, and Sharpe ratio — plus writes a standalone, re-runnable copy of the backtest to `generated_strategy.py`.

## Architecture

- [data_engine.py](data_engine.py) — fetches historical OHLCV data from Yahoo Finance via `yfinance`
- [engine/](engine/) — the backtesting engine
  - [conditions.py](engine/conditions.py) — the `Condition`/`Rule` model. **Every rule, however it was parsed, is validated against a strict allowlist of fields, operators, and values before it can run** — this is what makes rule text safe to turn into a backtest rather than a code-injection vector
  - [indicators.py](engine/indicators.py) — SMA, EMA, RSI, MACD, Bollinger Bands, computed on demand
  - [parser_regex.py](engine/parser_regex.py) — deterministic, no-network rule parser
  - [parser_llm.py](engine/parser_llm.py) — Gemini-powered rule parser for phrasing the regex parser can't handle
  - [backtest.py](engine/backtest.py) — the single-position backtest loop with position sizing
  - [metrics.py](engine/metrics.py) — total return, win rate, max drawdown, Sharpe ratio
  - [codegen.py](engine/codegen.py) — renders a validated `Rule` into a standalone script
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

Prompts you for an entry rule, an optional exit rule, whether to use AI parsing, a ticker, a date range, a timeframe, initial capital, and position sizing — then prints the trade log and metrics, and saves `generated_strategy.py`.

### Web UI

```bash
streamlit run app.py
```

Configure your strategy in the sidebar and click **Run backtest** to see the price chart with indicator overlays and buy/sell markers, the equity curve, metrics, and the trade log.

### Tests

```bash
pytest tests/
```

## Supported rule phrasing

**Fields:** `close`, `open`, `high`, `low`, `volume` (also `close price` / `closing price`, etc.)

**Indicators:** `sma_20` / `20 day sma` / `20 day moving average`, `ema_50` / `50 day ema`, `rsi_14` / `14 day rsi`, `macd`, `macd signal`, `upper`/`lower bollinger band` (default period 20)

**Comparisons:** `is above` / `greater than` / `crosses above` (`>`), `is below` / `less than` / `crosses below` (`<`), `is` / `is equal to` (`==`)

**Multiple conditions:** join with `and` or `or` (mixing both in one rule isn't supported — split it into two rules, or use AI parsing)

**Prefixes** (stripped): `buy when`, `sell when`, `exit when`, `enter long when`, `purchase when`

If the regex parser can't understand a rule, check **Use AI (Gemini) to interpret the rule** in the web UI (or answer `y` in the CLI) to have Gemini interpret it instead — its output still passes through the same field/operator allowlist, so it can't produce anything the regex parser couldn't have.

## Design notes

- **No code injection surface.** Rule text — from either parser — never gets turned into Python before being validated. It's parsed into `Condition(field, operator, value)` objects, and `Condition` rejects anything outside its field/operator allowlist. Even `codegen.py`, which writes an actual `.py` file, only ever splices in text produced by validated `Condition.render()` calls.
- **Position sizing** commits a configurable fraction of available cash to each new entry and compounds — win streaks grow position size, losses shrink it.
- **Backtests are long-only, single-position.** An open position at the end of the window is closed at the last bar's price so metrics reflect the full period.

## What's next

This is scaling from a personal script into a real product. Worth discussing before building further:

- **Data provider**: yfinance is fine for prototyping but rate-limits and has gaps. A paid provider (Polygon, Alpaca, Tiingo) is the next step once this needs to be reliable — that requires an account and API keys on your end.
- **Multi-position / portfolio backtesting**: right now it's one position in one ticker at a time.
- **More indicators & strategy composition**: stop-loss/take-profit rules, trailing stops, multi-symbol rules.
- **Persistence**: saving strategies and backtest runs somewhere other than a local file (a database) once this has users.
- **Auth & hosting**: if this becomes a hosted web product rather than something run locally.
