# coding: jev
# A tiny text adventure where Jev makes every decision: what you're trying
# to do, which way you mean, which thing you mean, and whether whatever you
# try actually works.  Python only stores the world and prints text.
#
# The world lives in a class because jevlang doesn't send classes to Jev.
# Each function copies out just the facts its questions need, which keeps
# Jev focused.  About 5 calls a turn; needs a real key.


class World:
    location = "cellar"
    door = "locked"
    key = "hidden"
    dog = "angry"
    carrying = []
    items = {"cellar": [], "kitchen": ["meaty bone"], "garden": []}
    exits = {
        "cellar": {"up": "kitchen"},
        "kitchen": {"down": "cellar", "outside": "garden"},
        "garden": {},
    }
    descriptions = {
        "cellar": "You're in a damp cellar. Stone stairs lead up to a wooden "
                  "door. A pile of old straw sits in the corner.",
        "kitchen": "You're in a farmhouse kitchen. Stairs lead down to the "
                   "cellar, and a back door leads outside.",
        "garden": "You're in a sunny garden.",
    }


def describe():
    room, dog = World.location, World.dog
    print(World.descriptions[room])
    items_here = World.items[room]
    if items_here has anything in it:
        print("You see: " + ", ".join(items_here) + ".")
    if room is the kitchen and dog is angry:
        print("A huge dog stands in front of the back door, growling at you.")


def go(command):
    direction = "nowhere"
    match command:
        case going up or climbing:
            direction = "up"
        case going down or descending:
            direction = "down"
        case going outside or out through a door:
            direction = "outside"
    destination = World.exits[World.location].get(direction, "nowhere")
    door, dog = World.door, World.dog
    if destination is nowhere:
        print("You can't go that way.")
    elif destination is the kitchen and door is locked:
        print("The door at the top of the stairs is locked.")
    elif destination is the garden and dog is angry:
        print("The dog snarls and won't let you near the back door.")
    else:
        World.location = destination
        describe()


def take(command):
    items_here = World.items[World.location]
    for item in items_here:
        if command is asking for the item:
            items_here.remove(item)
            World.carrying.append(item)
            print(f"You take the {item}.")
            return
    print("You don't see that here.")


def inventory():
    carrying = World.carrying
    if carrying is empty:
        print("You aren't carrying anything.")
    else:
        print("You're carrying: " + ", ".join(carrying) + ".")


def act(action):
    """Anything that isn't moving, taking or looking: Jev judges whether it works."""
    room, carrying, dog, key = World.location, World.carrying, World.dog, World.key
    if room is the cellar and action is about the pile of straw or hay in the corner:
        if key is still hidden:
            World.key = "found"
            World.items["cellar"].append("rusty key")
            print("Buried in the straw you find a rusty key!")
        else:
            print("Just straw.")
    elif room is the cellar and action is trying to unlock or open the door:
        if carrying includes a key:
            World.door = "unlocked"
            print("The key turns with a clunk. The door is unlocked.")
        else:
            print("It's locked. You'd need a key.")
    elif room is the kitchen and dog is angry and action might calm down or befriend a dog:
        if action uses something that isn't in carrying:
            print("You don't have that.")
        else:
            World.dog = "calm"
            print("The dog's tail starts to wag. It trots off to its bed by the stove.")
    else:
        print("Nothing happens.")


def play():
    describe()
    location = World.location
    while location is not the garden:
        command = input("> ")
        match command:
            case moving somewhere or going in a direction:
                go(command)
            case picking up or taking an object:
                take(command)
            case searching, examining or rummaging through a particular thing:
                act(command)
            case asking to look around or to have the room described again:
                describe()
            case checking what they are carrying:
                inventory()
            case quitting the game:
                print("You give up.")
                return
            case _:
                act(command)
        location = World.location
    print("You've escaped! You win.")


play()
