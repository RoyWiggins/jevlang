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
    }


def compile_rule(action, states):
    """Ask Jev what `action` does, one literal question at a time."""
    write = "unchanged"
    for symbol in ["0", "1", "blank"]:
        if action writes symbol onto the tape:
            write = symbol
            break
    # Left, right and staying put are exclusive, so one Choice weighs them
    # against each other.  (Asked separately, "leave it alone and move
    # right" once came out as moving left.)
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


def show(tape, head, state):
    lo, hi = min([*tape, head]), max([*tape, head])
    cells = [{"blank": "_"}.get(tape.get(i, "blank"), tape.get(i, "blank")) for i in range(lo, hi + 1)]
    print(f"  {' '.join(cells)}    [{state}]")
    print("  " + "  " * (head - lo) + "^")


def run(name, tape_text):
    machine = machines()[name]
    print(f"{name}: {machine['about']}\n")
    print("Compiling the rules:")
    program = {when: compile_rule(do, machine["states"]) for when, do in machine["rules"]}
    for when, do in machine["rules"]:
        op = program[when]
        arrow = {-1: "left", 0: "stay", 1: "right"}[op["move"]]
        print(f"  When {when}, {do}.\n      -> write {op['write']}, move {arrow}, next state {op['next']}")
    print()

    tape = {i: symbol for i, symbol in enumerate(tape_text)}
    head, state, steps = 0, machine["start"], 0
    while state is not halted:
        symbol = tape.get(head, "blank")
        show(tape, head, state)
        rule = find_rule(list(program), state, symbol)
        if rule is nothing:
            print(f"No rule covers {state!r} reading {symbol!r}. The machine is stuck.")
            return
        chosen = program[rule]
        tape[head] = {"unchanged": symbol}.get(chosen["write"], chosen["write"])
        head += chosen["move"]
        state = {"same": state}.get(chosen["next"], chosen["next"])
        steps += 1
    show(tape, head, state)
    lo, hi = min(tape), max(tape)
    result = "".join(tape.get(i, "blank") for i in range(lo, hi + 1)).replace("blank", "_").strip("_")
    print(f"\nHalted after {steps} steps. Tape: {result}")


args = sys.argv[1:]
run(args[0] if args else "increment", args[1] if len(args) > 1 else machines()[args[0] if args else "increment"]["tape"])
