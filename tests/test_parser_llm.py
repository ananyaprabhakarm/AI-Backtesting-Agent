import pytest

from engine.parser_llm import ConditionSchema, RuleSchema, _to_condition_group


def test_valid_schema_converts_to_condition_group():
    schema = RuleSchema(logic="and", conditions=[
        ConditionSchema(left="close", operator=">", right="sma_20"),
        ConditionSchema(left="volume", operator=">", right=1000000),
    ])
    group = _to_condition_group(schema)
    assert group.logic == "and"
    assert [(c.left, c.operator, c.right) for c in group.conditions] == [
        ("close", ">", "sma_20"),
        ("volume", ">", 1000000.0),
    ]


def test_schema_with_natural_phrasing_is_normalized():
    # Gemini might not perfectly canonicalize field names; the same
    # regex-based normalization used by the deterministic parser is
    # applied here too.
    schema = RuleSchema(logic="or", conditions=[
        ConditionSchema(left="closing price", operator="<", right="20 day sma"),
    ])
    group = _to_condition_group(schema)
    assert (group.conditions[0].left, group.conditions[0].operator, group.conditions[0].right) == (
        "close", "<", "sma_20",
    )


def test_hallucinated_field_is_rejected():
    # Even if the model returns something outside the allowlist, the
    # same Condition validation used by the regex parser still applies.
    schema = RuleSchema(logic="and", conditions=[
        ConditionSchema(left="close", operator=">", right="__import__('os').system('x')"),
    ])
    with pytest.raises(ValueError):
        _to_condition_group(schema)


def test_pydantic_rejects_disallowed_operator():
    with pytest.raises(ValueError):
        ConditionSchema(left="close", operator="<>", right=1)
