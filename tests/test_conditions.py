import pytest

from engine.conditions import Condition, ConditionGroup


def test_condition_rejects_unknown_field():
    with pytest.raises(ValueError):
        Condition("os.system('x')", ">", 1)


def test_condition_rejects_unknown_operator():
    with pytest.raises(ValueError):
        Condition("close", "<>", 1)


def test_condition_rejects_non_numeric_non_field_value():
    with pytest.raises(ValueError):
        Condition("close", ">", "not_a_field")


def test_condition_accepts_indicator_tokens():
    c = Condition("sma_20", "<", "ema_50")
    assert c.left == "sma_20" and c.right == "ema_50"


def test_condition_render_is_safe_text():
    c = Condition("close", ">", 40)
    assert c.render() == "row['close'] > 40.0"


def test_condition_group_requires_at_least_one_condition():
    with pytest.raises(ValueError):
        ConditionGroup(conditions=[])


def test_condition_group_evaluate_and():
    group = ConditionGroup(conditions=[Condition("close", ">", 1), Condition("close", "<", 100)], logic="and")
    assert group.evaluate({"close": 50}) is True
    assert group.evaluate({"close": 200}) is False


def test_condition_group_evaluate_or():
    group = ConditionGroup(conditions=[Condition("close", ">", 100), Condition("volume", ">", 1000)], logic="or")
    assert group.evaluate({"close": 1, "volume": 5000}) is True
    assert group.evaluate({"close": 1, "volume": 1}) is False
