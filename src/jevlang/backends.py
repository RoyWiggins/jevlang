"""Decision backends.

A backend is any object with ``decide(request: Request) -> Decision``.

* :class:`FakeJev` -- offline stand-in.  Evaluates real Python directly and
  uses a handful of keyword heuristics for English ("there are bottles
  left", "x is more than 10", "the list is empty", ...).
* :class:`AskJev`  -- prints the request and lets *you* be Jev.
* :class:`JevHTTP` -- the real thing, via ``POST /v1/decide``.  Untested:
  written against the example on https://jevai.net/ while waiting for a key.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
import urllib.request
from typing import Any

from .runtime import NOVALUE, Decision, Request, try_pattern

__all__ = ["FakeJev", "AskJev", "JevHTTP", "by_name"]


def by_name(name: str):
    """Build a backend from a name: ``fake``, ``ask``, ``http`` or
    ``package.module:factory``."""
    if ":" in name:
        mod, _, attr = name.partition(":")
        return getattr(importlib.import_module(mod), attr)()
    try:
        return {"fake": FakeJev, "ask": AskJev, "http": JevHTTP}[name.lower()]()
    except KeyError:
        raise ValueError(f"unknown JEV_BACKEND {name!r} (try fake, ask or http)") from None


# --------------------------------------------------------------------------
# FakeJev

NUMBER_WORDS = {
    w: i
    for i, w in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve "
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
    )
}
NUMBER_WORDS.update(thirty=30, forty=40, fifty=50, sixty=60, seventy=70,
                    eighty=80, ninety=90, hundred=100, thousand=1000, dozen=12)

NEGATIONS = {"no", "not", "none", "never", "nothing", "nobody", "empty",
             "zero", "without", "out", "neither", "nor", "nowhere"}

_NUM = r"(-?\d+(?:\.\d+)?|" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)) + r")\b"

# Checked in order; the first hit wins.  Phrases are removed from the text
# before counting negations, so "no more than" isn't read as a "no".
COMPARATORS = [
    (r"\bat least\b|\bno (?:less|fewer) than\b", ">="),
    (r"\bat most\b|\bno more than\b|\bup to\b", "<="),
    (r"\b(?:more|greater|bigger|larger|higher|longer|hotter|warmer|older) than\b|\bover\b|\babove\b|\bexceeds?\b", ">"),
    (r"\b(?:less|fewer|smaller|lower|shorter|colder|cooler|younger) than\b|\bunder\b|\bbelow\b", "<"),
    (r"\bexactly\b|\bequals?(?: to)?\b|\bis\b(?= +" + _NUM + r")", "=="),
]

OPS = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}

PREDICATES = {
    "even": lambda v: v % 2 == 0,
    "odd": lambda v: v % 2 == 1,
    "positive": lambda v: v > 0,
    "negative": lambda v: v < 0,
}


def _parse_number(tok: str) -> float | int:
    if tok in NUMBER_WORDS:
        return NUMBER_WORDS[tok]
    return float(tok) if "." in tok else int(tok)


def _name_forms(name: str) -> list[str]:
    base = name.lower()
    forms = {base, base.replace("_", " ")}
    for f in list(forms):
        forms.add(f[:-1] if f.endswith("s") and len(f) > 1 else f + "s")
    return sorted(forms, key=len, reverse=True)


def _mentions(text: str, variables: dict[str, Any]) -> list[tuple[int, int, str]]:
    """``(start, end, name)`` for each variable mentioned in ``text``."""
    found = []
    for name in variables:
        for form in _name_forms(name):
            m = re.search(rf"(?<![\w]){re.escape(form)}(?![\w])", text)
            if m:
                found.append((m.start(), m.end(), name))
                break
    return sorted(found)


class FakeJev:
    """A deterministic, offline, deeply unintelligent Jev."""

    def decide(self, req: Request) -> Decision:
        if req.kind == "match":
            return self.match(req)
        if req.is_python:
            try:
                value = eval(req.text, req.globals, req.locals)
            except NameError:
                pass  # English that happens to parse, like "x is truthy"
            else:
                return Decision(bool(value), 1.0, "python")
        return self.judge(req.text, req.variables)

    # -- conditions ------------------------------------------------------

    def judge(self, text: str, variables: dict[str, Any], subject: Any = NOVALUE) -> Decision:
        low = " " + re.sub(r"n't\b", " not", text.lower()) + " "
        mentions = _mentions(low, variables)

        if mentions:
            _, _, name = mentions[0]
            value, why = variables[name], name
        elif subject is not NOVALUE:
            value, why = subject, "subject"
        else:
            return Decision(False, 0.5, "no idea what that refers to")

        # Blank out variable names so they don't count as negations or numbers.
        scrubbed = low
        for start, end, _ in mentions:
            scrubbed = scrubbed[:start] + " " * (end - start) + scrubbed[end:]

        result, reason = None, None
        for pattern, op in COMPARATORS:
            m = re.search(pattern, scrubbed)
            if not m:
                continue
            rest = scrubbed[m.end():]
            num = re.match(r"\s*" + _NUM, rest)
            if num:
                other = _parse_number(num.group(1))
                span_end = m.end() + num.end()
            else:
                later = [x for x in mentions if x[0] >= m.end()]
                if not later:
                    return Decision(False, 0.5, f"{why} compared to what?")
                other, span_end = variables[later[0][2]], m.end()
            try:
                result = OPS[op](value, other)
            except TypeError:
                try:
                    result = OPS[op](len(value), other)
                except TypeError:
                    continue
            reason = f"{why} {op} {other!r}"
            scrubbed = scrubbed[: m.start()] + " " * (span_end - m.start()) + scrubbed[span_end:]
            break

        words = re.findall(r"[a-z]+", scrubbed)
        if result is None:
            for word, pred in PREDICATES.items():
                if word in words:
                    try:
                        result, reason = pred(value), f"{why} is {word}"
                    except TypeError:
                        pass
                    words.remove(word)
                    break
        negations = sum(w in NEGATIONS for w in words)
        confidence = 0.9
        if result is None:
            result, reason = bool(value), f"bool({why})"
            if not mentions and not negations:
                # "case something big:" -- truthiness of the subject says
                # nothing about that.
                confidence = 0.5
        if negations % 2:
            result, reason = not result, f"not {reason}"
        return Decision(bool(result), confidence, reason)

    # -- match -----------------------------------------------------------

    def match(self, req: Request) -> Decision:
        subject = req.subject
        if subject is NOVALUE:
            mentions = _mentions(" " + req.text.lower() + " ", req.variables)
            if mentions:
                subject = req.variables[mentions[0][2]]

        for i, (pattern, captures) in enumerate(req.cases):
            if captures is not None:  # a real Python pattern
                if subject is NOVALUE:
                    if re.fullmatch(r"\s*[A-Za-z_]\w*\s*", pattern):  # `_` or capture
                        return Decision(i, 1.0, "wildcard")
                    continue
                if try_pattern(pattern, subject, req.globals, req.locals) is not None:
                    return Decision(i, 1.0, "python")
                continue
            if isinstance(subject, str) and re.search(
                rf"(?<!\w){re.escape(subject.lower())}(?!\w)", pattern.lower()
            ):
                return Decision(i, 0.8, "mentions subject")
            verdict = self.judge(pattern, req.variables, subject)
            if verdict.value and verdict.confidence > 0.5:
                return Decision(i, verdict.confidence, verdict.reason)
        return Decision(-1, 0.5, "nothing fits")


# --------------------------------------------------------------------------
# AskJev


class AskJev:
    """Human-in-the-loop Jev: shows the request on stderr, reads an answer."""

    def __init__(self, stream=None):
        self.stream = stream

    def _readline(self, prompt: str) -> str:
        print(prompt, end="", file=sys.stderr, flush=True)
        if self.stream is not None:
            return self.stream.readline()
        try:
            with open("/dev/tty") as tty:
                return tty.readline()
        except OSError:
            return sys.stdin.readline()

    def decide(self, req: Request) -> Decision:
        print("\n" + req.prompt(), file=sys.stderr)
        while True:
            answer = self._readline("jev> ").strip().lower()
            if req.kind == "match":
                try:
                    return Decision(int(answer), 1.0, "human")
                except ValueError:
                    pass
            elif answer[:1] in ("y", "t", "1"):
                return Decision(True, 1.0, "human")
            elif answer[:1] in ("n", "f", "0"):
                return Decision(False, 1.0, "human")
            elif not answer:
                raise EOFError("no answer from the human Jev")


# --------------------------------------------------------------------------
# JevHTTP


class JevHTTP:
    """Client for the Jev decision API.

    Configured by ``$JEV_API_KEY`` and ``$JEV_API_URL`` (default
    ``https://api.jevai.net``).  The request shape follows the public
    example (``{"input": ..., "schema": {...}}`` -> typed values plus a
    ``confidence``); the exact schema types and auth header are guesses
    until we have access.
    """

    def __init__(self, api_key: str | None = None, url: str | None = None,
                 timeout: float = 10.0):
        self.api_key = api_key or os.environ.get("JEV_API_KEY")
        if not self.api_key:
            raise RuntimeError("JevHTTP needs an API key: set $JEV_API_KEY")
        self.url = (url or os.environ.get("JEV_API_URL") or "https://api.jevai.net").rstrip("/")
        self.timeout = timeout

    def payload(self, req: Request) -> dict:
        if req.kind == "match":
            schema = {"case": "number"}
        else:
            schema = {"answer": "boolean"}
        return {"input": req.prompt(), "schema": schema}

    def post(self, payload: dict) -> dict:
        request = urllib.request.Request(
            self.url + "/v1/decide",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as resp:
            return json.load(resp)

    def decide(self, req: Request) -> Decision:
        body = self.post(self.payload(req))
        confidence = float(body.get("confidence", 1.0))
        if req.kind == "match":
            return Decision(int(body["case"]), confidence, "jev")
        return Decision(bool(body["answer"]), confidence, "jev")
