"""Prove that a committed runtime asset provably comes from its committed source.

For every board that carries a CAD authoring source, this recompiles the model in
a fresh FreeCAD process and requires the result to be byte-identical to the
committed `assets/primary.usdz`, and the derived descriptor to equal the committed
`assets/primary.model.json`.

This is the guard that lets the USDZ be treated as a build output rather than a
hand-maintained artifact. Until it passes on a given platform, that platform must
not compile the asset for delivery, because the app hash-checks the delivered
bytes against the descriptor's `modelSHA256` and rejects the package on mismatch.

Run with the host interpreter; FreeCAD is invoked as a subprocess.

    python3 Tools/HangboardCAD/verify_reproducible.py            # all source-backed boards
    python3 Tools/HangboardCAD/verify_reproducible.py --package lattice-triple-rung
    python3 Tools/HangboardCAD/verify_reproducible.py --keep-rebuild <dir>

`--keep-rebuild` copies every rebuilt pair to `<dir>/<package>/assets/`
(`primary.usdz`, `primary.model.json`), mirroring `Hangboards/`, whether or not it
matched. It never changes the verdict or the exit status.
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


def source_backed_packages() -> list[str]:
    return sorted(
        path.parent.name
        for path in (REPOSITORY / "Hangboards").glob("*/*.FCStd")
        if path.name == f"{path.parent.name}.FCStd"
    )


def compile_into(package: str, destination: Path, freecad: Path, extra_path: str) -> None:
    """Run one board's build into a scratch directory, in a fresh process.

    FreeCAD's launcher consumes unrecognised options before the script sees them,
    so the arguments are embedded in a generated wrapper.
    """
    destination.mkdir(parents=True, exist_ok=True)
    wrapper = destination / "_build.py"
    expected = [
        "--package", package,
        "--source", str(REPOSITORY / "Hangboards" / package / f"{package}.FCStd"),
        "--assets", str(destination),
    ]
    wrapper.write_text(
        "import sys, traceback\n"
        f"path = {str(TOOLS / 'compile_board.py')!r}\n"
        f"sys.argv = [path] + {expected!r}\n"
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


def verify(
    package: str, freecad: Path, extra_path: str, keep: Path | None = None
) -> dict:
    committed_dir = REPOSITORY / "Hangboards" / package / "assets"
    committed_asset = committed_dir / "primary.usdz"
    committed_descriptor = committed_dir / "primary.model.json"
    if not committed_asset.is_file():
        raise RuntimeError(f"{package} has a source but no committed asset to verify against")

    with tempfile.TemporaryDirectory(prefix=f"hangten-repro-{package}-") as scratch:
        destination = Path(scratch) / "assets"
        compile_into(package, destination, freecad, extra_path)
        rebuilt_asset = destination / "primary.usdz"
        rebuilt_descriptor = destination / "primary.model.json"
        if not rebuilt_asset.is_file() or not rebuilt_descriptor.is_file():
            raise RuntimeError(f"{package}: the rebuild produced no asset/descriptor pair")

        if keep is not None:
            kept = keep / package / "assets"
            kept.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(rebuilt_asset, kept / "primary.usdz")
            shutil.copyfile(rebuilt_descriptor, kept / "primary.model.json")

        committed_sha = sha256(committed_asset)
        rebuilt_sha = sha256(rebuilt_asset)
        asset_matches = committed_sha == rebuilt_sha

        committed_json = json.loads(committed_descriptor.read_text())
        rebuilt_json = json.loads(rebuilt_descriptor.read_text())
        descriptor_matches = committed_json == rebuilt_json

        recorded = committed_json.get("modelSHA256")
        binds_to_committed = recorded == committed_sha

        # The app trusts the descriptor's modelSHA256, so the descriptor must
        # bind to the bytes that actually ship, independently of the rebuild.
        return {
            "package": package,
            "assetMatches": asset_matches,
            "descriptorMatches": descriptor_matches,
            "descriptorBindsCommittedAsset": binds_to_committed,
            "committedAssetSHA256": committed_sha,
            "rebuiltAssetSHA256": rebuilt_sha,
            "bytes": committed_asset.stat().st_size,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", action="append", default=None)
    parser.add_argument("--freecad", type=Path, default=DEFAULT_FREECAD)
    parser.add_argument(
        "--extra-python-path",
        default=os.environ.get("HANGTEN_CAD_PYTHONPATH", ""),
        help="site directory containing pxr, supplied to FreeCAD's interpreter",
    )
    parser.add_argument(
        "--keep-rebuild",
        type=Path,
        default=None,
        help="copy each rebuilt asset/descriptor pair to <dir>/<package>/assets/",
    )
    arguments = parser.parse_args(argv)

    packages = arguments.package or source_backed_packages()
    if not packages:
        print("no source-backed boards found; nothing to verify")
        return 0
    if not arguments.freecad.is_file():
        print(f"pinned FreeCAD is not installed at {arguments.freecad}", file=sys.stderr)
        return 2

    reports = []
    failures = []
    for package in packages:
        try:
            report = verify(
                package,
                arguments.freecad,
                arguments.extra_python_path,
                arguments.keep_rebuild,
            )
        except RuntimeError as error:
            failures.append(f"{package}: {error}")
            continue
        reports.append(report)
        status = (
            "reproducible"
            if report["assetMatches"] and report["descriptorMatches"]
            and report["descriptorBindsCommittedAsset"]
            else "MISMATCH"
        )
        print(
            f"  {package}: {status}  asset {report['committedAssetSHA256'][:16]}"
            f" vs rebuild {report['rebuiltAssetSHA256'][:16]}"
        )
        if status == "MISMATCH":
            failures.append(
                f"{package}: assetMatches={report['assetMatches']} "
                f"descriptorMatches={report['descriptorMatches']} "
                f"descriptorBindsCommittedAsset={report['descriptorBindsCommittedAsset']}"
            )

    print(json.dumps({"verified": reports, "failures": failures}, indent=2, sort_keys=True))
    if failures:
        print(f"\n{len(failures)} board(s) failed reproducibility:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(f"\nall {len(reports)} source-backed board(s) rebuild byte-identically")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())