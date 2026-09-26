"""Run the universal Turing machine from utm_table.py with Jev choosing
every rule.

The UTM's 55 rules are turned into a jevlang program, one `match` per UTM
state.  At every UTM step Python looks up the current state's `match`, Jev
decides which of its rules covers the symbol under the head, and Python
applies that rule.  Each choice is checked against the plain rule table,
and the run stops at the first disagreement, since one wrong rule derails
everything after it.

    python examples/utm_jev.py            # two simulated busy-beaver steps
    python examples/utm_jev.py 1          # one
    python examples/utm_jev.py 6          # all six, until it halts
    python examples/utm_jev.py --show     # print the generated jevlang
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import utm_table as utm  # noqa: E402
from jevlang import runtime, transform  # noqa: E402

# What Jev is shown for each tape symbol: a distinct noun, quoted.  Not a
# digit or a lone letter (shown "1", Jev was close to a coin flip on whether
# it was an "x"), no word inside another, and no word that is also an
# adjective ("the symbol is current" read as always true).
WORDS = {
    ">": "anchor", "}": "beacon", "B": "block", "C": "crown", "T": "target",
    "E": "entry", "F": "flag", "u": "unit", "v": "tally",
    "0": "zero", "1": "one", "L": "west", "R": "east",
    "$": "divider", "x": "ring", "y": "moon", "_": "hole",
}


def describe(symbols):
    words = [f'"{WORDS[c]}"' for c in symbols]
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " or " + words[-1]


def jevlang_source():
    """The UTM's rule table as a jevlang program."""
    out = ["# coding: jevlang", "# Generated from utm_table.RULES: one match per UTM state.", ""]
    for i, (state, lines) in enumerate(utm.RULES.items()):
        out += [f"def rule_{i}(symbol):", f"    # UTM state: {state}", "    match symbol:"]
        for j, (symbols, write, move, nxt) in enumerate(lines):
            pattern = "_" if symbols == utm.ANY else f"the symbol is {describe(symbols)}"
            out += [f"        case {pattern}:", f"            return {j}"]
        out += ["    return -1", "", ""]
    return "\n".join(out)


def load_rules():
    source = jevlang_source()
    namespace = {"__name__": "utm_rules", "__file__": "<utm rules>"}
    exec(compile(transform(source), "<utm rules>", "exec"), namespace)
    return {state: namespace[f"rule_{i}"] for i, state in enumerate(utm.RULES)}


def table_choice(state, symbol):
    for j, (symbols, *_rest) in enumerate(utm.RULES[state]):
        if symbols == utm.ANY or symbol in symbols:
            return j
    return -1


def main(target=2):
    rules = load_rules()
    start, table = utm.MACHINES["beaver"]
    tape_list, origin, states = utm.encode(start, table, pad=4)
    print(f"Simulating the 2-state busy beaver for {target} step(s) on the UTM, "
          f"with Jev choosing each of its rules.\n")
    tape = dict(enumerate(tape_list))
    pos, state, previous, utm_steps, sim_steps = 0, "find head", None, 0, -1
    calls_at_start = runtime.calls_made

    def cells():
        return "".join(tape.get(i, "_") for i in range(max(tape) + 1))

    while state != "halt":
        if state == "find head" and previous != "find head":
            sim_steps += 1
            sim_state, _, _ = utm.decode(list(cells()), origin, states)
            print(f"  simulated step {sim_steps}: UTM step {utm_steps:4}   state {sim_state}   {cells()}")
            if sim_steps == target:
                break
        symbol = tape.get(pos, "_")
        choice = rules[state](WORDS[symbol])
        expected = table_choice(state, symbol)
        if choice != expected:
            print(f"\nJev went wrong at UTM step {utm_steps}: in {state!r} reading {symbol!r} it "
                  f"chose rule {choice}, but the table says rule {expected}.")
            break
        _, write, move, nxt = utm.RULES[state][choice]
        tape[pos] = symbol if write is None else write
        pos += 1 if move == "R" else -1
        previous, state = state, nxt
        utm_steps += 1
    else:
        sim_steps += 1  # the step that halted never gets back to "find head"
        print(f"  simulated step {sim_steps}: UTM step {utm_steps:4}   halted    {cells()}")

    print(f"\n{utm_steps} UTM steps, every rule chosen by Jev "
          f"({runtime.calls_made - calls_at_start} calls).")
    expected = list(utm.run_direct(start, table, max(sim_steps, 0)))[-1]
    got = utm.decode(list(cells()), origin, states)
    ok = got[:2] == expected[:2] and utm.same_tape(got[2], expected[2])
    print(f"After {sim_steps} simulated step(s): state {got[0]}, "
          f"{'matching' if ok else 'NOT matching'} a direct simulation.")


if __name__ == "__main__":
    if "--show" in sys.argv:
        print(jevlang_source())
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
