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

from presentation_targets import source_targets

REPOSITORY = Path(__file__).resolve().parents[2]
TOOLS = REPOSITORY / "Tools" / "HangboardCAD"
DEFAULT_FREECAD = Path("/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd")
SOURCE_SUFFIX = ".FCStd"
# These audited sources intentionally contain faceted imported geometry. New
# faceted sources must be reviewed and added explicitly before publication.
FACETED_IMPORT_PACKAGES = frozenset({
    "soill-iron-palm-2",
    "soill-split-palm",
    "soill-training-tiles",
})


def source_backed_packages() -> list[str]:
    return sorted(
        path.parent.name
        for path in (REPOSITORY / "Hangboards").glob(f"*/*{SOURCE_SUFFIX}")
        if path.name == f"{path.parent.name}{SOURCE_SUFFIX}"
    )


def _run_build(package: str, destination: Path, freecad: Path, extra_path: str, presentation_id: str | None = None) -> None:
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
    if presentation_id is not None:
        arguments.extend(["--presentation", presentation_id])
    if package in FACETED_IMPORT_PACKAGES:
        arguments.append("--allow-faceted-import")
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
    package_root = REPOSITORY / "Hangboards" / package
    targets = source_targets(package_root / f"{package}{SOURCE_SUFFIX}")
    reports = []
    with tempfile.TemporaryDirectory(prefix=f"hangten-prepare-{package}-") as scratch:
        staging = Path(scratch) / "assets"
        for presentation_id, (asset_name, descriptor_name) in targets.items():
            committed_descriptor = package_root / "assets" / descriptor_name
            if not committed_descriptor.is_file():
                raise RuntimeError(f"{package}/{presentation_id} has no committed descriptor")
            committed = json.loads(committed_descriptor.read_text())
            _run_build(package, staging, freecad, extra_path, presentation_id if len(targets) > 1 else None)
            built_asset, built_descriptor = staging / asset_name, staging / descriptor_name
            if not built_asset.is_file() or not built_descriptor.is_file():
                raise RuntimeError(f"{package}/{presentation_id}: the build produced no asset/descriptor pair")
            derived = json.loads(built_descriptor.read_text())
            if derived != committed:
                raise RuntimeError(f"{package}/{presentation_id}: the compiled descriptor does not match the committed one; the source and descriptor have diverged")
            digest = sha256(built_asset)
            if derived.get("modelSHA256") != digest:
                raise RuntimeError(f"{package}/{presentation_id}: the compiled asset does not hash to the descriptor")
            reports.append((presentation_id, built_asset, built_descriptor, digest))
        # Validate all configurations before copying any of the delivered pairs.
        target = out / package / "assets"
        target.mkdir(parents=True, exist_ok=True)
        for _, asset, descriptor, _ in reports:
            shutil.copyfile(asset, target / asset.name)
            shutil.copyfile(descriptor, target / descriptor.name)
        return {"package": package, "assetSHA256": reports[0][3],
                "bytes": sum(asset.stat().st_size for _, asset, _, _ in reports),
                "out": str((target / reports[0][1].name).relative_to(out)),
                "presentations": [{"id": identifier, "assetSHA256": digest, "asset": asset.name}
                                  for identifier, asset, _, digest in reports]}


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
