"""A real universal Turing machine, as a plain rule table.  No Jev here.

This is the honest counterpart to utm.py: the universal machine does the
work itself, one square at a time.  It's plain Python so the machine can be
built and checked cheaply before anyone asks Jev to run it.

Tape layout:

    > B E w d u u E w d u B E ... $ 0 0 x 1 0 _ _ ...
    |  program: one block per simulated state |  simulated tape

* Each block `B` is one simulated state and holds two entries: the first
  for reading 0, the second for reading 1.  An entry is `E`, the symbol to
  write (0/1), the direction (L/R), then the next state in unary: one `u`
  per state number, none for halt.  States are numbered from 1.
* The current state's block is marked `C` instead of `B`.
* The simulated head is marked by writing its cell as `x` (a 0) or `y` (a 1).

One simulated step: find the head and remember what it reads; walk back to
the `C` block and mark the matching entry `F`; remember its symbol and
direction and carry them to the head; then unmark `C`, and count the
entry's `u`s by moving a marker `T` forward one block per `u`.  With no
`u`s the simulated machine halts.  The simulated tape is padded with 0s on
the left, since there's no room to grow into the program; blanks on the
right read as 0.

    python examples/utm_table.py            # run the 2-state busy beaver
    python examples/utm_table.py beaver3    # the 3-state busy beaver
"""

import random
import sys

ANY = "*"

# state: [(symbols read, symbol to write or None to keep, move, next state)]
# The first matching line wins; ANY matches anything.  Written this way the
# table is short, and each line reads as one English rule.
RULES = {
    # 1. Find the simulated head and remember what's under it.
    "find head": [("x", None, "L", "back to block, read 0"),
                  ("y", None, "L", "back to block, read 1"),
                  (ANY, None, "R", "find head")],
    "back to block, read 0": [("C", None, "R", "first entry"),
                              (ANY, None, "L", "back to block, read 0")],
    "back to block, read 1": [("C", None, "R", "skip first entry"),
                              (ANY, None, "L", "back to block, read 1")],
    # 2. Mark the entry for that symbol with F.
    "first entry": [("E", "F", "R", "read write"),
                    (ANY, None, "R", "first entry")],
    "skip first entry": [("E", None, "R", "second entry"),
                         (ANY, None, "R", "skip first entry")],
    "second entry": [("E", "F", "R", "read write"),
                     (ANY, None, "R", "second entry")],
    # 3. Remember the entry's symbol and direction.
    "read write": [("0", None, "R", "read move, write 0"),
                   ("1", None, "R", "read move, write 1")],
    "read move, write 0": [("L", None, "R", "carry 0 left"),
                           ("R", None, "R", "carry 0 right")],
    "read move, write 1": [("L", None, "R", "carry 1 left"),
                           ("R", None, "R", "carry 1 right")],
    # 4. Carry them to the head: write the symbol, step, mark the new head.
    "carry 0 left": [("xy", "0", "L", "mark head"), (ANY, None, "R", "carry 0 left")],
    "carry 0 right": [("xy", "0", "R", "mark head"), (ANY, None, "R", "carry 0 right")],
    "carry 1 left": [("xy", "1", "L", "mark head"), (ANY, None, "R", "carry 1 left")],
    "carry 1 right": [("xy", "1", "R", "mark head"), (ANY, None, "R", "carry 1 right")],
    "mark head": [("0_", "x", "L", "unmark block"),
                  ("1", "y", "L", "unmark block")],
    # 5. Switch state: unmark C, then move T forward one block per u.
    "unmark block": [("C", "B", "L", "mark start"),
                     (ANY, None, "L", "unmark block")],
    "mark start": [(">", "}", "R", "go to entry"),
                   (ANY, None, "L", "mark start")],
    "go to entry": [("F", None, "R", "count"),
                    (ANY, None, "R", "go to entry")],
    "count": [("u", "v", "L", "advance: go home"),
              ("01LRv", None, "R", "count"),
              (ANY, None, "L", "tidy entry")],
    "advance: go home": [("}", ">", "R", "advance: next block"),
                         (">", None, "R", "advance: find T"),
                         (ANY, None, "L", "advance: go home")],
    "advance: find T": [("T", "B", "R", "advance: next block"),
                        (ANY, None, "R", "advance: find T")],
    "advance: next block": [("B", "T", "L", "advance: back"),
                            (ANY, None, "R", "advance: next block")],
    "advance: back": [(">", None, "R", "go to entry"),
                      (ANY, None, "L", "advance: back")],
    # 6. Tidy up: v back to u, F back to E, T becomes the new C.
    "tidy entry": [("v", "u", "L", "tidy entry"),
                   ("F", "E", "L", "finish"),
                   (ANY, None, "L", "tidy entry")],
    "finish": [("}", ">", "R", "halt"),  # no u's: the simulated machine halted
               (">", None, "R", "finish: find T"),
               (ANY, None, "L", "finish")],
    "finish: find T": [("T", "C", "R", "find head"),
                       (ANY, None, "R", "finish: find T")],
}


