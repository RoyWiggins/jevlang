# coding: jevlang
"""Run the universal Turing machine from utm_table.py with Jev choosing
every rule.

This file is itself jevlang, so Jev also runs the loop that drives the UTM:
whether it has halted, whether a new simulated step has begun, whether to
stop, and how to apply each rule it picked.  Only the checker
(utm_table.check_choice) is plain Python, so that it can catch Jev's
mistakes rather than make them.

Every question is about words, never numbers, letters or None: with
Python-style conditions (`sim_steps == target`, `move == "R"`) Jev
miscounted and stopped a step early.  The working state lives in a class,
which jevlang doesn't show Jev, so each question sees only what it's about.

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


class Words:
    # What Jev is shown for each tape symbol: a distinct noun, quoted.  Not a
    # digit or a lone letter (shown "1", Jev was close to a coin flip on
    # whether it was an "x"), no word inside another, and no word that is
    # also an adjective ("the symbol is current" read as always true).
    SYMBOLS = {
        ">": "anchor", "}": "beacon", "B": "block", "C": "crown", "T": "target",
        "E": "entry", "F": "flag", "u": "unit", "v": "tally",
        "0": "zero", "1": "one", "L": "west", "R": "east",
        "$": "divider", "x": "ring", "y": "moon", "_": "hole",
    }
    # A rule's write, in words: None means leave the symbol as it is.
    WRITES = {None: "keep", **SYMBOLS}


def describe(symbols):
    words = [f'"{Words.SYMBOLS[c]}"' for c in symbols]
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


class Run:
    """The UTM's working state.  A class, so Jev doesn't see it all at once."""


def cells():
    return "".join(Run.tape.get(i, "_") for i in range(max(Run.tape) + 1))


def report(label):
    print(f"  simulated step {Run.completed}: UTM step {Run.utm_steps:4}   {label:9} {cells()}")


def utm_step():
    """Carry out one UTM step: Jev picks the rule, then applies it."""
    Run.symbol = Run.tape.get(Run.pos, "_")
    Run.choice = Run.rules[Run.state](Words.SYMBOLS[Run.symbol])
    utm.check_choice(Run.state, Run.symbol, Run.choice, Run.utm_steps)
    Run.rule = utm.RULES[Run.state][Run.choice]
    to_write, direction = Words.WRITES[Run.rule[1]], Words.SYMBOLS[Run.rule[2]]
    if to_write is "keep":
        Run.tape[Run.pos] = Run.symbol
    else:
        Run.tape[Run.pos] = Run.rule[1]
    if direction is "east":
        Run.pos += 1
    else:
        Run.pos -= 1
    Run.previous, Run.state = Run.state, Run.rule[3]
    Run.utm_steps += 1


def main(target=2):
    Run.rules = load_rules()
    start, table = utm.MACHINES["beaver"]
    tape_list, Run.origin, Run.states = utm.encode(start, table, pad=4)
    Run.tape, Run.pos, Run.state, Run.previous = dict(enumerate(tape_list)), 0, "find head", "nothing yet"
    Run.utm_steps, Run.completed = 0, 0
    print(f"Simulating the 2-state busy beaver for {target} step(s) on the UTM, "
          f"with Jev choosing each of its rules and running the loop.\n")
    calls_at_start = runtime.calls_made

    # One entry per simulated step still to run: Jev checks whether the list
    # is empty instead of comparing numbers.
    still_to_run = ["a step"] * target
    phase, previous = Run.state, Run.previous
    try:
        while phase is not "halt":
            if phase is "find head" and previous is something other than "find head":
                simulated_state = utm.decode(list(cells()), Run.origin, Run.states)[0]
                report(f"state {simulated_state}")
                if still_to_run is empty:
                    break
                still_to_run.pop()
                Run.completed += 1
            utm_step()
            phase, previous = Run.state, Run.previous
    except utm.WrongChoice as wrong:
        print(f"\nJev went wrong: {wrong}")
    if phase is "halt":
        report("halted")
    else:
        Run.completed -= 1  # counted when the step began, so not finished

    print(f"\n{Run.utm_steps} UTM steps, every rule and every step of the loop decided "
          f"by Jev ({runtime.calls_made - calls_at_start} calls).")
    done = max(Run.completed, 0)
    expected = list(utm.run_direct(start, table, done))[-1]
    got = utm.decode(list(cells()), Run.origin, Run.states)
    ok = got[:2] == expected[:2] and utm.same_tape(got[2], expected[2])
    print(f"After {done} simulated step(s): state {got[0]}, "
          f"{'matching' if ok else 'NOT matching'} a direct simulation.")


# `__name__` is hidden from Jev (it doesn't see dunders), so copy it out.
running_as, arguments = __name__, sys.argv[1:]
if running_as is "__main__":
    if arguments include "--show":
        print(jevlang_source())
    else:
        main(int(arguments[0]) if arguments else 2)
