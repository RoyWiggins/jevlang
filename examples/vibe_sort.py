# coding: jev
# Bubble sort, mildest first, where the comparison is Jev's judgment.
# Needs a real key: the fake backend can't taste anything.
foods = ["ghost pepper", "ketchup", "jalapeño", "habanero", "bell pepper", "sriracha"]

for i in range(len(foods)):
    for j in range(len(foods) - 1 - i):
        left, right = foods[j], foods[j + 1]
        if left is spicier than right:
            foods[j], foods[j + 1] = right, left

print(" < ".join(foods))
