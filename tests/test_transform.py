import ast

from jevlang.transform import JEV, pattern_captures, transform


def test_english_while_is_rewritten():
    out = transform("while there are bottles left:\n    pass\n")
    assert out == f"while {JEV}.cond('while', 'there are bottles left', 1, locals()):\n    pass\n"


def test_output_is_valid_python_with_same_line_count():
    src = (
        "# coding: jevlang\n"
        "if it's raining:  # a comment\n"
        "    x = 1\n"
        "elif the sky is falling:\n"
        "    x = 2\n"
        "else:\n"
        "    x = 3\n"
    )
    out = transform(src)
    ast.parse(out)
    assert len(out.splitlines()) == len(src.splitlines())
    assert "\"it's raining\", 2," in out
    assert "'the sky is falling', 4," in out


def test_colons_inside_condition_are_kept():
    out = transform("if d[1:2] and (lambda x: x)(1):\n    pass\n")
    assert "'d[1:2] and (lambda x: x)(1)'" in out


def test_strings_and_brackets_are_not_headers():
    src = (
        'doc = """\n'
        "if this were code:\n"
        '"""\n'
        "xs = [x for x in range(3)\n"
        "      if x:\n"
        "      ]\n"
        "y = 1 if x else 2\n"
    )
    assert transform(src) == src


def test_match_cases_are_numbered_and_keep_captures():
    src = (
        "match point:\n"
        "    case (0, 0):\n"
        "        pass\n"
        "    case (x, y) if x > y:\n"
        "        pass\n"
        "    case somewhere far away:\n"
        "        match other:\n"
        "            case _:\n"
        "                pass\n"
    )
    out = transform(src)
    ast.parse(out)
    lines = out.splitlines()
    assert lines[1] == "    case (0, {}):"
    assert lines[3] == "    case (1, {'x': x, 'y': y}):"
    assert lines[5] == "    case (2, {}):"
    assert lines[7] == "            case (0, {}):"
    assert "[('(0, 0)', []), ('(x, y) if x > y', ['x', 'y']), ('somewhere far away', None)]" in lines[0]
    assert lines[0].endswith("locals(), (point)):")


def test_english_match_subject_passes_no_value():
    out = transform("match the weather:\n    case _:\n        pass\n")
    assert out.splitlines()[0].endswith("locals()):")


def test_pattern_captures():
    assert pattern_captures("_") == []
    assert pattern_captures("[a, *rest]") == ["a", "rest"]
    assert set(pattern_captures("{'k': v, **kw}")) == {"v", "kw"}
    assert pattern_captures("Point(x=0) as p") == ["p"]
    assert pattern_captures("something odd") is None


def test_english_guard_on_python_pattern():
    from jevlang.transform import split_guard

    assert pattern_captures("(x, y) if it looks far away") == ["x", "y"]
    assert split_guard("(x, y) if it looks far away") == ("(x, y)", "it looks far away", False)
    assert split_guard("(x, y) if x > y") == ("[x, y]", "x > y", True)
    assert split_guard("something vague") is None


def test_roll_comment():
    out = transform("if the plan works:  # jev: roll\n    pass\nif plain:  # just a comment\n    pass\n")
    lines = out.splitlines()
    assert lines[0].endswith("locals(), 'roll'):")
    assert lines[2].endswith("locals()):")
