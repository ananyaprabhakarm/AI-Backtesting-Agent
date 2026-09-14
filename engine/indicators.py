"""Technical indicator calculations.

Indicator columns are computed on demand based on which tokens a parsed
rule actually references (see conditions.indicators_needed), so a
backtest only pays for the indicators it uses.
"""
import re

import pandas as pd

SMA_RE = re.compile(r'^sma_(\d{1,4})$')
EMA_RE = re.compile(r'^ema_(\d{1,4})$')
RSI_RE = re.compile(r'^rsi_(\d{1,4})$')
BB_RE = re.compile(r'^bb_(upper|lower)_(\d{1,4})$')
MACD_TOKENS = {"macd", "macd_signal"}

INDICATOR_TOKEN_RE = re.compile(
    r'^(sma_\d{1,4}|ema_\d{1,4}|rsi_\d{1,4}|bb_(?:upper|lower)_\d{1,4}|macd|macd_signal)$'
)


def is_indicator_token(token: str) -> bool:
    return bool(INDICATOR_TOKEN_RE.match(token))


def _sma(df, period):
    return df['close'].rolling(window=period, min_periods=period).mean()


def _ema(df, period):
    return df['close'].ewm(span=period, adjust=False).mean()


def _rsi(df, period):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, float('nan'))
    rsi = (100 - (100 / (1 + rs))).astype(float)
    rsi[(avg_gain == 0) & (avg_loss == 0)] = 50.0  # no movement at all: neutral
    rsi[(avg_gain > 0) & (avg_loss == 0)] = 100.0  # only gains in the window
    rsi[(avg_gain == 0) & (avg_loss > 0)] = 0.0    # only losses in the window
    return rsi


def _macd_line(df):
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    return ema12 - ema26


def _macd_signal(df):
    return _macd_line(df).ewm(span=9, adjust=False).mean()


def _bollinger(df, period):
    sma = _sma(df, period)
    std = df['close'].rolling(window=period, min_periods=period).std()
    return sma + 2 * std, sma - 2 * std


def compute_indicators(df: pd.DataFrame, tokens) -> pd.DataFrame:
    """Return a copy of df with one column added per requested indicator token."""
    df = df.copy()

    for token in tokens:
        if token in df.columns:
            continue

        m = SMA_RE.match(token)
        if m:
            df[token] = _sma(df, int(m.group(1)))
            continue

        m = EMA_RE.match(token)
        if m:
            df[token] = _ema(df, int(m.group(1)))
            continue

        m = RSI_RE.match(token)
        if m:
            df[token] = _rsi(df, int(m.group(1)))
            continue

        m = BB_RE.match(token)
        if m:
            side, period = m.group(1), int(m.group(2))
            upper_col, lower_col = f'bb_upper_{period}', f'bb_lower_{period}'
            if upper_col not in df.columns or lower_col not in df.columns:
                upper, lower = _bollinger(df, period)
                df[upper_col] = upper
                df[lower_col] = lower
            continue

        if token == "macd":
            df["macd"] = _macd_line(df)
            continue

        if token == "macd_signal":
            df["macd_signal"] = _macd_signal(df)
            continue

        raise ValueError(f"Unknown indicator token: '{token}'")

    return df
