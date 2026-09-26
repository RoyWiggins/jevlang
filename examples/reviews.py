# coding: jevlang
# The fake backend can't read; try this one with a real key.
reviews = [
    "Absolutely loved it, we're coming back next week!",
    "Cold food, and the waiter rolled his eyes at us.",
    "It was fine, I guess.",
]
for review in reviews:
    match review:
        case something enthusiastic:
            print("😀", review)
        case a complaint about the service or the food:
            print("😠", review)
        case _:
            print("😐", review)
