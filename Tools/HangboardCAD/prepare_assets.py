"""Compile every source-backed board into a directory of runtime assets.

This is the step that lets the committed USDZ become a build output. It produces
the pair the app needs (`primary.usdz` and `primary.model.json`) for each board
that carries a CAD authoring source, and refuses to emit anything that does not
match the descriptor committed alongside the source.

The descriptor is the contract: `BoardPackageStore` rejects a package at runtime
when the delivered bytes do not hash to `modelSHA256`. So a compiled asset is only
usable if the derived descriptor equals the committed one, which is exactly what
this checks before writing.

    python3 Tools/HangboardCAD/prepare_assets.py --out <directory>
    python3 Tools/HangboardCAD/prepare_assets.py --out <dir> --package <slug>

Writes `<out>/<package>/assets/primary.usdz` and `.../primary.model.json`.
Run with the host interpreter; FreeCAD is invoked as a subprocess.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
TOOLS = REPOSITORY / "Tools" / "HangboardCAD"
DEFAULT_FREECAD = Path("/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd")
SOURCE_SUFFIX = ".FCStd"


def source_backed_packages() -> list[str]:
    return sorted(
        path.parent.name
        for path in (REPOSITORY / "Hangboards").glob(f"*/*{SOURCE_SUFFIX}")
        if path.name == f"{path.parent.name}{SOURCE_SUFFIX}"
    )


def _run_build(package: str, destination: Path, freecad: Path, extra_path: str) -> None:
    """Run one board's build into a scratch directory, in a fresh process.

    FreeCAD's launcher consumes unrecognised options before the script ever sees
    them, so the arguments are embedded in a generated wrapper.
    """
    destination.mkdir(parents=True, exist_ok=True)
    wrapper = destination / "_build.py"
    arguments = [
        "--package", package,
        "--source", str(REPOSITORY / "Hangboards" / package / f"{package}{SOURCE_SUFFIX}"),
        "--assets", str(destination),
    ]
    wrapper.write_text(
        "import sys, traceback\n"
        f"path = {str(TOOLS / 'compile_board.py')!r}\n"
        f"sys.argv = [path] + {arguments!r}\n"
        "try:\n"
        "    exec(compile(open(path).read(), path, 'exec'), "
        "{'__name__': '__main__', '__file__': path})\n"
        "except SystemExit:\n"
        "    raise\n"
        "except BaseException:\n"
        "    traceback.print_exc()\n"
        "    raise SystemExit(3)\n"
    )
    environment = dict(os.environ)
    if extra_path:
        environment["HANGTEN_CAD_PYTHONPATH"] = extra_path
    result = subprocess.run(
        [str(freecad), str(wrapper)],
        capture_output=True,
        text=True,
        env=environment,
        cwd=str(REPOSITORY),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"compiling {package} failed (exit {result.returncode})\n"
            f"{result.stdout[-2000:]}{result.stderr[-2000:]}"
        )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(package: str, out: Path, freecad: Path, extra_path: str) -> dict:
    committed_descriptor = (
        REPOSITORY / "Hangboards" / package / "assets" / "primary.model.json"
    )
    if not committed_descriptor.is_file():
        raise RuntimeError(f"{package} has no committed descriptor to compile against")
    committed = json.loads(committed_descriptor.read_text())

    with tempfile.TemporaryDirectory(prefix=f"hangten-prepare-{package}-") as scratch:
        staging = Path(scratch) / "assets"
        _run_build(package, staging, freecad, extra_path)
        built_asset = staging / "primary.usdz"
        built_descriptor = staging / "primary.model.json"
        if not built_asset.is_file() or not built_descriptor.is_file():
            raise RuntimeError(f"{package}: the build produced no asset/descriptor pair")
        derived = json.loads(built_descriptor.read_text())
        if derived != committed:
            raise RuntimeError(
                f"{package}: the compiled descriptor does not match the committed one; "
                "the source and the descriptor have diverged, or this platform does not "
                "reproduce the committed bytes"
            )
        digest = sha256(built_asset)
        if derived.get("modelSHA256") != digest:
            raise RuntimeError(
                f"{package}: the compiled asset does not hash to the descriptor's "
                "modelSHA256, so the app would reject it"
            )

        target = out / package / "assets"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(built_asset, target / "primary.usdz")
        shutil.copyfile(built_descriptor, target / "primary.model.json")
        return {
            "package": package,
            "assetSHA256": digest,
            "bytes": (target / "primary.usdz").stat().st_size,
            "out": str((target / "primary.usdz").relative_to(out)),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--package", action="append", default=None)
    parser.add_argument("--freecad", type=Path, default=DEFAULT_FREECAD)
    parser.add_argument(
        "--extra-python-path",
        default=os.environ.get("HANGTEN_CAD_PYTHONPATH", ""),
        help="site directory containing pxr, supplied to FreeCAD's interpreter",
    )
    arguments = parser.parse_args(argv)

    packages = arguments.package or source_backed_packages()
    if not packages:
        print(json.dumps({"prepared": [], "note": "no source-backed boards"}, indent=2))
        return 0
    if not arguments.freecad.is_file():
        print(f"pinned FreeCAD is not installed at {arguments.freecad}", file=sys.stderr)
        return 2

    prepared: list[dict] = []
    failures: list[str] = []
    for package in packages:
        try:
            report = prepare(package, arguments.out, arguments.freecad, arguments.extra_python_path)
        except RuntimeError as error:
            failures.append(f"{package}: {error}")
            continue
        prepared.append(report)
        print(f"  {package}: {report['bytes']} bytes  {report['assetSHA256'][:16]}")

    print(json.dumps({"prepared": prepared, "failures": failures}, indent=2, sort_keys=True))
    if failures:
        print(f"\n{len(failures)} board(s) failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(f"\nprepared {len(prepared)} board(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())