# coding: jevlang
# A Turing machine whose program is written in English.
#
# Each rule is two bits of English: when it applies, and what it does.  Jev
# "compiles" the what-it-does half once (what does it write, which way does
# it move, what state comes next?) and then, every step, decides which rule's
# when-half fits the current state and symbol.  Python only keeps the tape.
#
#   python examples/turing.py                  # binary increment of 1011
#   python examples/turing.py increment 111
#   python examples/turing.py beaver           # the 2-state busy beaver
#   python examples/turing.py beaver3          # the 3-state busy beaver
#   python examples/turing.py wolfram          # Wolfram's universal (2,3) machine
#   python examples/turing.py wolfram "" 40    # ... for 40 steps
import sys


def machines():
    # Inside a function so Jev doesn't see every machine on every question.
    return {
        "increment": {
            "about": "Adds one to a binary number.",
            "tape": "1011",
            "start": "scanning right",
            "states": ["scanning right", "carrying", "halted"],
            "rules": [
                ("scanning right over a 0 or a 1", "leave it alone and move right"),
                ("scanning right and you reach a blank", "move left and start carrying"),
                ("carrying and you see a 1", "write a 0 and move left, still carrying"),
                ("carrying and you see a 0 or a blank", "write a 1 and halt"),
            ],
        },
        "beaver": {
            "about": "The 2-state busy beaver: writes four 1s on a blank tape, then halts.",
            "tape": "",
            "start": "A",
            "states": ["A", "B", "halted"],
            "rules": [
                ("in state A on a blank square", "write a 1, move right and switch to state B"),
                ("in state A on a 1", "leave it, move left and switch to state B"),
                ("in state B on a blank square", "write a 1, move left and go back to state A"),
                ("in state B on a 1", "leave it, move right and halt"),
            ],
        },
        "beaver3": {
            "about": "The 3-state busy beaver: writes six 1s on a blank tape in 14 steps, then halts.",
            "tape": "",
            "start": "A",
            "states": ["A", "B", "C", "halted"],
            "rules": [
                ("in state A on a blank square", "write a 1, move right and switch to state B"),
                ("in state A on a 1", "leave it, move right and halt"),
                ("in state B on a blank square", "leave it blank, move right and switch to state C"),
                ("in state B on a 1", "leave it, move right and stay in state B"),
                ("in state C on a blank square", "write a 1, move left and stay in state C"),
                ("in state C on a 1", "leave it, move left and switch to state A"),
            ],
        },
        "wolfram": {
            "about": "Wolfram's 2-state, 3-symbol machine, the smallest known "
                     "universal Turing machine. It never halts; this runs 20 steps.",
            "tape": "",
            "start": "A",
            "states": ["A", "B"],
            "blank": "0",
            "max_steps": 20,
            "rules": [
                ("in state A on a 0", "write a 1, move right and switch to state B"),
                ("in state A on a 1", "write a 2, move left and stay in state A"),
                ("in state A on a 2", "write a 1, move left and stay in state A"),
                ("in state B on a 0", "write a 2, move left and switch to state A"),
                ("in state B on a 1", "write a 2, move right and stay in state B"),
                ("in state B on a 2", "write a 0, move right and switch to state A"),
            ],
        },
    }


def compile_rule(action, states):
    """Ask Jev what `action` does."""
    # What to write and which way to move are each one Choice, weighing the
    # options against each other.  Asked as separate yes/no questions, Jev
    # was unsure about digits ("write a 1" came out as writing a 0) and
    # read "leave it alone and move right" as moving left.
    write = "unchanged"
    match action:
        case writing a 0:
            write = "0"
        case writing a 1:
            write = "1"
        case writing a 2:
            write = "2"
        case writing a blank or erasing the square:
            write = "blank"
        case not writing anything: leaving the square alone, only moving or changing state:
            write = "unchanged"
    match action:
        case moving the head to the left:
            move = -1
        case moving the head to the right:
            move = 1
        case _:
            move = 0
    next_state = "same"
    for candidate in states:
        if action puts the machine into the candidate state:
            next_state = candidate
            break
    return {"write": write, "move": move, "next": next_state}


def find_rule(conditions, state, symbol):
    for condition in conditions:
        if condition describes being in state and reading symbol:
            return condition
    return "nothing"


def show(tape, head, state, blank):
    lo, hi = min([*tape, head]), max([*tape, head])
    cells = [{"blank": "_"}.get(tape.get(i, blank), tape.get(i, blank)) for i in range(lo, hi + 1)]
    print(f"  {' '.join(cells)}    [{state}]")
    print("  " + "  " * (head - lo) + "^")


def run(name, tape_text, max_steps=None):
    machine = machines()[name]
    print(f"{name}: {machine['about']}\n")
    print("Compiling the rules:")
    blank = machine.get("blank", "blank")
    program = {when: compile_rule(do, machine["states"]) for when, do in machine["rules"]}
    for when, do in machine["rules"]:
        op = program[when]
        arrow = {-1: "left", 0: "stay", 1: "right"}[op["move"]]
        print(f"  When {when}, {do}.\n      -> write {op['write']}, move {arrow}, next state {op['next']}")
    print()

    tape = {i: symbol for i, symbol in enumerate(tape_text)}
    head, state, steps = 0, machine["start"], 0
    # A for loop, not `while steps < limit`: Jev isn't a calculator.
    for _ in range(max_steps or machine.get("max_steps", 1000)):
        if state is halted:
            break
        symbol = tape.get(head, blank)
        show(tape, head, state, blank)
        rule = find_rule(list(program), state, symbol)
        if rule is nothing:
            print(f"No rule covers {state!r} reading {symbol!r}. The machine is stuck.")
            return
        chosen = program[rule]
        tape[head] = {"unchanged": symbol}.get(chosen["write"], chosen["write"])
        head += chosen["move"]
        state = {"same": state}.get(chosen["next"], chosen["next"])
        steps += 1
    show(tape, head, state, blank)
    lo, hi = min(tape), max(tape)
    result = "".join(tape.get(i, blank) for i in range(lo, hi + 1)).replace("blank", "_").strip("_")
    if state is halted:
        print(f"\nHalted after {steps} steps. Tape: {result}")
    else:
        print(f"\nStopped after {steps} steps without halting. Tape: {result}")


args = sys.argv[1:]
name = args[0] if args else "increment"
run(name,
    args[1] if len(args) > 1 else machines()[name]["tape"],
    int(args[2]) if len(args) > 2 else None)
