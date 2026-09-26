# coding: jev
# Tic-tac-toe where Jev makes every decision: which square you meant, whether
# it's free, whether a line is complete, where O plays, and who won.  Python
# only stores the board, prints it, and lists which squares form lines.
#
# Jev can't reliably spot three in a row on a whole board, so it is asked
# about one line at a time instead.  It sort of works: a five-move game took
# about 230 calls, so run it with JEV_MAX_CALLS=300.
#
# Conditions name the variable they're about (`just_won is true`), and "no
# square" is the word "nothing" rather than None: Jev was unsure about both.
board = {
    "top left": "empty", "top middle": "empty", "top right": "empty",
    "middle left": "empty", "center": "empty", "middle right": "empty",
    "bottom left": "empty", "bottom middle": "empty", "bottom right": "empty",
}
LINES = [
    ("top left", "top middle", "top right"),
    ("middle left", "center", "middle right"),
    ("bottom left", "bottom middle", "bottom right"),
    ("top left", "middle left", "bottom left"),
    ("top middle", "center", "bottom middle"),
    ("top right", "middle right", "bottom right"),
    ("top left", "center", "bottom right"),
    ("top right", "center", "bottom left"),
]
LINES_THROUGH = {}
for line in LINES:
    for name in line:
        LINES_THROUGH.setdefault(name, []).append(line)


def show():
    marks = [{"empty": " "}.get(mark, mark) for mark in board.values()]
    for row in range(3):
        print(" " + " | ".join(marks[3 * row : 3 * row + 3]))
    print()


def square_for(description):
    match description:
        case the top left square:
            return "top left"
        case the top middle square:
            return "top middle"
        case the top right square:
            return "top right"
        case the middle left square:
            return "middle left"
        case the center square:
            return "center"
        case the middle right square:
            return "middle right"
        case the bottom left square:
            return "bottom left"
        case the bottom middle square:
            return "bottom middle"
        case the bottom right square:
            return "bottom right"
    return "nothing"


def completes_a_line(player, square, marks):
    """Would `player` on `square` make three in a row, given `marks`?"""
    for line in LINES_THROUGH[square]:
        first, second, third = (marks[name] for name in line)
        if first, second and third are all the same as player:
            return True
    return False


def free_square():
    for candidate, mark_there in board.items():
        if mark_there is empty:
            return candidate
    return "nothing"


def completing_square(player):
    """A free square where `player` would get three in a row, if any."""
    for candidate, mark_there in board.items():
        if mark_there is empty:
            would_win = completes_a_line(player, candidate, {**board, candidate: player})
            if would_win is true:
                return candidate
    return "nothing"


def jev_move():
    move = completing_square("O")  # win if we can
    if move is nothing:
        move = completing_square("X")  # otherwise block
    if move is nothing:
        move = free_square()
    return move


def human_move():
    typed = input("Your move (X), e.g. 'top left' or 'middle': ")
    square = square_for(typed)
    if square is nothing:
        print("I couldn't tell which square you meant.")
        return human_move()
    mark_there = board[square]
    if mark_there is an X or an O:
        print(f"The {square} square is taken.")
        return human_move()
    return square


def play():
    winner = "nothing"
    spare_square = free_square()
    while winner is nothing and spare_square is not nothing:
        show()
        square = human_move()
        board[square] = "X"
        just_won = completes_a_line("X", square, board)
        if just_won is true:
            winner = "X"
            break
        move = jev_move()
        if move is nothing:
            break
        print(f"Jev plays the {move} square.")
        board[move] = "O"
        just_won = completes_a_line("O", move, board)
        if just_won is true:
            winner = "O"
        spare_square = free_square()

    show()
    match winner:
        case the human playing X:
            print("You win!")
        case Jev playing O:
            print("Jev wins!")
        case nobody, it's a draw:
            print("It's a draw.")


play()
