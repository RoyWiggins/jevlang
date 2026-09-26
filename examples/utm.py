# coding: jevlang
# A "universal" Turing machine, the cheap way.
#
# Its tape holds another machine's program, written as English entries, plus
# that machine's own tape.  The universal machine's rules are five high-level
# English instructions ("find the program entry that matches..."), and Jev
# carries each one out.  The hard part of a real UTM, matching and copying
# symbols one square at a time, is hidden inside Jev, so this is a joke.
# See turing.py for machines that do their own work.
#
#   python examples/utm.py        # run the simulated busy beaver to the end
#   python examples/utm.py 2      # ... for two simulated steps
import sys


def program():
    """The simulated machine: the 2-state busy beaver, as entries on the tape."""
    return {
        "states": ["A", "B", "halt"],
        "start": "A",
        "entries": [
            "in state A on a blank: write a 1, move right, become B",
            "in state A on a 1: keep the 1, move left, become B",
            "in state B on a blank: write a 1, move left, become A",
            "in state B on a 1: keep the 1, move right, become halt",
        ],
    }


def look_up(entries, sim_state, symbol):
    for entry in entries:
        # The UTM reads the part before the colon: that's the entry's condition.
        condition = entry.partition(":")[0]
        if condition is about being in sim_state and reading symbol:
            return entry
    return "nothing"


def symbol_to_write(action, symbol):
    match action:
        case writing a 1:
            return "1"
        case writing a blank or erasing:
            return "blank"
        case keeping the symbol that's already there:
            return symbol
    return symbol


def direction(action):
    match action:
        case moving left:
            return -1
        case moving right:
            return 1
        case staying put:
            return 0
    return 0


def next_state(action, states):
    for candidate in states:
        if action says to become candidate:
            return candidate
    return "nothing"


def show(tape, head):
    lo, hi = min([*tape, head]), max([*tape, head])
    cells = [{"blank": "_", "1": "1"}[tape.get(i, "blank")] for i in range(lo, hi + 1)]
    return " ".join(f"[{c}]" if i + lo == head else f" {c} " for i, c in enumerate(cells))


def run(max_steps):
    prog = program()
    entries, states = prog["entries"], prog["states"]
    print("Program on the tape:")
    for entry in entries:
        print(f"  {entry}")
    print()

    sim_tape, sim_head, sim_state = {}, 0, prog["start"]
    utm_state, entry, symbol, steps = "reading", "nothing", "blank", 0
    while utm_state is not halted:
        # The universal machine's own rules, in English.  Jev picks which one
        # applies, then carries it out.
        match utm_state:
            case reading: note the simulated state and the symbol under the simulated head:
                symbol = sim_tape.get(sim_head, "blank")
                print(f"step {steps + 1}   {show(sim_tape, sim_head)}   state {sim_state}")
                utm_state = "looking up"
            case looking up: find the program entry that matches the state and symbol:
                entry = look_up(entries, sim_state, symbol)
                if entry is nothing:
                    print(f"  no entry for state {sim_state} on {symbol}: the machine is stuck")
                    return
                print(f"  found:  {entry}")
                utm_state = "writing"
            case writing: write the entry's symbol under the simulated head:
                action = entry.partition(":")[2]
                sim_tape[sim_head] = symbol_to_write(action, symbol)
                utm_state = "moving"
            case moving: move the simulated head the way the entry says:
                sim_head += direction(entry.partition(":")[2])
                utm_state = "switching"
            case switching: change the simulated state to the entry's next state:
                sim_state = next_state(entry.partition(":")[2], states)
                steps += 1
                if sim_state is halt:
                    utm_state = "halted"
                elif steps is max_steps:
                    utm_state = "halted"
                else:
                    utm_state = "reading"

    print(f"\n          {show(sim_tape, sim_head)}   state {sim_state}")
    ones = list(sim_tape.values()).count("1")
    print(f"\nThe universal machine ran {steps} simulated steps. The tape has {ones} ones.")


run(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
