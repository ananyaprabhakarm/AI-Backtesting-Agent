import pandas as pd
import pytest

from engine.indicators import compute_indicators


def test_sma():
    df = pd.DataFrame({"close": [10, 11, 12, 13, 14]})
    out = compute_indicators(df, {"sma_3"})
    assert out["sma_3"].iloc[-1] == pytest.approx((12 + 13 + 14) / 3)
    assert pd.isna(out["sma_3"].iloc[0])


def test_rsi_all_gains_saturates_at_100():
    df = pd.DataFrame({"close": list(range(1, 20))})
    out = compute_indicators(df, {"rsi_5"})
    assert out["rsi_5"].iloc[-1] == 100.0


def test_rsi_all_losses_hits_zero():
    df = pd.DataFrame({"close": list(range(20, 1, -1))})
    out = compute_indicators(df, {"rsi_5"})
    assert out["rsi_5"].iloc[-1] == 0.0


def test_rsi_flat_price_is_neutral():
    df = pd.DataFrame({"close": [10.0] * 10})
    out = compute_indicators(df, {"rsi_3"})
    assert out["rsi_3"].iloc[-1] == 50.0


def test_bollinger_bands_bracket_sma():
    df = pd.DataFrame({"close": [10, 12, 11, 13, 12, 14, 13, 15]})
    out = compute_indicators(df, {"bb_upper_4", "bb_lower_4", "sma_4"})
    last = out.iloc[-1]
    assert last["bb_lower_4"] < last["sma_4"] < last["bb_upper_4"]


def test_unknown_indicator_raises():
    df = pd.DataFrame({"close": [1, 2, 3]})
    with pytest.raises(ValueError):
        compute_indicators(df, {"not_a_real_indicator"})
