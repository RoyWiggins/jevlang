"""Runtime support for transformed modules.

Each transformed module gets a :class:`Session` bound to ``__jev__``.  Every
``if``/``elif``/``while`` condition and every ``match`` statement calls into
it; the session gathers the current variables and the surrounding source
code, and asks the configured backend (see :mod:`jevlang.backends`) to
decide.
"""

from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass, field
from typing import Any

from .transform import pattern_captures

__all__ = [
    "session",
    "Session",
    "Request",
    "Decision",
    "NOVALUE",
    "get_backend",
    "set_backend",
]


class _NoValue:
    """Marker for a ``match`` subject that is English rather than Python."""

    def __repr__(self) -> str:
        return "NOVALUE"

    def __bool__(self) -> bool:
        return False


NOVALUE = _NoValue()


@dataclass
class Request:
    """Everything Jev gets to see when making a decision."""

    kind: str  # "if", "elif", "while" or "match"
    text: str  # the condition / match subject, verbatim
    is_python: bool  # does ``text`` parse as a Python expression?
    variables: dict[str, Any]  # visible variables (globals overlaid by locals)
    code: str  # the surrounding source, with the line marked
    filename: str
    lineno: int
    iteration: int = 0  # how many times this line has been asked before
    # match only
    subject: Any = NOVALUE
    cases: list[tuple[str, list[str] | None]] = field(default_factory=list)
    # The real namespaces, for backends that want to eval() Python.
    globals: dict[str, Any] = field(default_factory=dict, repr=False)
    locals: dict[str, Any] = field(default_factory=dict, repr=False)

    def prompt(self) -> str:
        """Render the request as the text sent to a real model."""
        vars_ = "\n".join(
            f"  {k} = {_short_repr(v)}" for k, v in self.variables.items()
        ) or "  (none)"
        parts = [
            f"File {self.filename}, line {self.lineno}:",
            self.code,
            "",
            "Variables in scope:",
            vars_,
            "",
        ]
        if self.kind == "match":
            parts.append(f"Match subject: {self.text}")
            if self.subject is not NOVALUE:
                parts.append(f"Subject value: {_short_repr(self.subject)}")
            parts.append("Which case applies? Answer with its number, or -1 for none.")
            for i, (pat, _) in enumerate(self.cases):
                parts.append(f"  {i}: case {pat}")
        else:
            if self.iteration:
                parts.append(f"(This {self.kind} has been evaluated {self.iteration} times so far.)")
            parts.append(f"Is this condition true right now? {self.text}")
        return "\n".join(parts)


@dataclass
class Decision:
    value: Any  # bool for conditions, case index (-1 = none) for match
    confidence: float = 1.0
    reason: str = ""


def _short_repr(value: Any, limit: int = 200) -> str:
    try:
        r = repr(value)
    except Exception:  # pragma: no cover - hostile __repr__
        r = f"<{type(value).__name__}>"
    return r if len(r) <= limit else r[: limit - 3] + "..."


def _interesting(name: str, value: Any) -> bool:
    if name.startswith("__"):
        return False
    return not isinstance(
        value, (types.ModuleType, types.FunctionType, types.BuiltinFunctionType, type, Session)
    )


def _is_python_expr(text: str) -> bool:
    try:
        compile(text, "<jev>", "eval")
    except SyntaxError:
        return False
    return True


# --------------------------------------------------------------------------
# Backend selection

_backend = None


def get_backend():
    """The active backend, chosen from ``$JEV_BACKEND`` on first use.

    ``fake`` (default without an API key), ``ask`` (you are Jev), or
    ``http`` (the real Jev API; default when ``$JEV_API_KEY`` is set).
    """
    global _backend
    if _backend is None:
        from . import backends

        name = os.environ.get("JEV_BACKEND") or (
            "http" if os.environ.get("JEV_API_KEY") else "fake"
        )
        _backend = backends.by_name(name)
    return _backend


def set_backend(backend) -> None:
    """Install a backend object (anything with a ``decide(request)`` method)."""
    global _backend
    _backend = backend


# --------------------------------------------------------------------------


def session(module_globals: dict) -> "Session":
    """The Session for a module, created on first use and cached in its
    globals as ``__jev__``."""
    s = module_globals.get("__jev__")
    if s is None:
        filename = module_globals.get("__file__") or module_globals.get("__name__", "<jev>")
        s = module_globals["__jev__"] = Session(filename, _read_source(filename), module_globals)
    return s


