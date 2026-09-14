import pytest

from engine.parser_regex import parse_condition_group, parse_rule


def cond_tuples(group):
    return [(c.left, c.operator, c.right) for c in group.conditions]


@pytest.mark.parametrize("rule,expected_logic,expected", [
    ("Buy when close > open", "and", [("close", ">", "open")]),
    ("buy when close price is greater than open price", "and", [("close", ">", "open")]),
    ("buy when close crosses above open", "and", [("close", ">", "open")]),
    ("buy when volume crosses below 1000000", "and", [("volume", "<", 1000000.0)]),
    ("buy when close is above 40", "and", [("close", ">", 40.0)]),
    ("buy when closing price is greater than 100", "and", [("close", ">", 100.0)]),
    ("buy when close is above 20 day sma", "and", [("close", ">", "sma_20")]),
    ("sell when close is below the 50 day moving average", "and", [("close", "<", "sma_50")]),
    ("buy when macd is above macd_signal", "and", [("macd", ">", "macd_signal")]),
    ("buy when close is above upper bollinger band", "and", [("close", ">", "bb_upper_20")]),
    (
        "buy when close crosses above sma_20 and volume is above 1000000",
        "and",
        [("close", ">", "sma_20"), ("volume", ">", 1000000.0)],
    ),
    (
        "buy when rsi_14 is below 30 or close is below ema_50",
        "or",
        [("rsi_14", "<", 30.0), ("close", "<", "ema_50")],
    ),
])
def test_parses_expected_conditions(rule, expected_logic, expected):
    group = parse_condition_group(rule)
    assert group.logic == expected_logic
    assert cond_tuples(group) == expected


def test_unparseable_rule_raises():
    with pytest.raises(ValueError):
        parse_condition_group("buy when this stock is rising")


def test_mixed_and_or_rejected():
    with pytest.raises(ValueError):
        parse_condition_group("buy when close is above sma_20 and volume is above 1000000 or high is above 500")


def test_injection_attempt_rejected():
    with pytest.raises(ValueError):
        parse_condition_group("buy when close > 1 or __import__('os').system('echo pwned')")


def test_parse_rule_with_explicit_exit():
    rule = parse_rule("buy when close crosses above sma_20", "sell when close crosses below sma_20")
    assert cond_tuples(rule.entry) == [("close", ">", "sma_20")]
    assert cond_tuples(rule.exit) == [("close", "<", "sma_20")]


def test_parse_rule_without_exit():
    rule = parse_rule("buy when close is above 40")
    assert rule.exit is None
