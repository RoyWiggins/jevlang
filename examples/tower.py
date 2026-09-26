# coding: jev
# The Wizard's Tower: a text adventure where Jev is the game master.
#
#   * The troll's riddle has no single answer: Jev judges whatever you say.
#   * The cellar is dark: Jev decides whether anything you carry gives light.
#   * The ghost only lets you pass if your joke would make it laugh, and the
#     dragon stays asleep only if you're gentle enough.  Those two are
#     `# jev: roll` conditions: Jev's probability is the chance of success.
#   * Hints and replies to silly actions are picked by Jev too.
#
# Python stores the world, prints text, and nothing else.  Needs a real key;
# a playthrough is about 100-150 calls, so run it with JEV_MAX_CALLS=300.
import jevlang.runtime as jev


class World:
    # Kept in a class: jevlang doesn't show classes to Jev, so each function
    # copies out just the facts its questions need.
    location = "meadow"
    state = "playing"
    troll = "guarding"
    ghost = "gloomy"
    carrying = []
    riddle = "What has a neck but no head?"
    items = {
        "meadow": ["jar of fireflies"],
        "courtyard": ["rusty bucket"],
        "hall": ["box of matches"],
        "cellar": ["silver wand"],
        "library": [],
        "study": [],
    }
    exits = {
        "meadow": {"north": "courtyard"},
        "courtyard": {"south": "meadow", "north": "hall"},
        "hall": {"south": "courtyard", "up": "library", "down": "cellar"},
        "cellar": {"up": "hall"},
        "library": {"down": "hall", "up": "study"},
        "study": {"down": "library"},
    }
    descriptions = {
        "meadow": "You're in a wildflower meadow. A rickety bridge leads north "
                  "over a stream to a crooked stone tower.",
        "courtyard": "You're in the tower's overgrown courtyard. The tower door "
                     "stands open to the north; the bridge is back to the south.",
        "hall": "You're in a round entrance hall. A staircase winds up, and a "
                "narrow stair goes down into darkness. The courtyard is south.",
        "cellar": "You're in a cold cellar full of dusty shelves. Stairs lead up.",
        "library": "You're in a library of mouldering books. The stairs go on "
                   "up, and back down to the hall.",
        "study": "You're in the wizard's study. Stars are painted on the "
                 "ceiling. A tiny dragon is asleep on the desk. Stairs lead down.",
    }


def odds():
    return f"({jev.last_decision.odds:.0%} chance)"


def light_level():
    carrying = World.carrying
    if something in carrying could light up a dark room:
        return "lit"
    return "dark"


def describe():
    room = World.location
    troll, ghost, riddle = World.troll, World.ghost, World.riddle
    carrying, items_here = World.carrying, World.items[room]
    match room:
        case "cellar":
            light = light_level()
            if light is dark:
                print("It's pitch black. Somewhere, water drips.")
                return
        case "meadow":
            if troll is guarding the bridge:
                print(World.descriptions[room])
                print(f"A troll squats on the bridge. \"Answer my riddle to cross: {riddle}\"")
                return
        case "library":
            if ghost is gloomy:
                print(World.descriptions[room])
                print("A gloomy ghost hovers in front of the stairs up, sighing.")
                return
        case "study":
            if carrying includes the spellbook:
                print(World.descriptions[room])
                return
            print(World.descriptions[room])
            print("It's curled around a spellbook.")
            return
    print(World.descriptions[room])
    if items_here has anything in it:
        print("You see: " + ", ".join(items_here) + ".")


def go(command):
    direction = "nowhere"
    match command:
        case going north: across the bridge, or into the tower:
            direction = "north"
        case going south: out of the tower, or back over the bridge:
            direction = "south"
        case going up: upstairs, climbing, or back up the stairs:
            direction = "up"
        case going down: downstairs, descending, or down the stairs:
            direction = "down"
    destination = World.exits[World.location].get(direction, "nowhere")
    troll, ghost = World.troll, World.ghost
    if destination is nowhere:
        print("You can't go that way.")
    elif destination is the courtyard and troll is guarding:
        print("The troll blocks the bridge. \"Riddle first!\"")
    elif destination is the study and ghost is gloomy:
        print("The ghost drifts in front of the stairs and sighs so sadly you can't bear to push past.")
    else:
        World.location = destination
        describe()