def rule_for(state, symbol):
    for symbols, write, move, nxt in RULES[state]:
        if symbols == ANY or symbol in symbols:
            return (symbol if write is None else write), move, nxt
    raise RuntimeError(f"UTM stuck: no rule for {state!r} reading {symbol!r}")


# --------------------------------------------------------------------------
# Machines to simulate: {(state, read): (write, move, next)}, "H" = halt.

MACHINES = {
    "beaver": ("A", {("A", 0): (1, "R", "B"), ("A", 1): (1, "L", "B"),
                     ("B", 0): (1, "L", "A"), ("B", 1): (1, "R", "H")}),
    "beaver3": ("A", {("A", 0): (1, "R", "B"), ("A", 1): (1, "R", "H"),
                      ("B", 0): (0, "R", "C"), ("B", 1): (1, "R", "B"),
                      ("C", 0): (1, "L", "C"), ("C", 1): (1, "L", "A")}),
}


def encode(start, table, pad=8):
    """The UTM's starting tape for `table`, and where the simulated tape begins."""
    states = [start] + sorted({q for q, _ in table} - {start})
    number = {q: i + 1 for i, q in enumerate(states)} | {"H": 0}
    tape = [">"]
    for q in states:
        tape.append("C" if q == start else "B")
        for read in (0, 1):
            write, move, nxt = table[(q, read)]
            tape += ["E", str(write), move] + ["u"] * number[nxt]
    tape.append("$")
    origin = len(tape) + pad
    tape += ["0"] * pad + ["x"] + ["0"] * pad
    return tape, origin, states


def decode(tape, origin, states):
    """Read the simulated machine back off the UTM's tape."""
    cells = tape[tape.index("$") + 1:]
    base = tape.index("$") + 1
    head = next(i for i, c in enumerate(cells) if c in "xy") + base - origin
    values = {i + base - origin: {"0": 0, "x": 0, "_": 0, "1": 1, "y": 1}[c]
              for i, c in enumerate(cells)}
    if "C" in tape:
        block = [c for c in tape if c in "BC"].index("C")
        state = states[block]
    else:
        state = "H"
    return state, head, values


def run_utm(tape, max_steps=1_000_000, on_cycle=None):
    """Run the UTM.  Calls on_cycle(tape, utm_steps) at the start of each
    simulated step (whenever the UTM is back at "find head")."""
    tape = dict(enumerate(tape))
    pos, state, previous, steps = 0, "find head", None, 0
    while state != "halt":
        if state == "find head" and previous != "find head" and on_cycle:
            on_cycle(tape, steps)
        symbol = tape.get(pos, "_")
        previous = state
        write, move, state = rule_for(state, symbol)
        tape[pos] = write
        pos += 1 if move == "R" else -1
        if pos < 0:
            raise RuntimeError("UTM ran off the left end of its tape")
        steps += 1
        if steps > max_steps:
            raise RuntimeError("UTM step limit")
    return [tape.get(i, "_") for i in range(max(tape) + 1)], steps


