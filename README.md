# AI Backtesting Agent

Turns a plain-English trading rule into a runnable Python backtest against real historical stock data.

```
Enter your strategy rule: Buy when close is above 40
```

...generates a standalone script (`generated_strategy.py`) that pulls historical prices for a ticker you choose and prints buy/sell signals wherever your rule triggers.

## How it works

- [agent.py](agent.py) — reads your rule, translates it into a Python condition, and writes `generated_strategy.py`
- [data_engine.py](data_engine.py) — fetches historical OHLCV data from Yahoo Finance via `yfinance`
- `generated_strategy.py` — auto-generated each time you run the agent; not meant to be hand-edited

## Setup

Requires Python 3.9+.

```bash
git clone https://github.com/ananyaprabhakarm/AI-Backtesting-Agent.git
cd AI-Backtesting-Agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

**Step 1 — generate a strategy from a rule:**

```bash
python agent.py
```

```
Enter your strategy rule: Buy when close price crosses above open price
```

**Step 2 — run the generated backtest:**

```bash
python generated_strategy.py
```

```
Enter stock ticker (e.g., AAPL, NVDA, SPY): AAPL
Enter start date (YYYY-MM-DD): 2024-01-01
Enter end date (YYYY-MM-DD): 2024-02-01
Enter timeframe (e.g., 1d for daily, 1h for hourly): 1d

BUY SIGNAL at 2024-01-03 00:00:00 | Price: 182.03
SELL SIGNAL at 2024-01-04 00:00:00 | Price: 179.72
...

=== Backtest Summary ===
Total signals generated: 6
```

## Supported rule phrasing

The translator recognizes:

- **Fields:** `close`/`close price`, `open`/`open price`, `high`/`high price`, `low`/`low price`, `volume`
- **Comparisons:** `is above` / `greater than` / `crosses above` (`>`), `is below` / `less than` / `crosses below` (`<`), `is` / `is equal to` (`==`)
- **Prefixes** (stripped): `buy when`, `enter long when`, `purchase when`
- Or write conditions directly with symbols, e.g. `close > open`

If a rule can't be parsed into a comparison, the agent reports an error instead of generating a broken script.

## Roadmap

This is being scaled up from a personal script into a proper product. Next up: a real strategy engine (indicators, multi-condition rules, position sizing), performance metrics (P&L, Sharpe, drawdown) instead of raw signal prints, and a web UI.
