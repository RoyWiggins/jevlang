"""Source-to-source transform: route every ``if`` / ``elif`` / ``while`` /
``match`` decision through Jev.

The input is *almost* Python: block headers may contain arbitrary English
instead of an expression, e.g.::

    while there are bottles left:
        ...

Because such text is not valid Python (and may not even tokenize -- think
``if it's raining:``), we work line by line with a small scanner that only
understands enough of Python's lexical structure (strings, comments,
brackets, line continuations) to know when a line starts a new statement.

Every recognised header is rewritten to call into the module's
:class:`jevlang.runtime.Session` (``JEV`` below):

* ``if COND:``    -> ``if JEV.cond('if', 'COND', LINE, locals()):``
* ``while COND:`` -> ``while JEV.cond('while', 'COND', LINE, locals()):``
* ``match SUBJ:`` -> ``match JEV.choose('SUBJ', LINE, [...cases...], locals(), SUBJ):``
  and each of its ``case PAT:`` lines becomes ``case (N, {'x': x, ...}):``
  so that Jev picks the branch and capture variables still get bound.

Line numbers are preserved, so tracebacks point at the original source.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

__all__ = ["transform", "pattern_captures", "split_guard", "JEV"]

# Block header: keyword, then the condition, then a colon, then optionally a
# comment.  The condition is non-greedy, but because what follows the colon
# must be end-of-line (or a comment), colons *inside* the condition such as
# ``d[1:2]`` or ``lambda x: x`` are kept as part of it.
HEADER_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<kw>if|elif|while|match|case)"
    r"(?=[\s(\[{'\"])\s*(?P<cond>.+?)\s*:\s*(?:#.*)?$"
)

# Every rewritten header calls this.  It finds (or creates) the module's
# Session through globals(), so no setup code has to be injected -- which
# matters because the file-run path discards whatever we'd put on line 1.
JEV = "__import__('jevlang.runtime').runtime.session(globals())"

MATCHING_KWS = {"if", "elif", "while", "match"}


@dataclass
class _Line:
    text: str  # without the trailing newline
    newline: str
    stmt_start: bool  # does a new logical line begin here?
    header: re.Match | None = None
    replacement: str | None = None

    @property
    def indent(self) -> int:
        return len(self.text.expandtabs()) - len(self.text.expandtabs().lstrip())

    @property
    def blank(self) -> bool:
        s = self.text.strip()
        return not s or s.startswith("#")


@dataclass
class _ScanState:
    string: str | None = None  # open triple-quote delimiter, if any
    depth: int = 0  # bracket nesting
    continued: bool = False  # previous line ended with a backslash

    @property
    def at_stmt_start(self) -> bool:
        return self.string is None and self.depth == 0 and not self.continued

    def feed(self, line: str) -> None:
        """Advance the state over one physical line of (valid-ish) Python."""
        i, n = 0, len(line)
        self.continued = False
        while i < n:
            if self.string is not None:
                if line[i] == "\\":
                    i += 2
                    continue
                if line.startswith(self.string, i):
                    i += len(self.string)
                    self.string = None
                    continue
                i += 1
                continue
            c = line[i]
            if c == "#":
                break
            if c in "\"'":
                if line.startswith(c * 3, i):
                    self.string = c * 3
                    i += 3
                    continue
                # Single-line string: skip to its end.
                i += 1
                while i < n and line[i] != c:
                    i += 2 if line[i] == "\\" else 1
                i += 1
                continue
            if c in "([{":
                self.depth += 1
            elif c in ")]}":
                self.depth = max(0, self.depth - 1)
            elif c == "\\" and i == n - 1:
                self.continued = True
            i += 1


def _split_lines(source: str) -> list[_Line]:
    lines = []
    for raw in source.splitlines(keepends=True):
        body = raw.rstrip("\r\n")
        lines.append(_Line(body, raw[len(body):], False))
    return lines


def _is_python(expr: str, mode: str = "eval") -> bool:
    try:
        ast.parse(expr, mode=mode)
    except SyntaxError:
        return False
    return True


def split_guard(case: str) -> tuple[str, str | None, bool] | None:
    """Split ``case`` text into ``(pattern, guard, guard_is_python)``.

    Returns ``None`` if no prefix of it is a Python pattern.  The guard may be
    English: ``(x, y) if it looks far away`` is a real pattern with a guard
    only Jev can judge.
    """
    try:
        tree = ast.parse(f"match _:\n case {case}:\n  pass")
    except SyntaxError:
        pass
    else:
        c = tree.body[0].cases[0]
        if c.guard is None:
            return case, None, True
        return ast.unparse(c.pattern), ast.unparse(c.guard), True
    for m in re.finditer(r"\s+if\s+", case):
        pattern = case[: m.start()]
        try:
            ast.parse(f"match _:\n case {pattern}:\n  pass")
        except SyntaxError:
            continue
        return pattern, case[m.end():], False
    return None


def pattern_captures(case: str) -> list[str] | None:
    """Names bound by a ``case`` pattern (a guard, even an English one, is
    allowed), or ``None`` if there is no Python pattern in it."""
    split = split_guard(case)
    if split is None:
        return None
    tree = ast.parse(f"match _:\n case {split[0]}:\n  pass")
    names: list[str] = []
    for node in ast.walk(tree.body[0].cases[0].pattern):
        name = None
        if isinstance(node, (ast.MatchAs, ast.MatchStar)):
            name = node.name
        elif isinstance(node, ast.MatchMapping):
            name = node.rest
        if name and name not in names:
            names.append(name)
    return names


def _find_cases(lines: list[_Line], match_idx: int) -> list[int]:
    """Indices of the ``case`` lines belonging to the match at ``match_idx``."""
    base = lines[match_idx].indent
    case_indent = None
    found = []
    for j in range(match_idx + 1, len(lines)):
        ln = lines[j]
        if not ln.stmt_start or ln.blank:
            continue
        if ln.indent <= base:
            break
        if case_indent is None:
            case_indent = ln.indent
        if ln.indent == case_indent and ln.header and ln.header["kw"] == "case":
            found.append(j)
    return found


def transform(source: str) -> str:
    """Rewrite Jev-flavoured Python into plain Python, line for line."""
    lines = _split_lines(source)
    state = _ScanState()

    # Pass 1: find which lines start statements, and which of those are
    # block headers.  Header lines are not fed to the scanner: they may be
    # English full of stray apostrophes.
    for ln in lines:
        ln.stmt_start = state.at_stmt_start
        m = HEADER_RE.match(ln.text) if ln.stmt_start else None
        if m:
            ln.header = m
        else:
            state.feed(ln.text)

    # Pass 2: rewrite headers.
    for idx, ln in enumerate(lines):
        m = ln.header
        if not m or m["kw"] not in MATCHING_KWS:
            continue
        lineno = idx + 1
        indent, kw, cond = m["indent"], m["kw"], m["cond"]
        if kw != "match":
            ln.replacement = f"{indent}{kw} {JEV}.cond({kw!r}, {cond!r}, {lineno}, locals()):"
            continue

        cases = []
        for n, j in enumerate(_find_cases(lines, idx)):
            cm = lines[j].header
            caps = pattern_captures(cm["cond"])
            cases.append((cm["cond"], caps))
            binds = ", ".join(f"{c!r}: {c}" for c in caps or [])
            lines[j].replacement = f"{cm['indent']}case ({n}, {{{binds}}}):"
        subject = f", ({cond})" if _is_python(cond) else ""
        ln.replacement = (
            f"{indent}match {JEV}.choose({cond!r}, {lineno}, {cases!r}, locals(){subject}):"
        )

    return "".join(
        (ln.replacement if ln.replacement is not None else ln.text) + ln.newline
        for ln in lines
    )
