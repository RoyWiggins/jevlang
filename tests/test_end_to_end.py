import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import jevlang
from jevlang import runtime
from jevlang.backends import FakeJev

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


@pytest.fixture(autouse=True)
def fake_backend():
    runtime.set_backend(FakeJev())
    yield
    runtime.set_backend(None)


def run(source: str, tmp_path: Path) -> dict:
    """Compile bytes with a coding cookie, exactly as an import would."""
    jevlang.register()
    path = tmp_path / "mod.py"
    path.write_text(source)
    ns = {"__file__": str(path), "__name__": "mod"}
    exec(compile(path.read_bytes(), str(path), "exec"), ns)
    return ns


def test_codec_bottles(tmp_path, capsys):
    run((EXAMPLES / "bottles.py").read_text(), tmp_path)
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "99 bottles of beer on the wall"
    assert out[-2] == "1 bottles of beer on the wall"
    assert len(out) == 100


def test_functions_see_their_locals(tmp_path):
    ns = run(textwrap.dedent("""\
        # coding: jev
        def describe(items):
            if there are no items:
                return "nothing"
            elif items has more than 2 entries:
                return "lots"
            return "some"
        """), tmp_path)
    assert [ns["describe"](x) for x in ([], [1], [1, 2, 3])] == ["nothing", "some", "lots"]


def test_match_binds_captures(tmp_path):
    ns = run(textwrap.dedent("""\
        # coding: jev
        def f(p):
            match p:
                case (0, 0):
                    return "origin"
                case (x, y) if x == y:
                    return f"diagonal {x}"
                case (x, y):
                    return f"{x},{y}"
        """), tmp_path)
    assert [ns["f"](p) for p in [(0, 0), (2, 2), (1, 3)]] == ["origin", "diagonal 2", "1,3"]


def test_backend_sees_context(tmp_path):
    seen = []

    class Spy(FakeJev):
        def decide(self, req):
            seen.append(req)
            return super().decide(req)

    runtime.set_backend(Spy())
    run("# coding: jev\nsecret = 42\nif the secret is positive:\n    pass\n", tmp_path)
    (req,) = seen
    assert req.variables == {"secret": 42}
    assert req.lineno == 3
    assert "--> 3 | if the secret is positive:" in req.code
    assert "secret = 42" in req.prompt()


def test_tracebacks_keep_line_numbers(tmp_path):
    with pytest.raises(ZeroDivisionError) as exc:
        run("# coding: jev\nif we feel like it:\n    pass\n1/0\n", tmp_path)
    assert exc.traceback[-1].lineno + 1 == 4


def _python_with_codec(*args, **kw):
    """Run a fresh interpreter where the codec is registered at startup,
    like the installed .pth does."""
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "JEV_BACKEND": "fake"}
    for key in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY"):
        env.pop(key, None)
    code = "import jevlang, runpy, sys; jevlang.register(); sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')"
    return subprocess.run([sys.executable, "-c", code, *args], env=env,
                          capture_output=True, text=True, timeout=30, **kw)


def test_weather_example_via_runpy():
    r = _python_with_codec(str(EXAMPLES / "weather.py"))
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == [
        "Stay inside.",
        "Bring an umbrella.",
        "...which you don't have.",
        "31 degrees. Sweltering.",
    ]


def test_cli_runner():
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "JEV_BACKEND": "fake"}
    r = subprocess.run([sys.executable, "-m", "jevlang", str(EXAMPLES / "fizzbuzz.py")],
                       env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz".split()
