"""The plain-Python universal Turing machine in examples/utm_table.py."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "utm_table", Path(__file__).resolve().parent.parent / "examples" / "utm_table.py")
utm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utm)


@pytest.mark.parametrize("name, sim_steps, ones", [("beaver", 6, 4), ("beaver3", 14, 6)])
def test_busy_beavers(name, sim_steps, ones):
    start, table = utm.MACHINES[name]
    steps, utm_steps = utm.compare(start, table)  # asserts every step matches
    assert steps == sim_steps
    tape, origin, states = utm.encode(start, table)
    final, _ = utm.run_utm(tape)
    state, _, values = utm.decode(final, origin, states)
    assert state == "H" and sum(values.values()) == ones


def test_random_machines():
    assert utm.self_test(n=150, seed=7) == 150


def test_generated_jevlang_rules_compile():
    import ast
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import utm_jev
    from jevlang import transform

    source = utm_jev.jevlang_source()
    ast.parse(transform(source))
    assert source.count("def rule_") == len(utm.RULES)
    assert "case reading a zero, a one, an L, an R or a v:" in source
