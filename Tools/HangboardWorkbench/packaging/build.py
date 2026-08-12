#!/usr/bin/env python3
"""Build the Hangboard Workbench as a reproducible arm64 macOS runtime."""

from __future__ import annotations

import os
import platform
import re
import stat
import sys
import tempfile
from argparse import ArgumentParser, Namespace
from pathlib import Path


_EDITOR_MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_EDITOR_MODULE_ROOT))

import workbench_assets  # noqa: E402


_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")


class BuildError(ValueError):
    """A deterministic-build precondition was not met."""


def _editor_root(repository_root: Path) -> Path:
    return repository_root / "Tools" / "HangboardWorkbench"


def _onboarding_root(repository_root: Path) -> Path:
    return repository_root / "Tools" / "HangboardPipeline"


def _validate_source_layout(repository_root: Path) -> tuple[Path, Path]:
    editor_root = _editor_root(repository_root)
    onboarding_root = _onboarding_root(repository_root)
    required_files = [editor_root / "workbench_binary.py"] + [
        editor_root / asset for asset in workbench_assets.STATIC_ASSETS
    ]
    missing = [path for path in required_files if not path.is_file()]
    if missing:
        raise BuildError(f"required runtime input is missing: {missing[0]}")
    if not (onboarding_root / "src" / "hangboard_vectorizer").is_dir():
        raise BuildError("hangboard_vectorizer source package is missing")
    return editor_root, onboarding_root


def _write_build_metadata(metadata_root: Path, commit: str) -> Path:
    if _COMMIT_PATTERN.fullmatch(commit) is None:
        raise BuildError("commit must be an exact 40-character lowercase SHA")

    metadata_root.mkdir(parents=True, exist_ok=True)
    destination = metadata_root / "build-commit.txt"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="ascii",
        dir=metadata_root,
        prefix=".build-commit-",
        delete=False,
    ) as output:
        output.write(f"{commit}\n")
        output.flush()
        os.fsync(output.fileno())
        temporary_path = Path(output.name)
    os.replace(temporary_path, destination)
    return destination


def _add_data_argument(source: Path, destination: str = ".") -> list[str]:
    return ["--add-data", f"{source}{os.pathsep}{destination}"]


def _pyinstaller_arguments(
    repository_root: Path,
    metadata_root: Path,
    dist_dir: Path,
    work_dir: Path,
    codesign_identity: str | None = None,
) -> list[str]:
    """Return the complete, explicit runtime manifest for PyInstaller."""
    if codesign_identity is not None and not codesign_identity.strip():
        raise BuildError("codesign identity must be non-empty when supplied")

    editor_root, onboarding_root = _validate_source_layout(repository_root)
    metadata_path = metadata_root / "build-commit.txt"
    if not metadata_path.is_file():
        raise BuildError("build metadata is missing")

    arguments = [
        str(editor_root / "workbench_binary.py"),
        "--name",
        "hangboard-workbench",
        "--onedir",
        "--noconfirm",
        "--clean",
        "--target-architecture",
        "arm64",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir / "pyinstaller"),
        "--specpath",
        str(work_dir / "spec"),
        "--paths",
        str(onboarding_root / "src"),
        "--hidden-import",
        "hangboard_vectorizer.workbench",
        "--hidden-import",
        "hangboard_vectorizer.workbench_store",
        "--hidden-import",
        "hangboard_vectorizer.board_library",
    ]
    if codesign_identity is not None:
        arguments.extend(["--codesign-identity", codesign_identity])
    for asset in workbench_assets.STATIC_ASSETS:
        arguments.extend(_add_data_argument(editor_root / asset))
    arguments.extend(_add_data_argument(metadata_path))
    return arguments


def _require_arm64_macos() -> None:
    if sys.platform != "darwin":
        raise BuildError("the workbench binary can only be built on macOS")
    if platform.machine().lower() != "arm64":
        raise BuildError("the workbench binary must be built on an arm64 machine")


def _require_expected_output(dist_dir: Path) -> Path:
    runtime = dist_dir / "hangboard-workbench"
    executable = runtime / "hangboard-workbench"
    try:
        runtime_mode = runtime.stat().st_mode
        executable_mode = executable.stat().st_mode
    except OSError as error:
        raise BuildError(
            "PyInstaller did not produce the expected onedir runtime executable"
        ) from error
    if not stat.S_ISDIR(runtime_mode) or runtime.is_symlink():
        raise BuildError("PyInstaller did not produce the expected onedir runtime")
    if not stat.S_ISREG(executable_mode) or not executable_mode & stat.S_IXUSR:
        raise BuildError(
            "PyInstaller did not produce the expected onedir runtime executable"
        )
    return runtime


def _build(
    repository_root: Path,
    commit: str,
    dist_dir: Path,
    work_dir: Path,
    codesign_identity: str | None = None,
) -> Path:
    _require_arm64_macos()
    metadata_root = work_dir / "metadata"
    _write_build_metadata(metadata_root, commit)
    arguments = _pyinstaller_arguments(
        repository_root,
        metadata_root,
        dist_dir,
        work_dir,
        codesign_identity=codesign_identity,
    )

    import PyInstaller.__main__

    PyInstaller.__main__.run(arguments)
    return _require_expected_output(dist_dir)


def _arguments(arguments: list[str] | None = None) -> Namespace:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--dist-dir", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--codesign-identity")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    parsed = _arguments(arguments)
    repository_root = Path(__file__).resolve().parents[3]
    try:
        executable = _build(
            repository_root=repository_root,
            commit=parsed.commit,
            dist_dir=parsed.dist_dir.expanduser().resolve(),
            work_dir=parsed.work_dir.expanduser().resolve(),
            codesign_identity=parsed.codesign_identity,
        )
    except BuildError as error:
        print(f"Hangboard Workbench build: {error}", file=sys.stderr)
        return 2
    print(executable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
