import pandas as pd
import pytest

import data_engine as data_engine_module
from engine.backtest import run_backtest
from engine.codegen import generate_script
from engine.conditions import Condition, ConditionGroup, Rule
from engine.metrics import compute_metrics


def make_df(closes):
    dates = pd.date_range("2024-01-01", periods=len(closes))
    return pd.DataFrame({
        "date": dates, "close": closes, "open": closes, "high": closes, "low": closes,
        "volume": [1000] * len(closes),
    })


def test_generated_script_is_syntactically_valid():
    rule = Rule(entry=ConditionGroup(conditions=[Condition("close", ">", 9.0)], logic="and"), exit=None)
    script = generate_script(rule)
    compile(script, "<generated_strategy>", "exec")  # raises SyntaxError if malformed


def test_generated_script_matches_direct_backtest_call(monkeypatch, capsys):
    rule = Rule(
        entry=ConditionGroup(conditions=[Condition("close", ">", 9.0)], logic="and"),
        exit=ConditionGroup(conditions=[Condition("close", "<", 10.0)], logic="and"),
    )
    script = generate_script(rule, initial_capital=1000, position_size_pct=0.5, commission_pct=0.01, slippage_pct=0.005)
    compiled = compile(script, "<generated_strategy>", "exec")

    fake_df = make_df([9, 11, 12, 13, 9, 14])
    monkeypatch.setattr(data_engine_module, "fetch_historical_data", lambda *a, **k: fake_df)

    inputs = iter(["FAKE", "2024-01-01", "2024-01-10", "1d"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    exec(compiled, {"__name__": "__main__"})
    captured = capsys.readouterr().out

    direct_result = run_backtest(
        fake_df.copy(), rule, initial_capital=1000, position_size_pct=0.5,
        commission_pct=0.01, slippage_pct=0.005,
    )
    direct_metrics = compute_metrics(direct_result, df=fake_df.copy())

    assert f"Total trades:      {direct_metrics.num_trades}" in captured
    assert f"Total return:      {direct_metrics.total_return_pct:.2f}%" in captured
    assert f"Sharpe ratio:      {direct_metrics.sharpe_ratio:.2f}" in captured
    assert f"Sortino ratio:     {direct_metrics.sortino_ratio:.2f}" in captured
    assert f"Calmar ratio:      {direct_metrics.calmar_ratio:.2f}" in captured
    for t in direct_result.trades:
        assert f"P&L: {t.pnl:.2f}" in captured


def test_generated_script_renders_exit_rule_as_none_when_absent():
    rule = Rule(entry=ConditionGroup(conditions=[Condition("close", ">", 9.0)], logic="and"), exit=None)
    script = generate_script(rule)
    assert "exit=None" in script
