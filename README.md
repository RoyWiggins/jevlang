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

`examples/turing.py` is a Turing machine programmed in English. Each rule
says when it applies and what it does:

```python
("carrying and you see a 1", "write a 0 and move left, still carrying"),
("carrying and you see a 0 or a blank", "write a 1 and halt"),
```

Jev compiles the what-it-does half once (what to write, which way to move,
which state comes next), then picks the matching rule at every step:

```
$ python examples/turing.py increment 1011
  1 0 1 1 _    [carrying]
        ^
  1 0 1 0 _    [carrying]
      ^
  1 0 0 0 _    [carrying]
    ^
  1 1 0 0 _    [halted]
    ^

Halted after 8 steps. Tape: 1100
```

`python examples/turing.py beaver` runs the 2-state busy beaver (6 steps,
four 1s), and `beaver3` the 3-state one (14 steps, six 1s). Each run is
about 50 calls, or about 120 for `beaver3`.

`python examples/turing.py wolfram` runs Wolfram's 2-state, 3-symbol machine,
the smallest known universal Turing machine. Six English rules:

```python
("in state A on a 0", "write a 1, move right and switch to state B"),
("in state A on a 1", "write a 2, move left and stay in state A"),
("in state A on a 2", "write a 1, move left and stay in state A"),
("in state B on a 0", "write a 2, move left and switch to state A"),
("in state B on a 1", "write a 2, move right and stay in state B"),
("in state B on a 2", "write a 0, move right and switch to state A"),
```

It never halts, so it runs 20 steps by default (`wolfram "" 40` for 40).
Its universality goes through elaborate encodings of other systems, so
don't expect it to compute anything you'd recognise, but the tape it
leaves after 20 steps (`1 1 2 2 0 1 0`, head on the last square, state B)
matches a plain-Python run of the same table.

`examples/utm.py` is a "universal" Turing machine, the cheap way. Its tape
holds the busy beaver's program as English entries, and its own rules are
five English instructions that Jev carries out:

```python
match utm_state:
    case reading: note the simulated state and the symbol under the simulated head:
        ...
    case looking up: find the program entry that matches the state and symbol:
        ...
```

A real UTM matches and copies symbols one square at a time; this one hands
the hard part to Jev, so it's a joke. It does get the right answer:

```
step 5   [_]  1   1   1    state A
  found:  in state A on a blank: write a 1, move right, become B
step 6    1  [1]  1   1    state B
  found:  in state B on a 1: keep the 1, move right, become halt

The universal machine ran 6 simulated steps. The tape has 4 ones.
```

A full run is about 115 calls; `python examples/utm.py 2` stops after two
simulated steps (about 40).

`examples/utm_table.py` is the honest version, in plain Python with no Jev
yet: a direct-simulation universal machine with 25 states, 18 symbols and
55 rules. The simulated machine's rules sit on its tape, and it runs them
one square at a time:

```
$ python examples/utm_table.py
UTM: 25 states, 18 symbols, 55 rules
Simulating 'beaver'. Starting tape:
  >CE1RuuE1LuuBE1LuE1R$0000x0000

  after     0 UTM steps (+   0): state A   >CE1RuuE1LuuBE1LuE1R$0000x0000
  after   175 UTM steps (+ 175): state B   >BE1RuuE1LuuCE1LuE1R$00001x000
  ...
  after   909 UTM steps (+ 102): halted          >BE1RuuE1LuuBE1LuE1R$0011y1000

6 simulated steps in 909 UTM steps (about 152 per simulated step); 4 ones on the tape.
```

Each block (`C` marks the current state) holds two entries, for reading 0
and reading 1: the symbol to write, the direction, and the next state in
unary (`uu` = state 2, nothing = halt). `x`/`y` mark the simulated head on
a 0/1. It is checked against a direct simulation after every step, for both
busy beavers and for random 1-3 state machines (`uv run pytest`). The
3-state busy beaver takes 4,219 UTM steps.

`examples/utm_jev.py` runs that UTM with Jev choosing every rule. The rule
table becomes a jevlang program with one `match` per UTM state:

```python
def rule_16(symbol):
    # UTM state: count
    match symbol:
        case reading a u:
            return 0
        case reading a zero, a one, an L, an R or a v:
            return 1
        case _:
            return 2
```

At each UTM step Python calls the current state's function and applies the
rule Jev picks, and every pick is checked against the table:

```
$ python examples/utm_jev.py 2
  simulated step 0: UTM step    0   state A   >CE1RuuE1LuuBE1LuE1R$0000x0000
  simulated step 1: UTM step  175   state B   >BE1RuuE1LuuCE1LuE1R$00001x000
  simulated step 2: UTM step  312   state A   >CE1RuuE1LuuBE1LuE1R$0000y1000

312 UTM steps, every rule chosen by Jev (312 calls).
After 2 simulated step(s): state A, matching a direct simulation.
```

That's two steps of a busy beaver, interpreted by a universal machine, with
every rule chosen by Jev, in about 85 seconds. Digits had to be spelled out:
shown the symbol `1`, Jev was nearly a coin flip on whether it was an `x`,
and got one wrong 18 steps in. As "one" it made it through all 312 steps,
though the closest calls (p=0.54, 0.58) were still on "one".

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
