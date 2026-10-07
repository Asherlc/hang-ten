"""Compile every source-backed board into a directory of runtime assets.

The flat FCStd sources contain every authored input. USDZ files, model/physics
descriptors and solved suspension artifacts are generated together; no
previous export or cord route cache is needed.

    python3 Tools/HangboardCAD/prepare_assets.py --out <directory>
    python3 Tools/HangboardCAD/prepare_assets.py --out <dir> --package <slug>

Writes `<out>/<package>/assets/primary.usdz` and `.../primary.model.json`.
Run with the host interpreter; FreeCAD is invoked as a subprocess.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from presentation_targets import source_targets
import use_hangboard_packages  # noqa: F401
from hangboard_packages import cad_source

REPOSITORY = Path(__file__).resolve().parents[2]
TOOLS = REPOSITORY / "Tools" / "HangboardCAD"
DEFAULT_FREECAD = Path("/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd")
SOURCE_SUFFIX = ".FCStd"
CACHE_VERSION = 1
_PROCESSES: set[subprocess.Popen] = set()
_PROCESS_LOCK = threading.Lock()
_STOPPING = threading.Event()
# These audited sources intentionally contain faceted imported geometry. New
# faceted sources must be reviewed and added explicitly before publication.
FACETED_IMPORT_PACKAGES = frozenset({
    "soill-iron-palm-2",
    "soill-split-palm",
    "soill-training-tiles",
})


def source_backed_packages() -> list[str]:
    return sorted(
        path.stem
        for path in (REPOSITORY / "Hangboards").glob(f"*{SOURCE_SUFFIX}")
    )


def compiler_fingerprint() -> str:
    """Hash every retained compiler input, including non-Python depth audits."""
    paths = [REPOSITORY / "scripts/build-board-assets.sh", REPOSITORY / "scripts/install-freecad.sh"]
    for directory in ("Tools/HangboardCAD", "Tools/HangboardModels", "Tools/HangboardPackages/src"):
        paths.extend(path for path in (REPOSITORY / directory).rglob("*")
                     if path.suffix in {".py", ".json", ".txt"}
                     and not any(part in {"tests", "__pycache__"} or part.endswith(".egg-info")
                                 for part in path.relative_to(REPOSITORY).parts))
    digest = hashlib.sha256(f"runtime-assets-cache-{CACHE_VERSION};FreeCAD-1.1.3;USD-26.8".encode())
    for path in sorted(set(paths)):
        if path.is_file():
            digest.update(path.relative_to(REPOSITORY).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def shard_packages(packages: list[str], index: int, count: int) -> list[str]:
    """A new board cannot reshuffle the cached membership of existing boards."""
    if count < 1 or not 0 <= index < count:
        raise ValueError("shard index must be between zero and shard count minus one")
    return [package for package in packages
            if int(hashlib.sha256(package.encode()).hexdigest(), 16) % count == index]


def _run_build(package: str, destination: Path, freecad: Path, extra_path: str, presentation_id: str | None = None) -> None:
    arguments = [
        "--package", package,
        "--source", str(REPOSITORY / "Hangboards" / f"{package}{SOURCE_SUFFIX}"),
        "--assets", str(destination),
    ]
    if presentation_id is not None:
        arguments.extend(["--presentation", presentation_id])
    if package in FACETED_IMPORT_PACKAGES:
        arguments.append("--allow-faceted-import")
    _run_native(package, destination, freecad, extra_path, "compile_board.py", arguments)


def _run_suspension(package: str, destination: Path, freecad: Path, extra_path: str) -> None:
    _run_native(package, destination, freecad, extra_path, "compile_suspension.py", [
        "--source", str(REPOSITORY / "Hangboards" / f"{package}{SOURCE_SUFFIX}"),
        "--assets", str(destination),
    ])


def _run_native(package: str, destination: Path, freecad: Path, extra_path: str,
                script_name: str, arguments: list[str]) -> None:
    """Run one board's build into a scratch directory, in a fresh process.

    FreeCAD's launcher consumes unrecognised options before the script ever sees
    them, so the arguments are embedded in a generated wrapper.
    """
    destination.mkdir(parents=True, exist_ok=True)
    wrapper = destination / f"_{script_name}"
    wrapper.write_text(
        "import sys, traceback\n"
        f"sys.path[:0] = {extra_path.split(os.pathsep) if extra_path else []!r}\n"
        f"path = {str(TOOLS / script_name)!r}\n"
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
    # Two workers must not each create a whole runner's worth of BLAS threads.
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        environment[variable] = "1"
    started = time.monotonic()
    print(f"  {package}: starting {script_name} {' '.join(arguments[-2:])}", flush=True)
    with _PROCESS_LOCK:
        if _STOPPING.is_set():
            raise RuntimeError("compilation was cancelled")
        process = subprocess.Popen([str(freecad), str(wrapper)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env=environment, cwd=str(REPOSITORY))
        _PROCESSES.add(process)
        ownership = destination / f"_{script_name}.pid"
        ownership.write_text(str(process.pid))
    try:
        stdout, stderr = process.communicate()
    finally:
        with _PROCESS_LOCK:
            _PROCESSES.discard(process)
        ownership.unlink(missing_ok=True)
    print(f"  {package}: {script_name} finished in {time.monotonic() - started:.1f}s", flush=True)
    if process.returncode != 0:
        raise RuntimeError(
            f"compiling {package} failed (exit {process.returncode})\n"
            f"{stdout[-2000:]}{stderr[-2000:]}"
        )


def _stop_native_processes() -> None:
    _STOPPING.set()
    with _PROCESS_LOCK:
        processes = list(_PROCESSES)
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish_assets(source: Path, target: Path, names: set[str] | None = None) -> None:
    """Install a validated runtime set and prune superseded generated files."""
    def generated(path: Path) -> bool:
        return path.is_file() and (path.name == "suspension.json" or
                                  path.name.endswith((".usdz", ".model.json", ".physics.json")))

    names = names if names is not None else {path.name for path in source.iterdir() if generated(path)}
    target.mkdir(parents=True, exist_ok=True)
    for name in sorted(names):
        shutil.copyfile(source / name, target / name)
    for path in target.iterdir():
        if generated(path) and path.name not in names:
            path.unlink()


def validate_assets(package: str, assets: Path) -> tuple[dict, set[str]]:
    """Validate the complete current CAD-derived inventory before publishing it."""
    source = REPOSITORY / "Hangboards" / f"{package}{SOURCE_SUFFIX}"
    targets = source_targets(source)
    source_digest = sha256(source)
    physics = cad_source.load_rope_physics_authoring(source) is not None
    names: set[str] = set()
    presentations = []
    total_bytes = 0
    for identifier, (asset_name, descriptor_name) in targets.items():
        asset, descriptor = assets / asset_name, assets / descriptor_name
        if any(not path.is_file() or path.is_symlink() for path in (asset, descriptor)):
            raise RuntimeError(f"{package}/{identifier}: the build produced no regular asset/descriptor pair")
        digest = sha256(asset)
        derived = json.loads(descriptor.read_text())
        if not isinstance(derived, dict) or derived.get("modelSHA256") != digest:
            raise RuntimeError(f"{package}/{identifier}: the compiled asset does not hash to the descriptor")
        names.update({asset_name, descriptor_name})
        total_bytes += asset.stat().st_size
        presentations.append({"id": identifier, "assetSHA256": digest, "asset": asset_name})
        if physics:
            path = assets / "primary.physics.json"
            if len(targets) != 1:
                raise RuntimeError(f"{package}: multiple presentations cannot share a rope-physics descriptor")
            if not path.is_file() or path.is_symlink():
                raise RuntimeError(f"{package}: the build produced no rope-physics descriptor")
            derived = json.loads(path.read_text())
            if (not isinstance(derived, dict) or derived.get("modelSHA256") != digest
                    or derived.get("sourceSHA256") != source_digest):
                raise RuntimeError(f"{package}: rope physics does not match its compiled asset and CAD source")
            names.add(path.name)
    if cad_source.load_suspension_authoring(source) is not None:
        path = assets / "suspension.json"
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"{package}: the build produced no solved suspension")
        cad_source.merge_suspension_artifact(cad_source.load_board(source), assets.parent, source)
        names.add(path.name)
    return {"package": package, "sourceSHA256": source_digest, "assetSHA256": presentations[0]["assetSHA256"],
            "bytes": total_bytes, "out": f"{package}/assets/{presentations[0]['asset']}",
            "presentations": presentations}, names


def _restore_cache(package: str, cache_dir: Path, compiler: str) -> tuple[dict, set[str]] | None:
    entry = cache_dir / package
    try:
        manifest = entry / "manifest.json"
        if entry.is_symlink() or manifest.is_symlink() or (entry / "assets").is_symlink():
            return None
        recorded = json.loads(manifest.read_text())
        if (not isinstance(recorded, dict) or not isinstance(recorded.get("files"), dict)
                or recorded.get("version") != CACHE_VERSION or recorded.get("compilerSHA256") != compiler
                or recorded.get("platform") != [sys.platform, platform.machine()]):
            return None
        source = REPOSITORY / "Hangboards" / f"{package}{SOURCE_SUFFIX}"
        if recorded.get("sourceSHA256") != sha256(source):
            return None
        report, names = validate_assets(package, entry / "assets")
        if set(recorded["files"]) != names or {path.name for path in (entry / "assets").iterdir()} != names:
            return None
        if any((entry / "assets" / name).is_symlink() or
               recorded["files"][name] != sha256(entry / "assets" / name) for name in names):
            return None
        return report, names
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        return None


def _store_cache(package: str, cache_dir: Path, compiler: str, assets: Path, report: dict, names: set[str]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    owner = Path(os.environ.get("PASEO_WORKTREE_PATH", str(REPOSITORY))).name
    with tempfile.TemporaryDirectory(prefix=f"{owner}-cache-{package}-", dir=cache_dir) as temporary:
        entry = Path(temporary) / package
        publish_assets(assets, entry / "assets", names)
        (entry / "manifest.json").write_text(json.dumps({
            "version": CACHE_VERSION, "compilerSHA256": compiler, "sourceSHA256": report["sourceSHA256"],
            "platform": [sys.platform, platform.machine()],
            "files": {name: sha256(assets / name) for name in sorted(names)},
        }, indent=2, sort_keys=True) + "\n")
        target = cache_dir / package
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
        entry.rename(target)


def prepare(package: str, out: Path, freecad: Path, extra_path: str, *, cache_dir: Path | None = None,
            cache_only: bool = False, compiler: str | None = None) -> dict:
    if _STOPPING.is_set():
        raise RuntimeError("compilation was cancelled")
    package_root = REPOSITORY / "Hangboards" / package
    source = package_root.parent / f"{package}{SOURCE_SUFFIX}"
    targets = source_targets(source)
    source_digest = sha256(source)
    compiler = compiler or compiler_fingerprint()
    started = time.monotonic()
    if cache_dir is not None:
        cached = _restore_cache(package, cache_dir, compiler)
        if cached is not None:
            report, names = cached
            publish_assets(cache_dir / package / "assets", out / package / "assets", names)
            return dict(report, cacheHit=True, seconds=round(time.monotonic() - started, 3))
    if cache_only:
        raise RuntimeError(f"{package}: no valid runtime asset cache")
    scratch_root = REPOSITORY / ".context"
    scratch_root.mkdir(exist_ok=True)
    owner = Path(os.environ.get("PASEO_WORKTREE_PATH", str(REPOSITORY))).name
    with tempfile.TemporaryDirectory(prefix=f"{owner}-prepare-{package}-", dir=scratch_root) as scratch:
        staged_package = Path(scratch) / package
        staging = staged_package / "assets"
        for presentation_id, (asset_name, descriptor_name) in targets.items():
            _run_build(package, staging, freecad, extra_path, presentation_id if len(targets) > 1 else None)
        if sha256(source) != source_digest:
            raise RuntimeError(f"{package}: compiling modified the authored source")
        if cad_source.load_suspension_authoring(source) is not None:
            _run_suspension(package, staging, freecad, extra_path)
        if sha256(source) != source_digest:
            raise RuntimeError(f"{package}: compiling modified the authored source")
        # Validate all configurations before copying any of the delivered pairs.
        report, generated_files = validate_assets(package, staging)
        target = out / package / "assets"
        publish_assets(staging, target, generated_files)
        if cache_dir is not None:
            _store_cache(package, cache_dir, compiler, staging, report, generated_files)
        return dict(report, cacheHit=False, seconds=round(time.monotonic() - started, 3))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--package", action="append", default=None)
    parser.add_argument("--jobs", type=int, default=1, help="maximum independent native compiler processes")
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--cache-only", action="store_true", help="restore validated hits without invoking native tools")
    parser.add_argument("--cache-key", action="store_true", help="emit GitHub cache keys without compiling")
    parser.add_argument("--report", type=Path, help="write the complete shard report for catalog assembly")
    parser.add_argument("--freecad", type=Path, default=Path(os.environ.get("HANGTEN_FREECAD_CMD", str(DEFAULT_FREECAD))))
    parser.add_argument(
        "--extra-python-path",
        default=os.environ.get("HANGTEN_CAD_PYTHONPATH", ""),
        help="site directory containing pxr, supplied to FreeCAD's interpreter",
    )
    arguments = parser.parse_args(argv)

    all_packages = source_backed_packages()
    packages = arguments.package or all_packages
    if len(set(packages)) != len(packages) or set(packages) - set(all_packages):
        parser.error("packages must be distinct, current CAD source names")
    if arguments.jobs < 1:
        parser.error("--jobs must be positive")
    try:
        packages = shard_packages(packages, arguments.shard_index, arguments.shard_count)
    except ValueError as error:
        parser.error(str(error))
    compiler = compiler_fingerprint()
    if arguments.cache_key:
        owner = Path(os.environ.get("PASEO_WORKTREE_PATH", str(REPOSITORY))).name
        prefix = (f"{owner}-boards-v{CACHE_VERSION}-{sys.platform}-{platform.machine()}-{compiler}-"
                  f"shard-{arguments.shard_index}-of-{arguments.shard_count}-")
        sources = [(package, sha256(REPOSITORY / "Hangboards" / f"{package}{SOURCE_SUFFIX}")) for package in packages]
        print(f"cache-prefix={prefix}")
        print(f"cache-key={prefix}{hashlib.sha256(json.dumps(sources).encode()).hexdigest()}")
        print(f"owner={owner}")
        return 0
    arguments.out.mkdir(parents=True, exist_ok=True)
    if packages and arguments.cache_dir is None and not arguments.freecad.is_file() and not arguments.cache_only:
        print(f"pinned FreeCAD is not installed at {arguments.freecad}", file=sys.stderr)
        return 2

    prepared: list[dict] = []
    failures: list[str] = []
    _STOPPING.clear()
    def cancel(signum, frame):
        _stop_native_processes()
        raise KeyboardInterrupt
    previous_handlers = {signum: signal.signal(signum, cancel) for signum in (signal.SIGTERM, signal.SIGINT)}
    try:
        with ThreadPoolExecutor(max_workers=arguments.jobs) as executor:
            futures = {executor.submit(prepare, package, arguments.out, arguments.freecad, arguments.extra_python_path,
                                       cache_dir=arguments.cache_dir, cache_only=arguments.cache_only,
                                       compiler=compiler): package for package in packages}
            for future in as_completed(futures):
                package = futures[future]
                try:
                    report = future.result()
                except (RuntimeError, ValueError, OSError) as error:
                    failures.append(f"{package}: {error}")
                    print(f"  {package}: FAILED: {error}", file=sys.stderr, flush=True)
                    continue
                prepared.append(report)
                print(f"  {package}: {'cache hit' if report['cacheHit'] else 'compiled'} in {report['seconds']:.1f}s; "
                      f"{report['bytes']} bytes  {report['assetSHA256'][:16]}", flush=True)
    except KeyboardInterrupt:
        _stop_native_processes()
        return 130
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPOSITORY, text=True).strip()
    summary = {"schemaVersion": CACHE_VERSION, "compilerSHA256": compiler, "revision": revision,
               "shardIndex": arguments.shard_index, "shardCount": arguments.shard_count,
               "prepared": sorted(prepared, key=lambda report: report["package"]), "failures": sorted(failures)}
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if failures:
        print(f"\n{len(failures)} board(s) failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(f"\nprepared {len(prepared)} board(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
