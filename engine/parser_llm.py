"""Claude-powered rule parser.

Claude only ever returns a validated RuleSchema (via structured
outputs) describing fields/operators/values in plain text — it never
generates Python or any other executable code. Every value it returns
still passes through the exact same allowlist as the regex parser
(engine.conditions.Condition validation), so a prompt-injected or
hallucinated field name is rejected the same way a malicious typed
rule would be. This function raises on any failure (missing
dependency, missing/invalid API key, network error, invalid model
output) — callers should catch and fall back to the regex parser.
"""
import os
from typing import List, Literal, Optional, Union

from pydantic import BaseModel

from engine.conditions import Condition, ConditionGroup, Rule
from engine.parser_regex import resolve_field_or_number

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")

SYSTEM_PROMPT = """You translate a plain-English trading rule into a structured comparison.

Allowed left/right field tokens (case-sensitive, use exactly these forms):
- Price/volume fields: close, open, high, low, volume
- Simple moving average: sma_N (e.g. sma_20 for a 20-period SMA)
- Exponential moving average: ema_N (e.g. ema_50)
- Relative strength index: rsi_N (e.g. rsi_14)
- MACD line: macd
- MACD signal line: macd_signal
- Bollinger bands: bb_upper_N, bb_lower_N (default N=20 if unspecified)

A condition's "right" side may instead be a plain number (as a JSON number, not a string).

Allowed operators: >, <, >=, <=, ==, !=

A rule can combine multiple conditions with a single logic operator, either "and" or
"or" (never mix both in one rule — if the rule text mixes them, pick the operator
that best captures the user's intent). If the rule text does not clearly map to this
schema, do your best to extract the closest reasonable interpretation."""


class ConditionSchema(BaseModel):
    left: str
    operator: Literal[">", "<", ">=", "<=", "==", "!="]
    right: Union[str, float]


class RuleSchema(BaseModel):
    logic: Literal["and", "or"]
    conditions: List[ConditionSchema]


def _to_condition_group(schema: RuleSchema) -> ConditionGroup:
    conditions = [
        Condition(
            resolve_field_or_number(str(c.left)) if isinstance(c.left, str) else c.left,
            c.operator,
            resolve_field_or_number(str(c.right)) if isinstance(c.right, str) else c.right,
        )
        for c in schema.conditions
    ]
    return ConditionGroup(conditions=conditions, logic=schema.logic)


def parse_condition_group_with_llm(text: str, model: Optional[str] = None) -> ConditionGroup:
    import anthropic  # imported lazily so the regex-only path never requires the package

    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=model or DEFAULT_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
        output_format=RuleSchema,
    )
    return _to_condition_group(response.parsed_output)


def parse_rule_with_llm(entry_text: str, exit_text: Optional[str] = None, model: Optional[str] = None) -> Rule:
    entry = parse_condition_group_with_llm(entry_text, model=model)
    exit_group = parse_condition_group_with_llm(exit_text, model=model) if exit_text and exit_text.strip() else None
    return Rule(entry=entry, exit=exit_group)
