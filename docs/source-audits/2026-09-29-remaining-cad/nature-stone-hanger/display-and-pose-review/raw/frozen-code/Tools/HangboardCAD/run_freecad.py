"""Run a Python script under the pinned FreeCAD interpreter.

FreeCAD's launcher consumes unrecognised command-line options before a script
ever sees them, so `freecadcmd script.py --flag value` fails with
"unrecognised option '--flag'". This wrapper embeds the arguments in a generated
script instead, so they arrive as `sys.argv`, and it gives you a real exit code
and visible stdout/stderr.

    python3 Tools/HangboardCAD/run_freecad.py <script.py> [args...]

FreeCAD's interpreter also does not inherit PYTHONPATH. Set
HANGTEN_CAD_PYTHONPATH to any extra site directory (for example one containing
`pxr`), and the script under test is responsible for injecting it into
`sys.path`; the scripts here do that.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_FREECAD = Path("/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd")

# FreeCAD prints these on every run; they are noise for a script's own output.
_NOISE = (
    "FreeCAD 1.1.3",
    "(C) 2001-2026",
    "FreeCAD is free",
    "Importing project files",
)


def run(script: Path, arguments: list[str], freecad: Path, extra_path: str) -> int:
    script = script.resolve()
    if not script.is_file():
        print(f"no such script: {script}", file=sys.stderr)
        return 2
    if not freecad.is_file():
        print(f"pinned FreeCAD is not installed at {freecad}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="hangten-freecad-") as scratch:
        wrapper = Path(scratch) / "run.py"
        # FreeCAD's embedded interpreter block-buffers stdout when it is a pipe
        # and discards the buffer when a script exits through SystemExit, so a
        # script that ends with `raise SystemExit(main())` would report nothing
        # at all here. Flush both streams before the exit propagates.
        wrapper.write_text(
            "import sys, traceback\n"
            f"path = {str(script)!r}\n"
            f"sys.argv = [path] + {list(arguments)!r}\n"
            "try:\n"
            "    exec(compile(open(path).read(), path, 'exec'), "
            "{'__name__': '__main__', '__file__': path})\n"
            "except SystemExit:\n"
            "    raise\n"
            "except BaseException:\n"
            "    traceback.print_exc()\n"
            "    raise SystemExit(3)\n"
            "finally:\n"
            "    sys.stdout.flush()\n"
            "    sys.stderr.flush()\n"
        )
        environment = dict(os.environ)
        if extra_path:
            environment["HANGTEN_CAD_PYTHONPATH"] = extra_path
        # Inherit the caller's working directory: the scripts here locate the
        # repository from __file__, and a relative path argument must resolve
        # against where the user ran the command, not against the script.
        result = subprocess.run(
            [str(freecad), str(wrapper)],
            capture_output=True,
            text=True,
            env=environment,
        )

    for line in result.stdout.splitlines():
        if line.strip().startswith("(") or any(line.startswith(noise) for noise in _NOISE):
            continue
        if line.strip() in {"Recompute......", "Postprocessing......"}:
            continue
        print(line)
    if result.stderr.strip():
        print(result.stderr[-4000:], file=sys.stderr)
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    """Parse only this wrapper's own options, then pass the rest verbatim.

    Everything after the script belongs to the script, including flags, and must
    keep its original order. Manual parsing is used because argparse would
    reorder or reject the script's own options.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    freecad = DEFAULT_FREECAD
    extra_path = os.environ.get("HANGTEN_CAD_PYTHONPATH", "")
    script: Path | None = None

    while arguments:
        current = arguments[0]
        if current in {"-h", "--help"}:
            print(__doc__)
            return 0
        if current == "--freecad":
            arguments.pop(0)
            if not arguments:
                print("--freecad needs a path", file=sys.stderr)
                return 2
            freecad = Path(arguments.pop(0))
            continue
        if current == "--extra-python-path":
            arguments.pop(0)
            if not arguments:
                print("--extra-python-path needs a directory", file=sys.stderr)
                return 2
            extra_path = arguments.pop(0)
            continue
        if current.startswith("-"):
            print(f"unknown option for run_freecad.py: {current}", file=sys.stderr)
            return 2
        script = Path(arguments.pop(0))
        break

    if script is None:
        print(__doc__, file=sys.stderr)
        return 2
    return run(script, arguments, freecad, extra_path)


if __name__ == "__main__":
    raise SystemExit(main())