def _read_source(filename: str) -> str:
    # Read the file raw: linecache/tokenize would run it through our codec
    # and hand back the transformed text.
    try:
        with open(filename, encoding="utf-8-sig") as f:
            return f.read()
    except (OSError, UnicodeDecodeError, TypeError):
        return ""


class Session:
    """Per-module state: the original source and the module's globals."""

    CONTEXT_BEFORE = 3
    CONTEXT_AFTER = 8

    def __init__(self, filename: str, source: str, module_globals: dict):
        self.filename = filename
        self.source_lines = source.splitlines()
        self.globals = module_globals
        self.counts: dict[int, int] = {}
        self.trace = bool(os.environ.get("JEV_TRACE"))

    def context(self, lineno: int) -> str:
        lo = max(1, lineno - self.CONTEXT_BEFORE)
        hi = min(len(self.source_lines), lineno + self.CONTEXT_AFTER)
        if not self.source_lines:
            return "(source unavailable)"
        width = len(str(hi))
        out = []
        for n in range(lo, hi + 1):
            mark = "-->" if n == lineno else "   "
            out.append(f"{mark} {n:>{width}} | {self.source_lines[n - 1]}")
        return "\n".join(out)

    def _request(self, kind: str, text: str, lineno: int, local_vars: dict, **kw) -> Request:
        merged = {**self.globals, **local_vars}
        iteration = self.counts.get(lineno, 0)
        self.counts[lineno] = iteration + 1
        return Request(
            kind=kind,
            text=text,
            is_python=_is_python_expr(text),
            variables={k: v for k, v in merged.items() if _interesting(k, v)},
            code=self.context(lineno),
            filename=self.filename,
            lineno=lineno,
            iteration=iteration,
            globals=self.globals,
            locals=local_vars,
            **kw,
        )

    def _log(self, req: Request, decision: Decision) -> None:
        if self.trace:
            reason = f" ({decision.reason})" if decision.reason else ""
            print(
                f"[jev] {os.path.basename(self.filename)}:{req.lineno} "
                f"{req.kind} {req.text!r} -> {decision.value!r} "
                f"@ {decision.confidence:.2f}{reason}",
                file=sys.stderr,
            )

    def cond(self, kind: str, text: str, lineno: int, local_vars: dict) -> bool:
        req = self._request(kind, text, lineno, local_vars)
        decision = get_backend().decide(req)
        self._log(req, decision)
        return bool(decision.value)

    def choose(
        self,
        text: str,
        lineno: int,
        cases: list[tuple[str, list[str] | None]],
        local_vars: dict,
        subject: Any = NOVALUE,
    ) -> tuple[int, dict[str, Any]]:
        """Pick a case.  Returns ``(index, bindings)``; the transformed
        ``case (N, {...}):`` patterns destructure it."""
        req = self._request("match", text, lineno, local_vars, subject=subject, cases=cases)
        decision = get_backend().decide(req)
        self._log(req, decision)
        index = int(decision.value)
        if not 0 <= index < len(cases):
            return (-1, {})
        pattern, captures = cases[index]
        bindings = dict.fromkeys(captures or [])
        if captures:
            # Jev chose the branch; Python still does the destructuring.
            hit = try_pattern(pattern, subject, req.globals, req.locals)
            if hit is not None:
                bindings.update(hit)
        return (index, bindings)


def try_pattern(pattern: str, subject: Any, globals_: dict, locals_: dict) -> dict | None:
    """Match ``subject`` against a Python ``case`` pattern (guard included).

    Returns the captured names on success, ``None`` on failure or if the
    pattern isn't Python.
    """
    captures = pattern_captures(pattern)
    if captures is None or subject is NOVALUE:
        return None
    code = (
        "match __jev_subject__:\n"
        f" case {pattern}:\n"
        "  __jev_hit__ = True\n"
    )
    ns = {**globals_, **locals_, "__jev_subject__": subject, "__jev_hit__": False}
    exec(compile(code, "<jev-case>", "exec"), ns)
    if not ns["__jev_hit__"]:
        return None
    return {name: ns[name] for name in captures}
