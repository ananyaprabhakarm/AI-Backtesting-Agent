"""Structured, allowlisted representation of a strategy rule.

Both parsers (regex-based and Gemini-based) must produce Condition
objects that pass validate(). Nothing downstream ever executes
free-form text: the backtest engine evaluates Conditions directly in
Python, and the standalone-script renderer only ever emits
`row['<allowlisted field>'] <allowlisted op> <allowlisted field or number>`.
This is what keeps a crafted rule string from being able to inject
arbitrary code into either the running process or the generated file.
"""
from dataclasses import dataclass
from typing import List, Union

from engine.indicators import is_indicator_token

BASE_FIELDS = {"close", "open", "high", "low", "volume"}

OPERATORS = {">", "<", ">=", "<=", "==", "!="}

import operator as _operator

OPERATOR_FUNCS = {
    ">": _operator.gt,
    "<": _operator.lt,
    ">=": _operator.ge,
    "<=": _operator.le,
    "==": _operator.eq,
    "!=": _operator.ne,
}


def is_allowed_field(name: str) -> bool:
    return name in BASE_FIELDS or is_indicator_token(name)


@dataclass(frozen=True)
class Condition:
    left: str
    operator: str
    right: Union[str, float]

    def __post_init__(self):
        if not is_allowed_field(self.left):
            raise ValueError(f"Unknown field on left side of condition: '{self.left}'")
        if self.operator not in OPERATORS:
            raise ValueError(f"Unsupported operator: '{self.operator}'")
        if isinstance(self.right, str):
            if not is_allowed_field(self.right):
                raise ValueError(f"Unknown field on right side of condition: '{self.right}'")
        elif not isinstance(self.right, (int, float)):
            raise ValueError(f"Condition value must be a field name or a number, got {self.right!r}")

    def fields(self):
        fields = {self.left}
        if isinstance(self.right, str):
            fields.add(self.right)
        return fields

    def evaluate(self, row) -> bool:
        left_val = row[self.left]
        right_val = row[self.right] if isinstance(self.right, str) else self.right
        return OPERATOR_FUNCS[self.operator](left_val, right_val)

    def render(self) -> str:
        right = f"row['{self.right}']" if isinstance(self.right, str) else repr(float(self.right))
        return f"row['{self.left}'] {self.operator} {right}"


@dataclass(frozen=True)
class ConditionGroup:
    conditions: List[Condition]
    logic: str = "and"

    def __post_init__(self):
        if not self.conditions:
            raise ValueError("A condition group needs at least one condition")
        if self.logic not in ("and", "or"):
            raise ValueError(f"Unsupported logic operator: '{self.logic}'")

    def fields(self):
        fields = set()
        for c in self.conditions:
            fields |= c.fields()
        return fields

    def evaluate(self, row) -> bool:
        results = (c.evaluate(row) for c in self.conditions)
        return all(results) if self.logic == "and" else any(results)

    def render(self) -> str:
        joiner = " and " if self.logic == "and" else " or "
        return joiner.join(c.render() for c in self.conditions)


@dataclass(frozen=True)
class Rule:
    entry: ConditionGroup
    exit: Union[ConditionGroup, None] = None

    def fields(self):
        fields = self.entry.fields()
        if self.exit is not None:
            fields |= self.exit.fields()
        return fields

    def indicators_needed(self):
        return {f for f in self.fields() if is_indicator_token(f)}
