import pytest

from jevlang import runtime


@pytest.fixture(autouse=True)
def fresh_call_budget(monkeypatch):
    monkeypatch.setattr(runtime, "calls_made", 0)