def run_direct(start, table, max_steps=10_000):
    """The same machine, simulated directly.  Yields (state, head, tape)."""
    tape, head, state = {}, 0, start
    yield state, head, dict(tape)
    for _ in range(max_steps):
        if state == "H":
            return
        write, move, state = table[(state, tape.get(head, 0))]
        tape[head] = write
        head += 1 if move == "R" else -1
        yield state, head, dict(tape)


def same_tape(a, b):
    return all(a.get(k, 0) == b.get(k, 0) for k in set(a) | set(b))


class _Enough(Exception):
    pass


def compare(start, table, pad=8, max_sim_steps=None):
    """Run `table` on the UTM and directly, comparing after every simulated
    step.  Returns (simulated steps, UTM steps)."""
    tape, origin, states = encode(start, table, pad)
    expected = list(run_direct(start, table, max_sim_steps or 10_000))
    seen = []

    def cycle(t, _):
        seen.append(decode([t.get(i, "_") for i in range(max(t) + 1)], origin, states))
        if len(seen) == len(expected) and expected[-1][0] != "H":
            raise _Enough  # the direct run was cut short; stop here too

    utm_steps = None
    try:
        final, utm_steps = run_utm(tape, on_cycle=cycle)
        seen.append(decode(final, origin, states))
    except _Enough:
        pass
    assert len(seen) == len(expected), (len(seen), len(expected))
    for i, ((q1, h1, t1), (q2, h2, t2)) in enumerate(zip(expected, seen)):
        assert (q1, h1) == (q2, h2) and same_tape(t1, t2), f"diverged at simulated step {i}"
    return len(expected) - 1, utm_steps


def random_machine(n_states, rng):
    names = "ABCDE"[:n_states]
    table = {(q, r): (rng.randint(0, 1), rng.choice("LR"), rng.choice(names + "H"))
             for q in names for r in (0, 1)}
    return "A", table


def self_test(n=300, seed=1):
    """Random 1-3 state machines, 12 simulated steps each (or until they halt)."""
    rng = random.Random(seed)
    for _ in range(n):
        start, table = random_machine(rng.randint(1, 3), rng)
        compare(start, table, pad=14, max_sim_steps=12)  # room to wander left
    return n


def stats():
    lines = sum(len(v) for v in RULES.values())
    symbols = set("><}BCTEFuv01LR$xy_")
    return len(RULES), len(symbols), lines


def main(name="beaver"):
    start, table = MACHINES[name]
    tape, origin, states = encode(start, table, pad=4)
    n_states, n_symbols, n_lines = stats()
    print(f"UTM: {n_states} states, {n_symbols} symbols, {n_lines} rules")
    print(f"Simulating {name!r}. Starting tape:\n  {''.join(tape)}\n")
    last = [0]

    def show(t, steps):
        cells = [t.get(i, "_") for i in range(max(t) + 1)]
        state, head, values = decode(cells, origin, states)
        print(f"  after {steps:5} UTM steps (+{steps - last[0]:4}): state {state}   "
              f"{''.join(cells)}")
        last[0] = steps

    final, steps = run_utm(tape, on_cycle=show)
    state, head, values = decode(final, origin, states)
    print(f"  after {steps:5} UTM steps (+{steps - last[0]:4}): halted          {''.join(final)}")
    sim_steps, _ = compare(start, table, pad=4)
    print(f"\n{sim_steps} simulated steps in {steps} UTM steps "
          f"(about {steps / sim_steps:.0f} per simulated step); {sum(values.values())} ones on the tape.")
    print(f"Matches a direct simulation after every step. Self-test: {self_test()} random machines OK.")


if __name__ == "__main__":
    main(*sys.argv[1:])
