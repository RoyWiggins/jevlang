# jevlang

Python where every `if`, `elif`, `while` and `match` (ternaries, list comprehension excepted) is decided by
[Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev), enabling *modern coding style*: conditionals no longer have to be Python at all:

```python
# coding: jevlang
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

In fact, unless you set JEVLANG_LOCAL_PYTHON=1, even Python conditionals are evaluated by Jev. Setting this is otherwise known as "Luddite mode". 

## How it works

It's a source preprocessor built on Python's codec machinery (see
[Python's preprocessor](https://pydong.org/articles/pythons-preprocessor/)).

Each block header becomes a call into the runtime with the condition's
   text, its line number, and `locals()`:

   ```python
   while __import__('jevlang.runtime').runtime.session(globals()).cond('while', 'there are bottles left', 3, locals()):
   ```

At runtime the session gathers the variables in scope, the surrounding
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

With [uv](https://docs.astral.sh/uv/):

```
uv sync                                  # .venv with jevlang, the TypeSafe SDK and pytest
uv run python examples/bottles.py        # `# coding: jevlang` files run with plain python
uv run jevlang examples/weather.py       # or through the CLI
```

`uv sync` installs jevlang in editable mode, including `jevlang.pth`, which
registers the codec at startup, so edits under `src/` take effect without
reinstalling.

With pip:

```
pip install '.[jev]'              # installs the package and jevlang.pth
python examples/bottles.py
```

Without installing the `.pth`, run files through the CLI instead:

```
python -m jevlang examples/weather.py [args...]
python -m jevlang --install-pth [--user]    # write jevlang.pth by hand
```

## Backends

Pick one with `$JEVLANG_BACKEND`:

| name   | what it does |
|--------|--------------|
| `fake` | Default while there's no API key. Offline and deterministic. Evaluates conditions that are valid Python as Python, and has keyword heuristics for English
| `ask`  | You are Jev: shows the full request on stderr and reads `y`/`n` (or a case number) from the terminal. |
| `jev`  | The real Jev, via the [TypeSafe SDK](https://docs.typesafe.ai/sdk/python). Used by default when `TYPESAFE_API_KEY` or `OPENROUTER_API_KEY` is set. 
| `pkg.mod:factory` | Any object with a `decide(request) -> Decision` method. |

### Using the real Jev

```
export OPENROUTER_API_KEY=sk-or-...   # or TYPESAFE_API_KEY from https://console.typesafe.ai/
JEVLANG_TRACE=1 uv run python examples/reviews.py
```

```
[jev #1] reviews.py:9 match 'review' -> 0 @ 0.94 (p=0.95)
😀 Absolutely loved it, we're coming back next week!
[jev #2] reviews.py:9 match 'review' -> 1 @ 0.98 (p=0.99)
😠 Cold food, and the waiter rolled his eyes at us.
[jev #3] reviews.py:9 match 'review' -> 2 @ 0.98 (p=0.98)
😐 It was fine, I guess.
```
### Examples

`examples/fizzbuzz.py` is FizzBuzz with English conditions
(`if n is divisible by both three and five:`).

`examples/vibe_sort.py` bubble-sorts foods by spiciness

`examples/tictactoe.py` is tic-tac-toe with Jev in charge of everything. Jev can't spot three in a row on a whole board, so it checks
one line at a time, which comes to about 230 calls a game. It mostly works:

```
Your move (X), e.g. 'top left' or 'middle': middle
Jev plays the top left square.
 O |   |
   | X |
   |   |
Your move (X), e.g. 'top left' or 'middle': upper left
The top left square is taken.
Your move (X), e.g. 'top left' or 'middle': bottom right corner
Jev plays the top middle square.
 O | O |
   | X |
   |   | X
Your move (X), e.g. 'top left' or 'middle': top right
Jev plays the middle left square.
 O | O | X
 O | X |
   |   | X
Your move (X), e.g. 'top left' or 'middle': bottom left
 O | O | X
 O | X |
 X |   | X
You win!
```

On its last move Jev did find the block at middle right (p=0.96). Then it
judged `if move is nothing:` with `move='middle right'` at p=0.50, decided it
had no move after all, and took the first free square instead.

`examples/adventure.py` is a tiny text adventure where Jev decides
everything: what you're trying to do, which way you mean, which object you
mean, and whether a free-form action works.

`examples/tower.py`, "The Wizard's Tower", is a bigger adventure with Jev as
game master. A playthrough is
about 130 calls.

With an OpenRouter key, requests go to OpenRouter's pass-through to Jev
(`https://openrouter.ai/api/v1/systemone`, model `~typesafe/jev-latest`),
which speaks the same typed API as TypeSafe's own endpoint.

**Call budget.** A script stops with `JevBudgetExceeded` once it has asked
Jev `JEVLANG_MAX_CALLS` times: 1000 by default with the real backend, so a
runaway `while` can't drain your credits. `0` for no limit. The fake backend is
free, so it's unlimited unless you set the variable. 

Other knobs: `JEVLANG_MODEL` (or the SDK's own `TYPESAFE_BASE_URL` and
`TYPESAFE_DEFAULT_MODEL`, default `jev-latest`); `JEVLANG_THRESHOLD`; and `JEVLANG_LOCAL_PYTHON=1`, which evaluates
conditions that are already valid Python locally instead of asking. This is known as "Luddite mode". 

### Probabilistic branches

Add `# jev: roll` to a header and the branch is taken *with* Jev's
probability instead of whenever p ≥ 0.5:

```python
if what_you_said would make a gloomy ghost laugh:  # jev: roll
    ...
```

`JEVLANG_SEED` makes the
dice repeatable, and `jevlang.runtime.last_decision.odds` holds the p the
last roll used, so a game can show the odds.

Set `JEVLANG_TRACE=1` to log every decision to stderr:

```
[jev #2] bottles.py:3 while 'there are bottles left' [bottles=98] -> True @ 0.90 (bool(bottles))
```

Variables named in the condition are shown in brackets, so each line of a
loop's trace says what was being decided.

`jevlang.runtime.set_backend(obj)` installs a backend from code.

## Limits

- Headers must be the block form ending in `:` on one line (`if x: y` on a
  single line is left alone). A trailing `# comment` after the colon is fine.
- Every condition goes through the backend, including plain Python ones
  (unless `JEVLANG_LOCAL_PYTHON=1`). With the real API that's one request per
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
uv run pytest
```

The `jev` backend's tests run the real SDK against a mocked transport, so
they check the request/response format without an API key.
