# jevlang

Python where every `if`, `elif`, `while` and `match` is decided by
[Jev](https://jevai.net/) — which means the conditions don't have to be
Python at all:

```python
# coding: jev
bottles = 99
while there are bottles left:
    print(f"{bottles} bottles of beer on the wall")
    bottles -= 1
```

```
$ python examples/bottles.py
99 bottles of beer on the wall
98 bottles of beer on the wall
...
```

## How it works

It's a source preprocessor built on Python's codec machinery (the same trick
as [magic_codec](https://github.com/Tsche/magic_codec), explained in
[Python's preprocessor](https://pydong.org/articles/pythons-preprocessor/)):

1. `jevlang.pth` in site-packages registers a codec named `jev` at startup.
2. A file whose first or second line is `# coding: jev` is decoded by that
   codec, which rewrites the source before the tokenizer sees it.
3. Each block header becomes a call into the runtime with the condition's
   text, its line number, and `locals()`:

   ```python
   while __import__('jevlang.runtime').runtime.session(globals()).cond('while', 'there are bottles left', 3, locals()):
   ```

   Nothing else is added or removed, so line numbers in tracebacks still match
   your file. The module's session is created on first use and reads the
   original source from `__file__`.
4. At runtime the session gathers the variables in scope, the surrounding
   source (a few lines either side, with the current line marked) and how
   many times this line has been evaluated, and asks the backend for a
   decision.

`match` statements are rewritten too. Jev is shown the subject and all the
case patterns and picks one; each `case` becomes `case (N, {...}):` so that
capture variables in real Python patterns are still bound:

```python
match the forecast:                      # English subject
    case "snow": ...                     # Python pattern
    case anything involving rain: ...    # English pattern
    case t if t > 25: ...                # capture + guard: t is still bound
    case _: ...
```

Use `python -m jevlang --show FILE` to see the rewritten source.

## Install

```
pip install .                     # installs the package and jevlang.pth
python examples/bottles.py
```

Without installing the `.pth`, run files through the CLI instead:

```
python -m jevlang examples/weather.py [args...]
python -m jevlang --install-pth [--user]    # write jevlang.pth by hand (e.g. editable installs)
```

## Backends

Pick one with `$JEV_BACKEND`:

| name   | what it does |
|--------|--------------|
| `fake` | Default while there's no API key. Offline and deterministic. Evaluates conditions that are valid Python as Python, and has keyword heuristics for English: it finds the variable you mention (`bottles`, allowing plurals and `snake_case` → words), then handles comparisons (`more than 10`, `at least three`, `fewer than limit`), `even`/`odd`/`positive`/`negative`, and negation (`no`, `not`, `n't`, `empty`, `out of`, ...), or falls back to the variable's truthiness. If it can't tell what you mean, the answer is `False`. |
| `ask`  | You are Jev: shows the full request on stderr and reads `y`/`n` (or a case number) from the terminal. |
| `http` | The real Jev API, `POST $JEV_API_URL/v1/decide` with `Authorization: Bearer $JEV_API_KEY`. Used by default when `JEV_API_KEY` is set. **Untested**: the payload follows the example on jevai.net (`{"input": prompt, "schema": {"answer": "boolean"}}`, or `{"case": "number"}` for `match`) until we have a key. |
| `pkg.mod:factory` | Any object with a `decide(request) -> Decision` method. |

Set `JEV_TRACE=1` to log every decision to stderr:

```
[jev] bottles.py:3 while 'there are bottles left' -> True @ 0.90 (bool(bottles))
```

`jevlang.runtime.set_backend(obj)` installs a backend from code.

## Limits

- Headers must be the block form ending in `:` on one line (`if x: y` on a
  single line is left alone). A trailing `# comment` after the colon is fine.
- Every condition goes through the backend, including plain Python ones.
  With the real API that's one request per loop iteration.
- A bare single word in a `case` is a Python capture pattern (it matches
  everything); quote it if you mean the string.
- Imported modules are cached as `.pyc` like any other. If you upgrade
  jevlang, delete stale `__pycache__` directories, since Python won't know
  the transform changed.
- Conditional expressions (`a if b else c`) and comprehension `if`s are
  plain Python and aren't sent to Jev.

## Tests

```
pip install pytest
pytest
```
