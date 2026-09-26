"""The real backend, driven through the TypeSafe SDK with a mocked transport."""

import json
import textwrap

import pytest

pytest.importorskip("typesafe_sdk")
import httpx2
from typesafe_sdk import TypeSafeClient

import jevlang
from jevlang import runtime
from jevlang.backends import Jev


class FakeAPI:
    """Answers /v1/systemone requests from a list of canned answers."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def __call__(self, request):
        body = json.loads(request.content)
        self.requests.append((request, body))
        answer = self.answers.pop(0)
        return httpx2.Response(200, json={
            "model": "jev-1.13.0",
            "answers": {"decision": answer},
            "usage": {"input_tokens": 100, "output_tokens": 10},
        })

    def backend(self, **kw):
        client = TypeSafeClient(api_key="test-key", transport=httpx2.MockTransport(self))
        return Jev(client=client, **kw)


def noul(p):
    return {"type": "noul", "noul": p}


def choice(label, p=0.9):
    return {"type": "choice", "choice": label, "probabilities": {label: p}, "confidence": p}


@pytest.fixture
def run(tmp_path):
    def run(source, api):
        runtime.set_backend(api.backend())
        jevlang.register()
        path = tmp_path / "mod.py"
        path.write_text("# coding: jevlang\n" + textwrap.dedent(source))
        ns = {"__file__": str(path), "__name__": "mod"}
        try:
            exec(compile(path.read_bytes(), str(path), "exec"), ns)
        finally:
            runtime.set_backend(None)
        return ns
    return run


def test_while_loop_asks_a_noul_each_iteration(run):
    api = FakeAPI(noul(0.97), noul(0.91), noul(0.03))
    ns = run("""\
        bottles = 2
        while there are bottles left:
            bottles -= 1
        """, api)
    assert ns["bottles"] == 0
    assert len(api.requests) == 3

    request, body = api.requests[1]
    assert request.url.path == "/v1/systemone"
    assert request.headers["authorization"] == "Bearer test-key"
    question = body["questions"]["decision"]
    assert question["type"] == "noul"
    assert question["instructions"]["condition"] == "there are bottles left"
    state = body["state"]
    assert state["variables"] == {"bottles": 1}
    assert state["line"] == 3
    assert state["times_this_line_was_evaluated_before"] == 1
    assert "--> 3 | while there are bottles left:" in state["source"]


def test_match_asks_a_choice_and_binds_captures(run):
    api = FakeAPI(choice("case_1"))
    ns = run("""\
        point = (3, 4)
        match point:
            case (0, 0):
                where = "origin"
            case (x, y) if it looks far away:
                where = f"far: {x},{y}"
        """, api)
    assert ns["where"] == "far: 3,4"
    _, body = api.requests[0]
    q = body["questions"]["decision"]
    assert q["type"] == "choice"
    assert q["criteria"] == {
        "case_0": "case (0, 0)",
        "case_1": "case (x, y) if it looks far away",
        "none": "None of the cases apply.",
    }
    assert body["state"]["match_subject"] == {"text": "point", "value": [3, 4]}


def test_match_none_runs_no_case(run):
    ns = run("""\
        hit = False
        match the mood:
            case happy:
                hit = True
        """, FakeAPI(choice("none")))
    assert ns["hit"] is False


def test_threshold_and_local_python():
    api = FakeAPI(noul(0.6))
    jev = api.backend(threshold=0.7, local_python=True)
    req = runtime.Request(kind="if", text="n > 1", is_python=True, variables={"n": 2},
                          code="", filename="t", lineno=1, globals={"n": 2}, locals={})
    assert jev.decide(req).value is True and api.requests == []  # evaluated locally
    req.text, req.is_python = "n feels big", False
    d = jev.decide(req)
    assert d.value is False and d.confidence == pytest.approx(0.2)


def test_state_is_json_safe():
    class Thing:
        pass

    req = runtime.Request(kind="if", text="x", is_python=False, code="", filename="t", lineno=1,
                          variables={"t": Thing(), "f": float("nan"), "xs": list(range(100)),
                                     "d": {1: (2, 3)}})
    state = req.state()
    json.dumps(state)
    assert state["variables"]["d"] == {"1": [2, 3]}
    assert state["variables"]["f"] == "nan"
    assert state["variables"]["t"].startswith("<")


def test_openrouter_is_used_without_a_typesafe_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("JEVLANG_MODEL", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    assert Jev.default_options() == {
        "api_key": "sk-or-test",
        "base_url": "https://openrouter.ai/api",
        "model": "~typesafe/jev-latest",
    }
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-test")
    assert Jev.default_options() == {}  # the SDK's own defaults win
    monkeypatch.setenv("JEVLANG_MODEL", "jev-1.13")
    assert Jev.default_options() == {"model": "jev-1.13"}


def test_catch_all_case_replaces_none_option():
    req = runtime.Request(kind="match", text="cmd", is_python=True, variables={}, code="",
                          filename="t", lineno=1, subject="dance",
                          cases=[("going somewhere", None), ("_", []), ("unreachable", None)])
    criteria = Jev.question(req).criteria
    assert criteria == {"case_0": "case going somewhere",
                        "case_1": "Anything else: none of the other cases fit."}
