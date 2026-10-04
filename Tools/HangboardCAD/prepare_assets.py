"""Compile every source-backed board into a directory of runtime assets.

The FCStd and optional authoring sidecars are the only inputs. USDZ files,
model descriptors, and rope-physics descriptors are generated together; no
previous export is needed. Hash-bound suspension sidecars still reject a
changed model until its geometry and cord setup have been reviewed.

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
import use_hangboard_packages  # noqa: F401
from hangboard_packages import cad_source

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
        f"sys.path[:0] = {extra_path.split(os.pathsep) if extra_path else []!r}\n"
        f"path = {str(TOOLS / 'compile_board.py')!r}\n"
        f"sys.argv = [path] + {arguments!r}\n"
        "try:\n"
        "    import FreeCAD as App\n"
        "    from pxr import Usd\n"
        "    if tuple(App.Version()[:3]) != ('1', '1', '3'):\n"
        "        raise RuntimeError('board builds require pinned FreeCAD 1.1.3')\n"
        "    if Usd.GetVersion() != (0, 26, 8):\n"
        "        raise RuntimeError('board builds require pinned OpenUSD 26.8')\n"
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


def publish_assets(source: Path, target: Path, names: set[str] | None = None) -> None:
    """Install a validated runtime set and prune superseded generated files."""
    def generated(path: Path) -> bool:
        return path.is_file() and path.name.endswith((".usdz", ".model.json", ".physics.json"))

    names = names if names is not None else {path.name for path in source.iterdir() if generated(path)}
    target.mkdir(parents=True, exist_ok=True)
    for name in sorted(names):
        shutil.copyfile(source / name, target / name)
    for path in target.iterdir():
        if generated(path) and path.name not in names:
            path.unlink()


def prepare(package: str, out: Path, freecad: Path, extra_path: str) -> dict:
    package_root = REPOSITORY / "Hangboards" / package
    source = package_root / f"{package}{SOURCE_SUFFIX}"
    targets = source_targets(source)
    source_digest = sha256(source)
    reports = []
    scratch_root = REPOSITORY / ".context"
    scratch_root.mkdir(exist_ok=True)
    owner = Path(os.environ.get("PASEO_WORKTREE_PATH", str(REPOSITORY))).name
    with tempfile.TemporaryDirectory(prefix=f"{owner}-prepare-{package}-", dir=scratch_root) as scratch:
        staged_package = Path(scratch) / package
        staging = staged_package / "assets"
        generated_files = set()
        for presentation_id, (asset_name, descriptor_name) in targets.items():
            _run_build(package, staging, freecad, extra_path, presentation_id if len(targets) > 1 else None)
            built_asset, built_descriptor = staging / asset_name, staging / descriptor_name
            if not built_asset.is_file() or not built_descriptor.is_file():
                raise RuntimeError(f"{package}/{presentation_id}: the build produced no asset/descriptor pair")
            derived = json.loads(built_descriptor.read_text())
            digest = sha256(built_asset)
            if derived.get("modelSHA256") != digest:
                raise RuntimeError(f"{package}/{presentation_id}: the compiled asset does not hash to the descriptor")
            generated_files.update({asset_name, descriptor_name})
            if (package_root / "rope-physics.json").is_file():
                physics_path = staging / "primary.physics.json"
                if not physics_path.is_file():
                    raise RuntimeError(f"{package}: the build produced no rope-physics descriptor")
                if json.loads(physics_path.read_text()).get("modelSHA256") != digest:
                    raise RuntimeError(f"{package}: rope physics does not match its compiled asset")
                if "primary.physics.json" in generated_files:
                    raise RuntimeError(f"{package}: multiple presentations cannot share a rope-physics descriptor")
                generated_files.add("primary.physics.json")
            reports.append((presentation_id, built_asset, built_descriptor, digest))
        if sha256(source) != source_digest:
            raise RuntimeError(f"{package}: compiling modified the authored source")
        if (package_root / "suspension.json").is_file():
            shutil.copyfile(package_root / "suspension.json", staged_package / "suspension.json")
            # Check every sidecar entry against the freshly built descriptors,
            # not against any stale export left in the source workspace.
            cad_source.merge_suspension_sidecar(cad_source.load_board(source), staged_package)
        # Validate all configurations before copying any of the delivered pairs.
        target = out / package / "assets"
        publish_assets(staging, target, generated_files)
        return {"package": package, "assetSHA256": reports[0][3],
                "bytes": sum(asset.stat().st_size for _, asset, _, _ in reports),
                "out": str((target / reports[0][1].name).relative_to(out)),
                "presentations": [{"id": identifier, "assetSHA256": digest, "asset": asset.name}
                                  for identifier, asset, _, digest in reports]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--package", action="append", default=None)
    parser.add_argument("--freecad", type=Path, default=Path(os.environ.get("HANGTEN_FREECAD_CMD", str(DEFAULT_FREECAD))))
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
        except (RuntimeError, ValueError, OSError) as error:
            failures.append(f"{package}: {error}")
            continue
        prepared.append(report)
        print(f"  {package}: {report['bytes']} bytes  {report['assetSHA256'][:16]}", flush=True)

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
