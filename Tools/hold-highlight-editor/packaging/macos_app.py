#!/usr/bin/env python3
"""Bundle the native Workbench shell with its embedded backend runtime."""

from __future__ import annotations

import os
import plistlib
import shutil
import stat
import struct
import sys
import tempfile
from argparse import ArgumentParser, Namespace
from pathlib import Path


_SHELL_EXECUTABLE_NAME = "HangboardWorkbench"
_RUNTIME_EXECUTABLE_NAME = "hangboard-workbench"
_RUNTIME_RESOURCE_NAME = "workbench-runtime"
_ARM64_CPU_TYPE = 0x0100000C
_THIN_64_MAGIC = 0xFEEDFACF
_FAT_MAGICS = {b"\xca\xfe\xba\xbe": 20, b"\xca\xfe\xba\xbf": 32}


class MacOSAppError(ValueError):
    """A macOS app-bundle input does not meet the release contract."""


def _is_arm64_macho(executable: Path) -> bool:
    with executable.open("rb") as source:
        header = source.read(8)
        if len(header) < 8:
            return False
        magic, cpu_type = struct.unpack("<II", header)
        if magic == _THIN_64_MAGIC:
            return cpu_type == _ARM64_CPU_TYPE
        architecture_size = _FAT_MAGICS.get(header[:4])
        if architecture_size is None:
            return False
        architecture_count = struct.unpack(">I", header[4:8])[0]
        for _ in range(architecture_count):
            architecture = source.read(architecture_size)
            if len(architecture) != architecture_size:
                return False
            if struct.unpack(">I", architecture[:4])[0] == _ARM64_CPU_TYPE:
                return True
    return False


def _validate_shell(shell: Path) -> None:
    try:
        mode = shell.stat().st_mode
    except OSError as error:
        raise MacOSAppError(f"shell executable is unavailable: {shell}") from error
    if not stat.S_ISREG(mode):
        raise MacOSAppError("shell executable must be a regular file")
    if not mode & stat.S_IXUSR:
        raise MacOSAppError("shell executable must be executable")
    if not _is_arm64_macho(shell):
        raise MacOSAppError("shell executable must be an arm64 Mach-O file")


def _validate_runtime(runtime_dir: Path) -> None:
    try:
        mode = runtime_dir.stat().st_mode
    except OSError as error:
        raise MacOSAppError(f"runtime directory is unavailable: {runtime_dir}") from error
    if not stat.S_ISDIR(mode) or runtime_dir.is_symlink():
        raise MacOSAppError("runtime directory must be a directory")

    executable = runtime_dir / _RUNTIME_EXECUTABLE_NAME
    try:
        executable_mode = executable.stat().st_mode
    except OSError as error:
        raise MacOSAppError(
            f"runtime executable is unavailable: {executable}"
        ) from error
    if not stat.S_ISREG(executable_mode) or executable.is_symlink():
        raise MacOSAppError("runtime executable must be a regular file")
    if not executable_mode & stat.S_IXUSR:
        raise MacOSAppError("runtime executable must be executable")


def _validate_output(output: Path, version: str) -> None:
    if output.suffix != ".app":
        raise MacOSAppError("output must be a .app bundle")
    if not output.parent.is_dir():
        raise MacOSAppError("output parent directory must exist")
    if output.is_symlink():
        raise MacOSAppError("output must not be a symbolic link")
    if output.exists() and not output.is_dir():
        raise MacOSAppError("existing output must be a directory")
    if not version or version != version.strip() or any(ord(char) < 32 for char in version):
        raise MacOSAppError("version must be a non-empty printable value")


def _metadata(version: str) -> dict[str, str]:
    return {
        "CFBundleIdentifier": "com.hangten.hangboard-workbench",
        "CFBundleName": "Hangboard Workbench",
        "CFBundleExecutable": _SHELL_EXECUTABLE_NAME,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
    }


def _build_bundle(
    shell: Path, runtime_dir: Path, output: Path, version: str
) -> Path:
    """Create a complete app bundle before replacing an existing output."""
    _validate_shell(shell)
    _validate_runtime(runtime_dir)
    _validate_output(output, version)

    staging_root = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    staged_bundle = staging_root / output.name
    backup_root: Path | None = None
    backup_path: Path | None = None
    backup_can_be_removed = True
    try:
        macos_directory = staged_bundle / "Contents" / "MacOS"
        macos_directory.mkdir(parents=True)
        shutil.copy2(shell, macos_directory / _SHELL_EXECUTABLE_NAME)
        resources_directory = staged_bundle / "Contents" / "Resources"
        resources_directory.mkdir()
        shutil.copytree(
            runtime_dir,
            resources_directory / _RUNTIME_RESOURCE_NAME,
            copy_function=shutil.copy2,
            symlinks=True,
        )
        with (staged_bundle / "Contents" / "Info.plist").open("wb") as destination:
            plistlib.dump(_metadata(version), destination, fmt=plistlib.FMT_XML, sort_keys=False)

        if output.exists():
            backup_root = Path(
                tempfile.mkdtemp(prefix=f".{output.name}.backup-", dir=output.parent)
            )
            backup_path = backup_root / output.name
            os.replace(output, backup_path)
            backup_can_be_removed = False
        try:
            os.replace(staged_bundle, output)
        except OSError:
            if backup_path is not None:
                os.replace(backup_path, output)
            backup_can_be_removed = True
            raise
        backup_can_be_removed = True
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)
        if backup_root is not None and backup_can_be_removed:
            shutil.rmtree(backup_root, ignore_errors=True)
    return output


def _arguments(arguments: list[str] | None = None) -> Namespace:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--shell", required=True, type=Path)
    parser.add_argument("--runtime-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--version", required=True)
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    parsed = _arguments(arguments)
    try:
        output = _build_bundle(
            parsed.shell,
            parsed.runtime_dir,
            parsed.output,
            parsed.version,
        )
    except MacOSAppError as error:
        print(f"Hangboard Workbench app bundle: {error}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
