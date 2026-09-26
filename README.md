# jevlang

Python where every `if`, `elif`, `while` and `match` is decided by
[Jev](https://jevai.net/), TypeSafe's "System One" decision model — which means the conditions don't have to be
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
| `jev`  | The real Jev, via the [TypeSafe SDK](https://docs.typesafe.ai/sdk/python) (`pip install '.[jev]'`). Used by default when `TYPESAFE_API_KEY` or `OPENROUTER_API_KEY` is set. Conditions are asked as a Noul (probability of yes; true at ≥ `JEV_THRESHOLD`, default 0.5), `match` as a Choice between the cases plus `none`. |
| `pkg.mod:factory` | Any object with a `decide(request) -> Decision` method. |

### Using the real Jev

```
pip install '.[jev]'
export OPENROUTER_API_KEY=sk-or-...   # or TYPESAFE_API_KEY from https://console.typesafe.ai/
JEV_TRACE=1 python examples/reviews.py
```

```
[jev] reviews.py:9 match 'review' -> 0 @ 0.94 (p=0.95)
😀 Absolutely loved it, we're coming back next week!
[jev] reviews.py:9 match 'review' -> 1 @ 0.98 (p=0.99)
😠 Cold food, and the waiter rolled his eyes at us.
[jev] reviews.py:9 match 'review' -> 2 @ 0.98 (p=0.98)
😐 It was fine, I guess.
```

With only an OpenRouter key, requests go to OpenRouter's pass-through to Jev
(`https://openrouter.ai/api/v1/systemone`, model `~typesafe/jev-latest`),
which speaks the same typed API as TypeSafe's own endpoint. (OpenRouter's
`typesafe/jev-router` is something else: a chat-completions router that
forwards prompts to other LLMs and answers in prose, so it isn't used here.)

Each decision is one `system_one` call. The `state` is JSON:

```json
{
  "source": "   1 | # coding: jev\n   2 | bottles = 99\n-->3 | while there are bottles left:\n...",
  "line": 3,
  "variables": {"bottles": 98},
  "times_this_line_was_evaluated_before": 1
}
```

and the question is a Noul whose instructions name the `condition`
(`"there are bottles left"`). For `match`, `state` also has
`match_subject` (its text and, when it's Python, its value), and the Choice's
options are `case_0`, `case_1`, ... described by the case source.

Other knobs: `JEV_MODEL` (or the SDK's own `TYPESAFE_BASE_URL` and
`TYPESAFE_DEFAULT_MODEL`, default `jev-latest`); `JEV_THRESHOLD`; and `JEV_LOCAL_PYTHON=1`, which evaluates
conditions that are already valid Python locally instead of asking. Jev's
docs say it is [not a calculator](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md),
so `if n % 15 == 0:` is a better job for Python.

Set `JEV_TRACE=1` to log every decision to stderr:

```
[jev] bottles.py:3 while 'there are bottles left' -> True @ 0.90 (bool(bottles))
```

`jevlang.runtime.set_backend(obj)` installs a backend from code.

## Limits

- Headers must be the block form ending in `:` on one line (`if x: y` on a
  single line is left alone). A trailing `# comment` after the colon is fine.
- Every condition goes through the backend, including plain Python ones
  (unless `JEV_LOCAL_PYTHON=1`). With the real API that's one request per
  loop iteration.
- A bare single word in a `case` is a Python capture pattern (it matches
  everything); quote it if you mean the string.
- Imported modules are cached as `.pyc` like any other. If you upgrade
  jevlang, delete stale `__pycache__` directories, since Python won't know
  the transform changed.
- Conditional expressions (`a if b else c`) and comprehension `if`s are
  plain Python and aren't sent to Jev.

## Tests

```
pip install pytest typesafe-sdk
pytest
```

The `jev` backend's tests run the real SDK against a mocked transport, so
they check the request/response format without an API key.