def take(command):
    room, carrying = World.location, World.carrying
    match room:
        case "cellar":
            light = light_level()
            if light is dark:
                print("You grope around in the dark and find nothing.")
                return
        case "study":
            if command is about the spellbook:
                sneak(command)
                return
    items_here = World.items[room]
    for item in items_here:
        if command is asking for the item:
            items_here.remove(item)
            carrying.append(item)
            print(f"You take the {item}.")
            return
    print("You don't see that here.")


def sneak(action):
    carrying = World.carrying
    if carrying includes the spellbook:
        print("The dragon snores on. You already have what you came for.")
        return
    if action is gentle and quiet enough not to wake a sleeping dragon:  # jev: roll
        carrying.append("spellbook")
        print(f"Holding your breath, you ease the spellbook free. The dragon sleeps on. {odds()}")
    else:
        print(f"One golden eye snaps open. ROAR! You tumble down the stairs. {odds()}")
        World.location = "library"


def talk(what_you_said):
    room, troll, ghost, riddle = World.location, World.troll, World.ghost, World.riddle
    match room:
        case "meadow":
            if troll is gone:
                print("The meadow is quiet.")
            elif what_you_said is a correct answer to the riddle:
                World.troll = "gone"
                print("The troll groans. \"Fine. FINE.\" It stomps off downstream.")
            else:
                print("\"WRONG!\" bellows the troll.")
        case "library":
            if ghost is cheerful:
                print("The ghost is still chuckling to itself.")
            elif what_you_said would make a gloomy ghost laugh:  # jev: roll
                World.ghost = "cheerful"
                print(f"The ghost snorts, then howls with laughter and floats aside. {odds()}")
            else:
                print(f"The ghost sighs even more deeply. {odds()}")
        case _:
            print("Nobody answers.")


def act(action):
    room, carrying = World.location, World.carrying
    if action is casting a spell, waving a wand or reading from a spellbook:
        if carrying includes both a wand and a spellbook:
            print("You raise the wand and read the spell aloud. Light pours from")
            print("the pages and the whole tower sings. You are the wizard now.")
            World.state = "won"
        else:
            print("You wave your arms mysteriously. Nothing happens.")
        return
    match room:
        case "study":
            if action is about the spellbook or the dragon:
                sneak(action)
                return
    match action:
        case something violent or aggressive:
            print("Violence isn't the answer. Probably.")
        case singing, dancing or performing:
            print("You give a stirring performance to an audience of no one.")
        case eating, drinking or tasting something:
            print("You'd rather not put that in your mouth.")
        case sleeping or resting:
            print("You nap briefly. You feel refreshed, but no closer to your goal.")
        case _:
            print("Nothing happens.")


def hint():
    # The order of the quest lives here; Jev just answers each question.
    troll, ghost, carrying = World.troll, World.ghost, World.carrying
    if troll is guarding:
        print("The troll wants an answer to its riddle. Try saying one.")
    elif carrying has nothing that glows or burns:
        print("You'll want a light before you go poking around the cellar.")
    elif carrying has no wand:
        print("Wizards need wands. Have you checked below the hall?")
    elif ghost is gloomy:
        print("The ghost could do with a laugh.")
    elif carrying has no spellbook:
        print("The spellbook is in the study. Be very, very gentle.")
    else:
        print("You have everything. Cast the spell!")


def inventory():
    carrying = World.carrying
    if carrying is empty:
        print("You aren't carrying anything.")
    else:
        print("You're carrying: " + ", ".join(carrying) + ".")


def play():
    print("THE WIZARD'S TOWER\n")
    describe()
    state = World.state
    while state is playing:
        command = input("\n> ")
        match command:
            case walking or travelling to another place, like north or up the stairs:
                go(command)
            case picking up or taking an object:
                take(command)
            case talking to someone, answering a riddle or telling a joke:
                talk(command)
            case asking for a hint or for help:
                hint()
            case checking what they are carrying:
                inventory()
            case asking to look around or have the room described again:
                describe()
            case quitting the game:
                print("You give up and go home.")
                return
            case _:
                act(command)
        state = World.state
    print("\nTHE END")


play()
