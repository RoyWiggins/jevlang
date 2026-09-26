import pytest

from jevlang.backends import FakeJev
from jevlang.runtime import Request

jev = FakeJev()


def ask(text, **variables):
    return jev.judge(text, variables).value


@pytest.mark.parametrize(
    "text, variables, expected",
    [
        ("there are bottles left", {"bottles": 3}, True),
        ("there are bottles left", {"bottles": 0}, False),
        ("we're out of bottles", {"bottles": 0}, True),
        ("there isn't any beer", {"beer": 2}, False),
        ("the queue is empty", {"queue": []}, True),
        ("count is more than 10", {"count": 11}, True),
        ("count is at least ten", {"count": 10}, True),
        ("count is no more than 5", {"count": 6}, False),
        ("count is fewer than limit", {"count": 1, "limit": 2}, True),
        ("n is even", {"n": 4}, True),
        ("n is odd", {"n": 4}, False),
        ("the user name is set", {"user_name": ""}, False),
        ("the list has more than 2 items", {"list": [1, 2, 3]}, True),
        ("unicorns exist", {}, False),
        ("n is divisible by 3", {"n": 9}, True),
        ("n is a multiple of five", {"n": 9}, False),
        ("n is divisible by both three and five", {"n": 30}, True),
        ("n is divisible by both three and five", {"n": 9}, False),
        ("n is not a multiple of 4", {"n": 6}, True),
    ],
)
def test_judge(text, variables, expected):
    assert ask(text, **variables) is expected


def request(kind, text, variables, **kw):
    return Request(kind=kind, text=text, is_python=False, variables=variables,
                   code="", filename="t", lineno=1, globals=variables, locals={}, **kw)


def test_python_conditions_are_evaluated():
    req = request("if", "n % 3 == 0", {"n": 9})
    req.is_python = True
    assert jev.decide(req).value is True


def test_match_prefers_python_patterns_then_english():
    cases = [("0", []), ("something big", None), ("more than 100", None), ("_", [])]
    assert jev.decide(request("match", "n", {"n": 0}, subject=0, cases=cases)).value == 0
    assert jev.decide(request("match", "n", {"n": 500}, subject=500, cases=cases)).value == 2
    assert jev.decide(request("match", "n", {"n": 5}, subject=5, cases=cases)).value == 3


def test_match_english_subject_resolves_variable():
    cases = [('"snow"', []), ("rain or drizzle", None)]
    req = request("match", "the forecast", {"forecast": "rain"}, cases=cases)
    assert jev.decide(req).value == 1


def test_english_that_parses_as_python_falls_back():
    req = request("if", "x is truthy", {"x": 1})
    req.is_python = True
    assert jev.decide(req).value is True



def test_match_english_guard_is_judged():
    cases = [("[x, *rest] if there are more than 3 rest", ["x", "rest"]), ("_", [])]
    short = request("match", "xs", {}, subject=[1, 2], cases=cases)
    long = request("match", "xs", {}, subject=[1, 2, 3, 4, 5], cases=cases)
    assert jev.decide(short).value == 1
    assert jev.decide(long).value == 0
