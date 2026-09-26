"""``python -m jevlang``: run, inspect, or install."""

from __future__ import annotations

import argparse
import os
import site
import sys
import sysconfig

from . import runtime
from .transform import transform

PTH_NAME = "jevlang.pth"
PTH_LINE = "import jevlang.codec; jevlang.codec.register()\n"


def run_file(path: str, argv: list[str]) -> None:
    with open(path, "rb") as f:
        source = f.read().decode("utf-8-sig")
    code = compile(transform(source), path, "exec")
    module_globals = {"__name__": "__main__", "__file__": path, "__builtins__": __builtins__}
    module_globals["__jev__"] = runtime.Session(path, source, module_globals)
    sys.argv = [path, *argv]
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    exec(code, module_globals)


def install_pth(user: bool) -> str:
    target = site.getusersitepackages() if user else sysconfig.get_paths()["purelib"]
    os.makedirs(target, exist_ok=True)
    path = os.path.join(target, PTH_NAME)
    with open(path, "w") as f:
        f.write(PTH_LINE)
    return path


def main(args: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        prog="jevlang",
        description="Run Python whose if/while/match decisions are made by Jev.",
    )
    p.add_argument("file", nargs="?", help="script to run")
    p.add_argument("args", nargs=argparse.REMAINDER, help="arguments for the script")
    p.add_argument("--show", action="store_true", help="print the transformed source instead of running it")
    p.add_argument("--install-pth", action="store_true",
                   help=f"install {PTH_NAME} so '# coding: jev' works with plain `python`")
    p.add_argument("--user", action="store_true", help="with --install-pth: use the user site-packages")
    ns = p.parse_args(args)

    if ns.install_pth:
        print(f"wrote {install_pth(ns.user)}")
        return
    if not ns.file:
        p.error("a file is required")
    if ns.show:
        with open(ns.file, "rb") as f:
            sys.stdout.write(transform(f.read().decode("utf-8-sig")))
        return
    run_file(ns.file, ns.args)


if __name__ == "__main__":
    main()
