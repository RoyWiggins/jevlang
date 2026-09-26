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


def test_http_payload_shape(monkeypatch):
    from jevlang.backends import JevHTTP

    sent = []
    client = JevHTTP(api_key="test")
    monkeypatch.setattr(client, "post", lambda p: sent.append(p) or {"answer": True, "confidence": 0.97})
    d = client.decide(request("while", "there are bottles left", {"bottles": 3}))
    assert (d.value, d.confidence) == (True, 0.97)
    assert sent[0]["schema"] == {"answer": "boolean"}
    assert "bottles = 3" in sent[0]["input"]
    assert "there are bottles left" in sent[0]["input"]
