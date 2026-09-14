"""Deterministic, no-network parser: plain-English rule -> ConditionGroup.

Design note: operator detection works by searching a clause, in
priority order, for the FIRST matching operator phrase and splitting
there — rather than the old approach of sequentially rewriting
substrings in place. Sequential rewriting is what caused the original
bugs ("crosses above" got mangled because "above" was rewritten first).
Searching a fixed-priority list against the untouched clause text
avoids that whole class of ordering bug.
"""
import re
from typing import Optional

from engine.conditions import Condition, ConditionGroup, Rule, is_allowed_field

PREFIX_RE = re.compile(
    r'^(buy when|sell when|exit when|enter long when|purchase when|close position when)\s*'
)

FIELD_PHRASES = {
    "close price": "close",
    "closing price": "close",
    "close": "close",
    "open price": "open",
    "open": "open",
    "high price": "high",
    "high": "high",
    "low price": "low",
    "low": "low",
    "volume": "volume",
}

# Ordered by priority: longer/more specific phrases first, so a later,
# more general pattern (like "above") never gets a chance to match a
# substring of an earlier, more specific one (like "crosses above").
OPERATOR_PATTERNS = [
    ("crosses above", ">"),
    ("crosses below", "<"),
    ("is greater than", ">"),
    ("is more than", ">"),
    ("is above", ">"),
    ("greater than", ">"),
    ("above", ">"),
    ("is less than", "<"),
    ("is below", "<"),
    ("less than", "<"),
    ("below", "<"),
    ("is equal to", "=="),
    ("equals to", "=="),
    (">=", ">="),
    ("<=", "<="),
    ("==", "=="),
    ("!=", "!="),
    (">", ">"),
    ("<", "<"),
    ("is", "=="),
]

_INDICATOR_FIELD_PATTERNS = [
    (re.compile(r'^(\d{1,4})[\s-]*day[\s-]*sma$'), lambda m: f"sma_{m.group(1)}"),
    (re.compile(r'^sma[\s_-]*(\d{1,4})$'), lambda m: f"sma_{m.group(1)}"),
    (re.compile(r'^(\d{1,4})[\s-]*day[\s-]*ema$'), lambda m: f"ema_{m.group(1)}"),
    (re.compile(r'^ema[\s_-]*(\d{1,4})$'), lambda m: f"ema_{m.group(1)}"),
    (re.compile(r'^(\d{1,4})[\s-]*day[\s-]*rsi$'), lambda m: f"rsi_{m.group(1)}"),
    (re.compile(r'^rsi[\s_-]*(\d{1,4})$'), lambda m: f"rsi_{m.group(1)}"),
    (re.compile(r'^(\d{1,4})[\s-]*day[\s-]*moving[\s-]*average$'), lambda m: f"sma_{m.group(1)}"),
    (re.compile(r'^moving[\s-]*average$'), lambda m: "sma_20"),
    (re.compile(r'^macd[\s_-]*signal$'), lambda m: "macd_signal"),
    (re.compile(r'^macd$'), lambda m: "macd"),
    (re.compile(r'^(\d{1,4})[\s-]*day[\s-]*bollinger[\s-]*upper[\s-]*band$'), lambda m: f"bb_upper_{m.group(1)}"),
    (re.compile(r'^bollinger[\s-]*upper[\s-]*band$'), lambda m: "bb_upper_20"),
    (re.compile(r'^upper[\s-]*bollinger[\s-]*band$'), lambda m: "bb_upper_20"),
    (re.compile(r'^(\d{1,4})[\s-]*day[\s-]*bollinger[\s-]*lower[\s-]*band$'), lambda m: f"bb_lower_{m.group(1)}"),
    (re.compile(r'^bollinger[\s-]*lower[\s-]*band$'), lambda m: "bb_lower_20"),
    (re.compile(r'^lower[\s-]*bollinger[\s-]*band$'), lambda m: "bb_lower_20"),
]


def _canonicalize_field_text(text: str) -> str:
    for pattern, build in _INDICATOR_FIELD_PATTERNS:
        m = pattern.match(text)
        if m:
            return build(m)
    return text


def resolve_field_or_number(text: str):
    text = text.strip()
    canonical = _canonicalize_field_text(text)
    if canonical in FIELD_PHRASES:
        return FIELD_PHRASES[canonical]
    if is_allowed_field(canonical):
        return canonical
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"Could not understand '{text}' as a price field, indicator, or number")


def _parse_clause(clause: str) -> Condition:
    for phrase, op in OPERATOR_PATTERNS:
        regex = r'\b' + re.escape(phrase) + r'\b' if phrase[0].isalpha() else re.escape(phrase)
        m = re.search(regex, clause)
        if not m:
            continue
        left_text = clause[:m.start()].strip()
        right_text = clause[m.end():].strip()
        if not left_text or not right_text:
            continue
        return Condition(resolve_field_or_number(left_text), op, resolve_field_or_number(right_text))
    raise ValueError(f"Could not find a comparison operator in: '{clause}'")


def parse_condition_group(text: str) -> ConditionGroup:
    text = text.lower()
    text = re.sub(r'\bthe\b', ' ', text)
    text = re.sub(r'\s*([<>=!]+)\s*', r' \1 ', text).strip()
    text = PREFIX_RE.sub('', text)
    text = ' '.join(text.split())

    if not text:
        raise ValueError("Rule is empty")

    has_and = re.search(r'\band\b', text) is not None
    has_or = re.search(r'\bor\b', text) is not None
    if has_and and has_or:
        raise ValueError("Rule mixes 'and' and 'or' — please use only one logic operator per rule")

    if has_and:
        logic, clause_texts = "and", re.split(r'\band\b', text)
    elif has_or:
        logic, clause_texts = "or", re.split(r'\bor\b', text)
    else:
        logic, clause_texts = "and", [text]

    conditions = [_parse_clause(c.strip()) for c in clause_texts if c.strip()]
    if not conditions:
        raise ValueError(f"Could not find any condition in rule: '{text}'")
    return ConditionGroup(conditions=conditions, logic=logic)


def parse_rule(entry_text: str, exit_text: Optional[str] = None) -> Rule:
    entry = parse_condition_group(entry_text)
    exit_group = parse_condition_group(exit_text) if exit_text and exit_text.strip() else None
    return Rule(entry=entry, exit=exit_group)
